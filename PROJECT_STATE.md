# UploadSaathi Project State

Current Phase:
Phase 5 — complete (upload API + wizard document UI)

Current Task:
Phase 6: AI-assisted analysis behind a replaceable interface (document-type hints and readability
advice only — never byte-size, resize, format conversion or requirement validation)

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
- Phase 4a: formats.py (magic-byte sniffing, alias canonicalisation) + DocumentAnalyzer
  (dimensions, dpi, colour mode, alpha, PDF pages/text layer/image count/encryption)
- Phase 4a: tests/synthetic.py document builders (noisy images, PDFs, oversized JPEG, corrupt)
- Phase 4b: OptimizationStrategyProvider (pure decisions) + OptimizationPlan with readability
  guards (quality floor, min scale, min dimensions) and feasible/infeasible_reason
- Phase 4b: OptimizationEngine — auto-orient, strip metadata, alpha flatten, greyscale, LANCZOS
  fit-to-bounds, quality binary search then gentle downscale ladder, PDF structural clean +
  page rasterisation ladder; compliant files returned byte-identical
- Phase 4b: 24 strategy/engine tests incl. hero case 7.46 MB JPEG → under 2 MB, readable
- Phase 4c: engine carries physical DPI across a resize (300 dpi halved really is 150 dpi)
- Phase 4c: QualityValidator — re-measures output bytes, per-rule verdicts, readability guardrail,
  quality_status unchanged/passed/degraded/failed, DPI advisory only
- Phase 4c: UploadService.process/preview (injectable collaborators) + UploadResult contract
  (to_dict never exposes document bytes); output filename derived from the document slot
- Phase 4c: 15 validator/service tests running against the real aadhaar.json
- Phase 5a: DocumentStorage (opaque random keys, path-traversal guard, optimised bytes only) +
  STORAGE_DIR / MAX_UPLOAD_BYTES settings
- Phase 5a: EnrolmentDocument model + migration (one row per enrolment+slot, JSON result report)
- Phase 5a: POST/GET/GET {id}/GET {id}/file/POST {id}/accept/DELETE under
  /enrolments/{id}/documents; two-step flow (pending preview → explicit accept)
- Phase 5a: engine issue codes translated to plain-language citizen messages in the API layer
- Phase 5a: EnrolmentProgress.documents is now real (all config-required slots accepted) and
  prepare() refuses until every required document is accepted
- Phase 5a: 12 document API tests (hero upload, accept→can_prepare, replace, download, corrupt
  file, multi-page PDF for photograph, accept blocked, delete, ownership, prepared lock)
- Phase 5a: EnrolmentDocument.ready / DocumentOut.ready expose the engine's verdict separately
  from `accepted` (the citizen's), so the list endpoint alone tells the UI what to offer
- Phase 5b: frontend lib/documents.ts — zod mirrors of the upload contract, upload/accept/delete
  clients, and fetchDocumentObjectUrl (auth-protected file fetched as a blob URL)
- Phase 5b: DocumentSlot component — choose file → "preparing…" → before/after (struck-through
  original → optimised size, % smaller, Readable ✓, format/dimensions/pages) → what we changed →
  warnings → preview → "Use this file" / "Choose a different file" / "Remove"
- Phase 5b: engine step + warning codes translated to citizen language in the UI, with regex
  handling for the dynamic dpi_below_recommended_N / pages_rasterised_at_Ndpi codes
- Phase 5b: RequirementSummary extracted to its own module so DocumentSlot can reuse it
- Phase 5b: DocumentRequirementsPage rewritten — one slot per config document, "N of M documents
  ready", privacy note, Continue gated on every slot being accepted
- Phase 5b: ReviewPage shows a per-slot documents checklist and disables "Prepare my application"
  until progress.can_prepare is true
- Phase 5b: verified against a live server (7.46 MB JPEG → 1.93 MB, −72.9%, quality 88,
  3240×2430 retained, ready/accept/file all as the zod schemas expect)

Next:
Phase 6: AI-assisted analysis behind a replaceable interface — document-type suggestion and
readability advice only; deterministic operations stay deterministic

Known Issues:
- Docker not installed on this machine → compose files can be authored but not run/verified here
- No local PostgreSQL → local dev uses SQLite via DATABASE_URL; Postgres used in Docker Compose
- requirements.txt uses >= pins (Python 3.14 lacks older wheels)
- Vite dev server binds localhost (not 127.0.0.1); use http://localhost:5173
- JWT stored in localStorage (prototype tradeoff); revisit in Phase 8
- No refresh tokens / no rate limiting yet (Phase 8)
- documents step in EnrolmentProgress is real as of Phase 5a: it is true only when every
  config-required slot has an accepted document
- A compliant file is passed through untouched, so its EXIF (incl. GPS) is not stripped;
  revisit in Phase 8 (lossless metadata strip)
- Converting a PDF to an image, or rasterising PDF pages to hit a size limit, removes the text
  layer; the engine warns but this is irreversible
- min_dpi is validated as a warning, not a rejection (self-reported metadata is unreliable)
- Whole document is held in memory during processing; upload ceiling is MAX_UPLOAD_BYTES (25 MB),
  enforced after the body is buffered — streaming rejection is a Phase 8 item
- Optimised documents are stored unencrypted on local disk and are never purged (Phase 8)
- DocumentOut.format is lowercase ("jpeg") while UploadOutcome.format is upper-case ("JPEG"); the
  UI normalises both, but the contract should be made consistent
- Preview images are re-fetched as blobs on every mount (no caching); fine at prototype scale

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
- Engine reports failures as data (succeeded/failure_reason), never raises on bad input
- Readability guards are hard limits: BALANCED quality>=55 & scale>=0.45, AGGRESSIVE 35 / 0.28;
  if the portal's size limit needs more than that, the engine stops and says target_met=False
- Validation re-measures the produced bytes; the engine's own opinion of its output is not trusted
- UploadService is the only engine entry point the API layer uses; collaborators are injected so
  Phase 6 AI can replace analyzer/strategy without touching the API
- Only the optimised file is persisted; the original bytes are never written to disk
- Storage keys are opaque random hex, so a document id never reveals a filesystem path
- Upload is two-step (pending → accept): the citizen sees the result before it counts as done,
  and a not-ready file is still stored for viewing but cannot be accepted (409)
- Plain-language citizen messages live in the API layer; the engine only emits stable issue codes
- The upload response is the source of truth for the before/after moment; the stored row only keeps
  the summary, so the UI shows the full result while the response is in hand
- Auth-protected file endpoint means previews are blob URLs, revoked on unmount — never plain src
