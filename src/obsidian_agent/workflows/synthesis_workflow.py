"""Synthesis workflow."""

from obsidian_agent.services.review_service import ReviewService
from obsidian_agent.services.synthesis_service import SynthesisService


class SynthesisWorkflow:
    """Generate and persist review proposals."""

    def __init__(self, synthesis_service: SynthesisService, review_service: ReviewService) -> None:
        self.synthesis_service = synthesis_service
        self.review_service = review_service

    async def run(self, new_note_path: str, related_notes):
        target_path = related_notes[0].path if related_notes else None
        proposal = await self.synthesis_service.build_review_proposal(new_note_path, target_path, related_notes)
        review_id, proposal_path = await self.review_service.create_review_item(proposal)
        return {"review_id": review_id, "proposal_path": proposal_path, "proposal": proposal.model_dump(mode="json")}
