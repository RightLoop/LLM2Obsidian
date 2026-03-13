from pathlib import Path

from fastapi.testclient import TestClient

from obsidian_agent.app import build_container, create_app
from obsidian_agent.config import Settings


def test_capture_text_creates_inbox_note(tmp_path: Path) -> None:
    settings = Settings(
        vault_root=tmp_path / "vault",
        sqlite_path=tmp_path / "db.sqlite3",
        vector_store_path=tmp_path / "vectors.json",
    )
    app = create_app()
    app.state.container = build_container(settings)
    client = TestClient(app)
    response = client.post(
        "/capture/text",
        json={"title": "Test", "text": "Alpha beta gamma delta epsilon zeta"},
    )
    assert response.status_code == 200
    payload = response.json()
    note_path = payload["note_path"]
    assert "00 Inbox/" in note_path
    created = (settings.vault_root / note_path).read_text(encoding="utf-8")
    assert "# Test" in created
    assert "kind: inbox" in created
