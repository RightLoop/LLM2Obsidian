"""Capture service."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import sessionmaker

from obsidian_agent.domain.enums import JobState, NoteKind, NoteStatus
from obsidian_agent.domain.schemas import CaptureInput, FrontmatterSchema, NormalizedCapture
from obsidian_agent.services.llm_service import LLMService
from obsidian_agent.services.obsidian_service import ObsidianService
from obsidian_agent.storage.repositories import IngestionJobRepository
from obsidian_agent.utils.markdown import render_template
from obsidian_agent.utils.time import compact_timestamp, now_utc


class CaptureService:
    """Normalize external content into Inbox notes."""

    def __init__(
        self,
        session_factory: sessionmaker,
        obsidian_service: ObsidianService,
        llm_service: LLMService,
        inbox_template_path: Path,
    ) -> None:
        self.session_factory = session_factory
        self.obsidian_service = obsidian_service
        self.llm_service = llm_service
        self.inbox_template_path = inbox_template_path

    async def capture(self, payload: CaptureInput) -> dict[str, object]:
        with self.session_factory() as session:
            job_repo = IngestionJobRepository(session)
            job = job_repo.create(payload.source_type.value, payload.source_ref or payload.title or "inline")
            job_repo.set_state(job.id, JobState.RUNNING)
            try:
                normalized = await self.llm_service.normalize_capture(payload)
                write_result = await self._write_inbox(payload, normalized)
                job_repo.set_state(job.id, JobState.SUCCEEDED)
                response_payload = {
                    "job_id": job.id,
                    "normalized": normalized.model_dump(mode="json"),
                }
                if hasattr(write_result, "model_dump"):
                    response_payload["note_path"] = write_result.target_path
                    response_payload["action_preview"] = write_result.model_dump(mode="json")
                else:
                    response_payload["note_path"] = write_result
                return response_payload
            except Exception as exc:
                job_repo.set_state(job.id, JobState.FAILED, str(exc))
                raise

    async def _write_inbox(self, payload: CaptureInput, normalized: NormalizedCapture) -> str | object:
        timestamp = now_utc()
        frontmatter = FrontmatterSchema(
            id=compact_timestamp(),
            kind=NoteKind.INBOX,
            status=NoteStatus.INBOX,
            source_type=payload.source_type,
            source_ref=payload.source_ref,
            created_at=timestamp,
            updated_at=timestamp,
            tags=normalized.tags,
            entities=normalized.entities,
            topics=normalized.topics,
            confidence=normalized.confidence,
            review_required=False,
        )
        body = render_template(
            self.inbox_template_path,
            {
                "title": normalized.title,
                "summary": normalized.summary,
                "key_points": "\n".join(f"- {item}" for item in normalized.key_points) or "-",
                "entities": "\n".join(f"- {item}" for item in normalized.entities) or "-",
                "related_notes": "\n".join(
                    f"- [[{item.path}]] ({item.reason}, {item.score:.2f})"
                    for item in normalized.related_candidates
                )
                or "-",
                "source_ref": payload.source_ref,
                "raw_excerpt": normalized.raw_excerpt,
            },
        )
        return await self.obsidian_service.create_note(
            folder=self.obsidian_service.settings.inbox_folder,
            title=normalized.title,
            frontmatter=frontmatter.model_dump(mode="json"),
            body=body,
        )
