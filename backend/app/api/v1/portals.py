"""Portal configuration endpoints — requirements are served from config, never hardcoded in the UI."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.uploadsaathi.requirements.resolver import (
    ApplicantTypeNotFoundError,
    PortalNotFoundError,
    get_resolver,
)

router = APIRouter(prefix="/portals", tags=["portals"])


class RequirementOut(BaseModel):
    accepted_formats: list[str]
    max_bytes: int
    min_bytes: int
    min_width: int | None
    min_height: int | None
    max_width: int | None
    max_height: int | None
    min_dpi: int | None
    max_pages: int | None
    colour_mode: str


class DocumentTypeOut(BaseModel):
    id: str
    label: str
    short_label: str
    help: str
    examples: list[str]
    requirement: RequirementOut


class ApplicantTypeOut(BaseModel):
    id: str
    label: str
    description: str
    required_documents: list[str]
    is_primary_demo: bool


class PortalOut(BaseModel):
    portal_id: str
    portal_name: str
    authority_note: str
    journey_note: str
    config_version: str
    applicant_types: list[ApplicantTypeOut]


def _requirement_out(req) -> RequirementOut:
    return RequirementOut(
        accepted_formats=list(req.accepted_formats),
        max_bytes=req.max_bytes,
        min_bytes=req.min_bytes,
        min_width=req.min_width,
        min_height=req.min_height,
        max_width=req.max_width,
        max_height=req.max_height,
        min_dpi=req.min_dpi,
        max_pages=req.max_pages,
        colour_mode=req.colour_mode,
    )


@router.get("", response_model=list[str])
def list_portals() -> list[str]:
    return get_resolver().available_portals()


@router.get("/{portal_id}", response_model=PortalOut)
def get_portal(portal_id: str) -> PortalOut:
    try:
        portal = get_resolver().portal(portal_id)
    except PortalNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown portal")
    return PortalOut(
        portal_id=portal.portal_id,
        portal_name=portal.portal_name,
        authority_note=portal.authority_note,
        journey_note=portal.journey_note,
        config_version=portal.config_version,
        applicant_types=[
            ApplicantTypeOut(
                id=a.id,
                label=a.label,
                description=a.description,
                required_documents=list(a.required_documents),
                is_primary_demo=a.is_primary_demo,
            )
            for a in portal.applicant_types
        ],
    )


@router.get("/{portal_id}/documents", response_model=list[DocumentTypeOut])
def get_documents(portal_id: str, applicant_type: str) -> list[DocumentTypeOut]:
    try:
        docs = get_resolver().documents_for(portal_id, applicant_type)
    except PortalNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown portal")
    except ApplicantTypeNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown applicant type")

    return [
        DocumentTypeOut(
            id=d.id,
            label=d.label,
            short_label=d.short_label,
            help=d.help,
            examples=list(d.examples),
            requirement=_requirement_out(d.requirement),
        )
        for d in docs
    ]
