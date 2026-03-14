"""Maintenance workflows."""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from obsidian_agent.domain.schemas import MaintenanceFinding
from obsidian_agent.domain.schemas import ActionPreview
from obsidian_agent.services.llm_service import LLMService
from obsidian_agent.services.obsidian_service import ObsidianService
from obsidian_agent.storage.repositories import MaintenanceRepository, NoteRepository
from obsidian_agent.utils.markdown import render_template


class MaintenanceService:
    """Run scheduled knowledge base checks."""

    def __init__(
        self,
        session_factory: sessionmaker,
        obsidian_service: ObsidianService,
        llm_service: LLMService,
        weekly_digest_template_path: Path,
    ) -> None:
        self.session_factory = session_factory
        self.obsidian_service = obsidian_service
        self.llm_service = llm_service
        self.weekly_digest_template_path = weekly_digest_template_path

    async def find_orphan_notes(self) -> list[MaintenanceFinding]:
        findings: list[MaintenanceFinding] = []
        paths = await self.obsidian_service.list_notes()
        contents = {path: await self.obsidian_service.read_note(path) for path in paths}
        for path in paths:
            content = contents[path]
            outgoing = self._extract_links(content)
            incoming = any(path in self._extract_links(other) for other_path, other in contents.items() if other_path != path)
            if not outgoing and not incoming:
                findings.append(
                    MaintenanceFinding(
                        path=path,
                        reason="No incoming or outgoing explicit links",
                        score=0.85,
                    )
                )
        return findings

    async def find_duplicate_candidates(self) -> list[MaintenanceFinding]:
        findings: list[MaintenanceFinding] = []
        paths = await self.obsidian_service.list_notes()
        contents = {path: await self.obsidian_service.read_note(path) for path in paths}
        items = list(contents.items())
        for index, (path, content) in enumerate(items):
            for other_path, other_content in items[index + 1 :]:
                title_score = self._similarity(self._title(path), self._title(other_path))
                content_score = self._similarity(content[:600], other_content[:600])
                combined = (title_score * 0.45) + (content_score * 0.55)
                if combined >= 0.75:
                    findings.append(
                        MaintenanceFinding(
                            path=path,
                            reason=f"Potential duplicate of {other_path}",
                            score=round(combined, 3),
                        )
                    )
        return findings

    async def find_metadata_issues(self) -> list[MaintenanceFinding]:
        findings: list[MaintenanceFinding] = []
        paths = await self.obsidian_service.list_notes()
        for path in paths:
            frontmatter, _ = await self.obsidian_service.parse_note(path)
            for key in ("id", "kind", "status", "source_type"):
                if key not in frontmatter:
                    findings.append(MaintenanceFinding(path=path, reason=f"Missing frontmatter: {key}", score=1.0))
        return findings

    async def generate_weekly_digest(self, week_key: str) -> str | ActionPreview:
        note_bodies = []
        with self.session_factory() as session:
            notes = NoteRepository(session).list_all()
            for note in notes[:20]:
                note_bodies.append(await self.obsidian_service.read_note(note.vault_path))
        digest = await self.llm_service.generate_digest(note_bodies)
        markdown = render_template(
            self.weekly_digest_template_path,
            {"week_key": week_key, "content": digest},
        )
        created = await self.obsidian_service.create_note(
            folder="01 Daily",
            title=f"Weekly Digest - {week_key}",
            frontmatter={"kind": "digest", "status": "draft", "week_key": week_key},
            body=markdown,
        )
        if hasattr(created, "model_dump"):
            created.details["week_key"] = week_key
            return created
        created_path = created.target_path if hasattr(created, "target_path") else created
        with self.session_factory() as session:
            MaintenanceRepository(session).create("weekly_digest", week_key, created_path)
        return created_path

    @staticmethod
    def _extract_links(content: str) -> set[str]:
        return set(re.findall(r"\[\[([^\]]+)\]\]", content))

    @staticmethod
    def _title(path: str) -> str:
        return path.rsplit("/", 1)[-1].replace(".md", "").lower()

    @staticmethod
    def _similarity(left: str, right: str) -> float:
        return difflib.SequenceMatcher(None, left.lower(), right.lower()).ratio()
