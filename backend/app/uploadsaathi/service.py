"""UploadService — the one entry point the API layer needs.

analyze → plan → execute → re-measure → validate. Every collaborator is injected, so the AI layer
in Phase 6 can replace the analyzer or strategy provider without touching this orchestration or
anything above it.

Knows nothing about Aadhaar: it is handed a portal id and a document type, and the
RequirementResolver reads those from configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .analyzer import DocumentAnalysis, DocumentAnalyzer
from .engine import OptimizationEngine, OptimizedDocument
from .formats import extension_for, mime_for
from .quality import QualityValidator, ValidationResult
from .requirements.models import Requirement
from .requirements.resolver import RequirementResolver, get_resolver
from .strategy import OptimizationMode, OptimizationPlan, OptimizationStrategyProvider


@dataclass(frozen=True, slots=True)
class UploadResult:
    """Stable contract returned to the API layer. `data` never crosses the JSON boundary."""

    data: bytes
    filename: str
    original_size: int
    optimized_size: int
    format: str
    mime_type: str | None
    reduction_percent: float
    size_valid: bool
    format_valid: bool
    quality_status: str
    accepted: bool
    readable: bool
    steps: tuple[str, ...] = field(default_factory=tuple)
    issues: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    width: int | None = None
    height: int | None = None
    pages: int | None = None
    quality_used: int | None = None
    scale_applied: float = 1.0
    mode: str = OptimizationMode.BALANCED.value

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe view. Deliberately excludes the document bytes."""
        return {
            "filename": self.filename,
            "original_size": self.original_size,
            "optimized_size": self.optimized_size,
            "format": self.format.upper(),
            "mime_type": self.mime_type,
            "reduction_percent": self.reduction_percent,
            "size_valid": self.size_valid,
            "format_valid": self.format_valid,
            "quality_status": self.quality_status,
            "accepted": self.accepted,
            "readable": self.readable,
            "steps": list(self.steps),
            "issues": list(self.issues),
            "warnings": list(self.warnings),
            "notes": list(self.notes),
            "width": self.width,
            "height": self.height,
            "pages": self.pages,
            "quality_used": self.quality_used,
            "scale_applied": self.scale_applied,
            "mode": self.mode,
        }


class UploadService:
    def __init__(
        self,
        resolver: RequirementResolver | None = None,
        analyzer: DocumentAnalyzer | None = None,
        strategy: OptimizationStrategyProvider | None = None,
        engine: OptimizationEngine | None = None,
        validator: QualityValidator | None = None,
    ) -> None:
        self.resolver = resolver or get_resolver()
        self.analyzer = analyzer or DocumentAnalyzer()
        self.strategy = strategy or OptimizationStrategyProvider()
        self.engine = engine or OptimizationEngine()
        self.validator = validator or QualityValidator()

    def process(
        self,
        data: bytes,
        filename: str,
        portal_id: str,
        document_type: str,
        mode: OptimizationMode = OptimizationMode.BALANCED,
    ) -> UploadResult:
        """Make one document portal-ready. Raises only for an unknown portal/document type."""
        requirement = self.resolver.resolve(portal_id, document_type)
        analysis = self.analyzer.analyze(data, filename)
        plan = self.strategy.plan(analysis, requirement, mode)
        outcome = self.engine.execute(data, plan)
        optimized = self.analyzer.analyze(outcome.data, filename)
        validation = self.validator.validate(analysis, optimized, requirement, outcome=outcome)
        return self._build(
            analysis=analysis,
            optimized=optimized,
            outcome=outcome,
            plan=plan,
            validation=validation,
            requirement=requirement,
        )

    def preview(
        self, data: bytes, filename: str, portal_id: str, document_type: str
    ) -> tuple[DocumentAnalysis, Requirement, OptimizationPlan]:
        """Measure and decide without spending time on the actual conversion."""
        requirement = self.resolver.resolve(portal_id, document_type)
        analysis = self.analyzer.analyze(data, filename)
        return analysis, requirement, self.strategy.plan(analysis, requirement)

    # --- assembly ---------------------------------------------------------

    def _build(
        self,
        *,
        analysis: DocumentAnalysis,
        optimized: DocumentAnalysis,
        outcome: OptimizedDocument,
        plan: OptimizationPlan,
        validation: ValidationResult,
        requirement: Requirement,
    ) -> UploadResult:
        fmt = optimized.detected_format or outcome.detected_format
        return UploadResult(
            data=outcome.data,
            filename=self._output_filename(fmt, requirement.document_type),
            original_size=analysis.byte_size,
            optimized_size=optimized.byte_size,
            format=fmt,
            mime_type=optimized.mime_type or mime_for(fmt),
            reduction_percent=outcome.reduction_percent,
            size_valid=validation.size_valid,
            format_valid=validation.format_valid,
            quality_status=validation.quality_status,
            accepted=validation.is_valid,
            readable=validation.readable,
            steps=outcome.steps_applied,
            issues=validation.issues,
            warnings=validation.warnings,
            notes=plan.notes,
            width=optimized.width,
            height=optimized.height,
            pages=optimized.pages,
            quality_used=outcome.quality_used,
            scale_applied=outcome.scale_applied,
            mode=plan.mode.value,
        )

    @staticmethod
    def _output_filename(fmt: str, document_type: str) -> str:
        """A predictable, portal-friendly name. The uploaded filename is never trusted."""
        return f"{document_type}.{extension_for(fmt) or 'bin'}"
