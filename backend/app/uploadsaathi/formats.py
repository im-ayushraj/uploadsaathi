"""Format detection by content, not by filename.

A citizen renaming `bill.pdf` to `bill.jpg` must not confuse the pipeline, and a portal
requirement expressed in extensions ("jpg", "pdf") has to be matched against what the bytes
actually are.
"""

from __future__ import annotations

from typing import Final

# canonical format -> the extensions a portal config may use for it
FORMAT_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "jpeg": ("jpg", "jpeg", "jpe"),
    "png": ("png",),
    "pdf": ("pdf",),
}

MIME_TYPES: Final[dict[str, str]] = {
    "jpeg": "image/jpeg",
    "png": "image/png",
    "pdf": "application/pdf",
}

IMAGE_FORMATS: Final[frozenset[str]] = frozenset({"jpeg", "png"})
SUPPORTED_FORMATS: Final[frozenset[str]] = frozenset(FORMAT_ALIASES)


def canonical_format(value: str | None) -> str | None:
    """'JPG' / '.jpeg' / 'image/jpeg' -> 'jpeg'. Unknown values return None."""
    if not value:
        return None
    v = value.strip().lower().lstrip(".")
    if v in SUPPORTED_FORMATS:
        return v
    for canonical, aliases in FORMAT_ALIASES.items():
        if v in aliases or v == MIME_TYPES[canonical]:
            return canonical
    return None


def sniff_format(data: bytes) -> str | None:
    """Identify a format from its magic bytes. Returns None for anything unsupported."""
    if len(data) < 4:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    # Some writers prepend junk before %PDF-; the spec tolerates it in the first 1 KB.
    head = data[:1024]
    if head.startswith(b"%PDF-") or b"%PDF-" in head:
        return "pdf"
    return None


def mime_for(fmt: str | None) -> str | None:
    return MIME_TYPES.get(fmt) if fmt else None


def extension_for(fmt: str) -> str:
    """Preferred file extension for a canonical format."""
    return "jpg" if fmt == "jpeg" else fmt


def is_image(fmt: str | None) -> bool:
    return fmt in IMAGE_FORMATS
