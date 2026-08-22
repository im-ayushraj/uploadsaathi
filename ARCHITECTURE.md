# UploadSaathi — Architecture

> Prototype — Not an official UIDAI product. Synthetic/demo data only. No live government APIs.

## Two layers

1. **Aadhaar-inspired prototype portal** — first case study only (UI + enrolment workflow).
2. **UploadSaathi Smart Upload engine** — reusable, portal-agnostic document optimization core.

The engine must never import Aadhaar-specific code.

## Repository layout

```
backend/
  app/
    api/v1/            # FastAPI routers (health, auth, enrolments, uploads)
    core/              # config, security, logging
    db/                # session, base, models
    schemas/           # Pydantic
    uploadsaathi/      # SMART UPLOAD ENGINE (portal-agnostic)
      requirements/    # RequirementResolver + config loader
      analyzer/        # DocumentAnalyzer
      strategy/        # OptimizationStrategyProvider
      engine/          # OptimizationEngine (Pillow/PyMuPDF)
      quality/         # QualityValidator
      service.py       # UploadService (orchestrator)
      ai/              # Phase 6, replaceable interface
    config/portals/    # aadhaar.json, (passport.json, pan.json ... later)
  alembic/
frontend/
  src/
    app/               # router, providers
    features/          # auth, enrolment, uploadsaathi
    components/        # shared UI
    lib/               # api client, zod schemas
infra/                 # docker-compose, Dockerfiles
docs/
```

## Engine contracts

- `RequirementResolver.resolve(portal, document_type) -> Requirement`
  Requirement: allowed formats, max/min bytes, min/max dimensions, min DPI, colour mode, page limits.
- `DocumentAnalyzer.analyze(data, filename) -> DocumentAnalysis`
  Magic-byte type sniffing (the extension is never trusted), dimensions, DPI, colour mode, alpha,
  PDF pages / text layer / embedded images / encryption. Failures are returned as data.
- `OptimizationStrategyProvider.plan(analysis, requirement, mode) -> OptimizationPlan`
  Ordered deterministic steps (convert → resize → recompress → target-size search) plus the
  readability guards for the chosen mode. An impossible conversion is returned as
  `feasible=False` with a reason rather than attempted.
- `OptimizationEngine.execute(data, plan) -> OptimizedDocument`
  Quality binary search first, then a gentle downscale ladder; stops at the guards. A document
  that already complies is returned byte-identical.
- `QualityValidator.validate(original, optimized, requirement) -> ValidationResult`
  Re-measures the produced bytes and checks each rule separately. Readability guardrails; refuses
  to silently destroy a document. DPI is advisory (a warning), never a hard rejection.
- `UploadService.process(data, filename, portal, document_type, mode) -> UploadResult`

`UploadResult.to_dict()` shape (stable contract):
```json
{
  "filename": "address_proof.jpg",
  "original_size": 7458923, "optimized_size": 2021021, "format": "JPEG",
  "mime_type": "image/jpeg", "reduction_percent": 72.9,
  "size_valid": true, "format_valid": true, "quality_status": "passed",
  "accepted": true, "readable": true,
  "steps": ["auto_orient", "strip_metadata", "recompress", "target_size_search"],
  "issues": [], "warnings": [], "notes": [],
  "width": 3240, "height": 2430, "pages": 1,
  "quality_used": 88, "scale_applied": 1.0, "mode": "balanced"
}
```
`quality_status` is one of `unchanged` / `passed` / `degraded` / `failed`. `accepted` is the single
flag the UI gates on; `issues` explains a rejection, `warnings` explains a compromise. The
document bytes are on the dataclass only and never cross the JSON boundary.

## Requirements are configuration

`backend/app/config/portals/*.json` describes each portal and its document types. Adding
Passport/PAN/UPSC later means adding a config file, not changing engine or UI code.

## Data / privacy

- Uploads processed in temp storage, cleaned up after response.
- No document contents logged; no real identity data.
- Passwords hashed (bcrypt/argon2); JWT access tokens.

## AI boundary (Phase 6)

AI may classify documents, describe characteristics, recommend a strategy, and judge readability.
AI must never compute byte sizes, resize, compress, convert, or decide requirement validity.
