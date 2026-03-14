"""Structured error extraction for smart workflows."""

from __future__ import annotations

import logging

from obsidian_agent.domain.schemas import ErrorCaptureRequest, ErrorObject
from obsidian_agent.services.llm_service import LLMService
from obsidian_agent.utils.slugify import slugify

logger = logging.getLogger(__name__)


class ErrorExtractorService:
    """Extract a structured error object from a user submission."""

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service
        self.last_telemetry: dict[str, object] = {}

    async def extract(self, payload: ErrorCaptureRequest) -> ErrorObject:
        prompt_text = self._compose_input(payload)
        raw = await self.llm_service.run_structured_task(
            instructions=(
                "Return JSON with keys: title, language, error_signature, summary, root_cause, "
                "incorrect_assumption, evidence, related_concepts, tags, confidence. "
                "Keep the language field as the source language such as 'c'."
            ),
            input_text=prompt_text,
        )
        self.last_telemetry = self.llm_service.pop_telemetry()
        if self.last_telemetry:
            logger.info("smart_telemetry task=error_extract telemetry=%s", self.last_telemetry)
        if raw:
            return ErrorObject.model_validate(self._sanitize(raw, payload))
        return self._fallback(payload)

    def _compose_input(self, payload: ErrorCaptureRequest) -> str:
        return (
            f"Title: {payload.title or ''}\n"
            f"Language: {payload.language}\n"
            f"Prompt:\n{payload.prompt}\n\n"
            f"Code:\n{payload.code}\n\n"
            f"User analysis:\n{payload.user_analysis}\n"
        ).strip()

    def _sanitize(self, raw: dict[str, object], payload: ErrorCaptureRequest) -> dict[str, object]:
        fallback = self._fallback(payload)
        return {
            "title": str(raw.get("title") or fallback.title),
            "language": str(raw.get("language") or payload.language or "c"),
            "error_signature": str(raw.get("error_signature") or fallback.error_signature),
            "summary": str(raw.get("summary") or fallback.summary),
            "root_cause": str(raw.get("root_cause") or fallback.root_cause),
            "incorrect_assumption": str(
                raw.get("incorrect_assumption") or fallback.incorrect_assumption
            ),
            "evidence": self._coerce_list(raw.get("evidence")) or fallback.evidence,
            "related_concepts": self._coerce_list(raw.get("related_concepts"))
            or fallback.related_concepts,
            "tags": self._coerce_list(raw.get("tags")) or fallback.tags,
            "confidence": self._coerce_confidence(raw.get("confidence")),
        }

    def _fallback(self, payload: ErrorCaptureRequest) -> ErrorObject:
        title = payload.title or self._infer_title(payload.prompt)
        signature = self._infer_signature(payload.prompt, payload.code, payload.user_analysis)
        concepts = self._infer_related_concepts(payload.prompt, payload.code, payload.user_analysis)
        evidence = [item for item in [payload.prompt.strip(), payload.user_analysis.strip()] if item][:2]
        return ErrorObject(
            title=title,
            language=payload.language or "c",
            error_signature=signature,
            summary=payload.prompt.strip()[:240],
            root_cause=f"The submission indicates a misunderstanding around {concepts[0]}.",
            incorrect_assumption=f"The learner treated {concepts[0]} as interchangeable with a nearby concept.",
            evidence=evidence or ["User supplied error description."],
            related_concepts=concepts,
            tags=["c-language", *concepts[:2]],
            confidence=0.55,
        )

    def _infer_title(self, prompt: str) -> str:
        first_line = prompt.strip().splitlines()[0] if prompt.strip() else "C language error"
        return first_line[:80]

    def _infer_signature(self, prompt: str, code: str, analysis: str) -> str:
        haystack = f"{prompt}\n{code}\n{analysis}".lower()
        if "sizeof" in haystack and any(
            token in haystack for token in ("strlen", "string length", "字符长度", "可见字符")
        ):
            return "sizeof-vs-strlen"
        if "&arr" in haystack or "arr" in haystack and "pointer" in haystack:
            return "array-pointer-decay"
        if "char *" in haystack and "char[" in haystack:
            return "char-pointer-vs-array"
        if "function" in haystack and "parameter" in haystack:
            return "function-parameter-decay"
        return slugify(self._infer_title(prompt))

    def _infer_related_concepts(self, prompt: str, code: str, analysis: str) -> list[str]:
        haystack = f"{prompt}\n{code}\n{analysis}".lower()
        concepts: list[str] = []
        pairs = [
            ("sizeof", "sizeof"),
            ("strlen", "strlen"),
            ("pointer", "pointer"),
            ("array", "array"),
            ("decay", "array-decay"),
            ("char *", "char-pointer"),
            ("char[", "char-array"),
            ("parameter", "function-parameter"),
        ]
        for needle, label in pairs:
            if needle in haystack and label not in concepts:
                concepts.append(label)
        return concepts or ["pointer-semantics"]

    @staticmethod
    def _coerce_list(value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    @staticmethod
    def _coerce_confidence(value: object) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.55
