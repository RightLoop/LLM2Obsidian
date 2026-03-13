"""Retrieval service."""

from __future__ import annotations

import re

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
        query_tokens = self._tokenize(text)
        with self.session_factory() as session:
            repo = NoteRepository(session)
            scored: list[RelatedNoteCandidate] = []
            for note in repo.list_all():
                note_text = await self.obsidian_service.read_note(note.vault_path)
                haystack = f"{note.title} {note.source_ref or ''} {note_text}".lower()
                overlap_tokens = [token for token in query_tokens if token in haystack]
                overlap = len(set(overlap_tokens))
                if overlap:
                    matched = ", ".join(sorted(set(overlap_tokens))[:3])
                    scored.append(
                        RelatedNoteCandidate(
                            path=note.vault_path,
                            reason=f"Keyword overlap: {matched}",
                            score=min(1.0, overlap / max(len(query_tokens), 1) + 0.25),
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
                reason_parts.append(kw.reason)
            if sem:
                reason_parts.append(f"Semantic similarity {sem.score:.2f}")
            merged[path] = RelatedNoteCandidate(
                path=path,
                reason="; ".join(reason_parts),
                score=score,
            )
        return sorted(merged.values(), key=lambda item: item.score, reverse=True)[:top_k]

    async def find_related_notes(self, note_path: str, top_k: int = 5) -> list[RelatedNoteCandidate]:
        content = await self.obsidian_service.read_note(note_path)
        related = await self.hybrid_search(content, top_k=top_k + 1)
        return [item for item in related if item.path != note_path][:top_k]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", text.lower())
