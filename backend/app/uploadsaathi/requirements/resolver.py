"""RequirementResolver — loads portal configuration and resolves per-document requirements.

Adding a new portal (Passport, PAN, UPSC, NTA, RTPS, EPFO...) means adding a JSON file to the
config directory. No engine or UI code changes.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .models import ApplicantType, DocumentTypeInfo, PortalInfo, Requirement

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "portals"


class PortalNotFoundError(LookupError):
    pass


class DocumentTypeNotFoundError(LookupError):
    pass


class ApplicantTypeNotFoundError(LookupError):
    pass


def _as_tuple(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(str(v).lower().lstrip(".") for v in value)


class RequirementResolver:
    def __init__(self, config_dir: Path | str | None = None) -> None:
        self.config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR

    # --- raw config -------------------------------------------------------

    def available_portals(self) -> list[str]:
        return sorted(p.stem for p in self.config_dir.glob("*.json"))

    def _load(self, portal_id: str) -> dict[str, Any]:
        # Guard against path traversal via a caller-supplied portal id.
        if not portal_id.replace("_", "").replace("-", "").isalnum():
            raise PortalNotFoundError(portal_id)
        path = self.config_dir / f"{portal_id}.json"
        if not path.is_file():
            raise PortalNotFoundError(portal_id)
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    # --- resolution -------------------------------------------------------

    def portal(self, portal_id: str) -> PortalInfo:
        cfg = self._load(portal_id)
        return PortalInfo(
            portal_id=cfg["portal_id"],
            portal_name=cfg["portal_name"],
            authority_note=cfg.get("authority_note", ""),
            journey_note=cfg.get("journey_note", ""),
            config_version=cfg.get("config_version", "0"),
            applicant_types=tuple(
                ApplicantType(
                    id=a["id"],
                    label=a["label"],
                    description=a.get("description", ""),
                    required_documents=tuple(a.get("required_documents", ())),
                    is_primary_demo=bool(a.get("is_primary_demo", False)),
                )
                for a in cfg.get("applicant_types", [])
            ),
        )

    def applicant_type(self, portal_id: str, applicant_type_id: str) -> ApplicantType:
        for a in self.portal(portal_id).applicant_types:
            if a.id == applicant_type_id:
                return a
        raise ApplicantTypeNotFoundError(applicant_type_id)

    def resolve(self, portal_id: str, document_type: str) -> Requirement:
        """Merge portal defaults with the document type's overrides."""
        cfg = self._load(portal_id)
        doc_types = cfg.get("document_types", {})
        if document_type not in doc_types:
            raise DocumentTypeNotFoundError(document_type)

        doc = doc_types[document_type]
        merged: dict[str, Any] = {**cfg.get("defaults", {}), **doc.get("requirements", {})}

        return Requirement(
            portal_id=cfg["portal_id"],
            document_type=document_type,
            label=doc.get("label", document_type),
            accepted_formats=_as_tuple(merged.get("accepted_formats")),
            max_bytes=int(merged["max_bytes"]),
            min_bytes=int(merged.get("min_bytes", 0)),
            min_width=merged.get("min_width"),
            min_height=merged.get("min_height"),
            max_width=merged.get("max_width"),
            max_height=merged.get("max_height"),
            min_dpi=merged.get("min_dpi"),
            max_pages=merged.get("max_pages"),
            colour_mode=merged.get("colour_mode", "any"),
            help=doc.get("help", ""),
            examples=tuple(doc.get("examples", ())),
        )

    def document_type(self, portal_id: str, document_type: str) -> DocumentTypeInfo:
        cfg = self._load(portal_id)
        doc = cfg.get("document_types", {}).get(document_type)
        if doc is None:
            raise DocumentTypeNotFoundError(document_type)
        return DocumentTypeInfo(
            id=document_type,
            label=doc.get("label", document_type),
            short_label=doc.get("short_label", ""),
            help=doc.get("help", ""),
            examples=tuple(doc.get("examples", ())),
            requirement=self.resolve(portal_id, document_type),
        )

    def documents_for(self, portal_id: str, applicant_type_id: str) -> list[DocumentTypeInfo]:
        applicant = self.applicant_type(portal_id, applicant_type_id)
        return [self.document_type(portal_id, d) for d in applicant.required_documents]


@lru_cache
def get_resolver() -> RequirementResolver:
    return RequirementResolver()
