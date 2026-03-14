"""Infer weakness objects from extracted errors."""

from __future__ import annotations

from obsidian_agent.domain.schemas import ErrorObject, WeaknessObject


class WeaknessDiagnoserService:
    """Map an extracted error into one or more practice weaknesses."""

    async def diagnose(self, error: ErrorObject) -> list[WeaknessObject]:
        primary_concept = error.related_concepts[0] if error.related_concepts else "c-basics"
        return [
            WeaknessObject(
                name=f"Weakness: {primary_concept}",
                summary=f"The learner repeatedly confuses {primary_concept} in C code reasoning.",
                gap_type="conceptual",
                recommended_practice=f"Review worked examples that contrast correct and incorrect uses of {primary_concept}.",
                related_concepts=error.related_concepts,
                confidence=max(0.5, error.confidence),
            )
        ]
