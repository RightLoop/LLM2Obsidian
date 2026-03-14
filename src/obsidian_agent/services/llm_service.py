"""LLM orchestration and offline fallbacks."""

from __future__ import annotations

from typing import Protocol

from obsidian_agent.domain.enums import ProposalType, SourceType
from obsidian_agent.domain.policies import classify_risk
from obsidian_agent.domain.schemas import (
    CaptureInput,
    NormalizedCapture,
    RelatedNoteCandidate,
    ReviewProposal,
)


class JsonLLMClient(Protocol):
    """Minimal contract for provider clients used by LLMService."""

    async def create_json_response(self, instructions: str, input_text: str) -> dict[str, object]:
        """Return structured JSON output."""


class LLMService:
    """Normalize inputs and generate proposals."""

    def __init__(self, client: JsonLLMClient | None = None) -> None:
        self.client = client

    async def run_structured_task(self, instructions: str, input_text: str) -> dict[str, object] | None:
        """Execute a structured generation task when a provider is available."""

        if not self.client:
            return None
        return await self.client.create_json_response(instructions=instructions, input_text=input_text)

    async def normalize_capture(self, payload: CaptureInput) -> NormalizedCapture:
        """Return a structured capture payload."""

        if self.client:
            raw = await self.run_structured_task(
                instructions=(
                    "Return JSON with keys: title, summary, entities, topics, tags, "
                    "decision, confidence, conflicts, key_points, raw_excerpt. "
                    "The decision field must be exactly one of: "
                    "new_note, append_candidate, merge_candidate, review_only."
                ),
                input_text=payload.text,
            )
            return NormalizedCapture.model_validate(self._sanitize_normalized_capture(raw, payload))

        title = payload.title or payload.text.splitlines()[0][:80] or "Untitled"
        text = payload.text.strip()
        words = text.split()
        summary = " ".join(words[:60]).strip()
        key_points = []
        for sentence in text.replace("\n", " ").split("."):
            sentence = sentence.strip()
            if sentence:
                key_points.append(sentence)
            if len(key_points) == 3:
                break
        tags = list(dict.fromkeys([token.strip(".,:;!?").lower() for token in words if len(token) > 5]))[:5]
        return NormalizedCapture(
            title=title,
            summary=summary,
            entities=[],
            topics=tags[:3],
            tags=tags,
            decision=ProposalType.NEW_NOTE,
            confidence=0.65 if payload.source_type != SourceType.URL else 0.72,
            conflicts=[],
            key_points=key_points,
            raw_excerpt=text[:500],
        )

    def _sanitize_normalized_capture(
        self, raw: dict[str, object], payload: CaptureInput
    ) -> dict[str, object]:
        """Coerce provider JSON into the local schema contract."""

        sanitized = dict(raw)
        text = payload.text.strip()
        title = payload.title or text.splitlines()[0][:80] or "Untitled"
        sanitized["title"] = str(sanitized.get("title") or title)
        sanitized["summary"] = str(sanitized.get("summary") or " ".join(text.split()[:60]).strip())
        sanitized["raw_excerpt"] = str(sanitized.get("raw_excerpt") or text[:500])
        sanitized["confidence"] = self._coerce_confidence(sanitized.get("confidence"))
        sanitized["decision"] = self._coerce_decision(sanitized.get("decision"))
        for field_name in ("entities", "topics", "tags", "conflicts", "key_points"):
            sanitized[field_name] = self._coerce_string_list(sanitized.get(field_name))
        sanitized["related_candidates"] = self._coerce_related_candidates(
            sanitized.get("related_candidates"),
        )
        return sanitized

    @staticmethod
    def _coerce_decision(value: object) -> str:
        allowed = {item.value for item in ProposalType}
        candidate = str(value or "").strip().lower()
        return candidate if candidate in allowed else ProposalType.NEW_NOTE.value

    @staticmethod
    def _coerce_confidence(value: object) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.5

    @staticmethod
    def _coerce_string_list(value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _coerce_related_candidates(self, value: object) -> list[dict[str, object]]:
        if not isinstance(value, list):
            return []
        items: list[dict[str, object]] = []
        for raw_item in value:
            if not isinstance(raw_item, dict):
                continue
            path = str(raw_item.get("path") or "").strip()
            reason = str(raw_item.get("reason") or "").strip() or "Related context"
            score = self._coerce_confidence(raw_item.get("score"))
            if path:
                items.append({"path": path, "reason": reason, "score": score})
        return items

    async def classify_integration_action(
        self, new_note: str, related_notes: list[RelatedNoteCandidate]
    ) -> ProposalType:
        """Classify the integration action."""

        if not related_notes:
            return ProposalType.NEW_NOTE
        if related_notes[0].score > 0.92:
            return ProposalType.MERGE_CANDIDATE
        if related_notes[0].score > 0.65:
            return ProposalType.APPEND_CANDIDATE
        return ProposalType.REVIEW_ONLY

    async def generate_link_suggestions(
        self, new_note: str, related_notes: list[RelatedNoteCandidate]
    ) -> list[RelatedNoteCandidate]:
        """Return related notes as link suggestions."""

        del new_note
        return related_notes[:5]

    async def generate_review_proposal(
        self,
        new_note_path: str,
        target_note_path: str | None,
        rationale: str,
        suggested_patch: str,
        proposal_type: ProposalType,
    ) -> ReviewProposal:
        """Build a review proposal."""

        risk_level = classify_risk(proposal_type)
        return ReviewProposal(
            proposal_type=proposal_type,
            risk_level=risk_level,
            title=f"Review for {new_note_path}",
            source_note_path=new_note_path,
            target_note_path=target_note_path,
            rationale=rationale,
            suggested_patch=suggested_patch,
            related_links=[],
        )

    async def generate_digest(self, note_set: list[str]) -> str:
        """Generate a small digest body."""

        snippets = [note[:200].replace("\n", " ") for note in note_set[:10]]
        lines = ["## Highlights"]
        for snippet in snippets:
            lines.append(f"- {snippet}")
        return "\n".join(lines)
