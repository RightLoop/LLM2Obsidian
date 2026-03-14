"""Read-oriented helpers for smart node lookups."""

from __future__ import annotations

from obsidian_agent.domain.schemas import KnowledgeNodeSchema
from obsidian_agent.services.smart_node_pack_service import SmartNodePackService


class SmartQueryService:
    """Small query facade for UI-friendly smart lookups."""

    def __init__(self, smart_node_pack_service: SmartNodePackService) -> None:
        self.smart_node_pack_service = smart_node_pack_service

    async def related_nodes(self, node_key: str, top_k: int = 5) -> list[KnowledgeNodeSchema]:
        response = await self.smart_node_pack_service.build_node_pack(node_key=node_key, top_k=top_k)
        return response.pack.related_nodes
