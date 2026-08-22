"""Local document storage.

Only the *optimised* document is ever written to disk. The original upload lives in memory for the
duration of the request and is then dropped — a prototype should not accumulate copies of people's
documents.

Files are addressed by an opaque random key, never by user-supplied names, so a crafted filename
cannot escape the storage directory.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from app.core.config import settings


class DocumentStorage:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or settings.STORAGE_DIR).resolve()

    def new_key(self, extension: str) -> str:
        suffix = (extension or "bin").lstrip(".").lower()
        return f"{secrets.token_hex(16)}.{suffix}"

    def path_for(self, key: str) -> Path:
        """Resolve a key inside the storage root, refusing anything that tries to climb out."""
        candidate = (self.root / key).resolve()
        if candidate.parent != self.root:
            raise ValueError("invalid storage key")
        return candidate

    def save(self, key: str, data: bytes) -> int:
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return len(data)

    def read(self, key: str) -> bytes | None:
        path = self.path_for(key)
        return path.read_bytes() if path.is_file() else None

    def delete(self, key: str) -> None:
        try:
            self.path_for(key).unlink(missing_ok=True)
        except ValueError:
            return  # an unparseable key cannot refer to anything we stored


storage = DocumentStorage()
