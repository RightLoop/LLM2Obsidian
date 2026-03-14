from pathlib import Path

from fastapi.testclient import TestClient

from obsidian_agent.app import build_container, create_app
from obsidian_agent.config import Settings
from obsidian_agent.domain.models import IngestionJob
from obsidian_agent.test_support import make_test_dir


def _build_client(root: Path, dry_run: bool = False) -> tuple[TestClient, Settings]:
    settings = Settings(
        _env_file=None,
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
        dry_run=dry_run,
        obsidian_mode="filesystem",
    )
    return TestClient(create_app(settings)), settings


def test_capture_clipboard_creates_inbox_note() -> None:
    client, settings = _build_client(make_test_dir("capture_clipboard"))
    response = client.post("/capture/clipboard", json={"text": "Clipboard content about structured capture."})
    assert response.status_code == 200
    payload = response.json()
    note_path = payload["note_path"]
    created = (settings.vault_root / note_path).read_text(encoding="utf-8")
    assert "Clipboard content" in created


def test_capture_pdf_text_creates_inbox_note() -> None:
    client, settings = _build_client(make_test_dir("capture_pdf"))
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


def test_capture_url_uses_fetcher_output(monkeypatch) -> None:
    client, settings = _build_client(make_test_dir("capture_url"))

    async def fake_fetch(url: str, timeout_seconds: float = 30.0) -> tuple[str, str]:
        assert url == "https://example.com/article"
        assert timeout_seconds == 30.0
        return "Example Article", "Example article body about systems and notes."

    monkeypatch.setattr("obsidian_agent.api.routes_capture.fetch_url_text", fake_fetch)
    response = client.post("/capture/url", json={"url": "https://example.com/article"})
    assert response.status_code == 200
    payload = response.json()
    created = (settings.vault_root / payload["note_path"]).read_text(encoding="utf-8")
    assert "# Example Article" in created
    assert "https://example.com/article" in created


def test_capture_url_rejects_private_network_targets() -> None:
    client, _ = _build_client(make_test_dir("capture_url_private"))
    response = client.post("/capture/url", json={"url": "http://127.0.0.1/internal"})
    assert response.status_code == 400
    assert "blocked" in response.json()["detail"].lower()


def test_capture_dry_run_returns_action_preview_without_writing() -> None:
    client, settings = _build_client(make_test_dir("capture_dry_run"), dry_run=True)
    response = client.post("/capture/text", json={"title": "Dry Run", "text": "This should not write to disk."})
    assert response.status_code == 200
    payload = response.json()
    assert payload["action_preview"]["dry_run"] is True
    assert not (settings.vault_root / payload["note_path"]).exists()


def test_capture_persists_ingestion_job_state() -> None:
    client, settings = _build_client(make_test_dir("capture_job_state"))
    response = client.post("/capture/text", json={"title": "Job State", "text": "Persist job state."})
    assert response.status_code == 200
    payload = response.json()
    container = build_container(settings)
    with container.session_factory() as session:
        job = session.get(IngestionJob, payload["job_id"])
        assert job is not None
        assert job.state == "succeeded"
