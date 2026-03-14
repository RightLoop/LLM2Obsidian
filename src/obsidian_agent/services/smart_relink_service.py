"""Rebuild smart relations and prepare review-safe note updates."""

from __future__ import annotations

from obsidian_agent.config import Settings
from obsidian_agent.domain.enums import ProposalType, RiskLevel
from obsidian_agent.domain.schemas import (
    ActionPreview,
    ReviewProposal,
    SmartRelinkRequest,
    SmartRelinkResponse,
)
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
        related_section_markdown = self._render_related_section(pack)
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
            rationale=self._build_rationale(pack),
            suggested_patch=related_section_markdown,
            related_links=[node.note_path for node in pack.related_nodes[:3] if node.note_path],
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
        for edge in pack.edges[:3]:
            node = related_by_key.get(edge.to_node_key)
            target = edge.to_node_key
            if node and node.note_path:
                target = f"[[{node.note_path}]]"
            elif node:
                target = node.title
            label = self._relation_label(edge.relation_type.value)
            lines.append(f"- {target}：{label}，{edge.reason}")
        if not lines:
            lines.append("- 这一轮没有找到值得写入的高价值相关节点。")
        return "\n".join(lines)

    def _build_rationale(self, pack) -> str:
        if not pack.edges:
            return f"“{pack.anchor.title}”这轮没有形成足够强的关系建议。"
        edge_count = len(pack.edges[:3])
        if any(edge.relation_type.value == "contrasts_with" for edge in pack.edges[:3]):
            return f"建议为“{pack.anchor.title}”补充 {edge_count} 条高价值关联，其中包含关键对比关系。"
        return f"建议为“{pack.anchor.title}”补充 {edge_count} 条高价值关联，便于后续复盘。"

    def _relation_label(self, relation_type: str) -> str:
        mapping = {
            "reveals_gap_in": "暴露出理解缺口",
            "requires": "依赖前置概念",
            "contrasts_with": "需要并排对比",
            "commonly_confused_with": "容易混淆",
            "is_example_of": "可以作为例子",
            "fixes": "用于纠正",
            "repeated_in": "在相似错误中反复出现",
        }
        return mapping.get(relation_type, relation_type)
