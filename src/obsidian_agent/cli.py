"""CLI entrypoint."""

from __future__ import annotations

import argparse
import asyncio

from obsidian_agent.app import build_container


def main() -> None:
    """Run CLI commands."""

    parser = argparse.ArgumentParser(prog="obsidian-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("reindex")
    digest_parser = subparsers.add_parser("weekly-digest")
    digest_parser.add_argument("week_key")

    args = parser.parse_args()
    container = build_container()

    if args.command == "reindex":
        paths = asyncio.run(container.indexing_service.reindex_all())
        print(f"Indexed {len(paths)} notes")
    elif args.command == "weekly-digest":
        path = asyncio.run(container.maintenance_workflow.weekly_digest(args.week_key))
        print(path)
