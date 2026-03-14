from fastapi.testclient import TestClient

from obsidian_agent.app import create_app
from obsidian_agent.config import Settings
from obsidian_agent.test_support import make_test_dir


def test_smart_teach_returns_markdown_and_sections() -> None:
    root = make_test_dir("smart_teach")
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
            "title": "sizeof 和 strlen 混淆",
            "prompt": "我把 sizeof(arr) 当成字符串长度使用。",
            "code": 'char arr[] = "abc"; printf("%zu", sizeof(arr));',
            "user_analysis": "我以为 sizeof 会返回可见字符数量。",
            "language": "c",
        },
    )
    second = client.post(
        "/smart/error-capture",
        json={
            "title": "strlen 不统计终止符",
            "prompt": "我没有意识到 strlen 不会包含结尾的空字符。",
            "code": 'char arr[] = "abc"; printf("%zu", strlen(arr));',
            "user_analysis": "我把 strlen 和内存大小混成一类了。",
            "language": "c",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    response = client.post(
        "/smart/teach",
        json={"node_key": first.json()["node"]["node_key"], "top_k": 5, "delivery_mode": "remote"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"].startswith("Teaching Pack:")
    assert payload["sections"]
    assert payload["markdown"].startswith("# ")
    assert "## Practice Drills" in payload["markdown"]
    assert "telemetry" in payload
    assert payload["delivery_mode"] in {"remote", "local-fallback", "offline-fallback"}
    assert payload["telemetry"]["delivery_mode_requested"] == "remote"
    assert payload["telemetry"]["pack_token_budget_hint"] >= 300
    assert payload["pack"]["recommended_output_shape"]
    assert payload["pack"]["condensed_context"]
    assert isinstance(payload["pack"]["do_not_repeat"], list)


def test_smart_related_nodes_returns_related_entries() -> None:
    root = make_test_dir("smart_related_nodes")
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
            "title": "pointer and array decay",
            "prompt": "I thought arrays stayed as full arrays in function parameters.",
            "code": 'void f(int arr[10]) { printf("%zu", sizeof(arr)); }',
            "user_analysis": "I expected sizeof(arr) to behave like the call site.",
            "language": "c",
        },
    )
    second = client.post(
        "/smart/error-capture",
        json={
            "title": "array and pointer confusion",
            "prompt": "I assumed arr and &arr had the same pointer type.",
            "code": 'int arr[4]; int *p = arr; int (*q)[4] = &arr;',
            "user_analysis": "I collapsed array and pointer semantics together.",
            "language": "c",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    response = client.get(
        "/smart/related-nodes",
        params={"node_key": first.json()["node"]["node_key"], "top_k": 5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
