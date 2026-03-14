import asyncio
from pathlib import Path
from shutil import copytree

from fastapi.testclient import TestClient

from obsidian_agent.app import build_container, create_app
from obsidian_agent.config import Settings


def _build_maintenance_client(tmp_path: Path):
    fixture_root = Path("tests/fixtures/maintenance")
    vault_root = tmp_path / "vault"
    copytree(fixture_root, vault_root)
    settings = Settings(
        obsidian_mode="filesystem",
        vault_root=vault_root,
        sqlite_path=tmp_path / "db.sqlite3",
        vector_store_path=tmp_path / "vectors.json",
    )
    app = create_app()
    container = build_container(settings)
    app.state.container = container
    asyncio.run(container.indexing_service.reindex_all())
    client = TestClient(app)
    return client, settings


def _build_maintenance_client_with_dry_run(tmp_path: Path):
    fixture_root = Path("tests/fixtures/maintenance")
    vault_root = tmp_path / "vault"
    copytree(fixture_root, vault_root)
    settings = Settings(
        obsidian_mode="filesystem",
        vault_root=vault_root,
        sqlite_path=tmp_path / "db.sqlite3",
        vector_store_path=tmp_path / "vectors.json",
        dry_run=True,
    )
    app = create_app()
    container = build_container(settings)
    app.state.container = container
    asyncio.run(container.indexing_service.reindex_all())
    client = TestClient(app)
    return client, settings


def test_find_duplicate_candidates_flags_similar_c_notes(tmp_path: Path) -> None:
    client, _ = _build_maintenance_client(tmp_path)
    response = client.get("/maintenance/duplicates")
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["path"] == "00 Inbox/c-pointer-cheatsheet-copy.md" for item in items)


def test_find_orphan_notes_flags_unlinked_note(tmp_path: Path) -> None:
    client, _ = _build_maintenance_client(tmp_path)
    response = client.get("/maintenance/orphans")
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["path"] == "03 Projects/c-build-pipeline.md" for item in items) is False
    assert any(item["path"] == "05 Entities/stdio.md" for item in items)


def test_find_metadata_issues_flags_missing_frontmatter(tmp_path: Path) -> None:
    client, _ = _build_maintenance_client(tmp_path)
    response = client.get("/maintenance/metadata-issues")
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["path"] == "05 Entities/stdio.md" for item in items)


def test_generate_weekly_digest_creates_digest_note(tmp_path: Path) -> None:
    client, settings = _build_maintenance_client(tmp_path)
    response = client.post("/maintenance/weekly-digest", json={"week_key": "2026-W11"})
    assert response.status_code == 200
    note_path = response.json()["path"]
    digest_note = (settings.vault_root / note_path).read_text(encoding="utf-8")
    assert "Weekly Digest - 2026-W11" in digest_note
    assert "Highlights" in digest_note


def test_generate_weekly_digest_dry_run_returns_action_preview(tmp_path: Path) -> None:
    client, settings = _build_maintenance_client_with_dry_run(tmp_path)
    response = client.post("/maintenance/weekly-digest", json={"week_key": "2026-W11"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "dry_run"
    assert payload["action_preview"]["dry_run"] is True
    assert payload["action_preview"]["details"]["week_key"] == "2026-W11"
    assert not (settings.vault_root / "01 Daily/Weekly Digest - 2026-W11.md").exists()
