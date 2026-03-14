"""Write smart nodes into the vault and local metadata store."""

from __future__ import annotations

import json
import re
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
    """Persist smart nodes, reuse near-duplicates, and link them together."""

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
        action_previews: list[ActionPreview] = []
        error_node = await self._write_or_reuse_error_node(request, error, weaknesses, action_previews)
        supporting_nodes = await self._write_or_reuse_supporting_nodes(
            error=error,
            weaknesses=weaknesses,
            source_note_path=error_node.note_path,
            action_previews=action_previews,
        )

        with self.session_factory() as session:
            node_repo = KnowledgeNodeRepository(session)
            error_entity = node_repo.get_by_key(error_node.node_key)
            if error_entity is None:
                raise ValueError(f"Stored error node not found: {error_node.node_key}")
            ErrorOccurrenceRepository(session).create(
                error=error,
                raw_input=self._compose_raw_input(request),
                node_id=error_entity.id,
                source_note_path=error_node.note_path,
            )
            stored_edges = KnowledgeEdgeRepository(session).create_if_missing_batch(
                from_node_id=error_entity.id,
                edges=self._build_supporting_edges(error, error_node.node_key, supporting_nodes),
                node_ids_by_key={
                    entity.node_key: entity.id
                    for entity in node_repo.list_all()
                    if entity.id is not None
                },
            )

        preview = None
        if action_previews:
            preview = ActionPreview(
                dry_run=True,
                action="write_error_bundle",
                target_path=error_node.note_path or "",
                details={
                    "generated_paths": [item.target_path for item in action_previews],
                    "generated_count": len(action_previews),
                },
            )
        return error_node, supporting_nodes, preview, len(stored_edges)

    async def _write_or_reuse_error_node(
        self,
        request: ErrorCaptureRequest,
        error: ErrorObject,
        weaknesses: list[WeaknessObject],
        action_previews: list[ActionPreview],
    ) -> KnowledgeNodeSchema:
        node_key = f"error/{slugify(error.error_signature)}"
        existing = self._load_existing_node(node_key)
        note_path = existing.note_path if existing else None
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
            id=existing.id if existing else None,
            node_key=node_key,
            node_type=KnowledgeNodeType.ERROR,
            title=existing.title if existing else error.title,
            summary=existing.summary if existing and len(existing.summary) >= len(error.summary) else error.summary,
            note_path=note_path,
            source_note_path=request.source_ref or None,
            tags=sorted({*(existing.tags if existing else []), *error.tags}),
            metadata={
                "language": error.language,
                "error_signature": error.error_signature,
                "root_cause": error.root_cause,
                "incorrect_assumption": error.incorrect_assumption,
                "weaknesses": [item.model_dump(mode="json") for item in weaknesses],
            },
        )
        with self.session_factory() as session:
            stored = KnowledgeNodeRepository(session).upsert(node)
        return self._entity_to_schema(stored)

    async def _write_or_reuse_supporting_nodes(
        self,
        error: ErrorObject,
        weaknesses: list[WeaknessObject],
        source_note_path: str | None,
        action_previews: list[ActionPreview],
    ) -> list[KnowledgeNodeSchema]:
        specs = self._build_supporting_specs(error, weaknesses, source_note_path)
        stored_nodes: list[KnowledgeNodeSchema] = []
        for spec in specs:
            reused = self._find_existing_support_node(spec)
            note_path = reused.note_path if reused else None
            merged_tags = sorted({*(reused.tags if reused else []), *spec.tags})
            merged_metadata = dict(reused.metadata if reused else {})
            merged_metadata.update(spec.metadata)
            summary = reused.summary if reused and len(reused.summary) >= len(spec.summary) else spec.summary
            title = reused.title if reused else spec.title
            node_key = reused.node_key if reused else spec.node_key

            if not note_path:
                frontmatter = FrontmatterSchema(
                    id=compact_timestamp(),
                    kind=self._note_kind_for_node(spec.node_type),
                    status=NoteStatus.DRAFT,
                    source_type=SourceType.MANUAL,
                    source_ref=source_note_path or "",
                    created_at=now_utc(),
                    updated_at=now_utc(),
                    tags=merged_tags,
                    entities=[],
                    topics=[str(item) for item in merged_metadata.get("related_concepts", [])],
                    confidence=0.6,
                    review_required=False,
                )
                body = render_template(
                    self.smart_node_template_path,
                    {
                        "title": title,
                        "summary": summary,
                        "node_type": spec.node_type.value,
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
                write_result = await self.obsidian_service.create_note(
                    folder=self.obsidian_service.settings.smart_nodes_folder,
                    title=title,
                    frontmatter=frontmatter.model_dump(mode="json"),
                    body=body,
                )
                if hasattr(write_result, "model_dump"):
                    note_path = write_result.target_path
                    action_previews.append(write_result)
                else:
                    note_path = write_result

            node = KnowledgeNodeSchema(
                id=reused.id if reused else None,
                node_key=node_key,
                node_type=spec.node_type,
                title=title,
                summary=summary,
                note_path=note_path,
                source_note_path=source_note_path,
                tags=merged_tags,
                metadata=merged_metadata,
            )
            with self.session_factory() as session:
                stored = KnowledgeNodeRepository(session).upsert(node)
            stored_nodes.append(self._entity_to_schema(stored))
        return stored_nodes

    def _build_supporting_specs(
        self,
        error: ErrorObject,
        weaknesses: list[WeaknessObject],
        source_note_path: str | None,
    ) -> list[KnowledgeNodeSchema]:
        nodes: list[KnowledgeNodeSchema] = []
        concept_seen: set[str] = set()
        for weakness in weaknesses:
            for concept in weakness.related_concepts[:2]:
                node_key = f"concept/{slugify(concept)}"
                if node_key in concept_seen:
                    continue
                concept_seen.add(node_key)
                nodes.append(
                    KnowledgeNodeSchema(
                        node_key=node_key,
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
                            "evidence": error.evidence[:2],
                        },
                    )
                )

        nodes.append(
            KnowledgeNodeSchema(
                node_key=f"pitfall/{slugify(error.error_signature)}",
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

        contrast_title = self._contrast_title(error)
        if contrast_title:
            nodes.append(
                KnowledgeNodeSchema(
                    node_key=f"contrast/{slugify(contrast_title)}",
                    node_type=KnowledgeNodeType.CONTRAST,
                    title=contrast_title,
                    summary=f"Contrast the commonly confused ideas behind {error.title}.",
                    note_path=None,
                    source_note_path=source_note_path,
                    tags=["contrast", error.language, *error.tags[:2]],
                    metadata={
                        "practice_focus": error.incorrect_assumption,
                        "related_concepts": error.related_concepts,
                        "derived_from_error": error.error_signature,
                        "evidence": error.evidence,
                    },
                )
            )
        return nodes

    def _find_existing_support_node(self, candidate: KnowledgeNodeSchema) -> KnowledgeNodeSchema | None:
        direct = self._load_existing_node(candidate.node_key)
        if direct is not None:
            return direct
        normalized_title = self._normalize_text(candidate.title)
        normalized_summary = self._normalize_text(candidate.summary)
        with self.session_factory() as session:
            repo = KnowledgeNodeRepository(session)
            for entity in repo.list_all():
                if entity.node_type != candidate.node_type.value:
                    continue
                existing = self._entity_to_schema(entity)
                if self._normalize_text(existing.title) == normalized_title:
                    return existing
                if normalized_summary and self._normalize_text(existing.summary) == normalized_summary:
                    return existing
        return None

    def _build_supporting_edges(
        self,
        error: ErrorObject,
        error_node_key: str,
        nodes: list[KnowledgeNodeSchema],
    ) -> list[KnowledgeEdgeSchema]:
        edges: list[KnowledgeEdgeSchema] = []
        for node in nodes:
            relation_type = KnowledgeRelationType.COMMONLY_CONFUSED_WITH
            reason = error.incorrect_assumption
            if node.node_type == KnowledgeNodeType.CONCEPT:
                relation_type = KnowledgeRelationType.REVEALS_GAP_IN
                reason = f"{error.title} reveals a gap in {node.title}."
            elif node.node_type == KnowledgeNodeType.CONTRAST:
                relation_type = KnowledgeRelationType.CONTRASTS_WITH
                reason = f"{error.title} benefits from contrasting the nearby concepts explicitly."
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

    def _load_existing_node(self, node_key: str) -> KnowledgeNodeSchema | None:
        with self.session_factory() as session:
            entity = KnowledgeNodeRepository(session).get_by_key(node_key)
        return self._entity_to_schema(entity) if entity is not None else None

    def _entity_to_schema(self, entity) -> KnowledgeNodeSchema:
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

    def _contrast_title(self, error: ErrorObject) -> str | None:
        signature = error.error_signature.lower()
        if "-vs-" in signature:
            left, right = signature.split("-vs-", maxsplit=1)
            return f"Contrast: {left.replace('-', ' ')} vs {right.replace('-', ' ')}"
        concepts = error.related_concepts[:2]
        if len(concepts) >= 2:
            return f"Contrast: {concepts[0].replace('-', ' ')} vs {concepts[1].replace('-', ' ')}"
        if "arr" in error.incorrect_assumption.lower() and "&arr" in " ".join(error.evidence).lower():
            return "Contrast: arr vs &arr"
        return None

    def _normalize_text(self, text: str) -> str:
        lowered = text.lower()
        lowered = lowered.replace("&", " and ")
        lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
        tokens = [token for token in lowered.split() if token not in {"the", "a", "an", "in", "of"}]
        return " ".join(tokens)

    @staticmethod
    def _note_kind_for_node(node_type: KnowledgeNodeType) -> NoteKind:
        mapping = {
            KnowledgeNodeType.ERROR: NoteKind.ERROR,
            KnowledgeNodeType.CONCEPT: NoteKind.CONCEPT,
            KnowledgeNodeType.CONTRAST: NoteKind.CONTRAST,
            KnowledgeNodeType.PITFALL: NoteKind.PITFALL,
        }
        return mapping[node_type]
