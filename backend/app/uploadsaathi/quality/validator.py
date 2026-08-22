"""QualityValidator — checks the *finished bytes* against the portal's rules.

Two principles:

1. Validate what was actually produced, re-measured from the output bytes, never what the engine
   believed it wrote.
2. Never claim a document is fine when it has been degraded. A valid-but-heavily-reduced document
   is reported as ``degraded`` so the citizen can decide.

DPI is deliberately advisory. It is self-reported metadata that is missing or wrong on most phone
photos and meaningless for a PDF page box, so treating it as a hard gate would reject good
documents. It is surfaced as a warning instead.
"""

from __future__ import annotations

from ..analyzer.models import DocumentAnalysis
from ..engine.models import OptimizedDocument
from ..formats import canonical_format
from ..requirements.models import Requirement
from ..strategy.models import QUALITY_FLOOR_AGGRESSIVE
from .models import QualityStatus, ValidationResult

# Below these, a document has lost enough that the citizen should be told before uploading.
DEGRADED_SCALE = 0.6
DEGRADED_QUALITY_MARGIN = 5
MIN_READABLE_PIXELS = 100_000


class QualityValidator:
    def validate(
        self,
        original: DocumentAnalysis,
        optimized: DocumentAnalysis,
        requirement: Requirement,
        *,
        outcome: OptimizedDocument | None = None,
    ) -> ValidationResult:
        if outcome is not None and not outcome.succeeded:
            return self._failure(outcome.failure_reason or "processing_failed")
        if not optimized.is_usable:
            return self._failure(optimized.failure_reason or "output_unreadable")

        issues: list[str] = []
        warnings: list[str] = list(outcome.warnings) if outcome else []

        size_valid = self._check_size(optimized, requirement, issues)
        format_valid = self._check_format(optimized, requirement, issues)
        dimensions_valid = self._check_dimensions(optimized, requirement, issues)
        pages_valid = self._check_pages(optimized, requirement, issues)
        colour_valid = self._check_colour(optimized, requirement, issues)
        self._check_dpi(optimized, requirement, warnings)

        readable = self._is_readable(optimized, requirement, outcome)
        if not readable:
            issues.append("readability_below_acceptable_level")

        degraded = self._degradation_warnings(original, optimized, outcome, warnings)
        is_valid = all(
            (size_valid, format_valid, dimensions_valid, pages_valid, colour_valid, readable)
        )

        status: QualityStatus
        if not is_valid:
            status = "failed"
        elif outcome is not None and not outcome.changed:
            status = "unchanged"
        elif degraded:
            status = "degraded"
        else:
            status = "passed"

        return ValidationResult(
            is_valid=is_valid,
            quality_status=status,
            readable=readable,
            size_valid=size_valid,
            format_valid=format_valid,
            dimensions_valid=dimensions_valid,
            pages_valid=pages_valid,
            colour_valid=colour_valid,
            issues=tuple(dict.fromkeys(issues)),
            warnings=tuple(dict.fromkeys(warnings)),
        )

    # --- individual rules -------------------------------------------------

    @staticmethod
    def _check_size(
        optimized: DocumentAnalysis, requirement: Requirement, issues: list[str]
    ) -> bool:
        ok = True
        if optimized.byte_size > requirement.max_bytes:
            issues.append("file_too_large")
            ok = False
        if requirement.min_bytes and optimized.byte_size < requirement.min_bytes:
            issues.append("file_too_small")
            ok = False
        return ok

    @staticmethod
    def _check_format(
        optimized: DocumentAnalysis, requirement: Requirement, issues: list[str]
    ) -> bool:
        accepted = {canonical_format(f) or f for f in requirement.accepted_formats}
        if optimized.detected_format not in accepted:
            issues.append("format_not_accepted")
            return False
        return True

    @staticmethod
    def _check_dimensions(
        optimized: DocumentAnalysis, requirement: Requirement, issues: list[str]
    ) -> bool:
        width, height = optimized.width, optimized.height
        if width is None or height is None:
            return True  # nothing measurable; not a reason to reject
        ok = True
        if requirement.min_width and width < requirement.min_width:
            issues.append("below_min_width")
            ok = False
        if requirement.min_height and height < requirement.min_height:
            issues.append("below_min_height")
            ok = False
        if requirement.max_width and width > requirement.max_width:
            issues.append("above_max_width")
            ok = False
        if requirement.max_height and height > requirement.max_height:
            issues.append("above_max_height")
            ok = False
        return ok

    @staticmethod
    def _check_pages(
        optimized: DocumentAnalysis, requirement: Requirement, issues: list[str]
    ) -> bool:
        if not requirement.max_pages or optimized.pages is None:
            return True
        if optimized.pages > requirement.max_pages:
            issues.append("too_many_pages")
            return False
        return True

    @staticmethod
    def _check_colour(
        optimized: DocumentAnalysis, requirement: Requirement, issues: list[str]
    ) -> bool:
        mode = requirement.colour_mode
        if mode == "any" or optimized.colour_mode is None:
            return True
        if mode == "colour" and optimized.colour_mode != "colour":
            issues.append("colour_document_required")
            return False
        if mode == "greyscale" and optimized.colour_mode not in ("greyscale", "bw"):
            issues.append("greyscale_document_required")
            return False
        return True

    @staticmethod
    def _check_dpi(
        optimized: DocumentAnalysis, requirement: Requirement, warnings: list[str]
    ) -> None:
        if not requirement.min_dpi or optimized.kind != "image":
            return
        if optimized.dpi is None:
            warnings.append("dpi_not_declared_by_file")
        elif optimized.dpi < requirement.min_dpi:
            warnings.append(f"dpi_below_recommended_{requirement.min_dpi}")

    @staticmethod
    def _is_readable(
        optimized: DocumentAnalysis,
        requirement: Requirement,
        outcome: OptimizedDocument | None,
    ) -> bool:
        """The guardrail: refuse to call an unusably reduced document 'ready'."""
        if not optimized.is_usable:
            return False
        if outcome is not None and outcome.quality_used is not None:
            if outcome.quality_used < QUALITY_FLOOR_AGGRESSIVE:
                return False
        pixels = optimized.pixels or 0
        explicit_floor = bool(requirement.min_width or requirement.min_height)
        # Roughly below 400x250 nothing legible survives; only applied when the portal itself
        # states no minimum dimensions (if it does, _check_dimensions is the authority).
        return explicit_floor or not pixels or pixels >= MIN_READABLE_PIXELS

    @staticmethod
    def _degradation_warnings(
        original: DocumentAnalysis,
        optimized: DocumentAnalysis,
        outcome: OptimizedDocument | None,
        warnings: list[str],
    ) -> bool:
        degraded = False
        if outcome is not None:
            if outcome.scale_applied < DEGRADED_SCALE:
                warnings.append("significant_resolution_reduction")
                degraded = True
            if (
                outcome.quality_used is not None
                and outcome.quality_used <= QUALITY_FLOOR_AGGRESSIVE + DEGRADED_QUALITY_MARGIN
            ):
                warnings.append("heavy_compression_applied")
                degraded = True
        if (
            original.pdf_has_text_layer
            and optimized.kind == "pdf"
            and optimized.pdf_has_text_layer is False
        ):
            warnings.append("searchable_text_layer_lost")
            degraded = True
        if original.kind == "pdf" and optimized.kind == "image":
            degraded = True
        return degraded

    @staticmethod
    def _failure(reason: str) -> ValidationResult:
        return ValidationResult(
            is_valid=False,
            quality_status="failed",
            readable=False,
            size_valid=False,
            format_valid=False,
            dimensions_valid=False,
            pages_valid=False,
            colour_valid=False,
            issues=(reason,),
        )
