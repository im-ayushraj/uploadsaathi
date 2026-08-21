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
- `DocumentAnalyzer.analyze(file) -> DocumentAnalysis`
  Real type sniffing, dimensions, pages, byte size, estimated text density/sharpness.
- `OptimizationStrategyProvider.plan(analysis, requirement) -> OptimizationPlan`
  Ordered deterministic steps (convert → resize → recompress → target-size search).
- `OptimizationEngine.execute(file, plan) -> OptimizedDocument`
- `QualityValidator.validate(original, optimized, requirement) -> ValidationResult`
  Readability guardrails; refuses to silently destroy a document.
- `UploadService.process(file, portal, document_type) -> UploadResult`

`UploadResult` shape (stable contract):
```json
{
  "original_size": 7759462, "optimized_size": 1908736, "format": "JPEG",
  "reduction_percent": 75.4, "size_valid": true, "format_valid": true,
  "quality_status": "passed", "warnings": [], "steps": ["..."]
}
```

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
