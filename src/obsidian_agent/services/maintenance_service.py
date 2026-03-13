"""Maintenance workflows."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import sessionmaker

from obsidian_agent.domain.schemas import MaintenanceFinding
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
        for path in paths:
            content = await self.obsidian_service.read_note(path)
            if "[[" not in content:
                findings.append(MaintenanceFinding(path=path, reason="No explicit links", score=0.7))
        return findings

    async def find_duplicate_candidates(self) -> list[MaintenanceFinding]:
        findings: list[MaintenanceFinding] = []
        paths = await self.obsidian_service.list_notes()
        contents = {path: await self.obsidian_service.read_note(path) for path in paths}
        seen_titles: dict[str, str] = {}
        for path in paths:
            title = path.rsplit("/", 1)[-1].replace(".md", "").lower()
            if title in seen_titles:
                findings.append(MaintenanceFinding(path=path, reason=f"Similar title to {seen_titles[title]}", score=0.8))
            seen_titles[title] = path
        items = list(contents.items())
        for index, (path, content) in enumerate(items):
            for other_path, other_content in items[index + 1 :]:
                if content[:200] and content[:200] == other_content[:200]:
                    findings.append(MaintenanceFinding(path=path, reason=f"Content overlaps with {other_path}", score=0.85))
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

    async def generate_weekly_digest(self, week_key: str) -> str:
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
        created_path = created.target_path if hasattr(created, "target_path") else created
        with self.session_factory() as session:
            MaintenanceRepository(session).create("weekly_digest", week_key, created_path)
        return created_path
