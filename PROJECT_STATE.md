# UploadSaathi Project State

Current Phase:
Phase 0 — complete

Current Task:
Phase 0: repository inspection + specification + skeleton (done)

Completed:
- Phase 0: inspected repo (was empty), captured environment facts
- Created PROJECT_STATE.md, ARCHITECTURE.md, .gitignore, git init
- Created directory skeleton: backend/, frontend/, docs/, infra/

Next:
Phase 1: backend FastAPI app with GET /api/v1/health + settings via env vars

Known Issues:
- Docker not installed on this machine → compose files can be authored but not run/verified here
- No local PostgreSQL → local dev uses SQLite via DATABASE_URL; Postgres used in Docker Compose
- Python 3.14 is new; PyMuPDF/OpenCV wheel availability must be verified at Phase 4 (fallbacks: Pillow-only + pypdf)

Architecture Decisions:
- Smart Upload engine lives in backend/app/uploadsaathi/, framework-agnostic, no Aadhaar knowledge
- Portal requirements are JSON/YAML config resolved by RequirementResolver, never hardcoded in React
- DATABASE_URL env var; SQLAlchemy 2.x + Alembic
- Deterministic processing first; AI (Phase 6) behind a replaceable interface
- API prefix /api/v1
