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
        fallback = self._fallback_fields(anchor, related_nodes, edges)
        payload = await self._summarize(anchor, related_nodes, edges)
        fields = self._sanitize_payload(payload, fallback)
        return RelationPack(
            anchor=anchor,
            related_nodes=related_nodes,
            edges=edges,
            summary=fields["summary"],
            relation_summary=fields["relation_summary"],
            weakness_labels=fields["weakness_labels"],
            do_not_repeat=fields["do_not_repeat"],
            recommended_output_shape=fields["recommended_output_shape"],
            token_budget_hint=fields["token_budget_hint"],
            condensed_context=fields["condensed_context"],
        )

    async def _summarize(
        self,
        anchor: KnowledgeNodeSchema,
        related_nodes: list[KnowledgeNodeSchema],
        edges: list[KnowledgeEdgeSchema],
    ) -> dict[str, object] | None:
        if not edges:
            return None
        llm_service = self.routing_policy.for_structured_task("context_compressor")
        raw = await llm_service.run_structured_task(
            instructions=(
                "Return JSON with keys: summary, relation_summary, weakness_labels, do_not_repeat, "
                "recommended_output_shape, token_budget_hint, condensed_context. "
                "Summarize the anchor node and its highest-value relations for a teaching workflow. "
                "Keep condensed_context concise, include only the highest-value context, and set "
                "recommended_output_shape to a short label like teaching_note or teaching_note_with_drills."
            ),
            input_text="\n".join(
                [
                    f"Anchor: {anchor.title} - {anchor.summary}",
                    f"Anchor metadata: {anchor.metadata}",
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
        return raw if isinstance(raw, dict) else None

    def _sanitize_payload(
        self,
        raw: dict[str, object] | None,
        fallback: dict[str, object],
    ) -> dict[str, object]:
        data = dict(fallback)
        if not raw:
            return data
        summary = str(raw.get("summary") or "").strip()
        relation_summary = str(raw.get("relation_summary") or "").strip()
        condensed_context = str(raw.get("condensed_context") or "").strip()
        recommended_output_shape = str(raw.get("recommended_output_shape") or "").strip()
        if summary:
            data["summary"] = summary
        if relation_summary:
            data["relation_summary"] = relation_summary
        if condensed_context:
            data["condensed_context"] = condensed_context
        if recommended_output_shape:
            data["recommended_output_shape"] = recommended_output_shape
        weakness_labels = raw.get("weakness_labels")
        if isinstance(weakness_labels, list):
            data["weakness_labels"] = [str(item).strip() for item in weakness_labels if str(item).strip()]
        do_not_repeat = raw.get("do_not_repeat")
        if isinstance(do_not_repeat, list):
            data["do_not_repeat"] = [str(item).strip() for item in do_not_repeat if str(item).strip()]
        try:
            token_budget_hint = int(raw.get("token_budget_hint", data["token_budget_hint"]))
        except (TypeError, ValueError):
            token_budget_hint = int(data["token_budget_hint"])
        data["token_budget_hint"] = max(300, min(2400, token_budget_hint))
        return data

    def _fallback_fields(
        self,
        anchor: KnowledgeNodeSchema,
        related_nodes: list[KnowledgeNodeSchema],
        edges: list[KnowledgeEdgeSchema],
    ) -> dict[str, object]:
        top_edges = ", ".join(f"{edge.relation_type.value} {edge.to_node_key}" for edge in edges[:3])
        weakness_labels = self._extract_weakness_labels(anchor)
        do_not_repeat: list[str] = []
        incorrect_assumption = str(anchor.metadata.get("incorrect_assumption", "")).strip()
        if incorrect_assumption:
            do_not_repeat.append(f"Do not repeat the incorrect assumption: {incorrect_assumption}")
        if edges:
            do_not_repeat.append("Do not restate every related note; only keep the highest-value contrasts and prerequisites.")
        condensed_parts = [
            f"Anchor: {anchor.title}",
            f"Summary: {anchor.summary}",
        ]
        if weakness_labels:
            condensed_parts.append(f"Weaknesses: {', '.join(weakness_labels[:3])}")
        if related_nodes:
            condensed_parts.append(
                "Related: " + "; ".join(f"{item.title} ({item.node_type.value})" for item in related_nodes[:4])
            )
        if edges:
            condensed_parts.append(
                "Relations: " + "; ".join(
                    f"{edge.relation_type.value} -> {edge.to_node_key}" for edge in edges[:4]
                )
            )
        condensed_context = " | ".join(condensed_parts)
        token_budget_hint = max(450, min(1800, 280 + len(condensed_context) // 2))
        return {
            "summary": (
                f"{anchor.title} links to {len(edges)} related nodes. Priority relations: {top_edges}."
                if edges
                else f"No high-confidence related nodes were found yet for {anchor.title}."
            ),
            "relation_summary": top_edges or "No priority relations yet.",
            "weakness_labels": weakness_labels,
            "do_not_repeat": do_not_repeat,
            "recommended_output_shape": "teaching_note_with_drills" if edges else "teaching_note",
            "token_budget_hint": token_budget_hint,
            "condensed_context": condensed_context,
        }

    def _extract_weakness_labels(self, anchor: KnowledgeNodeSchema) -> list[str]:
        raw = anchor.metadata.get("weaknesses")
        if not isinstance(raw, list):
            return []
        labels: list[str] = []
        for item in raw:
            if isinstance(item, dict):
                label = str(item.get("name") or "").strip()
            else:
                label = str(item).strip()
            if label:
                labels.append(label)
        return labels[:5]
