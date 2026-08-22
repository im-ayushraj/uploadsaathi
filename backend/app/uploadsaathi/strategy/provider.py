"""OptimizationStrategyProvider — decides *what* to do, deterministically.

Pure decision logic: takes measurements (DocumentAnalysis) plus rules (Requirement) and returns
an ordered plan. No file I/O, no AI, no portal-specific knowledge. Phase 6 may add an advisory
AI layer on top, but this provider must always be able to stand alone.
"""

from __future__ import annotations

from ..analyzer.models import DocumentAnalysis
from ..formats import canonical_format, is_image
from ..requirements.models import Requirement
from .models import (
    MIN_SCALE_AGGRESSIVE,
    MIN_SCALE_BALANCED,
    QUALITY_FLOOR_AGGRESSIVE,
    QUALITY_FLOOR_BALANCED,
    QUALITY_START,
    Operation,
    OptimizationMode,
    OptimizationPlan,
)


class OptimizationStrategyProvider:
    def plan(
        self,
        analysis: DocumentAnalysis,
        requirement: Requirement,
        mode: OptimizationMode = OptimizationMode.BALANCED,
    ) -> OptimizationPlan:
        source = analysis.detected_format or "unknown"
        accepted = tuple(canonical_format(f) or f for f in requirement.accepted_formats)

        target, convert_note, infeasible = self._choose_target(
            source, accepted, analysis, requirement
        )
        aggressive = mode is OptimizationMode.AGGRESSIVE

        base = dict(
            source_format=source,
            target_format=target,
            kind=analysis.kind,
            mode=mode,
            max_bytes=requirement.max_bytes,
            min_bytes=requirement.min_bytes,
            max_width=requirement.max_width,
            max_height=requirement.max_height,
            min_width=requirement.min_width,
            min_height=requirement.min_height,
            quality_start=QUALITY_START,
            quality_floor=QUALITY_FLOOR_AGGRESSIVE if aggressive else QUALITY_FLOOR_BALANCED,
            min_scale=MIN_SCALE_AGGRESSIVE if aggressive else MIN_SCALE_BALANCED,
        )

        if infeasible:
            return OptimizationPlan(
                **base, operations=(), feasible=False, infeasible_reason=infeasible
            )

        notes: list[str] = []
        if convert_note:
            notes.append(convert_note)

        operations: list[Operation] = []
        converting = target != source

        if is_image(target):
            operations.extend(self._image_operations(analysis, requirement, target, converting, notes))
        else:
            operations.extend(self._pdf_operations(analysis, requirement, converting, notes))

        to_greyscale = (
            requirement.colour_mode == "greyscale" and analysis.colour_mode != "greyscale"
        )
        if to_greyscale:
            operations.append(Operation.GREYSCALE)
        if requirement.colour_mode == "colour" and analysis.colour_mode in ("greyscale", "bw"):
            notes.append("colour_required_but_source_is_not_colour")

        if analysis.byte_size > requirement.max_bytes:
            operations.append(Operation.TARGET_SIZE_SEARCH)
        if requirement.min_bytes and analysis.byte_size < requirement.min_bytes:
            notes.append("file_smaller_than_portal_minimum")

        # Keep the recipe in a stable, meaningful order regardless of how it was assembled.
        operations = [op for op in _ORDER if op in set(operations)]

        return OptimizationPlan(
            **base,
            operations=tuple(operations),
            to_greyscale=to_greyscale,
            notes=tuple(dict.fromkeys(notes)),
        )

    # --- decisions --------------------------------------------------------

    @staticmethod
    def _choose_target(
        source: str,
        accepted: tuple[str, ...],
        analysis: DocumentAnalysis,
        requirement: Requirement,
    ) -> tuple[str, str | None, str | None]:
        """Returns (target_format, conversion_note, infeasible_reason)."""
        if not analysis.is_usable:
            return source, None, analysis.failure_reason or "unusable_document"
        if not accepted:
            return source, None, "no_accepted_formats_configured"
        if source in accepted:
            # PNG is lossless, so the only way to shrink it is to throw away pixels — which hits
            # the readability floor long before a tight size limit is met. When the portal also
            # accepts JPEG, re-encoding is the readable way to fit (a screenshot of a document is
            # the common case).
            if (
                source == "png"
                and "jpeg" in accepted
                and analysis.byte_size > requirement.max_bytes
            ):
                return "jpeg", "png_re_encoded_as_jpeg_to_meet_size_limit", None
            return source, None, None

        # Conversion is required. Prefer a target that preserves the document's nature.
        if is_image(source):
            if "jpeg" in accepted:
                return "jpeg", "converted_png_to_jpeg", None
            if "png" in accepted:
                return "png", "converted_to_png", None
            if "pdf" in accepted:
                return "pdf", "converted_image_to_pdf", None
        elif source == "pdf":
            if (analysis.pages or 1) > 1:
                # Flattening a multi-page PDF into one image would silently lose pages.
                return source, None, "multipage_pdf_cannot_convert_to_image"
            if "jpeg" in accepted:
                return "jpeg", "converted_single_page_pdf_to_jpeg", None
            if "png" in accepted:
                return "png", "converted_single_page_pdf_to_png", None

        return source, None, "format_not_accepted_and_no_conversion_available"

    def _image_operations(
        self,
        analysis: DocumentAnalysis,
        requirement: Requirement,
        target: str,
        converting: bool,
        notes: list[str],
    ) -> list[Operation]:
        ops: list[Operation] = []
        if converting:
            ops.append(Operation.CONVERT)
        if analysis.has_alpha and target == "jpeg":
            ops.append(Operation.FLATTEN_ALPHA)
            notes.append("transparency_flattened_onto_white")

        if self._exceeds_bounds(analysis, requirement):
            ops.append(Operation.RESIZE)
        if analysis.byte_size > requirement.max_bytes:
            ops.append(Operation.RECOMPRESS)

        # Re-encoding always costs a little quality, so a compliant file is left byte-identical.
        # Auto-orient and metadata stripping ride along only when we are re-encoding anyway.
        if ops:
            ops.extend((Operation.AUTO_ORIENT, Operation.STRIP_METADATA))

        if requirement.min_width and analysis.width and analysis.width < requirement.min_width:
            notes.append("below_portal_minimum_width")
        if requirement.min_height and analysis.height and analysis.height < requirement.min_height:
            notes.append("below_portal_minimum_height")
        if requirement.min_dpi and analysis.dpi and analysis.dpi < requirement.min_dpi:
            notes.append("below_portal_minimum_dpi")
        return ops

    def _pdf_operations(
        self,
        analysis: DocumentAnalysis,
        requirement: Requirement,
        converting: bool,
        notes: list[str],
    ) -> list[Operation]:
        ops: list[Operation] = []
        if converting:
            ops.append(Operation.CONVERT)
            return ops

        # Structure/metadata cleanup is safe and often enough on its own, but a PDF that already
        # complies is left byte-identical rather than rewritten.
        if analysis.byte_size > requirement.max_bytes:
            ops.append(Operation.PDF_OPTIMISE_STRUCTURE)
            ops.append(Operation.PDF_DOWNSAMPLE_IMAGES)
        if requirement.max_pages and (analysis.pages or 0) > requirement.max_pages:
            notes.append("too_many_pages_for_portal")
        return ops

    @staticmethod
    def _exceeds_bounds(analysis: DocumentAnalysis, requirement: Requirement) -> bool:
        if requirement.max_width and analysis.width and analysis.width > requirement.max_width:
            return True
        if requirement.max_height and analysis.height and analysis.height > requirement.max_height:
            return True
        return False


_ORDER: tuple[Operation, ...] = (
    Operation.AUTO_ORIENT,
    Operation.STRIP_METADATA,
    Operation.CONVERT,
    Operation.FLATTEN_ALPHA,
    Operation.GREYSCALE,
    Operation.RESIZE,
    Operation.RECOMPRESS,
    Operation.PDF_OPTIMISE_STRUCTURE,
    Operation.PDF_DOWNSAMPLE_IMAGES,
    Operation.TARGET_SIZE_SEARCH,
)
