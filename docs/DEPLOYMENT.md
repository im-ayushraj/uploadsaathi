# Deploying the UploadSaathi prototype

Two public URLs, both on free plans, no card required:

| Piece | Host | What it is |
| --- | --- | --- |
| Backend (FastAPI) + PostgreSQL | Render | `https://uploadsaathi-api.onrender.com` |
| Frontend (React/Vite static build) | Vercel | `https://uploadsaathi.vercel.app` |

The frontend talks to the backend directly over HTTPS, so the backend has to allow the frontend's
origin (step 4). Nothing here connects to UIDAI or any government system; the deployed app carries
the same "Prototype — not an official UIDAI product" notice as local dev.

---

## 0. Before you start

- A GitHub account, plus [Render](https://render.com) and [Vercel](https://vercel.com) accounts
  (sign in to both with GitHub — fastest).
- Working tree committed. Check with:

```bash
git status
```

---

## 1. Push the repo to GitHub

There is no remote yet. Create an **empty** repo on GitHub (no README, no .gitignore), then:

```bash
git remote add origin https://github.com/<your-username>/uploadsaathi.git
```

```bash
git push -u origin master
```

Nothing secret is committed: `.env`, `*.db`, `backend/var/` and `node_modules/` are all ignored.

---

## 2. Backend + database on Render

The repo ships a Blueprint at [infra/render.yaml](../infra/render.yaml), which creates the web
service *and* a free PostgreSQL database, generates `JWT_SECRET`, and wires `DATABASE_URL` for you.

1. Render Dashboard → **New** → **Blueprint**.
2. Connect the GitHub repo.
3. When asked for the Blueprint file, enter `infra/render.yaml`.
4. It will prompt for the one value it cannot know yet — `CORS_ORIGINS`. Put
   `http://localhost:5173` for now; you will replace it in step 4.
5. **Apply**. First build takes 3–6 minutes (it compiles nothing, but PyMuPDF and Pillow are large).

What the Blueprint sets up:

- build: `pip install -r requirements.txt` (from `backend/`)
- start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  — migrations run on every boot, so a fresh database creates its tables by itself
- health check: `/api/v1/health`
- `STORAGE_DIR=/tmp/uploadsaathi-documents`, `MAX_UPLOAD_BYTES=12582912` (12 MB — see
  [Limits](#6-limits-of-the-free-tier-say-these-out-loud-if-asked))

When it goes live, confirm it:

```bash
curl https://uploadsaathi-api.onrender.com/api/v1/health
```

Expect `"status":"ok"` and `"database":"up"`. `"database":"down"` means `DATABASE_URL` did not get
wired — open the service's **Environment** tab and check it exists.

> Doing it by hand instead of the Blueprint? New → Web Service → root directory `backend`, runtime
> Python, then set `PYTHON_VERSION=3.12.11`, `APP_ENV=production`, `JWT_SECRET` (see below),
> `DATABASE_URL`, `CORS_ORIGINS`, `STORAGE_DIR=/tmp/uploadsaathi-documents`,
> `MAX_UPLOAD_BYTES=12582912`, with the same build and start commands. A hosted `postgres://…` URL
> can be pasted as-is — the app rewrites it to psycopg 3.
>
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(48))"
> ```

---

## 3. Frontend on Vercel

1. Vercel → **Add New** → **Project** → import the same repo.
2. **Root Directory**: `frontend`. The Vite preset fills in `npm run build` and `dist`;
   [frontend/vercel.json](../frontend/vercel.json) adds the SPA fallback so `/login` and
   `/enrolments/3` work when typed directly.
3. **Environment Variables** → add, for all environments:

   | Name | Value |
   | --- | --- |
   | `VITE_API_BASE_URL` | `https://uploadsaathi-api.onrender.com/api/v1` |

   Include `/api/v1`, and no trailing slash. Vite bakes this in **at build time**, so if you change
   it later you must redeploy.
4. **Deploy**, then copy the production URL.

---

## 4. Let the backend trust the frontend (do not skip)

Back in Render → your service → **Environment** → set:

```
CORS_ORIGINS = https://uploadsaathi.vercel.app
```

Exact scheme, no trailing slash, comma-separated if you add more. Save — Render restarts
automatically. Skipping this makes every request fail in the browser with a CORS error while
`curl` still works.

Vercel gives each preview deploy its own hostname, which will **not** be allowed. Demo from the
production URL, or add that specific preview host to the list too.

---

## 5. Verify the live journey

Open the Vercel URL and walk the real flow:

1. Sign up (synthetic details only — no real Aadhaar number, no real document).
2. Start an application, fill the wizard.
3. Upload an oversized demo file and confirm the before → after panel appears (e.g. 7.4 MB →
   under 500 KB, "Readable ✓"), then **Use this file**.
4. Accept every required document → **Prepare my application** → reference code
   `PREP-XXXXXXXX` and the honest closing note that real enrolment needs a visit to an Aadhaar
   Enrolment Centre.

Generate demo files to upload with:

```bash
cd backend && .venv/Scripts/python.exe -c "from tests.synthetic import make_oversized_jpeg; open('demo-bill.jpg','wb').write(make_oversized_jpeg())"
```

API docs are live at `https://uploadsaathi-api.onrender.com/docs` if a judge wants to see the
contract.

---

## 6. Limits of the free tier (say these out loud if asked)

- **Cold start.** A free Render service sleeps after ~15 minutes idle; the next request takes
  ~50 seconds. **Open the health URL 2 minutes before you demo**, so the judge never sees it.
- **Prepared files are not permanent.** No persistent disk on the free plan, so `/tmp` is wiped on
  restart or redeploy. Accounts and applications survive (they are in PostgreSQL), but a document
  uploaded before a restart can no longer be downloaded. Fix when it matters: attach a Render disk
  and point `STORAGE_DIR` at it.
- **Render's free PostgreSQL expires after 30 days.** If the submission may be reviewed later than
  that, create a free database on [Neon](https://neon.tech) instead (it does not expire) and paste
  its URL into `DATABASE_URL`.
- **Upload ceiling is 12 MB** on the hosted instance (25 MB locally), because the whole document is
  held in memory while it is optimised and the free instance has 512 MB RAM.
- Tokens are stored in `localStorage` and there is no rate limiting yet — both are noted as Phase 8
  work in [PROJECT_STATE.md](../PROJECT_STATE.md).

---

## 7. Redeploying after a change

Both hosts watch the branch you deployed:

```bash
git push
```

Render rebuilds and re-runs `alembic upgrade head`; Vercel rebuilds the static bundle. To roll
back, use each dashboard's deploy history.

---

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Browser console: "blocked by CORS policy" | `CORS_ORIGINS` missing the frontend origin | Step 4; match scheme exactly, drop any trailing slash |
| Frontend calls `https://uploadsaathi.vercel.app/api/v1/...` and 404s | `VITE_API_BASE_URL` was not set at build time | Add it in Vercel, then **Redeploy** (not just save) |
| `"database":"down"` in `/health` | Bad or missing `DATABASE_URL` | Check the Environment tab; a `postgres://` URL is fine as-is |
| Render build fails on `psycopg`/`pymupdf` wheels | Python version drift | Ensure `PYTHON_VERSION=3.12.11` |
| First request after a pause hangs ~50 s | Free instance was asleep | Expected; warm it before demoing |
| Login works, uploads 413 | File over `MAX_UPLOAD_BYTES` | Raise it, or use a smaller demo file |
| Old document download 404s | `/tmp` was wiped on restart | Re-upload; see the persistence note above |
