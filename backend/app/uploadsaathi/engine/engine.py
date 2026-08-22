"""OptimizationEngine — executes a plan over real bytes. Deterministic, no AI.

Every reduction is bounded by the plan's readability guards (`quality_floor`, `min_scale`,
`min_width`/`min_height`). If the portal's size limit cannot be reached without crossing one of
those guards, the engine stops and says so instead of destroying the document.
"""

from __future__ import annotations

import io
from collections.abc import Callable

import pymupdf
from PIL import Image, ImageOps

from ..formats import sniff_format
from ..strategy.models import Operation, OptimizationMode, OptimizationPlan
from .models import OptimizedDocument

# Downscale ladder: gentle steps so we give up as little resolution as possible.
_SCALE_STEP = 0.85
_PDF_RASTER_DPI_BALANCED: tuple[int, ...] = (150, 120, 100)
_PDF_RASTER_DPI_AGGRESSIVE: tuple[int, ...] = (150, 120, 100, 80, 72)
_PDF_WRAP_DPI = 150

Encoder = Callable[[Image.Image, int], bytes]


class OptimizationEngine:
    """Stateless. Safe to reuse across requests."""

    def execute(self, data: bytes, plan: OptimizationPlan) -> OptimizedDocument:
        original_size = len(data)

        if not plan.feasible:
            return OptimizedDocument(
                data=data,
                detected_format=plan.source_format,
                kind=plan.kind,
                byte_size=original_size,
                original_byte_size=original_size,
                succeeded=False,
                failure_reason=plan.infeasible_reason or "not_feasible",
            )

        if not plan.needs_work:
            return OptimizedDocument(
                data=data,
                detected_format=plan.source_format,
                kind=plan.kind,
                byte_size=original_size,
                original_byte_size=original_size,
                target_met=original_size <= plan.max_bytes,
            )

        try:
            if plan.source_format == "pdf" and plan.target_format == "pdf":
                return self._run_pdf(data, plan)
            if plan.source_format == "pdf":
                return self._run_pdf_to_image(data, plan)
            return self._run_image(data, plan)
        except Exception:  # noqa: BLE001 — a processing failure must be reported, not raised
            return OptimizedDocument(
                data=data,
                detected_format=plan.source_format,
                kind=plan.kind,
                byte_size=original_size,
                original_byte_size=original_size,
                succeeded=False,
                failure_reason="processing_failed",
            )

    # --- image path -------------------------------------------------------

    def _run_image(self, data: bytes, plan: OptimizationPlan) -> OptimizedDocument:
        with Image.open(io.BytesIO(data)) as opened:
            opened.load()
            source_dpi = _dpi_of(opened)
            img = ImageOps.exif_transpose(opened) or opened
            img = img.copy()

        steps: list[str] = [Operation.AUTO_ORIENT.value, Operation.STRIP_METADATA.value]
        warnings: list[str] = []
        original_width = img.width

        img, prep_steps = self._prepare(img, plan)
        steps.extend(prep_steps)

        if Operation.RESIZE in plan.operations:
            fitted = self._fit_within_bounds(img, plan)
            if fitted is not img:
                img = fitted
                steps.append(Operation.RESIZE.value)

        return self._search_and_build(
            img,
            plan,
            original_byte_size=len(data),
            original_width=original_width,
            source_dpi=source_dpi,
            steps=steps,
            warnings=warnings,
        )

    def _run_pdf_to_image(self, data: bytes, plan: OptimizationPlan) -> OptimizedDocument:
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            page = doc.load_page(0)
            img = self._render(page, _PDF_WRAP_DPI)

        steps = [Operation.CONVERT.value, Operation.STRIP_METADATA.value]
        img, prep_steps = self._prepare(img, plan)
        steps.extend(prep_steps)

        original_width = img.width
        if Operation.RESIZE in plan.operations or self._over_bounds(img, plan):
            fitted = self._fit_within_bounds(img, plan)
            if fitted is not img:
                img = fitted
                steps.append(Operation.RESIZE.value)

        return self._search_and_build(
            img,
            plan,
            original_byte_size=len(data),
            original_width=original_width,
            source_dpi=_PDF_WRAP_DPI,
            steps=steps,
            warnings=["pdf_converted_to_image_text_layer_removed"],
        )

    def _prepare(self, img: Image.Image, plan: OptimizationPlan) -> tuple[Image.Image, list[str]]:
        steps: list[str] = []
        has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info

        if plan.to_greyscale:
            if has_alpha:
                img = self._flatten(img)
                steps.append(Operation.FLATTEN_ALPHA.value)
            if img.mode != "L":
                img = img.convert("L")
            steps.append(Operation.GREYSCALE.value)
        elif plan.target_format in ("jpeg", "pdf") and has_alpha:
            img = self._flatten(img)
            steps.append(Operation.FLATTEN_ALPHA.value)
        elif plan.target_format in ("jpeg", "pdf") and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        if plan.target_format != plan.source_format:
            steps.append(Operation.CONVERT.value)
        return img, steps

    @staticmethod
    def _flatten(img: Image.Image) -> Image.Image:
        """Composite transparency onto white — a document scan is paper, not glass."""
        rgba = img.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, (255, 255, 255))
        canvas.paste(rgba, mask=rgba.split()[-1])
        return canvas

    @staticmethod
    def _over_bounds(img: Image.Image, plan: OptimizationPlan) -> bool:
        return bool(
            (plan.max_width and img.width > plan.max_width)
            or (plan.max_height and img.height > plan.max_height)
        )

    def _fit_within_bounds(self, img: Image.Image, plan: OptimizationPlan) -> Image.Image:
        ratio = 1.0
        if plan.max_width and img.width > plan.max_width:
            ratio = min(ratio, plan.max_width / img.width)
        if plan.max_height and img.height > plan.max_height:
            ratio = min(ratio, plan.max_height / img.height)
        if ratio >= 1.0:
            return img
        return self._scaled(img, ratio)

    @staticmethod
    def _scaled(img: Image.Image, ratio: float) -> Image.Image:
        width = max(1, round(img.width * ratio))
        height = max(1, round(img.height * ratio))
        return img.resize((width, height), Image.Resampling.LANCZOS)

    def _search_and_build(
        self,
        img: Image.Image,
        plan: OptimizationPlan,
        *,
        original_byte_size: int,
        original_width: int,
        source_dpi: int | None,
        steps: list[str],
        warnings: list[str],
    ) -> OptimizedDocument:
        encoder, quality_sensitive = self._encoder_for(plan, source_dpi, original_width)
        best: tuple[bytes, int | None, Image.Image] | None = None
        fallback: tuple[bytes, int | None, Image.Image] | None = None

        for ratio in self._scale_ladder(img, plan):
            candidate = img if ratio == 1.0 else self._scaled(img, ratio)
            data, quality = self._best_encoding(candidate, plan, encoder, quality_sensitive)
            if fallback is None or len(data) < len(fallback[0]):
                fallback = (data, quality, candidate)
            if len(data) <= plan.max_bytes:
                best = (data, quality, candidate)
                break

        chosen = best or fallback
        assert chosen is not None  # the ladder always yields at least one candidate
        data, quality, final_img = chosen

        if quality is not None and Operation.RECOMPRESS.value not in steps:
            steps.append(Operation.RECOMPRESS.value)
        if final_img.width != img.width and Operation.RESIZE.value not in steps:
            steps.append(Operation.RESIZE.value)
        if Operation.TARGET_SIZE_SEARCH in plan.operations:
            steps.append(Operation.TARGET_SIZE_SEARCH.value)
        if best is None:
            warnings.append("size_target_not_reached_readability_floor_hit")
        if plan.min_bytes and len(data) < plan.min_bytes:
            warnings.append("output_below_portal_minimum_size")

        is_pdf = plan.target_format == "pdf"
        return OptimizedDocument(
            data=data,
            detected_format=plan.target_format,
            kind="pdf" if is_pdf else "image",
            byte_size=len(data),
            original_byte_size=original_byte_size,
            target_met=len(data) <= plan.max_bytes,
            width=final_img.width,
            height=final_img.height,
            pages=1,
            steps_applied=tuple(dict.fromkeys(steps)),
            quality_used=quality,
            scale_applied=round(final_img.width / original_width, 4) if original_width else 1.0,
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def _scale_ladder(self, img: Image.Image, plan: OptimizationPlan) -> list[float]:
        """1.0 first, then gentle steps down — never past min_scale or the portal's floors."""
        ladder = [1.0]
        ratio = 1.0
        while True:
            ratio = round(ratio * _SCALE_STEP, 4)
            if ratio < plan.min_scale:
                if plan.min_scale < ladder[-1]:
                    ladder.append(plan.min_scale)
                break
            ladder.append(ratio)

        allowed = []
        for candidate in ladder:
            width = round(img.width * candidate)
            height = round(img.height * candidate)
            if plan.min_width and width < plan.min_width:
                break
            if plan.min_height and height < plan.min_height:
                break
            allowed.append(candidate)
        return allowed or [1.0]

    def _best_encoding(
        self,
        img: Image.Image,
        plan: OptimizationPlan,
        encoder: Encoder,
        quality_sensitive: bool,
    ) -> tuple[bytes, int | None]:
        """Highest quality that fits, else the smallest the floor allows."""
        if not quality_sensitive:
            return encoder(img, plan.quality_start), None

        top = encoder(img, plan.quality_start)
        if len(top) <= plan.max_bytes:
            return top, plan.quality_start

        low, high = plan.quality_floor, plan.quality_start - 1
        best: tuple[bytes, int] | None = None
        floor_output: tuple[bytes, int] | None = None
        while low <= high:
            mid = (low + high) // 2
            out = encoder(img, mid)
            if mid == plan.quality_floor:
                floor_output = (out, mid)
            if len(out) <= plan.max_bytes:
                best = (out, mid)
                low = mid + 1
            else:
                high = mid - 1
        if best:
            return best
        if floor_output:
            return floor_output
        return encoder(img, plan.quality_floor), plan.quality_floor

    def _encoder_for(
        self, plan: OptimizationPlan, source_dpi: int | None, source_width: int
    ) -> tuple[Encoder, bool]:
        """Build the encoder for the target format.

        Physical DPI is carried over and rescaled: the same sheet of paper photographed at 300 dpi
        and then halved in width really is 150 dpi, so that is what the output declares.
        """

        def dpi_for(img: Image.Image) -> tuple[int, int] | None:
            if not source_dpi or not source_width:
                return None
            scaled = max(1, round(source_dpi * img.width / source_width))
            return (scaled, scaled)

        fmt = plan.target_format
        if fmt == "pdf":
            return (
                lambda img, quality: self._image_to_pdf(
                    _encode_image(img, "jpeg", quality, dpi_for(img)), img
                ),
                True,
            )
        return (lambda img, quality: _encode_image(img, fmt, quality, dpi_for(img))), fmt == "jpeg"

    @staticmethod
    def _image_to_pdf(image_bytes: bytes, img: Image.Image) -> bytes:
        width_pt = img.width / _PDF_WRAP_DPI * 72
        height_pt = img.height / _PDF_WRAP_DPI * 72
        with pymupdf.open() as doc:
            page = doc.new_page(width=width_pt, height=height_pt)
            page.insert_image(page.rect, stream=image_bytes)
            return doc.tobytes(garbage=4, deflate=True)

    # --- pdf path ---------------------------------------------------------

    def _run_pdf(self, data: bytes, plan: OptimizationPlan) -> OptimizedDocument:
        steps: list[str] = []
        warnings: list[str] = []

        with pymupdf.open(stream=data, filetype="pdf") as doc:
            cleaned = doc.tobytes(garbage=4, deflate=True, clean=True)

        # A structural pass can grow tiny PDFs; only keep it if it actually helped.
        if len(cleaned) < len(data):
            steps.append(Operation.PDF_OPTIMISE_STRUCTURE.value)
        else:
            cleaned = data

        best = cleaned
        used_dpi: int | None = None
        if len(best) > plan.max_bytes and Operation.PDF_DOWNSAMPLE_IMAGES in plan.operations:
            for dpi in self._raster_dpi_ladder(plan):
                candidate = self._rasterise_pdf(data, plan, dpi)
                if len(candidate) < len(best):
                    best, used_dpi = candidate, dpi
                if len(candidate) <= plan.max_bytes:
                    best, used_dpi = candidate, dpi
                    break
            if used_dpi is not None:
                steps.append(Operation.PDF_DOWNSAMPLE_IMAGES.value)
                warnings.append(f"pages_rasterised_at_{used_dpi}dpi_text_layer_removed")

        if Operation.TARGET_SIZE_SEARCH in plan.operations:
            steps.append(Operation.TARGET_SIZE_SEARCH.value)
        target_met = len(best) <= plan.max_bytes
        if not target_met:
            warnings.append("size_target_not_reached_readability_floor_hit")

        with pymupdf.open(stream=best, filetype="pdf") as out:
            pages = out.page_count
            first = out.load_page(0).rect

        return OptimizedDocument(
            data=best,
            detected_format="pdf",
            kind="pdf",
            byte_size=len(best),
            original_byte_size=len(data),
            target_met=target_met,
            width=int(first.width),
            height=int(first.height),
            pages=pages,
            steps_applied=tuple(dict.fromkeys(steps)),
            warnings=tuple(dict.fromkeys(warnings)),
        )

    @staticmethod
    def _raster_dpi_ladder(plan: OptimizationPlan) -> tuple[int, ...]:
        if plan.mode is OptimizationMode.AGGRESSIVE:
            return _PDF_RASTER_DPI_AGGRESSIVE
        return _PDF_RASTER_DPI_BALANCED

    def _rasterise_pdf(self, data: bytes, plan: OptimizationPlan, dpi: int) -> bytes:
        """Re-render every page as a JPEG at `dpi`. Loses the text layer; caller warns about it."""
        quality = max(plan.quality_floor, 70)
        with pymupdf.open(stream=data, filetype="pdf") as src, pymupdf.open() as out:
            for index in range(src.page_count):
                source_page = src.load_page(index)
                img = self._render(source_page, dpi)
                if plan.to_greyscale and img.mode != "L":
                    img = img.convert("L")
                jpeg = _encode_image(img, "jpeg", quality)
                page = out.new_page(
                    width=source_page.rect.width, height=source_page.rect.height
                )
                page.insert_image(page.rect, stream=jpeg)
            return out.tobytes(garbage=4, deflate=True)

    @staticmethod
    def _render(page: pymupdf.Page, dpi: int) -> Image.Image:
        pixmap = page.get_pixmap(dpi=dpi)
        mode = "RGBA" if pixmap.alpha else "RGB"
        if pixmap.n - int(pixmap.alpha) == 1:
            mode = "LA" if pixmap.alpha else "L"
        return Image.frombytes(mode, (pixmap.width, pixmap.height), pixmap.samples)


def _encode_image(
    img: Image.Image, fmt: str, quality: int, dpi: tuple[int, int] | None = None
) -> bytes:
    """Encode without metadata, apart from the physical DPI. `quality` is ignored by PNG."""
    buf = io.BytesIO()
    extra: dict = {"dpi": dpi} if dpi else {}
    if fmt == "jpeg":
        target = img if img.mode in ("RGB", "L") else img.convert("RGB")
        target.save(
            buf, format="JPEG", quality=quality, optimize=True, progressive=True, **extra
        )
    elif fmt == "png":
        img.save(buf, format="PNG", optimize=True, compress_level=9, **extra)
    else:  # pragma: no cover — guarded by the strategy provider
        raise ValueError(f"unsupported target format: {fmt}")
    return buf.getvalue()


def _dpi_of(img: Image.Image) -> int | None:
    dpi = img.info.get("dpi")
    if not dpi:
        return None
    try:
        value = round(float(dpi[0]))
    except (TypeError, ValueError, IndexError):
        return None
    return value if 1 <= value <= 4800 else None


def detected_format_of(data: bytes) -> str | None:
    """Convenience for tests and callers that want to re-verify engine output."""
    return sniff_format(data)
