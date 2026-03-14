"""Write smart nodes into the vault and local metadata store."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import sessionmaker

from obsidian_agent.domain.enums import KnowledgeNodeType, NoteKind, NoteStatus, SourceType
from obsidian_agent.domain.schemas import (
    ErrorCaptureRequest,
    ErrorObject,
    FrontmatterSchema,
    KnowledgeNodeSchema,
    WeaknessObject,
)
from obsidian_agent.services.obsidian_service import ObsidianService
from obsidian_agent.storage.repositories import ErrorOccurrenceRepository, KnowledgeNodeRepository
from obsidian_agent.utils.markdown import render_template
from obsidian_agent.utils.slugify import slugify
from obsidian_agent.utils.time import compact_timestamp, now_utc


class NodeWriterService:
    """Persist error nodes and occurrences."""

    def __init__(
        self,
        session_factory: sessionmaker,
        obsidian_service: ObsidianService,
        error_template_path: Path,
    ) -> None:
        self.session_factory = session_factory
        self.obsidian_service = obsidian_service
        self.error_template_path = error_template_path

    async def write_error_node(
        self,
        request: ErrorCaptureRequest,
        error: ErrorObject,
        weaknesses: list[WeaknessObject],
    ) -> tuple[KnowledgeNodeSchema, object | None]:
        node_key = f"error/{slugify(error.error_signature)}"
        existing_node = self._load_existing_node(node_key)
        note_path = existing_node.note_path if existing_node else None
        action_preview = None
        if not note_path:
            frontmatter = FrontmatterSchema(
                id=compact_timestamp(),
                kind=NoteKind.ERROR,
                status=NoteStatus.DRAFT,
                source_type=SourceType.MANUAL,
                source_ref=request.source_ref,
                created_at=now_utc(),
                updated_at=now_utc(),
                tags=error.tags,
                entities=[],
                topics=error.related_concepts,
                confidence=error.confidence,
                review_required=False,
            )
            body = render_template(
                self.error_template_path,
                {
                    "title": error.title,
                    "summary": error.summary,
                    "root_cause": error.root_cause,
                    "incorrect_assumption": error.incorrect_assumption,
                    "evidence": "\n".join(f"- {item}" for item in error.evidence) or "-",
                    "related_concepts": "\n".join(f"- {item}" for item in error.related_concepts) or "-",
                    "recommended_practice": "\n".join(
                        f"- {item.recommended_practice}" for item in weaknesses
                    )
                    or "-",
                },
            )
            write_result = await self.obsidian_service.create_note(
                folder=self.obsidian_service.settings.smart_errors_folder,
                title=error.title,
                frontmatter=frontmatter.model_dump(mode="json"),
                body=body,
            )
            if hasattr(write_result, "model_dump"):
                note_path = write_result.target_path
                action_preview = write_result
            else:
                note_path = write_result
        node = KnowledgeNodeSchema(
            node_key=node_key,
            node_type=KnowledgeNodeType.ERROR,
            title=error.title,
            summary=error.summary,
            note_path=note_path,
            source_note_path=request.source_ref or None,
            tags=error.tags,
            metadata={
                "language": error.language,
                "error_signature": error.error_signature,
                "root_cause": error.root_cause,
                "incorrect_assumption": error.incorrect_assumption,
                "weaknesses": [item.model_dump(mode="json") for item in weaknesses],
            },
        )
        with self.session_factory() as session:
            node_repo = KnowledgeNodeRepository(session)
            stored = node_repo.upsert(node)
            occurrence_repo = ErrorOccurrenceRepository(session)
            occurrence_repo.create(
                error=error,
                raw_input=self._compose_raw_input(request),
                node_id=stored.id,
                source_note_path=node.note_path,
            )
        return node, action_preview

    def _load_existing_node(self, node_key: str) -> KnowledgeNodeSchema | None:
        with self.session_factory() as session:
            repo = KnowledgeNodeRepository(session)
            entity = repo.get_by_key(node_key)
            if entity is None:
                return None
            return KnowledgeNodeSchema(
                id=entity.id,
                node_key=entity.node_key,
                node_type=KnowledgeNodeType(entity.node_type),
                title=entity.title,
                summary=entity.summary,
                note_path=entity.note_path,
                source_note_path=entity.source_note_path,
                tags=[],
                metadata={},
            )

    def _compose_raw_input(self, request: ErrorCaptureRequest) -> str:
        return (
            f"Prompt:\n{request.prompt}\n\n"
            f"Code:\n{request.code}\n\n"
            f"Analysis:\n{request.user_analysis}\n"
        ).strip()
