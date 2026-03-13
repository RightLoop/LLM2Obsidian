"""Vault access service."""

from __future__ import annotations

from pathlib import Path

from obsidian_agent.config import Settings
from obsidian_agent.domain.schemas import ActionPreview
from obsidian_agent.integrations.obsidian_rest_client import ObsidianRestClient
from obsidian_agent.utils.frontmatter import dump_frontmatter, parse_frontmatter, patch_frontmatter
from obsidian_agent.utils.time import compact_timestamp, now_utc


class ObsidianService:
    """Single gateway for all Vault reads and writes."""

    def __init__(self, settings: Settings, client: ObsidianRestClient | None = None) -> None:
        self.settings = settings
        self.client = client
        self.settings.vault_root.mkdir(parents=True, exist_ok=True)
        self.settings.inbox_folder_path.mkdir(parents=True, exist_ok=True)
        self.settings.review_folder_path.mkdir(parents=True, exist_ok=True)

    def _path(self, vault_path: str) -> Path:
        return self.settings.vault_root / vault_path

    async def search_notes(
        self, query: str, top_k: int = 5, filters: dict[str, str] | None = None
    ) -> list[str]:
        del filters
        results: list[str] = []
        for path in self.settings.vault_root.rglob("*.md"):
            content = path.read_text(encoding="utf-8")
            if query.lower() in content.lower():
                results.append(str(path.relative_to(self.settings.vault_root)).replace("\\", "/"))
            if len(results) >= top_k:
                break
        return results

    async def read_note(self, path: str) -> str:
        return self._path(path).read_text(encoding="utf-8")

    async def read_notes(self, paths: list[str]) -> dict[str, str]:
        return {path: await self.read_note(path) for path in paths}

    async def create_note(
        self, folder: str, title: str, frontmatter: dict[str, object], body: str
    ) -> str | ActionPreview:
        folder_path = self.settings.vault_root / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        filename = self._build_filename(folder, title)
        target = folder_path / filename
        content = f"{dump_frontmatter(frontmatter)}\n\n{body.strip()}\n"
        if self.settings.dry_run:
            return ActionPreview(
                dry_run=True,
                action="create_note",
                target_path=str(target.relative_to(self.settings.vault_root)).replace("\\", "/"),
                details={"title": title},
            )
        target.write_text(content, encoding="utf-8")
        return str(target.relative_to(self.settings.vault_root)).replace("\\", "/")

    async def append_to_note(self, path: str, section: str, content: str) -> ActionPreview | str:
        existing = await self.read_note(path)
        marker = f"## {section}"
        if marker in existing:
            updated = existing.rstrip() + f"\n\n{content.strip()}\n"
        else:
            updated = existing.rstrip() + f"\n\n{marker}\n{content.strip()}\n"
        if self.settings.dry_run:
            return ActionPreview(dry_run=True, action="append_to_note", target_path=path)
        self._path(path).write_text(updated, encoding="utf-8")
        return path

    async def replace_section(self, path: str, section_heading: str, content: str) -> ActionPreview | str:
        existing = await self.read_note(path)
        marker = f"## {section_heading}"
        if marker not in existing:
            return await self.append_to_note(path, section_heading, content)
        prefix, _, remainder = existing.partition(marker)
        body_lines = remainder.splitlines()
        next_heading_idx = None
        for idx, line in enumerate(body_lines[1:], start=1):
            if line.startswith("## "):
                next_heading_idx = idx
                break
        suffix = "\n".join(body_lines[next_heading_idx:]) if next_heading_idx else ""
        updated = f"{prefix}{marker}\n{content.strip()}\n"
        if suffix:
            updated += suffix
        if self.settings.dry_run:
            return ActionPreview(dry_run=True, action="replace_section", target_path=path)
        self._path(path).write_text(updated, encoding="utf-8")
        return path

    async def update_frontmatter(self, path: str, patch: dict[str, object]) -> ActionPreview | str:
        existing = await self.read_note(path)
        updated = patch_frontmatter(existing, patch)
        if self.settings.dry_run:
            return ActionPreview(dry_run=True, action="update_frontmatter", target_path=path)
        self._path(path).write_text(updated, encoding="utf-8")
        return path

    async def move_note(self, path: str, target_folder: str) -> ActionPreview | str:
        source = self._path(path)
        target_dir = self.settings.vault_root / target_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        if self.settings.dry_run:
            return ActionPreview(
                dry_run=True,
                action="move_note",
                target_path=str(target.relative_to(self.settings.vault_root)).replace("\\", "/"),
            )
        source.rename(target)
        return str(target.relative_to(self.settings.vault_root)).replace("\\", "/")

    async def list_notes(self) -> list[str]:
        return [
            str(path.relative_to(self.settings.vault_root)).replace("\\", "/")
            for path in self.settings.vault_root.rglob("*.md")
        ]

    async def parse_note(self, path: str) -> tuple[dict[str, object], str]:
        content = await self.read_note(path)
        return parse_frontmatter(content)

    def _build_filename(self, folder: str, title: str) -> str:
        timestamp = now_utc()
        safe_title = " ".join(title.replace("/", " ").replace("\\", " ").split()).strip() or "Untitled"
        if folder == self.settings.inbox_folder:
            return f"{timestamp.strftime('%Y-%m-%d %H%M')} - {safe_title}.md"
        if folder == self.settings.review_folder:
            return f"Review - {safe_title} - {compact_timestamp()}.md"
        if safe_title.lower().startswith("weekly digest"):
            return f"{safe_title}.md"
        return f"{safe_title}.md"
