"""Replay the fixed C-language quality sample set and emit a baseline report."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from obsidian_agent.app import build_container
from obsidian_agent.config import Settings, get_settings
from obsidian_agent.domain.schemas import ErrorCaptureRequest


@dataclass
class QualitySample:
    sample_id: str
    title: str
    prompt: str
    code: str
    user_analysis: str
    expected_error_title: str
    expected_root_cause: str
    expected_related_concepts: list[str]
    forbidden_relations: list[str]
    forbidden_node_types: list[str]


def load_samples(path: Path) -> list[QualitySample]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    samples: list[QualitySample] = []
    for item in raw:
        samples.append(
            QualitySample(
                sample_id=str(item["id"]),
                title=str(item["title"]),
                prompt=str(item["prompt"]),
                code=str(item.get("code", "")),
                user_analysis=str(item.get("user_analysis", "")),
                expected_error_title=str(item["expected_error_title"]),
                expected_root_cause=str(item["expected_root_cause"]),
                expected_related_concepts=[str(entry) for entry in item["expected_related_concepts"]],
                forbidden_relations=[str(entry) for entry in item.get("forbidden_relations", [])],
                forbidden_node_types=[str(entry) for entry in item.get("forbidden_node_types", [])],
            )
        )
    return samples


async def replay_samples(
    settings: Settings,
    samples: list[QualitySample],
    limit: int | None = None,
) -> list[dict[str, object]]:
    container = build_container(settings)
    results: list[dict[str, object]] = []
    for sample in samples[:limit]:
        response = await container.smart_capture_service.capture_error(
            ErrorCaptureRequest(
                title=sample.title,
                prompt=sample.prompt,
                code=sample.code,
                user_analysis=sample.user_analysis,
                language="c",
                source_ref=f"quality-tuning/{sample.sample_id}",
            )
        )
        results.append(
            {
                "id": sample.sample_id,
                "title": sample.title,
                "expected": {
                    "error_title": sample.expected_error_title,
                    "root_cause": sample.expected_root_cause,
                    "related_concepts": sample.expected_related_concepts,
                    "forbidden_relations": sample.forbidden_relations,
                    "forbidden_node_types": sample.forbidden_node_types,
                },
                "actual": {
                    "error_title": response.error.title,
                    "summary": response.error.summary,
                    "trigger_mistake": response.error.trigger_mistake,
                    "root_cause": response.error.root_cause,
                    "incorrect_assumption": response.error.incorrect_assumption,
                    "corrective_rule": response.error.corrective_rule,
                    "next_time_checklist": response.error.next_time_checklist,
                    "related_concepts": response.error.related_concepts,
                    "related_nodes": [
                        {
                            "node_key": node.node_key,
                            "node_type": node.node_type.value,
                            "title": node.title,
                        }
                        for node in response.related_nodes
                    ],
                },
                "operator_scores": {
                    "error_note_accuracy": "",
                    "knowledge_node_reuse_value": "",
                    "relation_quality": "",
                    "review_quality": "",
                    "language_and_readability": "",
                    "noise_control": "",
                },
            }
        )
    return results


def build_markdown_report(
    results: list[dict[str, object]],
    settings: Settings,
    fixtures_path: Path,
) -> str:
    lines = [
        "# Quality Replay Report",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Fixtures: `{fixtures_path}`",
        f"- LLM provider: `{settings.llm_provider}`",
        f"- Embeddings provider: `{settings.embeddings_provider}`",
        f"- Dry run: `{settings.dry_run}`",
        "",
        "## Samples",
        "",
    ]
    for item in results:
        actual = item["actual"]
        expected = item["expected"]
        lines.extend(
            [
                f"### {item['id']} {item['title']}",
                "",
                f"- Expected error title: {expected['error_title']}",
                f"- Actual error title: {actual['error_title']}",
                f"- Expected root cause: {expected['root_cause']}",
                f"- Actual root cause: {actual['root_cause']}",
                f"- Expected related concepts: {', '.join(expected['related_concepts'])}",
                f"- Actual related concepts: {', '.join(actual['related_concepts'])}",
                f"- Trigger mistake: {actual['trigger_mistake']}",
                f"- Corrective rule: {actual['corrective_rule']}",
                f"- Checklist: {'; '.join(actual['next_time_checklist'])}",
                f"- Related nodes: {len(actual['related_nodes'])}",
                "",
                "| Rubric | Score | Notes |",
                "| --- | --- | --- |",
                "| Error Note Accuracy |  |  |",
                "| Knowledge Node Reuse Value |  |  |",
                "| Relation Quality |  |  |",
                "| Review Quality |  |  |",
                "| Language And Readability |  |  |",
                "| Noise Control |  |  |",
                "",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("tests/fixtures/quality_tuning/c_language_error_samples.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/quality-tuning-rounds"),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--write-vault", action="store_true", help="Allow the replay to write into the active vault.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    settings = settings.model_copy(update={"dry_run": not args.write_vault})
    samples = load_samples(args.fixtures)
    results = asyncio.run(replay_samples(settings, samples, args.limit))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = args.output_dir / f"{timestamp}-quality-replay.json"
    md_path = args.output_dir / f"{timestamp}-quality-replay.md"
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(build_markdown_report(results, settings, args.fixtures), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
