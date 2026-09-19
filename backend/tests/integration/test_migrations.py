import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]

EXPECTED_TABLES = {
    "candidates",
    "interview_sessions",
    "question_bank_items",
    "interview_questions",
    "candidate_answers",
    "answer_evaluations",
    "difficulty_log",
    "interview_reports",
    "coach_conversations",
    "coach_messages",
}


def _run_alembic(args: list[str], env: dict) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_migrations_upgrade_creates_all_tables_and_downgrade_removes_them(tmp_path) -> None:
    db_path = tmp_path / "test_migrations.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"

    _run_alembic(["upgrade", "head"], env)

    conn = sqlite3.connect(db_path)
    tables = {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}
    conn.close()
    assert EXPECTED_TABLES.issubset(tables)

    _run_alembic(["downgrade", "base"], env)

    conn = sqlite3.connect(db_path)
    tables_after_downgrade = {
        row[0] for row in conn.execute("select name from sqlite_master where type='table'")
    }
    conn.close()
    assert EXPECTED_TABLES.isdisjoint(tables_after_downgrade)
