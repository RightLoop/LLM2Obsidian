from obsidian_agent.utils.frontmatter import dump_frontmatter, parse_frontmatter, patch_frontmatter


def test_frontmatter_roundtrip() -> None:
    markdown = dump_frontmatter({"id": "1", "kind": "inbox"}) + "\n\nBody\n"
    data, body = parse_frontmatter(markdown)
    assert data["id"] == "1"
    assert body.strip() == "Body"


def test_patch_frontmatter() -> None:
    original = "---\nid: 1\nkind: inbox\n---\n\nBody\n"
    updated = patch_frontmatter(original, {"status": "review"})
    assert "status: review" in updated
