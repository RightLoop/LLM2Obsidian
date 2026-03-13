"""Create or update GitHub pull requests using explicit UTF-8 JSON payloads."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--title", help="PR title when creating a PR")
    parser.add_argument("--body-file", required=True, help="UTF-8 markdown file for the PR body")
    parser.add_argument("--base", help="Target branch when creating a PR")
    parser.add_argument("--head", help="Source branch when creating a PR")
    parser.add_argument("--pr-number", type=int, help="Existing PR number to update")
    parser.add_argument(
        "--token-env",
        default="GITHUB_TOKEN",
        help="Environment variable that stores the GitHub token",
    )
    args = parser.parse_args()

    if args.pr_number is None and not all((args.title, args.base, args.head)):
        parser.error("--title, --base, and --head are required when creating a PR")
    return args


def read_body(body_file: str) -> str:
    return Path(body_file).read_text(encoding="utf-8-sig")


def request_json(url: str, token: str, method: str, payload: dict[str, object]) -> dict[str, object]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json; charset=utf-8",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    args = parse_args()
    token = os.environ.get(args.token_env)
    if not token:
        print(f"Missing token in environment variable: {args.token_env}", file=sys.stderr)
        return 1

    body = read_body(args.body_file)

    try:
        if args.pr_number is not None:
            url = f"https://api.github.com/repos/{args.repo}/pulls/{args.pr_number}"
            payload = {"body": body}
            result = request_json(url, token, "PATCH", payload)
        else:
            url = f"https://api.github.com/repos/{args.repo}/pulls"
            payload = {
                "title": args.title,
                "head": args.head,
                "base": args.base,
                "body": body,
            }
            result = request_json(url, token, "POST", payload)
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        print(message, file=sys.stderr)
        return 1

    print(result["html_url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
