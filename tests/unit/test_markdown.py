from pathlib import Path

from obsidian_agent.utils.markdown import render_template


def test_render_template() -> None:
    template = Path("src/obsidian_agent/prompts/tasks/weekly_digest.md.tmpl")
    rendered = render_template(
        template,
        {"frontmatter": "kind: digest", "week_key": "2026-W11", "content": "Hi"},
    )
    assert "2026-W11" in rendered
    assert "Hi" in rendered
