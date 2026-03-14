"""Seed realistic demo notes into a target vault."""

from __future__ import annotations

from pathlib import Path

from obsidian_agent.utils.frontmatter import dump_frontmatter


def seed_demo_vault(vault: Path) -> list[str]:
    """Create or update a small C-language knowledge base for demos."""

    (vault / "00 Inbox").mkdir(parents=True, exist_ok=True)
    (vault / "01 Daily").mkdir(parents=True, exist_ok=True)
    (vault / "02 Literature").mkdir(parents=True, exist_ok=True)
    (vault / "03 Projects").mkdir(parents=True, exist_ok=True)
    (vault / "04 Evergreen").mkdir(parents=True, exist_ok=True)
    (vault / "05 Entities").mkdir(parents=True, exist_ok=True)
    (vault / "90 Review").mkdir(parents=True, exist_ok=True)

    notes = {
        "04 Evergreen/c-memory-model.md": (
            {
                "id": "seed-1",
                "kind": "evergreen",
                "status": "stable",
                "source_type": "manual",
                "source_ref": "",
            },
            "# C Memory Model\n\nC programs rely on explicit ownership, pointer validity, and careful lifetime rules.\n\n## Related Notes\n- [[03 Projects/c-build-pipeline.md]]\n- [[05 Entities/stdio.md]]\n",
        ),
        "03 Projects/c-build-pipeline.md": (
            {
                "id": "seed-2",
                "kind": "project",
                "status": "active",
                "source_type": "manual",
                "source_ref": "",
            },
            "# C Build Pipeline\n\nThe demo project compiles with `clang`, runs unit tests, and publishes warnings as CI annotations.\n",
        ),
        "02 Literature/c-struct-layout.md": (
            {
                "id": "seed-3",
                "kind": "literature",
                "status": "reference",
                "source_type": "url",
                "source_ref": "https://example.com/c-struct-layout",
            },
            "# Struct Layout Notes\n\nStructure padding affects ABI stability, binary serialization, and memory locality.\n",
        ),
        "05 Entities/stdio.md": (
            {
                "id": "seed-4",
                "kind": "entity",
                "status": "stable",
                "source_type": "manual",
                "source_ref": "",
            },
            "# stdio\n\n`stdio.h` defines buffered IO interfaces such as `printf`, `fprintf`, and `fopen`.\n",
        ),
        "00 Inbox/new-capture.md": (
            {
                "id": "seed-5",
                "kind": "inbox",
                "status": "inbox",
                "source_type": "text",
                "source_ref": "seed",
            },
            "# New Capture\n\nA fresh capture about pointer aliasing and ownership in C.\n",
        ),
    }

    paths: list[str] = []
    for relative_path, (frontmatter, body) in notes.items():
        target = vault / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(dump_frontmatter(frontmatter) + f"\n\n{body}", encoding="utf-8")
        paths.append(relative_path)
    return sorted(paths)
