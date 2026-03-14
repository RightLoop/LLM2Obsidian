"""Compress relation candidates into a compact relation pack."""

from __future__ import annotations

from obsidian_agent.domain.schemas import KnowledgeEdgeSchema, KnowledgeNodeSchema, RelationPack
from obsidian_agent.services.routing_policy_service import RoutingPolicyService


class ContextCompressorService:
    """Summarize relation candidates for preview and downstream teaching."""

    def __init__(self, routing_policy: RoutingPolicyService) -> None:
        self.routing_policy = routing_policy

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
        llm_service = self.routing_policy.for_structured_task()
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
        if isinstance(raw, dict) and str(raw.get("summary") or "").strip():
            return str(raw["summary"]).strip()
        top_edges = ", ".join(
            f"{edge.relation_type.value} {edge.to_node_key}" for edge in edges[:3]
        )
        return f"{anchor.title} links to {len(edges)} related nodes. Priority relations: {top_edges}."
