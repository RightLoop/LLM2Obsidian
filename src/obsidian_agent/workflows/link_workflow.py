"""Linking workflow."""

from obsidian_agent.services.retrieval_service import RetrievalService


class LinkWorkflow:
    """Resolve related notes for a note path."""

    def __init__(self, retrieval_service: RetrievalService) -> None:
        self.retrieval_service = retrieval_service

    async def run(self, note_path: str, top_k: int = 5):
        return await self.retrieval_service.find_related_notes(note_path, top_k=top_k)
