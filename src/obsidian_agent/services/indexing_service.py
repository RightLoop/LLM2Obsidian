"""Vault reindexing service."""

from __future__ import annotations

import hashlib

from sqlalchemy.orm import sessionmaker

from obsidian_agent.domain.schemas import NoteRecordSchema
from obsidian_agent.services.embeddings_service import EmbeddingsService
from obsidian_agent.services.obsidian_service import ObsidianService
from obsidian_agent.storage.repositories import NoteRepository
from obsidian_agent.storage.vector_store import VectorStore


class IndexingService:
    """Sync Vault notes into metadata and vector stores."""

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

    async def reindex_all(self) -> list[str]:
        paths = await self.obsidian_service.list_notes()
        indexed: list[str] = []
        with self.session_factory() as session:
            repo = NoteRepository(session)
            repo.delete_missing(set(paths))
            self.vector_store.clear()
            for path in paths:
                frontmatter, body = await self.obsidian_service.parse_note(path)
                content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
                repo.upsert(
                    NoteRecordSchema(
                        vault_path=path,
                        title=self._title_from_path(path),
                        kind=str(frontmatter.get("kind", "unknown")),
                        status=str(frontmatter.get("status", "unknown")),
                        source_type=str(frontmatter.get("source_type", "")),
                        source_ref=str(frontmatter.get("source_ref", "")),
                        content_hash=content_hash,
                        word_count=len(body.split()),
                    )
                )
                vector = await self.embeddings_service.embed_text(body)
                self.vector_store.upsert(path, vector)
                indexed.append(path)
        return indexed

    @staticmethod
    def _title_from_path(path: str) -> str:
        return path.rsplit("/", 1)[-1].replace(".md", "")
