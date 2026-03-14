import json
from pathlib import Path


def test_quality_tuning_samples_have_required_fields() -> None:
    fixture_path = Path("tests/fixtures/quality_tuning/c_language_error_samples.json")
    samples = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert len(samples) >= 24
    required_fields = {
        "id",
        "title",
        "prompt",
        "code",
        "user_analysis",
        "expected_error_title",
        "expected_root_cause",
        "expected_related_concepts",
        "forbidden_relations",
        "forbidden_node_types",
    }

    sample_ids = set()
    for sample in samples:
        assert required_fields.issubset(sample)
        assert sample["id"] not in sample_ids
        sample_ids.add(sample["id"])
        assert isinstance(sample["expected_related_concepts"], list)
        assert sample["expected_related_concepts"]
        assert isinstance(sample["forbidden_relations"], list)
        assert isinstance(sample["forbidden_node_types"], list)
