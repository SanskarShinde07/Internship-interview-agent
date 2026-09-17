# Deployment Runbook

Follows the plan in `docs/BLUEPRINT.md` §21. This app has no CI/CD deploy
step by design (see §21's reasoning on hosting choice) - deploying is a
short manual click-through on Render (or Railway) and Vercel using the
config files already committed in this repo.

## 1. Backend (Render)

The Blueprint file lives at the **repo root**: `render.yaml`. Render's
Blueprint flow auto-detects it there; you don't point it at `backend/`
yourself - the `rootDir: backend` line inside `render.yaml` is what tells
Render the actual service code lives in that subdirectory.

1. Sign in at https://dashboard.render.com (create a free account if you
   don't have one).
2. Click **New +** (top right) -> **Blueprint**.
3. Under "Connect a repository", authorize Render to access GitHub if
   prompted, then find and select
   `SanskarShinde07/Internship-interview-agent`.
4. Render reads `render.yaml` from the repo root automatically and shows
   a preview: one service, `intervue-ai-backend`. Give the Blueprint a
   name (anything) and click **Apply** (or **Create New Resources**,
   depending on Render's current UI wording).
5. Render creates the service but the first deploy will fail (or sit
   waiting) until you fill in the two secret env vars - these are marked
   `sync: false` in `render.yaml` specifically so Render prompts you for
   them instead of expecting them committed to the repo:
   - Open the new `intervue-ai-backend` service -> **Environment** tab.
   - Set `GEMINI_API_KEY` to your Gemini API key
     (https://aistudio.google.com/apikey).
   - Set `ALLOWED_ORIGINS` to `["http://localhost:3000"]` for now - you'll
     update this to your real Vercel URL in step 3 below once it exists.
   - Save changes; Render will redeploy automatically.
6. Watch the **Logs** tab. A healthy deploy runs `pip install -r
   requirements.txt`, then `bash scripts/start_prod.sh`, which applies
   Alembic migrations, seeds the question bank, and starts uvicorn bound
   to Render's `$PORT`.
7. Once live, note the backend URL shown at the top of the service page,
   e.g. `https://intervue-ai-backend.onrender.com`. Confirm it works by
   opening `https://<that-url>/api/v1/health` in a browser - it should
   return `{"status":"ok"}`.

Railway alternative: the same `backend/Procfile` (`web: bash
scripts/start_prod.sh`) works on Railway - create a new project from this
repo, set the service's root directory to `backend` in Railway's project
settings, add the same env vars listed above (plus `ENVIRONMENT=production`,
`GEMINI_MODEL`, etc. - see `.env.example`), and Railway's Nixpacks builder
will pick up the Procfile.

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
