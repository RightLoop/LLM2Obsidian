from pathlib import Path

from fastapi.testclient import TestClient

from obsidian_agent.app import build_container, create_app
from obsidian_agent.config import Settings
from obsidian_agent.domain.models import IngestionJob


def _build_client(tmp_path: Path, dry_run: bool = False) -> tuple[TestClient, Settings]:
    settings = Settings(
        vault_root=tmp_path / "vault",
        sqlite_path=tmp_path / "db.sqlite3",
        vector_store_path=tmp_path / "vectors.json",
        dry_run=dry_run,
        obsidian_mode="filesystem",
    )
    app = create_app()
    app.state.container = build_container(settings)
    return TestClient(app), settings


def test_capture_clipboard_creates_inbox_note(tmp_path: Path) -> None:
    client, settings = _build_client(tmp_path)
    response = client.post("/capture/clipboard", json={"text": "Clipboard content about structured capture."})
    assert response.status_code == 200
    payload = response.json()
    note_path = payload["note_path"]
    created = (settings.vault_root / note_path).read_text(encoding="utf-8")
    assert "Clipboard content" in created


def test_capture_pdf_text_creates_inbox_note(tmp_path: Path) -> None:
    client, settings = _build_client(tmp_path)
    response = client.post(
        "/capture/pdf-text",
        json={
            "title": "Paper Notes",
            "text": "PDF extracted text about a paper and its findings.",
            "source_ref": "paper.pdf",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    created = (settings.vault_root / payload["note_path"]).read_text(encoding="utf-8")
    assert "# Paper Notes" in created
    assert "paper.pdf" in created


def test_capture_url_uses_fetcher_output(tmp_path: Path, monkeypatch) -> None:
    client, settings = _build_client(tmp_path)

    async def fake_fetch(url: str) -> tuple[str, str]:
        assert url == "https://example.com/article"
        return "Example Article", "Example article body about systems and notes."

    monkeypatch.setattr("obsidian_agent.api.routes_capture.fetch_url_text", fake_fetch)
    response = client.post("/capture/url", json={"url": "https://example.com/article"})
    assert response.status_code == 200
    payload = response.json()
    created = (settings.vault_root / payload["note_path"]).read_text(encoding="utf-8")
    assert "# Example Article" in created
    assert "https://example.com/article" in created


def test_capture_dry_run_returns_action_preview_without_writing(tmp_path: Path) -> None:
    client, settings = _build_client(tmp_path, dry_run=True)
    response = client.post("/capture/text", json={"title": "Dry Run", "text": "This should not write to disk."})
    assert response.status_code == 200
    payload = response.json()
    assert payload["action_preview"]["dry_run"] is True
    assert not (settings.vault_root / payload["note_path"]).exists()


def test_capture_persists_ingestion_job_state(tmp_path: Path) -> None:
    client, settings = _build_client(tmp_path)
    response = client.post("/capture/text", json={"title": "Job State", "text": "Persist job state."})
    assert response.status_code == 200
    payload = response.json()
    container = build_container(settings)
    with container.session_factory() as session:
        job = session.get(IngestionJob, payload["job_id"])
        assert job is not None
        assert job.state == "succeeded"
