import json
from pathlib import Path

import pytest

SEED_DIR = Path(__file__).resolve().parents[2] / "app" / "question_bank" / "seed_data"

FILE_TO_ROUND = {
    "python.json": "PYTHON",
    "machine_learning.json": "MACHINE_LEARNING",
    "nlp.json": "NLP",
    "scenario.json": "SCENARIO",
    "hr.json": "HR",
}

REQUIRED_FIELDS = {"round", "topic", "difficulty", "question_text", "expected_concepts"}


@pytest.mark.parametrize(("filename", "expected_round"), FILE_TO_ROUND.items())
def test_seed_file_integrity(filename: str, expected_round: str) -> None:
    items = json.loads((SEED_DIR / filename).read_text())
    assert len(items) > 0, f"{filename} has no questions"

    seen_texts = set()
    for item in items:
        missing = REQUIRED_FIELDS - item.keys()
        assert not missing, f"{filename} item missing fields: {missing}"
        assert item["round"] == expected_round
        assert 1 <= item["difficulty"] <= 5
        assert isinstance(item["expected_concepts"], list)
        assert item["expected_concepts"]
        assert item["question_text"] not in seen_texts, f"duplicate question in {filename}"
        seen_texts.add(item["question_text"])

        for key in ("followup_hints", "prerequisites"):
            if item.get(key) is not None:
                assert isinstance(item[key], list)


def test_prerequisites_reference_existing_subtopics() -> None:
    for filename in FILE_TO_ROUND:
        items = json.loads((SEED_DIR / filename).read_text())
        subtopics = {item.get("subtopic") for item in items if item.get("subtopic")}
        for item in items:
            for prereq in item.get("prerequisites") or []:
                assert prereq in subtopics, f"{filename}: unknown prerequisite '{prereq}'"
