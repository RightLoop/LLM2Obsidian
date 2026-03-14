from obsidian_agent.config import Settings
from obsidian_agent.services.obsidian_service import ObsidianService
from obsidian_agent.test_support import make_test_dir


def test_build_filename_sanitizes_windows_reserved_characters() -> None:
    root = make_test_dir("obsidian_filename")
    settings = Settings(
        _env_file=None,
        obsidian_mode="filesystem",
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
    )
    service = ObsidianService(settings)

    filename = service._build_filename(settings.smart_nodes_folder, 'char* 指针: <test>?')

    assert "*" not in filename
    assert ":" not in filename
    assert "<" not in filename
    assert "?" not in filename
    assert filename.endswith(".md")
