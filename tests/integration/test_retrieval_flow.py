from pathlib import Path
from shutil import copytree
import asyncio

from fastapi.testclient import TestClient

from obsidian_agent.app import build_container, create_app
from obsidian_agent.config import Settings


def _build_indexed_client(tmp_path: Path):
    fixture_root = Path("tests/fixtures/retrieval")
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
    client = TestClient(app)
    return client, container


def test_search_returns_keyword_and_semantic_results(tmp_path: Path) -> None:
    client, container = _build_indexed_client(tmp_path)
    asyncio.run(container.indexing_service.reindex_all())
    response = client.get("/search", params={"q": "semantic search retrieval for notes"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    top_paths = [item["path"] for item in payload["results"]]
    assert "02 Literature/rag-pipeline.md" in top_paths


def test_find_related_notes_excludes_source_note(tmp_path: Path) -> None:
    client, container = _build_indexed_client(tmp_path)
    asyncio.run(container.indexing_service.reindex_all())
    response = client.get("/notes/related", params={"path": "00 Inbox/new-capture.md"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert all(item["path"] != "00 Inbox/new-capture.md" for item in payload["results"])
    assert any("Semantic similarity" in item["reason"] or "Keyword overlap" in item["reason"] for item in payload["results"])
