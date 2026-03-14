"""Write smart nodes into the vault and local metadata store."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from obsidian_agent.domain.enums import (
    KnowledgeNodeType,
    KnowledgeRelationType,
    NoteKind,
    NoteStatus,
    SourceType,
)
from obsidian_agent.domain.schemas import (
    ActionPreview,
    ErrorCaptureRequest,
    ErrorObject,
    FrontmatterSchema,
    KnowledgeEdgeSchema,
    KnowledgeNodeSchema,
    WeaknessObject,
)
from obsidian_agent.services.obsidian_service import ObsidianService
from obsidian_agent.storage.repositories import (
    ErrorOccurrenceRepository,
    KnowledgeEdgeRepository,
    KnowledgeNodeRepository,
)
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
        smart_node_template_path: Path,
    ) -> None:
        self.session_factory = session_factory
        self.obsidian_service = obsidian_service
        self.error_template_path = error_template_path
        self.smart_node_template_path = smart_node_template_path

    async def write_error_bundle(
        self,
        request: ErrorCaptureRequest,
        error: ErrorObject,
        weaknesses: list[WeaknessObject],
    ) -> tuple[KnowledgeNodeSchema, list[KnowledgeNodeSchema], ActionPreview | None, int]:
        node_key = f"error/{slugify(error.error_signature)}"
        existing_node = self._load_existing_node(node_key)
        note_path = existing_node.note_path if existing_node else None
        action_previews: list[ActionPreview] = []
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
                action_previews.append(write_result)
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
        supporting_nodes = self._build_supporting_nodes(error, weaknesses, note_path)
        persisted_supporting_nodes = await self._upsert_supporting_nodes(supporting_nodes, action_previews)
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
            edge_repo = KnowledgeEdgeRepository(session)
            stored_edges = edge_repo.create_if_missing_batch(
                from_node_id=stored.id,
                edges=self._build_supporting_edges(stored.node_key, persisted_supporting_nodes, error),
                node_ids_by_key={
                    item.node_key: item.id
                    for item in node_repo.list_all()
                    if item.id is not None
                },
            )
        action_preview = None
        if action_previews:
            action_preview = ActionPreview(
                dry_run=True,
                action="write_error_bundle",
                target_path=node.note_path or "",
                details={
                    "generated_paths": [item.target_path for item in action_previews],
                    "generated_count": len(action_previews),
                },
            )
        return node, persisted_supporting_nodes, action_preview, len(stored_edges)

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
                tags=json.loads(entity.tags_json or "[]"),
                metadata=json.loads(entity.metadata_json or "{}"),
            )

    def _compose_raw_input(self, request: ErrorCaptureRequest) -> str:
        return (
            f"Prompt:\n{request.prompt}\n\n"
            f"Code:\n{request.code}\n\n"
            f"Analysis:\n{request.user_analysis}\n"
        ).strip()

    def _build_supporting_nodes(
        self,
        error: ErrorObject,
        weaknesses: list[WeaknessObject],
        source_note_path: str | None,
    ) -> list[KnowledgeNodeSchema]:
        nodes: list[KnowledgeNodeSchema] = []
        concept_keys: set[str] = set()
        for weakness in weaknesses:
            for concept in weakness.related_concepts[:2]:
                key = f"concept/{slugify(concept)}"
                if key in concept_keys:
                    continue
                concept_keys.add(key)
                nodes.append(
                    KnowledgeNodeSchema(
                        node_key=key,
                        node_type=KnowledgeNodeType.CONCEPT,
                        title=concept.replace("-", " ").title(),
                        summary=weakness.summary,
                        note_path=None,
                        source_note_path=source_note_path,
                        tags=["concept", error.language, *error.tags[:2]],
                        metadata={
                            "practice_focus": weakness.recommended_practice,
                            "related_concepts": weakness.related_concepts,
                            "derived_from_error": error.error_signature,
                        },
                    )
                )
        pitfall_key = f"pitfall/{slugify(error.error_signature)}"
        nodes.append(
            KnowledgeNodeSchema(
                node_key=pitfall_key,
                node_type=KnowledgeNodeType.PITFALL,
                title=f"Pitfall: {error.title}",
                summary=error.incorrect_assumption,
                note_path=None,
                source_note_path=source_note_path,
                tags=["pitfall", error.language, *error.tags[:2]],
                metadata={
                    "practice_focus": error.root_cause,
                    "related_concepts": error.related_concepts,
                    "derived_from_error": error.error_signature,
                    "evidence": error.evidence,
                },
            )
        )
        return nodes

    async def _upsert_supporting_nodes(
        self,
        nodes: list[KnowledgeNodeSchema],
        action_previews: list[ActionPreview],
    ) -> list[KnowledgeNodeSchema]:
        persisted: list[KnowledgeNodeSchema] = []
        for node in nodes:
            existing = self._load_existing_node(node.node_key)
            note_path = existing.note_path if existing else None
            merged_tags = sorted({*(existing.tags if existing else []), *node.tags})
            merged_metadata = dict(existing.metadata if existing else {})
            merged_metadata.update(node.metadata)
            if not note_path:
                body = render_template(
                    self.smart_node_template_path,
                    {
                        "title": node.title,
                        "summary": node.summary,
                        "node_type": node.node_type.value,
                        "practice_focus": str(merged_metadata.get("practice_focus", "-")),
                        "related_concepts": "\n".join(
                            f"- {item}" for item in merged_metadata.get("related_concepts", [])
                        )
                        or "-",
                        "evidence": "\n".join(
                            f"- {item}" for item in merged_metadata.get("evidence", [])
                        )
                        or "-",
                    },
                )
                frontmatter = FrontmatterSchema(
                    id=compact_timestamp(),
                    kind=self._note_kind_for_node(node.node_type),
                    status=NoteStatus.DRAFT,
                    source_type=SourceType.MANUAL,
                    source_ref=node.source_note_path or "",
                    created_at=now_utc(),
                    updated_at=now_utc(),
                    tags=merged_tags,
                    entities=[],
                    topics=[str(item) for item in merged_metadata.get("related_concepts", [])],
                    confidence=0.6,
                    review_required=False,
                )
                write_result = await self.obsidian_service.create_note(
                    folder=self.obsidian_service.settings.smart_nodes_folder,
                    title=node.title,
                    frontmatter=frontmatter.model_dump(mode="json"),
                    body=body,
                )
                if hasattr(write_result, "model_dump"):
                    note_path = write_result.target_path
                    action_previews.append(write_result)
                else:
                    note_path = write_result
            summary = node.summary
            if existing and len(existing.summary) > len(summary):
                summary = existing.summary
            persisted.append(
                KnowledgeNodeSchema(
                    id=existing.id if existing else None,
                    node_key=node.node_key,
                    node_type=node.node_type,
                    title=existing.title if existing else node.title,
                    summary=summary,
                    note_path=note_path,
                    source_note_path=node.source_note_path,
                    tags=merged_tags,
                    metadata=merged_metadata,
                )
            )
        with self.session_factory() as session:
            repo = KnowledgeNodeRepository(session)
            stored_nodes = [repo.upsert(node) for node in persisted]
        return [
            KnowledgeNodeSchema(
                id=item.id,
                node_key=item.node_key,
                node_type=KnowledgeNodeType(item.node_type),
                title=item.title,
                summary=item.summary,
                note_path=item.note_path,
                source_note_path=item.source_note_path,
                tags=json.loads(item.tags_json or "[]"),
                metadata=json.loads(item.metadata_json or "{}"),
            )
            for item in stored_nodes
        ]

    def _build_supporting_edges(
        self,
        error_node_key: str,
        nodes: list[KnowledgeNodeSchema],
        error: ErrorObject,
    ) -> list[KnowledgeEdgeSchema]:
        edges: list[KnowledgeEdgeSchema] = []
        for node in nodes:
            relation_type = (
                KnowledgeRelationType.REVEALS_GAP_IN
                if node.node_type == KnowledgeNodeType.CONCEPT
                else KnowledgeRelationType.COMMONLY_CONFUSED_WITH
            )
            reason = (
                f"{error.title} reveals a gap in {node.title}."
                if node.node_type == KnowledgeNodeType.CONCEPT
                else error.incorrect_assumption
            )
            edges.append(
                KnowledgeEdgeSchema(
                    from_node_key=error_node_key,
                    to_node_key=node.node_key,
                    relation_type=relation_type,
                    reason=reason,
                    confidence=max(0.55, error.confidence),
                )
            )
        return edges

    @staticmethod
    def _note_kind_for_node(node_type: KnowledgeNodeType) -> NoteKind:
        mapping = {
            KnowledgeNodeType.CONCEPT: NoteKind.CONCEPT,
            KnowledgeNodeType.PITFALL: NoteKind.PITFALL,
            KnowledgeNodeType.CONTRAST: NoteKind.CONTRAST,
            KnowledgeNodeType.ERROR: NoteKind.ERROR,
        }
        return mapping[node_type]
