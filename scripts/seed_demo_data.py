"""Seed a realistic demo vault for local walkthroughs."""

from pathlib import Path

from obsidian_agent.utils.demo_data import seed_demo_vault


def main() -> None:
    seed_demo_vault(Path("data/demo_vault"))


if __name__ == "__main__":
    main()
