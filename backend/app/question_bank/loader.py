"""Loads the curated question bank seed files into the database.

Idempotent: re-running only inserts items that aren't already present
(matched on round + question_text), so it's safe to run repeatedly
after editing a seed file without duplicating existing rows.
"""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BankRound, QuestionBankItem
from app.db.session import SessionLocal

SEED_DATA_DIR = Path(__file__).parent / "seed_data"
SEED_FILES = [
    "python.json",
    "machine_learning.json",
    "nlp.json",
    "scenario.json",
    "hr.json",
]


def _load_seed_file(filename: str) -> list[dict]:
    path = SEED_DATA_DIR / filename
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def seed_question_bank(db: Session) -> dict[str, int]:
    """Seeds all question bank files. Returns {filename: inserted_count}."""
    results: dict[str, int] = {}

    for filename in SEED_FILES:
        items = _load_seed_file(filename)
        inserted = 0

        for item in items:
            round_value = BankRound(item["round"])
            exists = db.execute(
                select(QuestionBankItem.id).where(
                    QuestionBankItem.round == round_value,
                    QuestionBankItem.question_text == item["question_text"],
                )
            ).first()
            if exists:
                continue

            db.add(
                QuestionBankItem(
                    round=round_value,
                    topic=item["topic"],
                    subtopic=item.get("subtopic"),
                    difficulty=item["difficulty"],
                    question_text=item["question_text"],
                    expected_concepts=item.get("expected_concepts", []),
                    followup_hints=item.get("followup_hints"),
                    prerequisites=item.get("prerequisites"),
                )
            )
            inserted += 1

        results[filename] = inserted

    db.commit()
    return results


def main() -> None:
    db = SessionLocal()
    try:
        results = seed_question_bank(db)
        total = sum(results.values())
        for filename, count in results.items():
            print(f"{filename}: inserted {count} new item(s)")
        print(f"Total inserted: {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
