# Deployment Runbook

Follows the plan in `docs/BLUEPRINT.md` §21. This app has no CI/CD deploy
step by design (see §21's reasoning on hosting choice) - deploying is a
short manual click-through using the Blueprint file already committed at
the repo root: `render.yaml`.

Both the backend and the frontend deploy to Render from that single file
(one platform, one dashboard). Vercel is documented as an alternative for
the frontend at the bottom, if you'd rather split them later.

## 1. Deploy the Blueprint

The Blueprint file lives at the **repo root**: `render.yaml`. Render's
Blueprint flow auto-detects it there. It defines two services:
`intervue-ai-frontend` (Next.js, `rootDir: frontend`) and
`intervue-ai-backend` (FastAPI, `rootDir: backend`) - each `rootDir` tells
Render where that service's code lives in this monorepo.

1. Sign in at https://dashboard.render.com (create a free account if you
   don't have one).
2. Click **New +** (top right) -> **Blueprint**.
3. Under "Connect a repository", authorize Render to access GitHub if
   prompted, then find and select
   `SanskarShinde07/Internship-interview-agent`.
4. Render reads `render.yaml` and shows a preview with both services.
   Give the Blueprint a name (anything) and click **Apply** (or **Create
   New Resources**, depending on Render's current UI wording).
5. Render creates both services but the backend's first deploy will wait
   until you fill in its secret env vars - these are marked `sync: false`
   in `render.yaml` specifically so Render prompts you for them instead of
   expecting them committed to the repo:
   - Open the `intervue-ai-backend` service -> **Environment** tab.
   - Set `GEMINI_API_KEY` to your Gemini API key
     (https://aistudio.google.com/apikey).
   - Set `ALLOWED_ORIGINS` to `["http://localhost:3000"]` for now - you'll
     update this once the frontend's real URL exists (step 2 below).
   - Set `JWT_SECRET_KEY` - this signs every login/password-reset token,
     and the app **refuses to start** in production without one. Generate
     one locally and paste it in:
     `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
   - Set `RESEND_API_KEY` if you want password-reset emails to actually
     send (https://resend.com/api-keys, free tier). Leave it blank to
     skip this - the reset link still works, it's just not emailed to the
     candidate (see the Note below).
   - Save changes; Render redeploys automatically.
6. Watch each service's **Logs** tab.
   - Backend: `pip install -r requirements.txt`, then `bash
     scripts/start_prod.sh` - applies Alembic migrations, seeds the
     question bank, starts uvicorn bound to Render's `$PORT`.
   - Frontend: `npm ci && npm run build`, then `npm run start -- -p
     $PORT`.
7. Once both are live, note their URLs from the top of each service page,
   e.g. `https://intervue-ai-backend-xxxx.onrender.com` and
   `https://intervue-ai-frontend-xxxx.onrender.com` (Render appends a
   random suffix if the plain name is already taken by someone else).
   Confirm the backend works by opening
   `https://<backend-url>/api/v1/health` - it should return
   `{"status":"ok"}`.

## 2. Point the frontend at the backend, and close the CORS loop

`render.yaml` bakes a `NEXT_PUBLIC_API_BASE_URL` value into the frontend
service - if your backend's actual URL differs from what's committed
there (it will, once Render assigns its own random suffix), update it:

1. Open the `intervue-ai-frontend` service -> **Environment** tab.
2. Set `NEXT_PUBLIC_API_BASE_URL` to your real backend URL with `/api/v1`
   appended, e.g. `https://intervue-ai-backend-xxxx.onrender.com/api/v1`.
3. Save - this triggers a rebuild (Next.js bakes `NEXT_PUBLIC_*` vars into
   the client bundle at build time, so a redeploy is required, not just a
   restart).
4. Once the frontend's real URL is known, go back to the
   `intervue-ai-backend` service -> **Environment** tab and update
   `ALLOWED_ORIGINS` to a JSON array with that exact URL, e.g.
   `["https://intervue-ai-frontend-xxxx.onrender.com"]`. Save to redeploy
   the backend so CORS allows the live frontend.

## 3. Smoke test

Open the frontend URL and run through one full interview end to end:
setup -> instructions -> interview (a few answers) -> report -> analytics
-> coach. This exercises the full stack including the live Gemini API.

## Notes

- The `ENVIRONMENT=production` env var (set by `render.yaml`) disables
  the `/docs`, `/redoc`, and `/openapi.json` endpoints on the backend -
  this is expected, not a bug.
- The backend uses the managed Postgres instance (`intervue-ai-db`)
  defined in `render.yaml`, not SQLite - a free-tier web service has no
  persistent disk, so a SQLite file there resets on every redeploy and
  every idle spin-down, wiping all registered accounts. Render's free
  Postgres plan expires 30 days after creation; upgrade it to a paid
  plan before then if you need accounts to persist beyond that.
- Free-tier Render services spin down after inactivity and take ~30-60s
  to wake on the next request - the first request after a quiet period
  will feel slow. That's a free-tier limitation, not a bug.
- Changing `GEMINI_API_KEY`, `ALLOWED_ORIGINS`, `JWT_SECRET_KEY`, or
  `RESEND_API_KEY` only redeploys the backend. Changing
  `NEXT_PUBLIC_API_BASE_URL` only redeploys the frontend (but does
  require a full rebuild, unlike backend env vars).
- Without `RESEND_API_KEY` set, password-reset links are never emailed -
  they're only logged (`RESEND_API_KEY not set - skipping email; reset
  link: ...`) at WARNING level in the backend's Logs tab. Fine for
  testing the flow yourself; set the key for real candidates to receive
  the email.
- `render.yaml` bakes `FRONTEND_URL` in as the URL that gets embedded in
  password-reset links. Update it (backend env vars) if your frontend's
  real URL differs from what's committed there.

## Alternative: frontend on Vercel instead

If you'd rather split the frontend onto Vercel (e.g. for its faster
global CDN or preview-per-PR workflow):

1. Go to https://vercel.com/new and import this repository.
2. Set the project's root directory to `frontend`.
3. Skip Vercel's "detected environment variables" (they're your root
   `.env.example`, which is for the *backend* and irrelevant here). Add
   one manually instead: `NEXT_PUBLIC_API_BASE_URL` set to your Render
   backend URL with `/api/v1` appended.
4. Deploy. Vercel auto-detects Next.js - no build command changes needed.
5. Use the URL shown on the project's **Overview** page (not a
   deployment-specific preview URL) once the deployment is tagged
   **Production** in the Deployments tab.
6. Update the backend's `ALLOWED_ORIGINS` on Render to that Vercel URL,
   as in step 2 above, and remove/disable the `intervue-ai-frontend`
   service in `render.yaml` if you don't want both running.
