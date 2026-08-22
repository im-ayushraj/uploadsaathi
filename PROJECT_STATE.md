# UploadSaathi Project State

Current Phase:
Phase 3 — complete

Current Task:
Phase 3: Aadhaar enrolment journey — done

Completed:
- Phase 0: inspected repo (was empty), captured environment facts
- Created PROJECT_STATE.md, ARCHITECTURE.md, .gitignore, git init
- Created directory skeleton: backend/, frontend/, docs/, infra/
- Phase 1: FastAPI app (app.main) + /api/v1/health (reports DB connectivity) + CORS
- Phase 1: SQLAlchemy engine/session/Base, env-driven settings (pydantic-settings)
- Phase 1: React+TS+Vite+Tailwind v4 frontend, React Router, TanStack Query, axios, zod
- Phase 1: landing page calls /api/v1/health via Vite proxy; PrototypeBanner component
- Phase 1: Dockerfiles + infra/docker-compose.yml (db/backend/frontend), .env.example, README
- Phase 2: User model, Alembic initialised + initial users migration (applied on SQLite)
- Phase 2: bcrypt hashing, PyJWT HS256 access tokens, security.py
- Phase 2: POST /auth/signup, POST /auth/login (email OR mobile), GET /auth/me, POST /auth/logout
- Phase 2: get_current_user HTTPBearer dependency; generic login error message
- Phase 2: frontend AuthProvider + token store, axios auth/401 interceptors, RequireAuth /
  RedirectIfAuthenticated route guards, Login/Signup pages, AppHeader with logout, Dashboard stub
- Phase 3: app/config/portals/aadhaar.json (3 applicant types, 5 document types, defaults+overrides)
- Phase 3: RequirementResolver + Requirement/DocumentTypeInfo/ApplicantType/PortalInfo models
- Phase 3: GET /portals, /portals/{id}, /portals/{id}/documents?applicant_type=
- Phase 3: Enrolment model + migration; POST/GET/PATCH/DELETE /enrolments, POST /{id}/prepare
- Phase 3: ownership checks (404 for other users), prepared drafts immutable, idempotent prepare
- Phase 3: wizard UI — applicant type, personal details, address, document requirements, review,
  prepared (centre info + honest disclaimer); dashboard lists/resumes/deletes applications
- Phase 3: tests/conftest.py with isolated SQLite + client/auth_headers fixtures

Next:
Phase 4: deterministic Smart Upload engine — DocumentAnalyzer first (real file-type sniffing,
dimensions, page count, byte size) with tests on synthetic images/PDFs

Known Issues:
- Docker not installed on this machine → compose files can be authored but not run/verified here
- No local PostgreSQL → local dev uses SQLite via DATABASE_URL; Postgres used in Docker Compose
- Python 3.14 is new; PyMuPDF/OpenCV wheel availability must be verified at Phase 4 (fallbacks: Pillow-only + pypdf)
- requirements.txt uses >= pins (Python 3.14 lacks older wheels)
- Vite dev server binds localhost (not 127.0.0.1); use http://localhost:5173
- JWT stored in localStorage (prototype tradeoff); revisit in Phase 8
- No refresh tokens / no rate limiting yet (Phase 8)
- documents step in EnrolmentProgress is always false until Phase 5 wires uploads;
  prepare() therefore does not yet require documents

Architecture Decisions:
- Smart Upload engine lives in backend/app/uploadsaathi/, framework-agnostic, no Aadhaar knowledge
- Portal requirements are JSON/YAML config resolved by RequirementResolver, never hardcoded in React
- DATABASE_URL env var; SQLAlchemy 2.x + Alembic
- Deterministic processing first; AI (Phase 6) behind a replaceable interface
- API prefix /api/v1
- Auth: stateless JWT access token only; logout is client-side token discard
- Login accepts email or 10-digit Indian mobile (normalised, +91/0 tolerated)
- Enrolment personal_details/address stored as JSON columns (portal-neutral); no Aadhaar number field
- Wizard step completeness computed backend-side (EnrolmentProgress), not in React
- Prototype reference code format PREP-XXXXXXXX, deliberately unlike a real UIDAI EID/URN
