"""RequirementResolver tests — the engine's config layer must stay portal-agnostic."""

import pytest

from app.uploadsaathi.requirements import RequirementResolver
from app.uploadsaathi.requirements.resolver import (
    ApplicantTypeNotFoundError,
    DocumentTypeNotFoundError,
    PortalNotFoundError,
)

resolver = RequirementResolver()


def test_aadhaar_portal_is_available():
    assert "aadhaar" in resolver.available_portals()


def test_portal_metadata_carries_prototype_notes():
    portal = resolver.portal("aadhaar")
    assert "not affiliated" in portal.authority_note.lower()
    assert "enrolment centre" in portal.journey_note.lower()
    assert any(a.is_primary_demo for a in portal.applicant_types)


def test_defaults_merge_with_document_overrides():
    poa = resolver.resolve("aadhaar", "address_proof")
    assert poa.max_bytes == 512_000
    assert poa.min_bytes == 1024  # inherited from portal defaults
    assert poa.min_width is None  # dimension floors are off in the current demo config
    assert poa.max_pages is None
    assert poa.accepts_format(".JPG")
    assert not poa.accepts_format("bmp")


def test_photograph_overrides_are_stricter():
    photo = resolver.resolve("aadhaar", "photograph")
    assert photo.min_width == 350  # overridden by the document type
    assert photo.max_pages == 1
    assert photo.colour_mode == "colour"
    assert "pdf" not in photo.accepted_formats


def test_documents_for_adult_demo_path():
    docs = resolver.documents_for("aadhaar", "adult")
    assert [d.id for d in docs] == ["identity_proof", "address_proof", "dob_proof"]
    assert all(d.requirement.max_bytes > 0 for d in docs)
    assert docs[1].examples  # address proof suggests real-world examples


def test_unknown_lookups_raise():
    with pytest.raises(PortalNotFoundError):
        resolver.portal("passport")
    with pytest.raises(DocumentTypeNotFoundError):
        resolver.resolve("aadhaar", "no_such_doc")
    with pytest.raises(ApplicantTypeNotFoundError):
        resolver.applicant_type("aadhaar", "alien")


def test_portal_id_traversal_is_rejected():
    with pytest.raises(PortalNotFoundError):
        resolver.portal("../../secrets")
