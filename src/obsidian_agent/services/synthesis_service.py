"""Synthesis service."""

from __future__ import annotations

from obsidian_agent.domain.enums import ProposalType
from obsidian_agent.domain.schemas import RelatedNoteCandidate, ReviewProposal
from obsidian_agent.services.llm_service import LLMService


class SynthesisService:
    """Build integration decisions and review proposals."""

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def decide_action(
        self, new_note_path: str, related_notes: list[RelatedNoteCandidate]
    ) -> ProposalType:
        return await self.llm_service.classify_integration_action(new_note_path, related_notes)

    async def build_review_proposal(
        self, new_note_path: str, target_note_path: str | None, related_notes: list[RelatedNoteCandidate]
    ) -> ReviewProposal:
        rationale = "Generated from related note analysis."
        if related_notes:
            rationale += f" Top candidate: {related_notes[0].path} ({related_notes[0].score:.2f})."
        proposal_type = await self.decide_action(new_note_path, related_notes)
        suggested_patch = self._build_suggested_patch(new_note_path, related_notes, proposal_type)
        return await self.llm_service.generate_review_proposal(
            new_note_path=new_note_path,
            target_note_path=target_note_path,
            rationale=rationale,
            suggested_patch=suggested_patch,
            proposal_type=proposal_type,
        )

    @staticmethod
    def _build_suggested_patch(
        new_note_path: str,
        related_notes: list[RelatedNoteCandidate],
        proposal_type: ProposalType,
    ) -> str:
        if proposal_type == ProposalType.APPEND_CANDIDATE:
            return f"- Link to [[{new_note_path}]]"
        if proposal_type == ProposalType.MERGE_CANDIDATE:
            return f"Merge candidate based on [[{new_note_path}]]"
        if proposal_type == ProposalType.REVIEW_ONLY:
            return "\n".join(
                f"- Review relationship with [[{item.path}]] because {item.reason}"
                for item in related_notes[:5]
            ) or f"- Review [[{new_note_path}]]"
        return f"- Created from [[{new_note_path}]]"
