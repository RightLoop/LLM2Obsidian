"""Infer weakness objects from extracted errors."""

from __future__ import annotations

from obsidian_agent.domain.schemas import ErrorObject, WeaknessObject


class WeaknessDiagnoserService:
    """Map an extracted error into one or more practice weaknesses."""

    async def diagnose(self, error: ErrorObject) -> list[WeaknessObject]:
        primary_concept = error.related_concepts[0] if error.related_concepts else "c-basics"
        concept_label = primary_concept.replace("-", " ")
        return [
            WeaknessObject(
                name=f"薄弱点：{concept_label}",
                summary=f"需要补强“{concept_label}”的判定边界，避免再次出现“{error.incorrect_assumption}”这类误判。",
                gap_type="conceptual",
                recommended_practice=(
                    f"围绕“{concept_label}”做 2 到 3 组对照题复盘，先写判断依据，再核对正确语义。"
                ),
                related_concepts=error.related_concepts,
                confidence=max(0.5, error.confidence),
            )
        ]
