import io
import json
from dataclasses import FrozenInstanceError

import pdfplumber
import pytest
from PIL import Image as PILImage
from PIL import ImageDraw
from pypdf import PdfReader

from cardreport import (
    Card,
    ChromiumRenderer,
    Column,
    Image,
    LayoutOverflowError,
    RenderError,
    Report,
    ReportTemplate,
    TemplateError,
    Text,
    ValidationError,
    WeasyPrintRenderer,
)


def picture(kind="PNG", *, orientation=None):
    image = PILImage.new("RGB", (120, 60), "#20a6c4")
    ImageDraw.Draw(image).rectangle((0, 0, 59, 29), fill="#ed4747")
    buf = io.BytesIO()
    options = {}
    if orientation is not None:
        exif = PILImage.Exif()
        exif[274] = orientation
        options["exif"] = exif
    image.save(buf, format=kind, **options)
    return buf.getvalue()


def spec():
    return {
        "format": "cardreport.template/1",
        "datasets": {},
        "assets": {"company": Image.from_bytes(picture()).to_asset()},
        "report": {
            "title": "Daily report",
            "logo": {"asset": "company", "alt": "Company"},
            "logo_position": "right",
            "blocks": [
                {
                    "type": "card",
                    "content": {
                        "type": "image",
                        "asset": "company",
                        "width_mm": 40,
                    },
                }
            ],
        },
    }


def test_snapshot_and_file(tmp_path):
    original = bytearray(picture())
    image = Image.from_bytes(original, width_mm=30, alt='<img src="bad">')
    original[:] = b"x" * len(original)
    assert image.data == picture()
    path = tmp_path / "logo.png"
    path.write_bytes(image.data)
    assert Image.from_file(path, width_mm=30)._size == (120, 60)
    with pytest.raises(FrozenInstanceError):
        image.alt = "other"
    html = Report(logo=image).to_html()
    assert "&lt;img src=&quot;bad&quot;&gt;" in html
    assert "header-logo" in html


def test_template_transports():
    template = ReportTemplate(spec())
    for loaded in (
        ReportTemplate.from_json(template.to_json()),
        ReportTemplate.from_yaml(template.to_yaml()),
    ):
        report = loaded.bind({})
        assert report.logo.data == picture()
        assert report.logo_position == "right"
        assert isinstance(report.blocks[0].content, Image)
        assert loaded.to_dict() == template.to_dict()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s["assets"]["company"].update(data_base64="not base64!"),
        lambda s: s["assets"]["company"].update(media_type="image/jpeg"),
        lambda s: s["report"]["logo"].update(asset="missing"),
        lambda s: s["report"]["blocks"][0]["content"].update(asset="missing"),
        lambda s: s["report"].update(logo_position="top"),
    ],
)
def test_bad_template(mutate):
    definition = spec()
    mutate(definition)
    with pytest.raises(TemplateError) as error:
        ReportTemplate(definition)
    assert error.value.template_path


@pytest.mark.parametrize(
    "options",
    [
        {"width_mm": 0},
        {"height_mm": -1},
        {"width_mm": float("nan")},
        {"align": "bad"},
        {"valign": "bad"},
        {"alt": None},
    ],
)
def test_invalid_options(options):
    with pytest.raises(ValidationError):
        Image.from_bytes(picture(), **options)


def test_formats_and_metadata_only(monkeypatch):
    def no_decode(*args, **kwargs):
        raise AssertionError("metadata inspection decoded pixels")

    png, jpeg = picture(), picture("JPEG", orientation=6)
    monkeypatch.setattr(PILImage.Image, "load", no_decode)
    assert Image.from_bytes(png)._size == (120, 60)
    assert Image.from_bytes(jpeg)._size == (60, 120)
    with pytest.raises(ValidationError):
        Image.from_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"/>')


def test_pillow_guard_is_preserved(monkeypatch):
    data = picture()
    monkeypatch.setattr(PILImage, "MAX_IMAGE_PIXELS", 4000)
    with pytest.warns(PILImage.DecompressionBombWarning):
        Image.from_bytes(data)
    monkeypatch.setattr(PILImage, "MAX_IMAGE_PIXELS", 1000)
    with pytest.raises(ValidationError, match="Pillow safety"):
        Image.from_bytes(data)


@pytest.mark.parametrize(
    "renderer",
    [ChromiumRenderer(), WeasyPrintRenderer()],
    ids=["chromium", "weasyprint"],
)
@pytest.mark.parametrize(
    "options",
    [
        {"width_mm": 30},
        {"height_mm": 15},
        {"width_mm": 40, "height_mm": 30},
        {},
    ],
)
def test_both_engines_geometry(renderer, options):
    image = Image.from_bytes(picture(), alt="Company", **options)
    report = Report(
        "Image report", logo=Image.from_bytes(picture()), logo_position="right"
    )
    report.row(Card(image), Text("Image alongside text"), widths=[1, 2], height_mm=40)
    report.add(Image.from_bytes(picture(), width_mm=20, align="right"))
    report.add(Column(Image.from_bytes(picture(), width_mm=15), Text("End")))
    data = report.to_pdf(renderer=renderer, timeout=60)
    reader = PdfReader(io.BytesIO(data))
    assert len(reader.pages) == 1
    assert "End" in reader.pages[0].extract_text()
    assert reader.pages[0].images
    with pdfplumber.open(io.BytesIO(data)) as document:
        placements = document.pages[0].images
        mm = 72 / 25.4
        target = placements[1]
        expected_width = (
            (options.get("width_mm") or 2 * options["height_mm"])
            if options
            else (190 - 4) / 3 - 8.4
        )
        assert target["width"] / mm == pytest.approx(expected_width, abs=0.3)
        assert target["width"] / target["height"] == pytest.approx(2, abs=0.04)
        assert placements[0]["width"] / mm == pytest.approx(30, abs=0.3)
        assert placements[0]["height"] / mm == pytest.approx(15, abs=0.3)


@pytest.mark.parametrize(
    "renderer",
    [ChromiumRenderer(), WeasyPrintRenderer()],
    ids=["chromium", "weasyprint"],
)
def test_auto_free_height_and_logo_only(renderer):
    report = Report(logo=Image.from_bytes(picture()), logo_position="left")
    report.add(Card(Image.from_bytes(picture())))
    data = report.to_pdf(renderer=renderer, timeout=60)
    assert len(PdfReader(io.BytesIO(data)).pages) == 1
    with pdfplumber.open(io.BytesIO(data)) as document:
        target = document.pages[0].images[1]
        assert target["width"] * 25.4 / 72 == pytest.approx(181.6, abs=0.3)
        assert target["width"] / target["height"] == pytest.approx(2, abs=0.03)


@pytest.mark.parametrize(
    "renderer",
    [ChromiumRenderer(), WeasyPrintRenderer()],
    ids=["chromium", "weasyprint"],
)
def test_explicit_image_overflow(renderer):
    report = Report().row(
        Image.from_bytes(picture(), width_mm=200), Text("Other"), height_mm=20
    )
    with pytest.raises(LayoutOverflowError):
        report.to_pdf(renderer=renderer, timeout=60)


@pytest.mark.parametrize(
    "renderer",
    [ChromiumRenderer(), WeasyPrintRenderer()],
    ids=["chromium", "weasyprint"],
)
def test_jpeg_orientation(renderer):
    image = Image.from_bytes(picture("JPEG", orientation=6), width_mm=15)
    assert image._size == (60, 120)
    data = (
        Report(logo=image)
        .add(Text("Oriented JPEG"))
        .to_pdf(renderer=renderer, timeout=60)
    )
    assert PdfReader(io.BytesIO(data)).pages[0].images


@pytest.mark.parametrize(
    "renderer",
    [ChromiumRenderer(), WeasyPrintRenderer()],
    ids=["chromium", "weasyprint"],
)
def test_broken_pixels_do_not_disappear(renderer):
    data = picture()
    # Preserve valid PNG metadata, destroy the compressed pixel stream and its checksum.
    offset = data.index(b"IDAT") + 4
    corrupt = data[:offset] + b"x" * (len(data) - offset)
    image = Image.from_bytes(corrupt, width_mm=30)
    with pytest.raises(RenderError, match="image could not be decoded"):
        Report(logo=image).to_pdf(renderer=renderer, timeout=60)


def test_template_json_schema_contains_image():
    from jsonschema import Draft202012Validator

    from cardreport import json_schema

    Draft202012Validator(json.loads(json_schema("template"))).validate(spec())


def test_html_export_checks_pixel_data():
    data = picture()
    offset = data.index(b"IDAT") + 4
    image = Image.from_bytes(data[:offset] + b"x" * (len(data) - offset))
    with pytest.raises(RenderError, match="image could not be decoded"):
        Report(logo=image).to_html()


def test_invalid_bytes_type():
    with pytest.raises(ValidationError, match="expected image bytes"):
        Image.from_bytes(1000)


def test_animated_png_is_rejected():
    first, second = (
        PILImage.new("RGB", (2, 2), "red"),
        PILImage.new("RGB", (2, 2), "blue"),
    )
    buffer = io.BytesIO()
    first.save(buffer, format="PNG", save_all=True, append_images=[second])
    with pytest.raises(ValidationError, match="animated"):
        Image.from_bytes(buffer.getvalue())


@pytest.mark.parametrize(
    "renderer",
    [ChromiumRenderer(), WeasyPrintRenderer()],
    ids=["chromium", "weasyprint"],
)
def test_jpeg_pixels_and_fixed_alignment(renderer):
    report = Report().row(
        Image.from_bytes(
            picture("JPEG", orientation=6), width_mm=15, align="right", valign="bottom"
        ),
        Text("Other"),
        widths=[1, 1],
        height_mm=40,
    )
    with pdfplumber.open(
        io.BytesIO(report.to_pdf(renderer=renderer, timeout=60))
    ) as pdf:
        page = pdf.pages[0]
        image = page.images[0]
        mm = 72 / 25.4
        assert image["width"] / mm == pytest.approx(15, abs=0.3)
        assert image["height"] / mm == pytest.approx(30, abs=0.3)
        assert image["x1"] / mm == pytest.approx(103, abs=0.3)
        assert image["bottom"] / mm == pytest.approx(50, abs=0.3)
        # The red upper-left quarter rotates into the upper-right quarter.
        bitmap = page.to_image(resolution=72).original.convert("RGB")
        left, top = image["x0"], image["top"]
        w, h = image["width"], image["height"]
        red = bitmap.getpixel((round(left + w * 0.75), round(top + h * 0.25)))
        cyan = bitmap.getpixel((round(left + w * 0.25), round(top + h * 0.25)))
        assert red[0] > 180 and red[1] < 120
        assert cyan[0] < 80 and cyan[1] > 120


@pytest.mark.parametrize("alt", ["\ud800", "\x00"])
def test_alt_rejects_invalid_unicode_and_controls(alt):
    with pytest.raises(ValidationError, match="image.alt"):
        Image.from_bytes(picture(), alt=alt)


def test_mpo_first_frame_is_a_static_jpeg():
    buf = io.BytesIO()
    first, second = (
        PILImage.new("RGB", (20, 10), "red"),
        PILImage.new("RGB", (20, 10), "blue"),
    )
    first.save(buf, format="MPO", save_all=True, append_images=[second])
    image = Image.from_bytes(buf.getvalue())
    assert image._media_type == "image/jpeg"
    assert image._size == (20, 10)
    assert "data:image/jpeg" in Report(logo=image).to_html()


@pytest.mark.parametrize(
    "renderer",
    [ChromiumRenderer(), WeasyPrintRenderer()],
    ids=["chromium", "weasyprint"],
)
def test_oversized_logo_fails(renderer):
    with pytest.raises(LayoutOverflowError):
        Report("Title", logo=Image.from_bytes(picture(), width_mm=300)).to_pdf(
            renderer=renderer, timeout=60
        )


@pytest.mark.parametrize(
    "renderer",
    [ChromiumRenderer(), WeasyPrintRenderer()],
    ids=["chromium", "weasyprint"],
)
def test_png_orientation_is_stored(renderer):
    image = Image.from_bytes(picture(orientation=6), width_mm=30)
    assert image._size == (120, 60)
    with pdfplumber.open(
        io.BytesIO(Report().add(image).to_pdf(renderer=renderer, timeout=60))
    ) as pdf:
        page = pdf.pages[0]
        bounds = page.images[0]
        bitmap = page.to_image(resolution=72).original.convert("RGB")
        red = bitmap.getpixel(
            (
                round(bounds["x0"] + bounds["width"] * 0.25),
                round(bounds["top"] + bounds["height"] * 0.25),
            )
        )
        assert red[0] > 180 and red[1] < 120
        assert bounds["width"] / bounds["height"] == pytest.approx(2, abs=0.03)


@pytest.mark.parametrize(
    "renderer",
    [ChromiumRenderer(), WeasyPrintRenderer()],
    ids=["chromium", "weasyprint"],
)
def test_mpo_pdf_renders_first_frame(renderer):
    buffer = io.BytesIO()
    first, second = (
        PILImage.new("RGB", (20, 10), "red"),
        PILImage.new("RGB", (20, 10), "blue"),
    )
    first.save(buffer, format="MPO", save_all=True, append_images=[second])
    report = Report().add(Image.from_bytes(buffer.getvalue(), width_mm=20))
    with pdfplumber.open(
        io.BytesIO(report.to_pdf(renderer=renderer, timeout=60))
    ) as document:
        page = document.pages[0]
        image = page.images[0]
        bitmap = page.to_image(resolution=72).original.convert("RGB")
        color = bitmap.getpixel(
            (
                round(image["x0"] + image["width"] / 2),
                round(image["top"] + image["height"] / 2),
            )
        )
        assert color[0] > 200 and color[2] < 40


@pytest.mark.parametrize("logo", [True, False])
def test_invalid_template_alt_location(logo):
    definition = spec()
    node = (
        definition["report"]["logo"]
        if logo
        else definition["report"]["blocks"][0]["content"]
    )
    node["alt"] = "\x00"
    with pytest.raises(TemplateError) as error:
        ReportTemplate(definition)
    expected = "report.logo.alt" if logo else "report.blocks[0].content.alt"
    assert error.value.template_path == expected
