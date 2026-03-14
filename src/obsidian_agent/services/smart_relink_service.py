"""Rebuild smart relations and prepare review-safe note updates."""

from __future__ import annotations

from obsidian_agent.config import Settings
from obsidian_agent.domain.enums import ProposalType, RiskLevel
from obsidian_agent.domain.schemas import ActionPreview, ReviewProposal, SmartRelinkRequest, SmartRelinkResponse
from obsidian_agent.services.review_service import ReviewService
from obsidian_agent.services.smart_node_pack_service import SmartNodePackService


class SmartRelinkService:
    """Refresh related-node suggestions for an existing smart node."""

    def __init__(
        self,
        settings: Settings,
        smart_node_pack_service: SmartNodePackService,
        review_service: ReviewService,
    ) -> None:
        self.settings = settings
        self.smart_node_pack_service = smart_node_pack_service
        self.review_service = review_service

    async def relink(self, request: SmartRelinkRequest) -> SmartRelinkResponse:
        pack_response = await self.smart_node_pack_service.build_node_pack(
            node_key=request.node_key,
            top_k=request.top_k,
        )
        pack = pack_response.pack
        if not pack.anchor.note_path:
            raise ValueError(f"Knowledge node is missing note_path: {request.node_key}")
        related_section_markdown = self._render_related_section(pack_response.pack)
        preview = ActionPreview(
            dry_run=True,
            action="smart_relink_review",
            target_path=pack.anchor.note_path,
            details={
                "create_review": request.create_review,
                "top_k": request.top_k,
                "stored_edges": pack_response.stored_edges,
            },
        )
        if request.dry_run or self.settings.dry_run or not request.create_review:
            return SmartRelinkResponse(
                pack=pack,
                related_section_markdown=related_section_markdown,
                stored_edges=pack_response.stored_edges,
                action_preview=preview,
                telemetry=pack_response.telemetry,
            )

        proposal = ReviewProposal(
            proposal_type=ProposalType.APPEND_CANDIDATE,
            risk_level=RiskLevel.MEDIUM,
            title=f"Refresh related nodes for {pack.anchor.title}",
            source_note_path=pack.anchor.note_path,
            target_note_path=pack.anchor.note_path,
            rationale=pack.summary or f"Refresh relation links for {pack.anchor.title}.",
            suggested_patch=related_section_markdown,
            related_links=[node.note_path for node in pack.related_nodes if node.note_path],
        )
        review_id, proposal_path = await self.review_service.create_review_item(proposal)
        return SmartRelinkResponse(
            pack=pack,
            related_section_markdown=related_section_markdown,
            stored_edges=pack_response.stored_edges,
            review_id=review_id,
            proposal_path=proposal_path,
            telemetry=pack_response.telemetry,
        )

    def _render_related_section(self, pack) -> str:
        lines: list[str] = []
        related_by_key = {node.node_key: node for node in pack.related_nodes}
        for edge in pack.edges:
            node = related_by_key.get(edge.to_node_key)
            target = edge.to_node_key
            if node and node.note_path:
                target = f"[[{node.note_path}]]"
            elif node:
                target = node.title
            lines.append(
                f"- {target}: {edge.relation_type.value} ({edge.confidence:.2f}) - {edge.reason}"
            )
        if not lines:
            lines.append("- No strong related-node suggestions were found in this pass.")
        return "\n".join(lines)
