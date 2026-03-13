"""Simple JSON-backed vector store."""

from __future__ import annotations

import json
import math
from pathlib import Path


class VectorStore:
    """Minimal vector store abstraction."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _load(self) -> dict[str, list[float]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, payload: dict[str, list[float]]) -> None:
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert(self, key: str, vector: list[float]) -> None:
        payload = self._load()
        payload[key] = vector
        self._save(payload)

    def clear(self) -> None:
        """Reset the vector store."""

        self._save({})

    def search(self, vector: list[float], top_k: int = 5) -> list[tuple[str, float]]:
        payload = self._load()
        scored: list[tuple[str, float]] = []
        for key, candidate in payload.items():
            scored.append((key, cosine_similarity(vector, candidate)))
        return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity."""

    if not left or not right or len(left) != len(right):
        return 0.0

    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
