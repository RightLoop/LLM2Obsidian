"""Helpers shared by integration tests."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4


def make_test_dir(label: str) -> Path:
    root = Path("data/test_runs") / f"{label}_{uuid4().hex[:8]}"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root
