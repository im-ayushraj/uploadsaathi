"""Portal-agnostic requirement model.

A Requirement is the complete, resolved set of constraints a single document must satisfy
for one portal. Nothing here knows about Aadhaar — portals are JSON configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ColourMode = Literal["any", "colour", "greyscale"]


@dataclass(frozen=True, slots=True)
class Requirement:
    portal_id: str
    document_type: str
    label: str
    accepted_formats: tuple[str, ...]
    max_bytes: int
    min_bytes: int = 0
    min_width: int | None = None
    min_height: int | None = None
    max_width: int | None = None
    max_height: int | None = None
    min_dpi: int | None = None
    max_pages: int | None = None
    colour_mode: ColourMode = "any"
    help: str = ""
    examples: tuple[str, ...] = field(default_factory=tuple)

    def accepts_format(self, fmt: str) -> bool:
        return fmt.lower().lstrip(".") in self.accepted_formats


@dataclass(frozen=True, slots=True)
class DocumentTypeInfo:
    """Presentation metadata for a document slot, plus its resolved Requirement."""

    id: str
    label: str
    short_label: str
    help: str
    examples: tuple[str, ...]
    requirement: Requirement


@dataclass(frozen=True, slots=True)
class ApplicantType:
    id: str
    label: str
    description: str
    required_documents: tuple[str, ...]
    is_primary_demo: bool = False


@dataclass(frozen=True, slots=True)
class PortalInfo:
    portal_id: str
    portal_name: str
    authority_note: str
    journey_note: str
    config_version: str
    applicant_types: tuple[ApplicantType, ...]
