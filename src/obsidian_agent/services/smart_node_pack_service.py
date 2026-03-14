"""Build relation packs around smart knowledge nodes."""

from __future__ import annotations

import json

from sqlalchemy.orm import sessionmaker

from obsidian_agent.domain.enums import KnowledgeNodeType
from obsidian_agent.domain.schemas import KnowledgeEdgeSchema, KnowledgeNodeSchema, SmartNodePackResponse
from obsidian_agent.services.context_compressor_service import ContextCompressorService
from obsidian_agent.services.relation_miner_service import RelationMinerService
from obsidian_agent.storage.repositories import KnowledgeEdgeRepository, KnowledgeNodeRepository


class SmartNodePackService:
    """Load an anchor node, mine relations, and return a relation pack."""

    def __init__(
        self,
        session_factory: sessionmaker,
        relation_miner: RelationMinerService,
        context_compressor: ContextCompressorService,
    ) -> None:
        self.session_factory = session_factory
        self.relation_miner = relation_miner
        self.context_compressor = context_compressor

    async def build_node_pack(self, node_key: str, top_k: int = 5) -> SmartNodePackResponse:
        with self.session_factory() as session:
            node_repo = KnowledgeNodeRepository(session)
            anchor_entity = node_repo.get_by_key(node_key)
            if anchor_entity is None:
                raise ValueError(f"Knowledge node not found: {node_key}")
            anchor = self._to_schema(anchor_entity)
            candidates = [self._to_schema(entity) for entity in node_repo.list_others(node_key)[: max(top_k * 2, 6)]]

        edges = await self.relation_miner.mine(anchor, candidates)
        normalized_edges = [
            KnowledgeEdgeSchema(
                from_node_key=anchor.node_key,
                to_node_key=edge.to_node_key,
                relation_type=edge.relation_type,
                reason=edge.reason,
                confidence=edge.confidence,
            )
            for edge in edges
        ]
        related_nodes = [
            item for item in candidates if item.node_key in {edge.to_node_key for edge in normalized_edges}
        ][:top_k]
        pack = await self.context_compressor.build_pack(anchor, related_nodes, normalized_edges)

        with self.session_factory() as session:
            node_repo = KnowledgeNodeRepository(session)
            edge_repo = KnowledgeEdgeRepository(session)
            anchor_entity = node_repo.get_by_key(node_key)
            stored = edge_repo.replace_for_source(
                from_node_id=anchor_entity.id if anchor_entity else None,
                edges=normalized_edges,
                node_ids_by_key={
                    item.node_key: item.id
                    for item in node_repo.list_all()
                    if item.id is not None
                },
            )
        return SmartNodePackResponse(
            pack=pack,
            stored_edges=len(stored),
            telemetry={
                "relation_miner": self.relation_miner.last_telemetry,
                "context_compressor": self.context_compressor.last_telemetry,
                "candidate_count": len(candidates),
                "related_count": len(related_nodes),
                "token_budget_hint": pack.token_budget_hint,
                "condensed_context_chars": len(pack.condensed_context),
            },
        )

    def _to_schema(self, entity) -> KnowledgeNodeSchema:
        tags = json.loads(entity.tags_json or "[]")
        metadata = json.loads(entity.metadata_json or "{}")
        return KnowledgeNodeSchema(
            id=entity.id,
            node_key=entity.node_key,
            node_type=KnowledgeNodeType(entity.node_type),
            title=entity.title,
            summary=entity.summary,
            note_path=entity.note_path,
            source_note_path=entity.source_note_path,
            tags=tags if isinstance(tags, list) else [],
            metadata=metadata if isinstance(metadata, dict) else {},
        )
