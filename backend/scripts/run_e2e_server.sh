#!/usr/bin/env bash
# Launches a throwaway, freshly-seeded backend instance for the frontend's
# Playwright E2E suite (docs/BLUEPRINT.md §18, §19 Phase 8). Forces the
# stub AI gateway (empty GEMINI_API_KEY) so the suite is deterministic and
# never depends on - or spends quota against - a live model.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

PORT="${1:-8765}"
DB_DIR="$(mktemp -d)"

export DATABASE_URL="sqlite:///${DB_DIR}/e2e.db"
export GEMINI_API_KEY=""
export ALLOWED_ORIGINS="${E2E_ALLOWED_ORIGINS:-[\"http://localhost:3100\",\"http://127.0.0.1:3100\"]}"
# A full interview submits far more than 20 requests/minute when driven by
# a script instead of a human; rate limiting itself has its own dedicated
# backend tests, so it's not what this suite is checking.
export RATE_LIMIT_PER_MINUTE="${E2E_RATE_LIMIT_PER_MINUTE:-1000}"
export AUTH_RATE_LIMIT_PER_MINUTE="${E2E_AUTH_RATE_LIMIT_PER_MINUTE:-1000}"
# Only signs tokens for this throwaway instance's lifetime - starting an
# interview now requires an account, so the suite registers one.
export JWT_SECRET_KEY="e2e-suite-only-not-for-production"

if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

python -m alembic upgrade head
python -m app.question_bank.loader

exec python -m uvicorn app.main:app --port "$PORT"
