from fastapi.testclient import TestClient

from obsidian_agent.app import create_app
from obsidian_agent.config import Settings
from obsidian_agent.test_support import make_test_dir


def test_smart_relink_dry_run_returns_preview() -> None:
    root = make_test_dir("smart_relink_preview")
    settings = Settings(
        _env_file=None,
        obsidian_mode="filesystem",
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
        smart_errors_folder="21 Errors",
    )
    client = TestClient(create_app(settings))

    first = client.post(
        "/smart/error-capture",
        json={
            "title": "pointer decay",
            "prompt": "I thought array parameters stayed arrays inside a function.",
            "code": 'void f(int arr[10]) { printf("%zu", sizeof(arr)); }',
            "user_analysis": "I expected the array length to survive parameter passing.",
            "language": "c",
        },
    )
    second = client.post(
        "/smart/error-capture",
        json={
            "title": "pointer confusion",
            "prompt": "I assumed arr and &arr had the same type.",
            "code": "int arr[4]; int *p = arr; int (*q)[4] = &arr;",
            "user_analysis": "I collapsed array and pointer semantics together.",
            "language": "c",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    response = client.post(
        "/smart/relink",
        json={
            "node_key": first.json()["node"]["node_key"],
            "top_k": 5,
            "create_review": True,
            "dry_run": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["action_preview"]["dry_run"] is True
    assert payload["review_id"] is None
    assert payload["related_section_markdown"].startswith("- ")
    assert payload["related_section_markdown"].count("\n") <= 2


def test_smart_relink_creates_review_item() -> None:
    root = make_test_dir("smart_relink_review")
    settings = Settings(
        _env_file=None,
        obsidian_mode="filesystem",
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
        smart_errors_folder="21 Errors",
    )
    client = TestClient(create_app(settings))

    first = client.post(
        "/smart/error-capture",
        json={
            "title": "sizeof vs strlen",
            "prompt": "I treated sizeof(arr) as the string length.",
            "code": 'char arr[] = "abc"; printf("%zu", sizeof(arr));',
            "user_analysis": "I assumed sizeof returned visible characters only.",
            "language": "c",
        },
    )
    second = client.post(
        "/smart/error-capture",
        json={
            "title": "strlen terminator confusion",
            "prompt": "I expected strlen to count the null terminator.",
            "code": 'char arr[] = "abc"; printf("%zu", strlen(arr));',
            "user_analysis": "I blurred string length and storage size.",
            "language": "c",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    response = client.post(
        "/smart/relink",
        json={
            "node_key": first.json()["node"]["node_key"],
            "top_k": 5,
            "create_review": True,
            "dry_run": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["review_id"] is not None
    assert payload["proposal_path"]
    assert payload["related_section_markdown"].count("\n") <= 2

    pending = client.get("/review/pending")
    assert pending.status_code == 200
    items = pending.json()["items"]
    assert any(item["id"] == payload["review_id"] for item in items)
