"""DocumentAnalyzer tests — measurement only, on synthetic documents."""

from app.uploadsaathi.analyzer import DocumentAnalyzer
from app.uploadsaathi.formats import canonical_format, sniff_format

from .synthetic import corrupt, make_image, make_pdf

analyzer = DocumentAnalyzer()


def test_canonical_format_aliases():
    assert canonical_format("JPG") == "jpeg"
    assert canonical_format(".jpeg") == "jpeg"
    assert canonical_format("image/jpeg") == "jpeg"
    assert canonical_format("bmp") is None
    assert canonical_format(None) is None


def test_sniff_ignores_filename():
    jpeg = make_image(400, 300, fmt="JPEG")
    assert sniff_format(jpeg) == "jpeg"
    # A PDF renamed to .jpg is still detected as a PDF.
    a = analyzer.analyze(make_pdf(), filename="bill.jpg")
    assert a.detected_format == "pdf"
    assert a.extension_mismatch is True


def test_jpeg_analysis():
    data = make_image(1600, 1200, fmt="JPEG", dpi=(200, 200))
    a = analyzer.analyze(data, filename="electricity_bill.jpg")
    assert a.detected_format == "jpeg"
    assert a.kind == "image"
    assert a.is_usable
    assert (a.width, a.height) == (1600, 1200)
    assert a.pages == 1
    assert a.dpi == 200
    assert a.colour_mode == "colour"
    assert a.has_alpha is False
    assert a.megapixels == 1.92
    assert a.byte_size == len(data)
    assert a.extension_mismatch is False


def test_png_with_alpha_and_greyscale_modes():
    rgba = analyzer.analyze(make_image(300, 200, fmt="PNG", mode="RGBA"))
    assert rgba.detected_format == "png"
    assert rgba.has_alpha is True

    grey = analyzer.analyze(make_image(300, 200, fmt="PNG", mode="L"))
    assert grey.colour_mode == "greyscale"

    bw = analyzer.analyze(make_image(300, 200, fmt="PNG", mode="1"))
    assert bw.colour_mode == "bw"


def test_pdf_analysis_multipage_with_image():
    photo = make_image(800, 600, fmt="JPEG")
    a = analyzer.analyze(make_pdf(pages=3, image_bytes=photo), filename="passbook.pdf")
    assert a.detected_format == "pdf"
    assert a.kind == "pdf"
    assert a.is_usable
    assert a.pages == 3
    assert a.pdf_has_text_layer is True
    assert a.pdf_image_count >= 3
    assert (a.width, a.height) == (595, 842)
    assert a.dpi == 72


def test_pdf_without_text_layer_is_flagged():
    a = analyzer.analyze(make_pdf(pages=1, image_bytes=make_image(400, 300), with_text=False))
    assert a.pdf_has_text_layer is False
    assert a.pdf_image_count == 1


def test_unsupported_format_is_reported_not_raised():
    a = analyzer.analyze(b"GIF89a" + b"\x00" * 100, filename="scan.gif")
    assert a.is_supported is False
    assert a.is_usable is False
    assert a.failure_reason == "unsupported_format"
    assert a.kind == "unknown"


def test_empty_file():
    a = analyzer.analyze(b"", filename="empty.jpg")
    assert a.byte_size == 0
    assert a.failure_reason == "unsupported_format"


def test_corrupted_image_and_pdf():
    bad_jpeg = analyzer.analyze(corrupt(make_image(800, 600, fmt="JPEG")), filename="x.jpg")
    assert bad_jpeg.detected_format == "jpeg"
    assert bad_jpeg.is_readable is False
    assert bad_jpeg.failure_reason == "corrupted_or_unreadable"

    bad_pdf = analyzer.analyze(corrupt(make_pdf()), filename="x.pdf")
    assert bad_pdf.detected_format == "pdf"
    assert bad_pdf.is_readable is False
    assert bad_pdf.failure_reason == "corrupted_or_unreadable"


def test_pixel_ceiling_rejects_oversized_dimensions():
    tiny_limit = DocumentAnalyzer(max_decoded_pixels=10_000)
    a = tiny_limit.analyze(make_image(400, 300, fmt="PNG"))
    assert a.is_readable is False
    assert a.failure_reason == "image_too_large_to_process"
    # Dimensions are still reported so the UI can explain the refusal.
    assert (a.width, a.height) == (400, 300)
