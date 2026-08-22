"""OptimizationEngine tests — real bytes in, real bytes out, on synthetic documents."""

import io

import pymupdf
from PIL import Image

from app.uploadsaathi.analyzer import DocumentAnalyzer
from app.uploadsaathi.engine import OptimizationEngine
from app.uploadsaathi.formats import sniff_format
from app.uploadsaathi.strategy import OptimizationMode, OptimizationStrategyProvider

from .synthetic import corrupt, make_image, make_oversized_jpeg, make_pdf
from .test_strategy import requirement

analyzer = DocumentAnalyzer()
provider = OptimizationStrategyProvider()
engine = OptimizationEngine()


def run(data: bytes, filename: str = "doc", mode=OptimizationMode.BALANCED, **req):
    analysis = analyzer.analyze(data, filename)
    plan = provider.plan(analysis, requirement(**req), mode)
    return engine.execute(data, plan), plan


def test_hero_scenario_oversized_jpeg_becomes_portal_ready():
    data = make_oversized_jpeg()
    assert len(data) > 5_000_000
    result, _ = run(data, "electricity_bill.jpg", max_bytes=2_097_152, max_width=5000, max_height=5000)

    assert result.succeeded
    assert result.target_met
    assert result.byte_size <= 2_097_152
    assert sniff_format(result.data) == "jpeg"
    assert result.reduction_percent > 50
    # Readability guard: the document was not shrunk into unreadability.
    assert result.scale_applied >= 0.45
    assert result.quality_used is not None and result.quality_used >= 55
    # Output is still a decodable image of sane size.
    with Image.open(io.BytesIO(result.data)) as img:
        assert img.width == result.width
        assert img.width >= 1000


def test_compliant_file_is_returned_untouched():
    data = make_image(700, 500, fmt="JPEG", quality=60)
    result, plan = run(data, "bill.jpg", max_bytes=5_000_000)
    assert plan.needs_work is False
    assert result.data == data
    assert result.changed is False
    assert result.target_met
    assert result.reduction_percent == 0.0


def test_resize_respects_max_dimensions():
    data = make_image(2400, 1800, fmt="JPEG", quality=90)
    result, _ = run(data, "bill.jpg", max_bytes=5_000_000, max_width=1200, max_height=1200)
    assert result.width <= 1200
    assert result.height <= 1200
    assert "resize" in result.steps_applied


def test_png_with_alpha_converted_to_jpeg_on_white():
    data = make_image(900, 700, fmt="PNG", mode="RGBA")
    result, _ = run(data, "photo.png", accepted_formats=("jpg",), max_bytes=5_000_000)
    assert result.detected_format == "jpeg"
    assert sniff_format(result.data) == "jpeg"
    assert "flatten_alpha" in result.steps_applied
    with Image.open(io.BytesIO(result.data)) as img:
        assert img.mode == "RGB"


def test_greyscale_conversion_is_applied():
    data = make_image(800, 600, fmt="JPEG", quality=90)
    result, _ = run(data, "bill.jpg", max_bytes=5_000_000, colour_mode="greyscale")
    assert "greyscale" in result.steps_applied
    with Image.open(io.BytesIO(result.data)) as img:
        assert img.mode == "L"


def test_single_page_pdf_converted_to_jpeg():
    data = make_pdf(pages=1, image_bytes=make_image(1000, 700, fmt="JPEG"))
    result, _ = run(data, "bill.pdf", accepted_formats=("jpg",), max_bytes=500_000)
    assert result.succeeded
    assert sniff_format(result.data) == "jpeg"
    assert result.target_met
    assert "pdf_converted_to_image_text_layer_removed" in result.warnings


def test_oversized_pdf_is_shrunk_and_stays_a_pdf():
    data = make_pdf(pages=3, image_bytes=make_image(1800, 1400, fmt="JPEG", quality=95))
    result, _ = run(data, "passbook.pdf", accepted_formats=("pdf",), max_bytes=250_000)
    assert result.succeeded
    assert sniff_format(result.data) == "pdf"
    assert result.byte_size < len(data)
    assert result.pages == 3  # no page is ever silently dropped
    with pymupdf.open(stream=result.data, filetype="pdf") as doc:
        assert doc.page_count == 3


def test_impossible_target_is_reported_honestly():
    data = make_image(2000, 1500, fmt="JPEG", quality=95)
    result, _ = run(data, "bill.jpg", max_bytes=1_500, min_width=1500, min_height=1000)
    assert result.succeeded  # work was done...
    assert result.target_met is False  # ...but the portal limit was unreachable
    assert "size_target_not_reached_readability_floor_hit" in result.warnings
    assert result.width >= 1500  # the readability floor held
    assert sniff_format(result.data) == "jpeg"


def test_infeasible_plan_is_passed_through_as_failure():
    data = corrupt(make_image(800, 600, fmt="JPEG"))
    result, plan = run(data, "x.jpg")
    assert plan.feasible is False
    assert result.succeeded is False
    assert result.failure_reason == "corrupted_or_unreadable"
    assert result.data == data


def test_aggressive_mode_reaches_smaller_sizes():
    data = make_image(2200, 1600, fmt="JPEG", quality=95)
    balanced, _ = run(data, "bill.jpg", max_bytes=40_000)
    aggressive, _ = run(data, "bill.jpg", mode=OptimizationMode.AGGRESSIVE, max_bytes=40_000)
    assert aggressive.byte_size <= balanced.byte_size
    assert aggressive.scale_applied <= balanced.scale_applied


def test_metadata_is_stripped_when_re_encoding():
    data = make_image(2000, 1500, fmt="JPEG", quality=95, dpi=(300, 300))
    result, _ = run(data, "bill.jpg", max_bytes=120_000)
    assert "strip_metadata" in result.steps_applied
    with Image.open(io.BytesIO(result.data)) as img:
        assert not img.getexif()
