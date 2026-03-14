from fastapi.testclient import TestClient

from obsidian_agent.app import build_container, create_app
from obsidian_agent.config import Settings
from obsidian_agent.domain.models import ErrorOccurrence, KnowledgeNode
from obsidian_agent.test_support import make_test_dir


def test_smart_error_capture_creates_error_node_and_db_records() -> None:
    root = make_test_dir("smart_error_capture")
    settings = Settings(
        _env_file=None,
        ui_admin_token="test-token",
        obsidian_mode="filesystem",
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
        smart_errors_folder="21 Errors",
    )
    client = TestClient(create_app(settings))

    response = client.post(
        "/smart/error-capture",
        json={
            "title": "sizeof 和 strlen 混淆",
            "prompt": "我把 sizeof(arr) 当成字符串长度使用，结果输出包含结尾空字符。",
            "code": 'char arr[] = "abc"; printf("%zu", sizeof(arr));',
            "user_analysis": "我以为 sizeof 会返回可见字符数量。",
            "language": "c",
            "source_ref": "manual/c-sizeof",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["error"]["error_signature"] == "sizeof-vs-strlen"
    assert payload["node"]["node_type"] == "error"
    note_path = payload["node"]["note_path"]
    assert note_path.startswith("21 Errors/")
    created = (settings.vault_root / note_path).read_text(encoding="utf-8")
    assert "# sizeof 和 strlen 混淆" in created
    assert "Incorrect Assumption" in created

    container = build_container(settings)
    with container.session_factory() as session:
        node = session.query(KnowledgeNode).one()
        occurrence = session.query(ErrorOccurrence).one()
        assert node.node_key == "error/sizeof-vs-strlen"
        assert occurrence.error_signature == "sizeof-vs-strlen"


def test_smart_node_pack_builds_relations_between_related_errors() -> None:
    root = make_test_dir("smart_node_pack")
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
    assert first.status_code == 200
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
    assert second.status_code == 200

    pack = client.post(
        "/smart/node-pack",
        json={"node_key": first.json()["node"]["node_key"], "top_k": 5},
    )
    assert pack.status_code == 200
    payload = pack.json()
    assert payload["stored_edges"] >= 1
    assert payload["pack"]["edges"][0]["relation_type"] == "commonly_confused_with"
    assert "sizeof" in payload["pack"]["summary"].lower()
