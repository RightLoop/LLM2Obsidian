"""Review queue service."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import sessionmaker

from obsidian_agent.domain.enums import ProposalType, ReviewState
from obsidian_agent.domain.policies import can_auto_apply
from obsidian_agent.domain.schemas import ActionPreview, ReviewProposal
from obsidian_agent.services.obsidian_service import ObsidianService
from obsidian_agent.storage.repositories import ReviewRepository
from obsidian_agent.utils.markdown import render_template
from obsidian_agent.utils.time import compact_timestamp


class ReviewService:
    """Render, persist and apply review proposals."""

    def __init__(
        self,
        session_factory: sessionmaker,
        obsidian_service: ObsidianService,
        template_path: Path,
    ) -> None:
        self.session_factory = session_factory
        self.obsidian_service = obsidian_service
        self.template_path = template_path

    async def render_review_markdown(self, proposal: ReviewProposal) -> str:
        context = {
            "title": proposal.title,
            "proposal_type": proposal.proposal_type.value,
            "source_note": proposal.source_note_path,
            "target_note": proposal.target_note_path or "",
            "rationale": proposal.rationale,
            "suggested_patch": proposal.suggested_patch,
            "risk": proposal.risk_level.value,
        }
        return render_template(self.template_path, context)

    async def create_review_item(self, proposal: ReviewProposal) -> tuple[int, str]:
        source_title = proposal.source_note_path.rsplit("/", 1)[-1].replace(".md", "")
        created = await self.obsidian_service.create_note(
            folder=self.obsidian_service.settings.review_folder,
            title=source_title,
            frontmatter={
                "id": compact_timestamp(),
                "kind": "review",
                "status": "review",
                "source_type": "manual",
                "source_ref": proposal.source_note_path,
                "review_required": True,
            },
            body=await self.render_review_markdown(proposal),
        )
        created_path = created.target_path if hasattr(created, "target_path") else created
        with self.session_factory() as session:
            repo = ReviewRepository(session)
            item = repo.create(proposal, created_path)
        return item.id, created_path

    async def list_pending(self) -> list[dict[str, str | int | None]]:
        with self.session_factory() as session:
            repo = ReviewRepository(session)
            items = repo.list_pending()
            return [
                {
                    "id": item.id,
                    "proposal_path": item.proposal_path,
                    "proposal_type": item.proposal_type,
                    "source_note_path": item.source_note_path,
                    "target_note_path": item.target_note_path,
                    "state": item.state,
                    "risk_level": item.risk_level,
                }
                for item in items
            ]

    async def approve(self, review_id: int) -> None:
        with self.session_factory() as session:
            ReviewRepository(session).set_state(review_id, ReviewState.APPROVED)

    async def reject(self, review_id: int) -> None:
        with self.session_factory() as session:
            ReviewRepository(session).set_state(review_id, ReviewState.REJECTED)

    async def apply_approved_review(self, review_id: int) -> ActionPreview | str:
        with self.session_factory() as session:
            repo = ReviewRepository(session)
            item = repo.get(review_id)
            if item is None:
                raise ValueError(f"Review item not found: {review_id}")
            if item.state != ReviewState.APPROVED.value:
                raise ValueError("Review item must be approved before apply")
            if not can_auto_apply(item.risk_level):
                raise ValueError("High risk review items cannot be auto-applied")
            if item.proposal_type == ProposalType.APPEND_CANDIDATE.value:
                if not item.target_note_path:
                    raise ValueError("Approved append proposal is missing target note path")
                write_result = await self.obsidian_service.append_to_note(
                    item.target_note_path,
                    "Related Notes",
                    item.suggested_patch,
                )
                if hasattr(write_result, "model_dump"):
                    return ActionPreview(
                        dry_run=True,
                        action="apply_review",
                        target_path=item.target_note_path,
                        details={"review_id": review_id, "proposal_type": item.proposal_type},
                    )
                repo.set_state(review_id, ReviewState.APPLIED)
                return write_result
            raise ValueError(f"Auto-apply is not implemented for proposal type: {item.proposal_type}")
