from fastapi.testclient import TestClient

from obsidian_agent.app import build_container, create_app
from obsidian_agent.config import Settings
from obsidian_agent.domain.models import ErrorOccurrence, KnowledgeEdge, KnowledgeNode
from obsidian_agent.test_support import make_test_dir


def test_smart_error_capture_creates_error_and_supporting_nodes() -> None:
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
            "title": "sizeof vs strlen confusion",
            "prompt": "I treated sizeof(arr) as the visible string length in C.",
            "code": 'char arr[] = "abc"; printf("%zu", sizeof(arr));',
            "user_analysis": "I assumed sizeof returned only visible characters.",
            "language": "c",
            "source_ref": "manual/c-sizeof",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["error"]["error_signature"] == "sizeof-vs-strlen"
    assert payload["node"]["node_type"] == "error"
    assert payload["related_nodes"]
    assert payload["stored_edges"] >= 1

    note_path = payload["node"]["note_path"]
    assert note_path.startswith("21 Errors/")
    created = (settings.vault_root / note_path).read_text(encoding="utf-8")
    assert "# sizeof vs strlen confusion" in created
    assert "Incorrect Assumption" in created

    container = build_container(settings)
    with container.session_factory() as session:
        nodes = session.query(KnowledgeNode).all()
        edges = session.query(KnowledgeEdge).all()
        occurrence = session.query(ErrorOccurrence).one()
        assert any(node.node_key == "error/sizeof-vs-strlen" for node in nodes)
        assert any(node.node_type == "concept" for node in nodes)
        assert any(node.node_type == "pitfall" for node in nodes)
        assert edges
        assert occurrence.error_signature == "sizeof-vs-strlen"


def test_smart_error_capture_reuses_existing_supporting_nodes() -> None:
    root = make_test_dir("smart_error_capture_novelty")
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
            "prompt": "I thought array parameters stayed arrays inside a function.",
            "code": 'void f(int arr[10]) { printf("%zu", sizeof(arr)); }',
            "user_analysis": "I expected the array length to survive parameter passing.",
            "language": "c",
        },
    )
    second = client.post(
        "/smart/error-capture",
        json={
            "title": "parameter decay again",
            "prompt": "I still confuse array parameters with full arrays in C.",
            "code": 'void g(int arr[3]) { printf("%zu", sizeof(arr)); }',
            "user_analysis": "I repeated the same misunderstanding about array decay.",
            "language": "c",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    container = build_container(settings)
    with container.session_factory() as session:
        nodes = session.query(KnowledgeNode).all()
        concept_keys = [node.node_key for node in nodes if node.node_type == "concept"]
        pitfall_keys = [node.node_key for node in nodes if node.node_type == "pitfall"]
        assert len(concept_keys) == len(set(concept_keys))
        assert len(pitfall_keys) == len(set(pitfall_keys))


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
            "title": "sizeof vs strlen confusion",
            "prompt": "I treated sizeof(arr) as the visible string length.",
            "code": 'char arr[] = "abc"; printf("%zu", sizeof(arr));',
            "user_analysis": "I assumed sizeof only tracked visible characters.",
            "language": "c",
        },
    )
    assert first.status_code == 200
    second = client.post(
        "/smart/error-capture",
        json={
            "title": "strlen terminator confusion",
            "prompt": "I expected strlen to count the null terminator.",
            "code": 'char arr[] = "abc"; printf("%zu", strlen(arr));',
            "user_analysis": "I mixed up string length and storage size.",
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
