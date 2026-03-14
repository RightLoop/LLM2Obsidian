"""Compress relation candidates into a compact relation pack."""

from __future__ import annotations

import logging

from obsidian_agent.domain.schemas import KnowledgeEdgeSchema, KnowledgeNodeSchema, RelationPack
from obsidian_agent.services.routing_policy_service import RoutingPolicyService

logger = logging.getLogger(__name__)


class ContextCompressorService:
    """Summarize relation candidates for preview and downstream teaching."""

    def __init__(self, routing_policy: RoutingPolicyService) -> None:
        self.routing_policy = routing_policy
        self.last_telemetry: dict[str, object] = {}

    async def build_pack(
        self,
        anchor: KnowledgeNodeSchema,
        related_nodes: list[KnowledgeNodeSchema],
        edges: list[KnowledgeEdgeSchema],
    ) -> RelationPack:
        summary = await self._summarize(anchor, related_nodes, edges)
        return RelationPack(
            anchor=anchor,
            related_nodes=related_nodes,
            edges=edges,
            summary=summary,
        )

    async def _summarize(
        self,
        anchor: KnowledgeNodeSchema,
        related_nodes: list[KnowledgeNodeSchema],
        edges: list[KnowledgeEdgeSchema],
    ) -> str:
        if not edges:
            return f"No high-confidence related nodes were found yet for {anchor.title}."
        llm_service = self.routing_policy.for_structured_task("context_compressor")
        raw = await llm_service.run_structured_task(
            instructions=(
                "Return JSON with one key 'summary'. Summarize the anchor node and its highest-value relations "
                "for a teaching or review workflow in 2-4 sentences."
            ),
            input_text="\n".join(
                [
                    f"Anchor: {anchor.title} - {anchor.summary}",
                    "Related nodes:",
                    *[f"- {item.title}: {item.summary}" for item in related_nodes],
                    "Relations:",
                    *[
                        f"- {edge.relation_type.value} -> {edge.to_node_key}: {edge.reason}"
                        for edge in edges
                    ],
                ]
            ),
        )
        self.last_telemetry = llm_service.pop_telemetry()
        if self.last_telemetry:
            logger.info("smart_telemetry task=context_compressor telemetry=%s", self.last_telemetry)
        if isinstance(raw, dict) and str(raw.get("summary") or "").strip():
            return str(raw["summary"]).strip()
        top_edges = ", ".join(
            f"{edge.relation_type.value} {edge.to_node_key}" for edge in edges[:3]
        )
        return f"{anchor.title} links to {len(edges)} related nodes. Priority relations: {top_edges}."
