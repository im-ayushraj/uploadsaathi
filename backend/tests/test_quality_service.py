"""QualityValidator + UploadService tests.

The service tests run against the real Aadhaar configuration file, so they also prove the engine
stays portal-agnostic: nothing below UploadService is told which portal it is serving.
"""

import pytest

from app.uploadsaathi.analyzer import DocumentAnalyzer
from app.uploadsaathi.engine import OptimizationEngine
from app.uploadsaathi.quality import QualityValidator
from app.uploadsaathi.requirements.resolver import DocumentTypeNotFoundError, PortalNotFoundError
from app.uploadsaathi.service import UploadService
from app.uploadsaathi.strategy import OptimizationMode, OptimizationStrategyProvider

from .synthetic import corrupt, make_image, make_oversized_jpeg, make_pdf
from .test_strategy import requirement

analyzer = DocumentAnalyzer()
provider = OptimizationStrategyProvider()
engine = OptimizationEngine()
validator = QualityValidator()
service = UploadService()


def validate(data: bytes, filename: str = "doc", mode=OptimizationMode.BALANCED, **req):
    req_obj = requirement(**req)
    original = analyzer.analyze(data, filename)
    plan = provider.plan(original, req_obj, mode)
    outcome = engine.execute(data, plan)
    optimized = analyzer.analyze(outcome.data, filename)
    return validator.validate(original, optimized, req_obj, outcome=outcome), outcome


# --- validator ------------------------------------------------------------


def test_compliant_document_validates_as_unchanged():
    result, _ = validate(make_image(900, 700, fmt="JPEG", quality=60), "bill.jpg", max_bytes=5_000_000)
    assert result.is_valid
    assert result.quality_status == "unchanged"
    assert result.readable
    assert result.issues == ()


def test_optimised_document_validates_as_passed():
    result, outcome = validate(
        make_image(1600, 1200, fmt="JPEG", quality=95), "bill.jpg", max_bytes=400_000
    )
    assert result.is_valid
    assert result.quality_status in ("passed", "degraded")
    assert result.size_valid and result.format_valid
    assert outcome.byte_size <= 400_000


def test_unreachable_target_fails_validation_with_reasons():
    result, outcome = validate(
        make_image(2000, 1500, fmt="JPEG", quality=95),
        "bill.jpg",
        max_bytes=2_000,
        min_width=1500,
        min_height=1000,
    )
    assert result.is_valid is False
    assert result.quality_status == "failed"
    assert result.size_valid is False
    assert "file_too_large" in result.issues
    # The document itself is still readable — only the portal's limit was impossible.
    assert result.readable
    assert outcome.target_met is False


def test_corrupted_upload_fails_with_engine_reason():
    result, _ = validate(corrupt(make_image(800, 600, fmt="JPEG")), "x.jpg")
    assert result.is_valid is False
    assert result.quality_status == "failed"
    assert result.issues == ("corrupted_or_unreadable",)


def test_too_small_file_is_reported():
    result, _ = validate(
        make_image(800, 600, fmt="JPEG", quality=30),
        "bill.jpg",
        max_bytes=5_000_000,
        min_bytes=4_000_000,
    )
    assert result.size_valid is False
    assert "file_too_small" in result.issues


def test_colour_requirement_violation_is_reported():
    result, _ = validate(
        make_image(800, 600, fmt="PNG", mode="L"),
        "photo.png",
        accepted_formats=("png",),
        max_bytes=5_000_000,
        colour_mode="colour",
    )
    assert result.colour_valid is False
    assert "colour_document_required" in result.issues


def test_page_limit_violation_is_reported():
    result, _ = validate(
        make_pdf(pages=6), "doc.pdf", accepted_formats=("pdf",), max_bytes=5_000_000, max_pages=4
    )
    assert result.pages_valid is False
    assert "too_many_pages" in result.issues


def test_lost_text_layer_is_reported_as_degraded():
    data = make_pdf(pages=2, image_bytes=make_image(1800, 1400, fmt="JPEG", quality=95))
    result, _ = validate(data, "doc.pdf", accepted_formats=("pdf",), max_bytes=200_000)
    assert result.is_valid
    assert result.quality_status == "degraded"
    assert "searchable_text_layer_lost" in result.warnings


def test_dpi_is_advisory_not_a_failure():
    result, _ = validate(
        make_image(1200, 900, fmt="JPEG", quality=95, dpi=(72, 72)),
        "bill.jpg",
        max_bytes=5_000_000,
        min_dpi=150,
    )
    assert result.is_valid
    assert any(w.startswith("dpi_below_recommended") for w in result.warnings)


# --- service --------------------------------------------------------------


def test_service_hero_journey_on_real_aadhaar_config():
    data = make_oversized_jpeg()
    result = service.process(data, "electricity bill.JPG", "aadhaar", "address_proof")

    assert result.accepted
    assert result.readable
    assert result.original_size == len(data)
    assert result.optimized_size <= 512_000  # aadhaar.json default max_bytes
    assert result.format == "jpeg"
    assert result.to_dict()["format"] == "JPEG"  # contract uses the display form
    assert result.mime_type == "image/jpeg"
    assert result.reduction_percent > 50
    assert result.quality_status in ("passed", "degraded")
    assert result.size_valid and result.format_valid
    assert "recompress" in result.steps
    # The uploaded filename is not trusted; output is named after the document slot.
    assert result.filename == "address_proof.jpg"


def test_service_result_dict_matches_documented_contract():
    payload = service.process(
        make_image(1400, 1000, fmt="JPEG", quality=95), "id.jpg", "aadhaar", "identity_proof"
    ).to_dict()

    for key in (
        "original_size",
        "optimized_size",
        "format",
        "reduction_percent",
        "size_valid",
        "format_valid",
        "quality_status",
        "warnings",
        "steps",
    ):
        assert key in payload
    assert "data" not in payload  # document bytes never cross the JSON boundary
    assert isinstance(payload["steps"], list)


def test_service_photograph_slot_enforces_its_tighter_rules():
    # aadhaar.json photograph: min 350x450, colour, no PDF, single page.
    result = service.process(
        make_image(2000, 2600, fmt="JPEG", quality=95), "me.jpg", "aadhaar", "photograph"
    )
    assert result.accepted
    assert result.optimized_size <= 512_000
    assert result.width is not None and result.width >= 350
    assert result.height is not None and result.height >= 450


def test_service_rejects_multipage_pdf_for_photograph_slot():
    data = make_pdf(pages=3, image_bytes=make_image(600, 800))
    result = service.process(data, "photos.pdf", "aadhaar", "photograph")
    assert result.accepted is False
    assert result.quality_status == "failed"
    assert "multipage_pdf_cannot_convert_to_image" in result.issues
    assert result.optimized_size == len(data)  # untouched


def test_service_unknown_portal_and_document_type_raise():
    data = make_image(400, 300)
    with pytest.raises(PortalNotFoundError):
        service.process(data, "x.jpg", "passport", "identity_proof")
    with pytest.raises(DocumentTypeNotFoundError):
        service.process(data, "x.jpg", "aadhaar", "caste_certificate")


def test_service_preview_decides_without_processing():
    data = make_oversized_jpeg()
    analysis, req, plan = service.preview(data, "bill.jpg", "aadhaar", "address_proof")
    assert analysis.byte_size == len(data)
    assert req.max_bytes == 512_000
    assert plan.needs_work
    assert plan.feasible
