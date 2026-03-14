"""Small diff helpers."""

import difflib


def unified_diff(before: str, after: str, before_name: str = "before", after_name: str = "after") -> str:
    """Return a unified diff string."""

    return "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=before_name,
            tofile=after_name,
            lineterm="",
        )
    )
