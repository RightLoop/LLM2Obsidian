"""Infer relations between knowledge nodes."""

from __future__ import annotations

import json
import logging

from obsidian_agent.domain.enums import KnowledgeRelationType
from obsidian_agent.domain.schemas import KnowledgeEdgeSchema, KnowledgeNodeSchema
from obsidian_agent.services.routing_policy_service import RoutingPolicyService

logger = logging.getLogger(__name__)


class RelationMinerService:
    """Mine semantic relations between an anchor node and candidate nodes."""

    def __init__(self, routing_policy: RoutingPolicyService) -> None:
        self.routing_policy = routing_policy
        self.last_telemetry: dict[str, object] = {}

    async def mine(
        self,
        anchor: KnowledgeNodeSchema,
        candidates: list[KnowledgeNodeSchema],
    ) -> list[KnowledgeEdgeSchema]:
        if not candidates:
            return []
        llm_service = self.routing_policy.for_structured_task("relation_miner")
        raw = await llm_service.run_structured_task(
            instructions=(
                "Return JSON with a top-level key 'relations' containing a list of objects with keys: "
                "to_node_key, relation_type, reason, confidence. Allowed relation_type values are: "
                "reveals_gap_in, requires, contrasts_with, commonly_confused_with, is_example_of, fixes, "
                "repeated_in. Only return relations that are strongly supported. Use Simplified Chinese "
                "for reason. Return at most 3 relations. Skip weak, generic, or self-evident links."
            ),
            input_text=self._compose_input(anchor, candidates),
        )
        self.last_telemetry = llm_service.pop_telemetry()
        if self.last_telemetry:
            logger.info("smart_telemetry task=relation_miner telemetry=%s", self.last_telemetry)
        relations = self._sanitize(raw, candidates)
        if relations:
            return relations
        return self._fallback(anchor, candidates)

    def _compose_input(
        self,
        anchor: KnowledgeNodeSchema,
        candidates: list[KnowledgeNodeSchema],
    ) -> str:
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
        candidates: list[KnowledgeNodeSchema],
    ) -> list[KnowledgeEdgeSchema]:
        if not raw or not isinstance(raw.get("relations"), list):
            return []
        candidate_keys = {item.node_key for item in candidates}
        best_by_key: dict[str, KnowledgeEdgeSchema] = {}
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
            if confidence < 0.68:
                continue
            edge = KnowledgeEdgeSchema(
                from_node_key="",
                to_node_key=to_node_key,
                relation_type=KnowledgeRelationType(relation_type),
                reason=self._compress_reason(str(item.get("reason") or "相关概念。")),
                confidence=confidence,
            )
            current = best_by_key.get(to_node_key)
            if current is None or edge.confidence > current.confidence:
                best_by_key[to_node_key] = edge
        return sorted(best_by_key.values(), key=lambda item: item.confidence, reverse=True)[:3]

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
            reason = self._fallback_reason(anchor, candidate, relation)
            if not reason:
                continue
            edges.append(
                KnowledgeEdgeSchema(
                    from_node_key=anchor.node_key,
                    to_node_key=candidate.node_key,
                    relation_type=relation,
                    reason=reason,
                    confidence=0.72 if relation != KnowledgeRelationType.REPEATED_IN else 0.68,
                )
            )
        return sorted(edges, key=lambda item: item.confidence, reverse=True)[:3]

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
        if any(
            token in anchor_text and token in candidate_text
            for token in ("pointer", "array", "sizeof", "strlen")
        ):
            return KnowledgeRelationType.REPEATED_IN
        return None

    def _fallback_reason(
        self,
        anchor: KnowledgeNodeSchema,
        candidate: KnowledgeNodeSchema,
        relation: KnowledgeRelationType,
    ) -> str:
        if relation == KnowledgeRelationType.COMMONLY_CONFUSED_WITH:
            return f"“{anchor.title}”和“{candidate.title}”在这类 C 题里很容易被混淆。"
        if relation == KnowledgeRelationType.REQUIRES:
            return f"要解释“{anchor.title}”，必须先补上“{candidate.title}”这条前置规则。"
        if relation == KnowledgeRelationType.CONTRASTS_WITH:
            return f"这次判断要把“{anchor.title}”和“{candidate.title}”并排对比才不容易出错。"
        if relation == KnowledgeRelationType.REPEATED_IN:
            title_overlap = anchor.title == candidate.title
            same_source = (
                anchor.metadata.get("derived_from_error")
                and anchor.metadata.get("derived_from_error")
                == candidate.metadata.get("derived_from_error")
            )
            if title_overlap or same_source:
                return ""
            return f"“{candidate.title}”里重复出现了与当前错误相同的判断边界。"
        return ""

    def _compress_reason(self, reason: str) -> str:
        compact = " ".join(reason.split()).strip()
        if not compact:
            return "相关概念。"
        if len(compact) > 72:
            compact = compact[:72].rstrip("，,。.;； ") + "。"
        return compact
