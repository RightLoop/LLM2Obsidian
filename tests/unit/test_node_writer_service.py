from pathlib import Path

from obsidian_agent.domain.enums import KnowledgeNodeType
from obsidian_agent.domain.schemas import KnowledgeNodeSchema
from obsidian_agent.services.node_writer_service import NodeWriterService
from obsidian_agent.storage.db import create_session_factory
from obsidian_agent.storage.repositories import KnowledgeNodeRepository
from obsidian_agent.test_support import make_test_dir


def test_find_existing_support_node_reuses_legacy_contrast_key() -> None:
    root = make_test_dir("node_writer_legacy_contrast")
    session_factory = create_session_factory(root / "db.sqlite3")
    service = NodeWriterService(
        session_factory=session_factory,
        obsidian_service=None,  # type: ignore[arg-type]
        error_template_path=Path("unused"),
        smart_node_template_path=Path("unused"),
    )
    legacy = KnowledgeNodeSchema(
        node_key="contrast/contrast-sizeof-vs-strlen",
        node_type=KnowledgeNodeType.CONTRAST,
        title="Contrast: sizeof vs strlen",
        summary="legacy contrast",
        note_path="20 Smart/Contrast-sizeof-vs-strlen.md",
        source_note_path=None,
        tags=["contrast"],
        metadata={"derived_from_error": "sizeof-vs-strlen"},
    )
    with session_factory() as session:
        KnowledgeNodeRepository(session).upsert(legacy)

    candidate = KnowledgeNodeSchema(
        node_key="contrast/sizeof-vs-strlen",
        node_type=KnowledgeNodeType.CONTRAST,
        title="对比：sizeof 的语义 vs strlen 的语义",
        summary="new contrast",
        note_path=None,
        source_note_path=None,
        tags=["contrast"],
        metadata={
            "derived_from_error": "sizeof-vs-strlen",
            "legacy_node_keys": [
                "contrast/contrast-sizeof-vs-strlen",
                "contrast/sizeof-vs-strlen",
            ],
        },
    )

    reused = service._find_existing_support_node(candidate)

    assert reused is not None
    assert reused.node_key == "contrast/contrast-sizeof-vs-strlen"
