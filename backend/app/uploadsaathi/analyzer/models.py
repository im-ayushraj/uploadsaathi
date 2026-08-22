"""What the analyzer reports about a document. Portal-agnostic."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DocumentAnalysis:
    """Measured facts about an uploaded file. No judgements about any portal's rules."""

    byte_size: int
    detected_format: str | None
    mime_type: str | None
    kind: str  # "image" | "pdf" | "unknown"
    is_supported: bool
    is_readable: bool
    failure_reason: str | None = None
    declared_extension: str | None = None
    extension_mismatch: bool = False

    # images (and PDF page 1, rendered-equivalent dimensions are not computed here)
    width: int | None = None
    height: int | None = None
    dpi: int | None = None
    colour_mode: str | None = None  # "colour" | "greyscale" | "bw"
    has_alpha: bool = False

    # pdf
    pages: int | None = None
    pdf_has_text_layer: bool | None = None
    pdf_image_count: int | None = None
    pdf_is_encrypted: bool = False

    @property
    def pixels(self) -> int | None:
        if self.width and self.height:
            return self.width * self.height
        return None

    @property
    def megapixels(self) -> float | None:
        px = self.pixels
        return round(px / 1_000_000, 2) if px else None

    @property
    def is_usable(self) -> bool:
        """Safe to hand to the optimisation engine."""
        return self.is_supported and self.is_readable
