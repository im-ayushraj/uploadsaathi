"""Synthetic document builders for tests (and later, demo files).

No real documents are ever used. Images are deterministic (fixed seed) but noisy enough that
JPEG cannot compress them away, so size-reduction tests exercise real behaviour.
"""

from __future__ import annotations

import io
import random

import pymupdf
from PIL import Image, ImageDraw


def make_image(
    width: int = 1600,
    height: int = 1200,
    fmt: str = "JPEG",
    quality: int = 95,
    mode: str = "RGB",
    noise: bool = True,
    seed: int = 7,
    dpi: tuple[int, int] | None = None,
) -> bytes:
    """A document-like image: noisy background, readable dark text on light paper."""
    rng = random.Random(seed)
    img = Image.new("RGB", (width, height), (246, 244, 238))

    if noise:
        # Grain from a downscaled random tile: fast (C-level randbytes + resize) and, once blended,
        # incompressible enough that JPEG size tests exercise real behaviour.
        tile_w, tile_h = max(1, width // 3), max(1, height // 3)
        raw = rng.randbytes(tile_w * tile_h * 3)
        grain = Image.frombytes("RGB", (tile_w, tile_h), raw).resize(
            (width, height), Image.Resampling.BILINEAR
        )
        img = Image.blend(img, grain, 0.28)

    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, width - 20, height - 20], outline=(60, 60, 60), width=3)
    line_height = max(18, height // 26)
    for i in range(10):
        y = 60 + i * line_height * 2
        if y > height - 80:
            break
        draw.text((50, y), f"DEMO BILL LINE {i + 1} — 1234567890 ABCDEFGH", fill=(20, 20, 20))
        draw.line([50, y + line_height, width - 60, y + line_height], fill=(90, 90, 90), width=2)

    if mode != "RGB":
        img = img.convert(mode)

    buf = io.BytesIO()
    save_kwargs: dict = {}
    if fmt.upper() == "JPEG":
        save_kwargs.update(quality=quality, subsampling=0)
    if dpi:
        save_kwargs["dpi"] = dpi
    img.save(buf, format=fmt.upper(), **save_kwargs)
    return buf.getvalue()


def make_pdf(pages: int = 1, image_bytes: bytes | None = None, with_text: bool = True) -> bytes:
    """A PDF with optional text layer and one embedded raster image per page."""
    doc = pymupdf.open()
    for index in range(pages):
        page = doc.new_page(width=595, height=842)  # A4 in points
        if with_text:
            page.insert_text((60, 80), f"Demo document — page {index + 1}", fontsize=14)
        if image_bytes:
            page.insert_image(pymupdf.Rect(50, 120, 545, 620), stream=image_bytes)
    data = doc.tobytes()
    doc.close()
    return data


def make_oversized_jpeg(target_bytes: int = 7_400_000) -> bytes:
    """Grow dimensions until the encoded JPEG is at least `target_bytes` (a real 7.4 MB photo)."""
    width, height = 2400, 1800
    for _ in range(8):
        data = make_image(width, height, fmt="JPEG", quality=97)
        if len(data) >= target_bytes:
            return data
        width = int(width * 1.35)
        height = int(height * 1.35)
    return data


def corrupt(data: bytes) -> bytes:
    """Keep the magic bytes, destroy the payload — the shape of a truncated upload."""
    return data[:64] + b"\x00" * 512
