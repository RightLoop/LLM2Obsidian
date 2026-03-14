"""Infer relations between knowledge nodes."""

from __future__ import annotations

import json
from pathlib import Path

from obsidian_agent.domain.enums import KnowledgeRelationType
from obsidian_agent.domain.schemas import KnowledgeEdgeSchema, KnowledgeNodeSchema
from obsidian_agent.services.routing_policy_service import RoutingPolicyService


class RelationMinerService:
    """Mine semantic relations between an anchor node and candidate nodes."""

    def __init__(self, routing_policy: RoutingPolicyService) -> None:
        self.routing_policy = routing_policy

    async def mine(
        self,
        anchor: KnowledgeNodeSchema,
        candidates: list[KnowledgeNodeSchema],
    ) -> list[KnowledgeEdgeSchema]:
        if not candidates:
            return []
        llm_service = self.routing_policy.for_structured_task()
        raw = await llm_service.run_structured_task(
            instructions=(
                "Return JSON with a top-level key 'relations' containing a list of objects with keys: "
                "to_node_key, relation_type, reason, confidence. Allowed relation_type values are: "
                "reveals_gap_in, requires, contrasts_with, commonly_confused_with, is_example_of, fixes, repeated_in. "
                "Only return relations that are strongly supported."
            ),
            input_text=self._compose_input(anchor, candidates),
        )
        relations = self._sanitize(raw, anchor, candidates)
        if relations:
            return relations
        return self._fallback(anchor, candidates)

    def _compose_input(self, anchor: KnowledgeNodeSchema, candidates: list[KnowledgeNodeSchema]) -> str:
        parts = [
            f"Anchor title: {anchor.title}",
            f"Anchor summary: {anchor.summary}",
            f"Anchor metadata: {json.dumps(anchor.metadata, ensure_ascii=False)}",
            "Candidates:",
        ]
        for item in candidates:
            parts.append(
                json.dumps(
                    {
                        "node_key": item.node_key,
                        "title": item.title,
                        "summary": item.summary,
                        "metadata": item.metadata,
                    },
                    ensure_ascii=False,
                )
            )
        return "\n".join(parts)

    def _sanitize(
        self,
        raw: dict[str, object] | None,
        anchor: KnowledgeNodeSchema,
        candidates: list[KnowledgeNodeSchema],
    ) -> list[KnowledgeEdgeSchema]:
        del anchor
        if not raw or not isinstance(raw.get("relations"), list):
            return []
        candidate_keys = {item.node_key for item in candidates}
        edges: list[KnowledgeEdgeSchema] = []
        for item in raw["relations"]:
            if not isinstance(item, dict):
                continue
            to_node_key = str(item.get("to_node_key") or "").strip()
            relation_type = str(item.get("relation_type") or "").strip()
            if to_node_key not in candidate_keys:
                continue
            if relation_type not in {member.value for member in KnowledgeRelationType}:
                continue
            try:
                confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
            except (TypeError, ValueError):
                confidence = 0.5
            edges.append(
                KnowledgeEdgeSchema(
                    from_node_key="",
                    to_node_key=to_node_key,
                    relation_type=KnowledgeRelationType(relation_type),
                    reason=str(item.get("reason") or "Related concept"),
                    confidence=confidence,
                )
            )
        return edges

    def _fallback(
        self,
        anchor: KnowledgeNodeSchema,
        candidates: list[KnowledgeNodeSchema],
    ) -> list[KnowledgeEdgeSchema]:
        edges: list[KnowledgeEdgeSchema] = []
        anchor_text = self._normalized_text(anchor)
        for candidate in candidates:
            candidate_text = self._normalized_text(candidate)
            relation = self._guess_relation(anchor_text, candidate_text)
            if relation is None:
                continue
            edges.append(
                KnowledgeEdgeSchema(
                    from_node_key=anchor.node_key,
                    to_node_key=candidate.node_key,
                    relation_type=relation,
                    reason=f"Fallback relation inferred from overlapping C-language concepts in {Path(candidate.note_path or candidate.title).stem}.",
                    confidence=0.62,
                )
            )
        return edges

    def _normalized_text(self, node: KnowledgeNodeSchema) -> str:
        values = [node.title, node.summary]
        values.extend(str(value) for value in node.metadata.values())
        return " ".join(values).lower()

    def _guess_relation(
        self,
        anchor_text: str,
        candidate_text: str,
    ) -> KnowledgeRelationType | None:
        if "sizeof" in anchor_text and ("strlen" in candidate_text or "string" in candidate_text):
            return KnowledgeRelationType.COMMONLY_CONFUSED_WITH
        if "pointer" in anchor_text and "array" in candidate_text:
            return KnowledgeRelationType.COMMONLY_CONFUSED_WITH
        if "array" in anchor_text and "decay" in candidate_text:
            return KnowledgeRelationType.REQUIRES
        if "char-pointer" in anchor_text and "char-array" in candidate_text:
            return KnowledgeRelationType.CONTRASTS_WITH
        if any(token in anchor_text and token in candidate_text for token in ("pointer", "array", "sizeof", "strlen")):
            return KnowledgeRelationType.REPEATED_IN
        return None
