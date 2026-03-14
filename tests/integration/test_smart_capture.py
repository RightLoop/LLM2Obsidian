from fastapi.testclient import TestClient

from obsidian_agent.app import build_container, create_app
from obsidian_agent.config import Settings
from obsidian_agent.domain.models import ErrorOccurrence, KnowledgeEdge, KnowledgeNode
from obsidian_agent.test_support import make_test_dir


def test_smart_error_capture_creates_supporting_nodes_and_edges() -> None:
    root = make_test_dir("smart_error_capture")
    settings = Settings(
        _env_file=None,
        ui_admin_token="test-token",
        obsidian_mode="filesystem",
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
        smart_errors_folder="21 Errors",
        smart_nodes_folder="20 Smart",
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
    assert payload["stored_edges"] >= 2
    assert any(item["node_type"] == "contrast" for item in payload["related_nodes"])
    assert "telemetry" in payload
    assert "error_extractor" in payload["telemetry"]

    error_note_path = payload["node"]["note_path"]
    assert error_note_path.startswith("21 Errors/")
    error_note_text = (settings.vault_root / error_note_path).read_text(encoding="utf-8")
    assert "# sizeof vs strlen confusion" in error_note_text

    support_paths = [item["note_path"] for item in payload["related_nodes"] if item["note_path"]]
    assert any(path.startswith("20 Smart/") for path in support_paths)

    container = build_container(settings)
    with container.session_factory() as session:
        nodes = session.query(KnowledgeNode).all()
        edges = session.query(KnowledgeEdge).all()
        occurrence = session.query(ErrorOccurrence).one()
        assert any(node.node_key == "error/sizeof-vs-strlen" for node in nodes)
        assert any(node.node_type == "concept" for node in nodes)
        assert any(node.node_type == "pitfall" for node in nodes)
        assert any(node.node_type == "contrast" for node in nodes)
        assert edges
        assert occurrence.error_signature == "sizeof-vs-strlen"


def test_smart_error_capture_reuses_near_duplicate_supporting_nodes() -> None:
    root = make_test_dir("smart_error_capture_novelty")
    settings = Settings(
        _env_file=None,
        obsidian_mode="filesystem",
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
        smart_errors_folder="21 Errors",
        smart_nodes_folder="20 Smart",
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
    second = client.post(
        "/smart/error-capture",
        json={
            "title": "sizeof versus strlen again",
            "prompt": "I still mix up sizeof(arr) and strlen(arr) when reading C strings.",
            "code": 'char arr[] = "abc"; printf("%zu %zu", sizeof(arr), strlen(arr));',
            "user_analysis": "I keep treating storage size and logical string length as the same thing.",
            "language": "c",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    container = build_container(settings)
    with container.session_factory() as session:
        nodes = session.query(KnowledgeNode).all()
        contrast_titles = [node.title for node in nodes if node.node_type == "contrast"]
        concept_keys = [node.node_key for node in nodes if node.node_type == "concept"]
        assert len(contrast_titles) == 1
        assert len(concept_keys) == len(set(concept_keys))


def test_smart_node_pack_builds_relations_between_related_errors() -> None:
    root = make_test_dir("smart_node_pack")
    settings = Settings(
        _env_file=None,
        obsidian_mode="filesystem",
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
        smart_errors_folder="21 Errors",
        smart_nodes_folder="20 Smart",
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
            "title": "array and pointer confusion",
            "prompt": "I assumed arr and &arr had the same pointer type.",
            "code": "int arr[4]; int *p = arr; int (*q)[4] = &arr;",
            "user_analysis": "I collapsed array and pointer semantics together.",
            "language": "c",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    pack = client.post(
        "/smart/node-pack",
        json={"node_key": first.json()["node"]["node_key"], "top_k": 5},
    )
    assert pack.status_code == 200
    payload = pack.json()
    assert payload["stored_edges"] >= 1
    assert payload["pack"]["edges"]
    assert "telemetry" in payload
    assert "relation_miner" in payload["telemetry"]
