# UploadSaathi

Smart document upload for Indian public-service portals — makes a document portal-ready
(size, format, dimensions) while preserving readability.

> **Prototype — not an official UIDAI product.** No government system is contacted. No real
> Aadhaar numbers, identity documents, or OTPs are used. Demo/synthetic data only.

The Aadhaar/UIDAI enrolment document-preparation journey is the first case study; the Smart Upload
engine is portal-agnostic (Passport, PAN, SSC, UPSC, NTA, RTPS, EPFO can be added as config).

## Run locally (no Docker)

Backend:

```bash
cd backend && py -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements.txt && .venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 — the landing page shows live backend/database status.
API docs: http://localhost:8000/docs

## Run with Docker Compose

```bash
cd infra && docker compose up --build
```

## Tests

```bash
cd backend && .venv/Scripts/python.exe -m pytest -q
```

See [ARCHITECTURE.md](ARCHITECTURE.md) and [PROJECT_STATE.md](PROJECT_STATE.md).
