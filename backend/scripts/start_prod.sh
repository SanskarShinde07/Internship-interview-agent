#!/usr/bin/env bash
# Production entrypoint (docs/BLUEPRINT.md §21): applies pending migrations,
# seeds the question bank (idempotent - see app/question_bank/loader.py),
# then starts the API bound to the host's assigned $PORT.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# backend/data/ is gitignored (holds the local SQLite file), so it never
# exists on a fresh clone - sqlite3 fails to create the DB file inside a
# directory that isn't there yet.
mkdir -p data

python -m alembic upgrade head
python -m app.question_bank.loader

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
