"""DocumentAnalyzer — measures a document deterministically.

Everything here is measurement, never judgement: no portal rules, no AI. Failures are reported
as data (`is_readable=False`, `failure_reason`) rather than raised, so callers can show a helpful
message instead of a stack trace.
"""

from __future__ import annotations

import io
from pathlib import PurePath

import pymupdf
from PIL import Image, UnidentifiedImageError

from ..formats import canonical_format, is_image, mime_for, sniff_format
from .models import DocumentAnalysis

# A ceiling on decoded pixels, well above any legitimate document scan, to stop
# decompression-bomb style inputs from exhausting memory.
MAX_DECODED_PIXELS = 300_000_000

# How many PDF pages to inspect for a text layer / embedded images.
PDF_INSPECT_PAGES = 5

_GREYSCALE_MODES = {"L", "LA", "I", "I;16", "F"}
_BILEVEL_MODES = {"1"}


class DocumentAnalyzer:
    def __init__(self, max_decoded_pixels: int = MAX_DECODED_PIXELS) -> None:
        self.max_decoded_pixels = max_decoded_pixels

    def analyze(self, data: bytes, filename: str | None = None) -> DocumentAnalysis:
        declared = self._declared_extension(filename)
        fmt = sniff_format(data)
        mismatch = bool(declared and fmt and canonical_format(declared) != fmt)

        if fmt is None:
            return DocumentAnalysis(
                byte_size=len(data),
                detected_format=None,
                mime_type=None,
                kind="unknown",
                is_supported=False,
                is_readable=False,
                failure_reason="unsupported_format",
                declared_extension=declared,
                extension_mismatch=bool(declared),
            )

        base = {
            "byte_size": len(data),
            "detected_format": fmt,
            "mime_type": mime_for(fmt),
            "declared_extension": declared,
            "extension_mismatch": mismatch,
            "is_supported": True,
        }

        if is_image(fmt):
            return self._analyze_image(data, base)
        return self._analyze_pdf(data, base)

    # --- internals --------------------------------------------------------

    @staticmethod
    def _declared_extension(filename: str | None) -> str | None:
        if not filename:
            return None
        suffix = PurePath(filename).suffix.lower().lstrip(".")
        return suffix or None

    @staticmethod
    def _colour_mode(mode: str) -> str:
        if mode in _BILEVEL_MODES:
            return "bw"
        if mode in _GREYSCALE_MODES:
            return "greyscale"
        return "colour"

    def _analyze_image(self, data: bytes, base: dict) -> DocumentAnalysis:
        try:
            with Image.open(io.BytesIO(data)) as img:
                width, height = img.size
                if width * height > self.max_decoded_pixels:
                    return DocumentAnalysis(
                        **base,
                        kind="image",
                        is_readable=False,
                        failure_reason="image_too_large_to_process",
                        width=width,
                        height=height,
                    )
                # verify() consumes the file object, so read attributes first.
                mode = img.mode
                dpi_pair = img.info.get("dpi")
                has_alpha = mode in ("RGBA", "LA", "PA") or "transparency" in img.info
                img.load()  # forces a full decode; raises on truncated data
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
            reason = (
                "image_too_large_to_process"
                if isinstance(exc, Image.DecompressionBombError)
                else "corrupted_or_unreadable"
            )
            return DocumentAnalysis(**base, kind="image", is_readable=False, failure_reason=reason)

        dpi: int | None = None
        if dpi_pair:
            try:
                dpi = int(round(min(float(dpi_pair[0]), float(dpi_pair[1]))))
            except (TypeError, ValueError, IndexError):
                dpi = None
            if dpi is not None and dpi <= 0:
                dpi = None

        return DocumentAnalysis(
            **base,
            kind="image",
            is_readable=True,
            width=width,
            height=height,
            dpi=dpi,
            colour_mode=self._colour_mode(mode),
            has_alpha=has_alpha,
            pages=1,
        )

    def _analyze_pdf(self, data: bytes, base: dict) -> DocumentAnalysis:
        try:
            with pymupdf.open(stream=data, filetype="pdf") as doc:
                if doc.needs_pass:
                    return DocumentAnalysis(
                        **base,
                        kind="pdf",
                        is_readable=False,
                        failure_reason="password_protected",
                        pages=doc.page_count or None,
                        pdf_is_encrypted=True,
                    )

                pages = doc.page_count
                if pages == 0:
                    return DocumentAnalysis(
                        **base,
                        kind="pdf",
                        is_readable=False,
                        failure_reason="corrupted_or_unreadable",
                        pages=0,
                    )

                has_text = False
                image_count = 0
                for index in range(min(pages, PDF_INSPECT_PAGES)):
                    page = doc.load_page(index)
                    if not has_text and page.get_text("text").strip():
                        has_text = True
                    image_count += len(page.get_images(full=False))

                first = doc.load_page(0)
                # Page geometry is in points (1/72 inch); convert to pixels at the PDF's
                # native 72 dpi so width/height stay comparable with image inputs.
                rect = first.rect
                width = int(round(rect.width))
                height = int(round(rect.height))
        except Exception:
            # PyMuPDF raises a variety of types for malformed input; all mean "unreadable".
            return DocumentAnalysis(
                **base, kind="pdf", is_readable=False, failure_reason="corrupted_or_unreadable"
            )

        return DocumentAnalysis(
            **base,
            kind="pdf",
            is_readable=True,
            width=width,
            height=height,
            dpi=72,
            pages=pages,
            pdf_has_text_layer=has_text,
            pdf_image_count=image_count,
        )
