"""OptimizationStrategyProvider tests — decisions only, no bytes are modified."""

from app.uploadsaathi.analyzer import DocumentAnalyzer
from app.uploadsaathi.requirements.models import Requirement
from app.uploadsaathi.strategy import (
    QUALITY_FLOOR_AGGRESSIVE,
    QUALITY_FLOOR_BALANCED,
    Operation,
    OptimizationMode,
    OptimizationStrategyProvider,
)

from .synthetic import corrupt, make_image, make_pdf

analyzer = DocumentAnalyzer()
provider = OptimizationStrategyProvider()


def requirement(**overrides) -> Requirement:
    base = dict(
        portal_id="demo",
        document_type="address_proof",
        label="Address proof",
        accepted_formats=("jpg", "jpeg", "png", "pdf"),
        max_bytes=200_000,
        min_bytes=0,
        min_width=None,
        min_height=None,
        max_width=None,
        max_height=None,
        min_dpi=None,
        max_pages=None,
        colour_mode="any",
        help="",
        examples=(),
    )
    base.update(overrides)
    return Requirement(**base)


def test_already_compliant_file_needs_no_work():
    data = make_image(700, 500, fmt="JPEG", quality=60)
    plan = provider.plan(analyzer.analyze(data, "bill.jpg"), requirement(max_bytes=5_000_000))
    assert plan.feasible
    assert plan.needs_work is False
    assert plan.operations == ()


def test_oversized_jpeg_plans_recompress_and_size_search():
    data = make_image(2000, 1500, fmt="JPEG", quality=95)
    plan = provider.plan(analyzer.analyze(data, "bill.jpg"), requirement(max_bytes=150_000))
    assert plan.target_format == "jpeg"
    assert Operation.RECOMPRESS in plan.operations
    assert Operation.TARGET_SIZE_SEARCH in plan.operations
    assert Operation.STRIP_METADATA in plan.operations
    assert plan.quality_floor == QUALITY_FLOOR_BALANCED


def test_dimension_bounds_trigger_resize():
    data = make_image(1600, 1200, fmt="JPEG", quality=40)
    plan = provider.plan(
        analyzer.analyze(data),
        requirement(max_bytes=5_000_000, max_width=1200, max_height=1600),
    )
    assert Operation.RESIZE in plan.operations
    assert Operation.TARGET_SIZE_SEARCH not in plan.operations


def test_png_converted_to_jpeg_and_alpha_flattened():
    data = make_image(900, 700, fmt="PNG", mode="RGBA")
    plan = provider.plan(
        analyzer.analyze(data, "photo.png"), requirement(accepted_formats=("jpg",))
    )
    assert plan.source_format == "png"
    assert plan.target_format == "jpeg"
    assert Operation.CONVERT in plan.operations
    assert Operation.FLATTEN_ALPHA in plan.operations
    assert "transparency_flattened_onto_white" in plan.notes


def test_oversized_png_is_re_encoded_as_jpeg_even_though_png_is_accepted():
    # PNG is lossless, so shrinking it means throwing away pixels. When JPEG is also accepted,
    # re-encoding keeps the document readable instead of downscaling it into mush.
    data = make_image(1600, 1200, fmt="PNG")
    plan = provider.plan(analyzer.analyze(data, "screenshot.png"), requirement(max_bytes=200_000))
    assert plan.source_format == "png"
    assert plan.target_format == "jpeg"
    assert Operation.CONVERT in plan.operations
    assert "png_re_encoded_as_jpeg_to_meet_size_limit" in plan.notes


def test_compliant_png_is_left_as_png():
    data = make_image(400, 300, fmt="PNG")
    plan = provider.plan(analyzer.analyze(data, "screenshot.png"), requirement(max_bytes=5_000_000))
    assert plan.target_format == "png"
    assert plan.needs_work is False


def test_greyscale_requirement_adds_greyscale_step():
    plan = provider.plan(
        analyzer.analyze(make_image(800, 600, fmt="JPEG")),
        requirement(max_bytes=5_000_000, colour_mode="greyscale"),
    )
    assert plan.to_greyscale is True
    assert Operation.GREYSCALE in plan.operations


def test_colour_requirement_notes_greyscale_source():
    plan = provider.plan(
        analyzer.analyze(make_image(800, 600, fmt="PNG", mode="L")),
        requirement(max_bytes=5_000_000, colour_mode="colour", accepted_formats=("png",)),
    )
    assert plan.to_greyscale is False
    assert "colour_required_but_source_is_not_colour" in plan.notes


def test_multipage_pdf_cannot_become_an_image():
    data = make_pdf(pages=3, image_bytes=make_image(600, 400))
    plan = provider.plan(analyzer.analyze(data, "doc.pdf"), requirement(accepted_formats=("jpg",)))
    assert plan.feasible is False
    assert plan.infeasible_reason == "multipage_pdf_cannot_convert_to_image"
    assert plan.operations == ()


def test_single_page_pdf_can_become_a_jpeg():
    data = make_pdf(pages=1, image_bytes=make_image(600, 400))
    plan = provider.plan(analyzer.analyze(data, "doc.pdf"), requirement(accepted_formats=("jpg",)))
    assert plan.feasible
    assert plan.target_format == "jpeg"
    assert Operation.CONVERT in plan.operations


def test_pdf_over_limit_plans_structure_then_downsample():
    data = make_pdf(pages=2, image_bytes=make_image(1600, 1200, fmt="JPEG", quality=95))
    plan = provider.plan(analyzer.analyze(data, "doc.pdf"), requirement(max_bytes=120_000))
    assert plan.target_format == "pdf"
    assert plan.operations[0] == Operation.PDF_OPTIMISE_STRUCTURE
    assert Operation.PDF_DOWNSAMPLE_IMAGES in plan.operations


def test_unreadable_document_is_infeasible():
    plan = provider.plan(analyzer.analyze(corrupt(make_image(800, 600)), "x.jpg"), requirement())
    assert plan.feasible is False
    assert plan.infeasible_reason == "corrupted_or_unreadable"


def test_unsupported_format_with_no_conversion_is_infeasible():
    plan = provider.plan(analyzer.analyze(b"GIF89a" + b"\x00" * 64, "x.gif"), requirement())
    assert plan.feasible is False
    assert plan.infeasible_reason == "unsupported_format"


def test_aggressive_mode_lowers_the_guards():
    data = make_image(2000, 1500, fmt="JPEG", quality=95)
    analysis = analyzer.analyze(data)
    balanced = provider.plan(analysis, requirement(max_bytes=100_000))
    aggressive = provider.plan(analysis, requirement(max_bytes=100_000), OptimizationMode.AGGRESSIVE)
    assert aggressive.quality_floor == QUALITY_FLOOR_AGGRESSIVE < balanced.quality_floor
    assert aggressive.min_scale < balanced.min_scale


def test_notes_flag_undersized_and_too_many_pages():
    small = provider.plan(
        analyzer.analyze(make_image(400, 300, fmt="JPEG", quality=30)),
        requirement(max_bytes=5_000_000, min_bytes=100_000, min_width=800, min_height=600),
    )
    assert "below_portal_minimum_width" in small.notes
    assert "below_portal_minimum_height" in small.notes
    assert "file_smaller_than_portal_minimum" in small.notes

    long_pdf = provider.plan(
        analyzer.analyze(make_pdf(pages=5), "doc.pdf"),
        requirement(max_bytes=5_000_000, max_pages=4),
    )
    assert "too_many_pages_for_portal" in long_pdf.notes
