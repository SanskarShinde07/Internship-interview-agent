# Deployment Runbook

Follows the plan in `docs/BLUEPRINT.md` §21. This app has no CI/CD deploy
step by design (see §21's reasoning on hosting choice) - deploying is a
short manual click-through on Render (or Railway) and Vercel using the
config files already committed in this repo.

## 1. Backend (Render)

1. Go to https://dashboard.render.com/blueprints and connect this GitHub
   repository.
2. Render will detect `backend/render.yaml` automatically. Confirm the
   root directory is `backend`.
3. Before the first deploy, set these secret env vars in the Render
   dashboard (they're marked `sync: false` in `render.yaml` so Render
   won't ask you to commit them):
   - `GEMINI_API_KEY` - your Gemini API key.
   - `ALLOWED_ORIGINS` - a JSON array with your Vercel frontend's exact
     URL once you have it, e.g. `["https://intervue-ai.vercel.app"]`.
     (You can leave this as `localhost` initially and come back to it
     after step 2 gives you the real Vercel URL - see step 3 below.)
4. Deploy. Render will run `pip install -r requirements.txt`, then
   `bash scripts/start_prod.sh`, which applies Alembic migrations, seeds
   the question bank, and starts uvicorn bound to Render's `$PORT`.
5. Note the resulting backend URL, e.g. `https://intervue-ai-backend.onrender.com`.
   Health check: `GET /api/v1/health` should return `{"status":"ok"}`.

Railway alternative: the same `backend/Procfile` (`web: bash
scripts/start_prod.sh`) works on Railway - create a new project from this
repo, set the root directory to `backend`, add the same env vars listed
above (plus `ENVIRONMENT=production`, `GEMINI_MODEL`, etc. - see
`.env.example`), and Railway's Nixpacks builder will pick up the Procfile.

## 2. Frontend (Vercel)

1. Go to https://vercel.com/new and import this repository.
2. Set the project's root directory to `frontend`.
3. Add one environment variable: `NEXT_PUBLIC_API_BASE_URL` set to your
   Render backend URL from step 1.5 above, with `/api/v1` appended, e.g.
   `https://intervue-ai-backend.onrender.com/api/v1`.
4. Deploy. Vercel auto-detects Next.js - no build command changes needed.
5. Note the resulting frontend URL, e.g. `https://intervue-ai.vercel.app`.

## 3. Close the loop

Go back to the Render dashboard and update `ALLOWED_ORIGINS` to the real
Vercel URL from step 2.5 (a JSON array, e.g.
`["https://intervue-ai.vercel.app"]`), then redeploy the backend service
so CORS allows the live frontend.

## 4. Smoke test

Open the Vercel URL and run through one full interview end to end:
setup -> instructions -> interview (a few answers) -> report -> analytics
-> coach. This exercises the full stack including the live Gemini API.

## Notes

- The `ENVIRONMENT=production` env var (set by `render.yaml`) disables
  the `/docs`, `/redoc`, and `/openapi.json` endpoints on the backend -
  this is expected, not a bug.
- SQLite lives on a small persistent disk attached to the Render service
  (`render.yaml`'s `disk` block). It survives restarts and redeploys but
  not disk deletion. See BLUEPRINT.md §21 for the Postgres migration path
  if you outgrow it.
- Rotating `GEMINI_API_KEY` or changing `ALLOWED_ORIGINS` only requires a
  redeploy of the backend service, not the frontend.
