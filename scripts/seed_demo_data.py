"""Seed a small demo vault."""

from pathlib import Path

from obsidian_agent.utils.frontmatter import dump_frontmatter


def main() -> None:
    vault = Path("data/demo_vault")
    (vault / "00 Inbox").mkdir(parents=True, exist_ok=True)
    (vault / "04 Evergreen").mkdir(parents=True, exist_ok=True)
    sample = vault / "04 Evergreen" / "knowledge-graph.md"
    sample.write_text(
        dump_frontmatter(
            {
                "id": "seed-1",
                "kind": "evergreen",
                "status": "stable",
                "source_type": "manual",
                "source_ref": "",
            }
        )
        + "\n\n# Knowledge Graph\n\nKnowledge graphs connect entities.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
