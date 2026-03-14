"""Repository helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from obsidian_agent.domain.enums import JobState, ReviewState
from obsidian_agent.domain.models import (
    ErrorOccurrence,
    IngestionJob,
    KnowledgeEdge,
    KnowledgeNode,
    MaintenanceReport,
    NoteLink,
    NoteRecord,
    ReviewItem,
)
from obsidian_agent.domain.schemas import (
    ErrorObject,
    KnowledgeEdgeSchema,
    KnowledgeNodeSchema,
    NoteRecordSchema,
    ReviewProposal,
)


class NoteRepository:
    """Note metadata repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, data: NoteRecordSchema) -> NoteRecord:
        existing = self.session.scalar(select(NoteRecord).where(NoteRecord.vault_path == data.vault_path))
        now = datetime.now(timezone.utc)
        if existing:
            existing.title = data.title
            existing.kind = data.kind
            existing.status = data.status
            existing.created_at = data.created_at
            existing.updated_at = data.updated_at
            existing.source_type = data.source_type
            existing.source_ref = data.source_ref
            existing.content_hash = data.content_hash
            existing.word_count = data.word_count
            existing.indexed_at = now
            entity = existing
        else:
            entity = NoteRecord(
                vault_path=data.vault_path,
                title=data.title,
                kind=data.kind,
                status=data.status,
                created_at=data.created_at,
                updated_at=data.updated_at,
                source_type=data.source_type,
                source_ref=data.source_ref,
                content_hash=data.content_hash,
                word_count=data.word_count,
                indexed_at=now,
            )
            self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def list_all(self) -> list[NoteRecord]:
        return list(self.session.scalars(select(NoteRecord).order_by(NoteRecord.vault_path)).all())

    def get_by_path(self, vault_path: str) -> NoteRecord | None:
        return self.session.scalar(select(NoteRecord).where(NoteRecord.vault_path == vault_path))

    def delete_missing(self, active_paths: set[str]) -> None:
        """Remove stale metadata rows that no longer exist in the vault."""

        rows = list(self.session.scalars(select(NoteRecord)).all())
        for row in rows:
            if row.vault_path not in active_paths:
                self.session.delete(row)
        self.session.commit()


class IngestionJobRepository:
    """Capture job state repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, input_type: str, input_ref: str) -> IngestionJob:
        job = IngestionJob(input_type=input_type, input_ref=input_ref, state=JobState.PENDING.value)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def set_state(self, job_id: int, state: JobState, error_message: str | None = None) -> IngestionJob:
        job = self.session.get(IngestionJob, job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        job.state = state.value
        job.error_message = error_message
        self.session.commit()
        self.session.refresh(job)
        return job


class ReviewRepository:
    """Review queue repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        proposal: ReviewProposal,
        proposal_path: str,
        source_note_id: int | None = None,
        target_note_id: int | None = None,
    ) -> ReviewItem:
        item = ReviewItem(
            source_note_id=source_note_id,
            target_note_id=target_note_id,
            source_note_path=proposal.source_note_path,
            target_note_path=proposal.target_note_path,
            proposal_type=proposal.proposal_type.value,
            proposal_path=proposal_path,
            suggested_patch=proposal.suggested_patch,
            state=ReviewState.PENDING.value,
            risk_level=proposal.risk_level.value,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list_pending(self) -> list[ReviewItem]:
        return list(
            self.session.scalars(select(ReviewItem).where(ReviewItem.state == ReviewState.PENDING.value)).all()
        )

    def get(self, review_id: int) -> ReviewItem | None:
        return self.session.get(ReviewItem, review_id)

    def list_all(self) -> list[ReviewItem]:
        return list(self.session.scalars(select(ReviewItem).order_by(ReviewItem.id)).all())

    def set_state(self, review_id: int, state: ReviewState) -> ReviewItem:
        item = self.get(review_id)
        if item is None:
            raise ValueError(f"Review item not found: {review_id}")
        item.state = state.value
        self.session.commit()
        self.session.refresh(item)
        return item


class LinkRepository:
    """Suggested/explicit links repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, from_note_id: int | None, to_note_id: int | None, link_type: str, score: float) -> NoteLink:
        link = NoteLink(from_note_id=from_note_id, to_note_id=to_note_id, link_type=link_type, score=score)
        self.session.add(link)
        self.session.commit()
        self.session.refresh(link)
        return link


class MaintenanceRepository:
    """Maintenance report repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, report_type: str, report_key: str, content_path: str) -> MaintenanceReport:
        report = MaintenanceReport(report_type=report_type, report_key=report_key, content_path=content_path)
        self.session.add(report)
        self.session.commit()
        self.session.refresh(report)
        return report


class KnowledgeNodeRepository:
    """Knowledge node repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, data: KnowledgeNodeSchema) -> KnowledgeNode:
        entity = self.session.scalar(select(KnowledgeNode).where(KnowledgeNode.node_key == data.node_key))
        payload = {
            "node_type": data.node_type.value,
            "title": data.title,
            "summary": data.summary,
            "note_path": data.note_path,
            "source_note_path": data.source_note_path,
            "tags_json": json.dumps(data.tags, ensure_ascii=False),
            "metadata_json": json.dumps(data.metadata, ensure_ascii=False),
        }
        if entity:
            for key, value in payload.items():
                setattr(entity, key, value)
        else:
            entity = KnowledgeNode(node_key=data.node_key, **payload)
            self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def get_by_key(self, node_key: str) -> KnowledgeNode | None:
        return self.session.scalar(select(KnowledgeNode).where(KnowledgeNode.node_key == node_key))

    def list_all(self) -> list[KnowledgeNode]:
        return list(self.session.scalars(select(KnowledgeNode).order_by(KnowledgeNode.node_key)).all())


class KnowledgeEdgeRepository:
    """Knowledge edge repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: KnowledgeEdgeSchema, from_node_id: int | None, to_node_id: int | None) -> KnowledgeEdge:
        entity = KnowledgeEdge(
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            relation_type=data.relation_type.value,
            reason=data.reason,
            confidence=data.confidence,
        )
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity


class ErrorOccurrenceRepository:
    """Captured error occurrences repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, error: ErrorObject, raw_input: str, node_id: int | None, source_note_path: str | None) -> ErrorOccurrence:
        entity = ErrorOccurrence(
            node_id=node_id,
            source_note_path=source_note_path,
            title=error.title,
            language=error.language,
            error_signature=error.error_signature,
            raw_input=raw_input,
        )
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity
