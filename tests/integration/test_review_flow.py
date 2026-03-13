import asyncio
from pathlib import Path
from shutil import copytree

from fastapi.testclient import TestClient

from obsidian_agent.app import build_container, create_app
from obsidian_agent.domain.enums import ProposalType, RiskLevel, ReviewState
from obsidian_agent.domain.schemas import ReviewProposal
def _build_review_client(tmp_path: Path):
    fixture_root = Path("tests/fixtures/review")
    vault_root = tmp_path / "vault"
    copytree(fixture_root, vault_root)
    settings_module = __import__("obsidian_agent.config", fromlist=["Settings"])
    settings = settings_module.Settings(
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
    return client, container, settings


def test_generate_review_creates_pending_item(tmp_path: Path) -> None:
    client, _, _ = _build_review_client(tmp_path)
    response = client.post("/review/generate", json={"note_path": "00 Inbox/new-input.md", "top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["review_id"] > 0
    assert payload["proposal"]["proposal_type"] in {
        "append_candidate",
        "merge_candidate",
        "review_only",
        "new_note",
    }


def test_approve_and_apply_append_review_updates_target_note(tmp_path: Path) -> None:
    _, container, settings = _build_review_client(tmp_path)
    proposal = ReviewProposal(
        proposal_type=ProposalType.APPEND_CANDIDATE,
        risk_level=RiskLevel.MEDIUM,
        title="Append Related Notes",
        source_note_path="00 Inbox/new-input.md",
        target_note_path="04 Evergreen/evergreen-note.md",
        rationale="Related topic overlap.",
        suggested_patch="- Link to [[00 Inbox/new-input.md]]",
        related_links=["00 Inbox/new-input.md"],
    )
    review_id, _ = asyncio.run(container.review_service.create_review_item(proposal))
    asyncio.run(container.review_service.approve(review_id))
    asyncio.run(container.review_service.apply_approved_review(review_id))
    updated = (settings.vault_root / "04 Evergreen/evergreen-note.md").read_text(encoding="utf-8")
    assert "Related Notes" in updated
    assert "[[00 Inbox/new-input.md]]" in updated
    assert "[[04 Evergreen/evergreen-note.md]]" not in updated


def test_high_risk_review_cannot_be_applied(tmp_path: Path) -> None:
    _, container, _ = _build_review_client(tmp_path)
    proposal = ReviewProposal(
        proposal_type=ProposalType.MERGE_CANDIDATE,
        risk_level=RiskLevel.HIGH,
        title="High Risk Merge",
        source_note_path="00 Inbox/new-input.md",
        target_note_path="04 Evergreen/evergreen-note.md",
        rationale="High risk merge candidate.",
        suggested_patch="Merge content",
        related_links=[],
    )
    review_id, _ = asyncio.run(container.review_service.create_review_item(proposal))
    asyncio.run(container.review_service.approve(review_id))
    try:
        asyncio.run(container.review_service.apply_approved_review(review_id))
    except ValueError as exc:
        assert "cannot be auto-applied" in str(exc)
    else:
        raise AssertionError("Expected high risk review application to fail")


def test_reject_review_keeps_state_rejected(tmp_path: Path) -> None:
    _, container, _ = _build_review_client(tmp_path)
    proposal = ReviewProposal(
        proposal_type=ProposalType.APPEND_CANDIDATE,
        risk_level=RiskLevel.MEDIUM,
        title="Reject Review",
        source_note_path="00 Inbox/new-input.md",
        target_note_path="04 Evergreen/evergreen-note.md",
        rationale="Test reject flow.",
        suggested_patch="- Link",
        related_links=[],
    )
    review_id, _ = asyncio.run(container.review_service.create_review_item(proposal))
    asyncio.run(container.review_service.reject(review_id))
    with container.session_factory() as session:
        repo = __import__(
            "obsidian_agent.storage.repositories",
            fromlist=["ReviewRepository"],
        ).ReviewRepository(session)
        item = repo.get(review_id)
        assert item is not None
        assert item.state == ReviewState.REJECTED.value
