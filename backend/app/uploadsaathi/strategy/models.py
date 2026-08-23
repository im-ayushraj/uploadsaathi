"""What the strategy provider decides, before any bytes are touched."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class OptimizationMode(StrEnum):
    """BALANCED protects readability; AGGRESSIVE is only used when the citizen opts in."""

    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class Operation(StrEnum):
    AUTO_ORIENT = "auto_orient"
    STRIP_METADATA = "strip_metadata"
    FLATTEN_ALPHA = "flatten_alpha"
    GREYSCALE = "greyscale"
    CONVERT = "convert"
    RESIZE = "resize"
    RECOMPRESS = "recompress"
    TARGET_SIZE_SEARCH = "target_size_search"
    PDF_OPTIMISE_STRUCTURE = "pdf_optimise_structure"
    PDF_DOWNSAMPLE_IMAGES = "pdf_downsample_images"
    PDF_RASTERISE_PAGES = "pdf_rasterise_pages"


# Readability guards. Going past these destroys the document, so the engine never does.
QUALITY_FLOOR_BALANCED = 55
QUALITY_FLOOR_AGGRESSIVE = 35
MIN_SCALE_BALANCED = 0.45
MIN_SCALE_AGGRESSIVE = 0.28
QUALITY_START = 90


@dataclass(frozen=True, slots=True)
class OptimizationPlan:
    """A deterministic, ordered recipe. Contains no bytes and performs no work."""

    source_format: str
    target_format: str
    kind: str  # "image" | "pdf"
    mode: OptimizationMode
    operations: tuple[Operation, ...]
    max_bytes: int
    min_bytes: int = 0

    # upper bounds the output must fit inside (from the portal requirement)
    max_width: int | None = None
    max_height: int | None = None
    # floors the engine must never shrink below (readability guard)
    min_width: int | None = None
    min_height: int | None = None

    quality_start: int = QUALITY_START
    quality_floor: int = QUALITY_FLOOR_BALANCED
    min_scale: float = MIN_SCALE_BALANCED
    to_greyscale: bool = False

    feasible: bool = True
    infeasible_reason: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def needs_work(self) -> bool:
        return bool(self.operations)
