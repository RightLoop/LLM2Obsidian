"""Retrieval service."""

from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from obsidian_agent.domain.schemas import RelatedNoteCandidate
from obsidian_agent.services.embeddings_service import EmbeddingsService
from obsidian_agent.services.obsidian_service import ObsidianService
from obsidian_agent.storage.repositories import NoteRepository
from obsidian_agent.storage.vector_store import VectorStore


class RetrievalService:
    """Keyword, semantic and hybrid note retrieval."""

    def __init__(
        self,
        session_factory: sessionmaker,
        obsidian_service: ObsidianService,
        embeddings_service: EmbeddingsService,
        vector_store: VectorStore,
    ) -> None:
        self.session_factory = session_factory
        self.obsidian_service = obsidian_service
        self.embeddings_service = embeddings_service
        self.vector_store = vector_store

    async def keyword_search(self, text: str, top_k: int = 5) -> list[RelatedNoteCandidate]:
        with self.session_factory() as session:
            repo = NoteRepository(session)
            scored: list[RelatedNoteCandidate] = []
            for note in repo.list_all():
                haystack = f"{note.title} {note.source_ref or ''}".lower()
                overlap = sum(1 for token in text.lower().split() if token in haystack)
                if overlap:
                    scored.append(
                        RelatedNoteCandidate(
                            path=note.vault_path,
                            reason="Keyword overlap",
                            score=min(1.0, overlap / max(len(text.split()), 1) + 0.2),
                        )
                    )
            return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]

    async def semantic_search(self, text: str, top_k: int = 5) -> list[RelatedNoteCandidate]:
        vector = await self.embeddings_service.embed_text(text)
        return [
            RelatedNoteCandidate(path=path, reason="Semantic similarity", score=score)
            for path, score in self.vector_store.search(vector, top_k=top_k)
        ]

    async def hybrid_search(self, text: str, top_k: int = 5) -> list[RelatedNoteCandidate]:
        keyword = {item.path: item for item in await self.keyword_search(text, top_k=top_k * 2)}
        semantic = {item.path: item for item in await self.semantic_search(text, top_k=top_k * 2)}
        merged: dict[str, RelatedNoteCandidate] = {}
        for path in set(keyword) | set(semantic):
            kw = keyword.get(path)
            sem = semantic.get(path)
            score = ((kw.score if kw else 0.0) * 0.45) + ((sem.score if sem else 0.0) * 0.55)
            reason_parts = []
            if kw:
                reason_parts.append("keyword")
            if sem:
                reason_parts.append("semantic")
            merged[path] = RelatedNoteCandidate(path=path, reason="+".join(reason_parts), score=score)
        return sorted(merged.values(), key=lambda item: item.score, reverse=True)[:top_k]

    async def find_related_notes(self, note_path: str, top_k: int = 5) -> list[RelatedNoteCandidate]:
        content = await self.obsidian_service.read_note(note_path)
        return await self.hybrid_search(content, top_k=top_k)
