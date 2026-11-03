import io
import time
import unicodedata
from dataclasses import FrozenInstanceError

import pytest
from fontTools.ttLib import TTFont
from pypdf import PdfReader

from cardreport import (
    KPI,
    BarChart,
    Card,
    ChromiumRenderer,
    Column,
    DependencyError,
    Funnel,
    LayoutOverflowError,
    LineChart,
    Page,
    Report,
    ReportDocument,
    Text,
    UnsupportedFeatureError,
    ValidationError,
    WeasyPrintRenderer,
)
from examples.reference_report import build_report


@pytest.fixture(
    params=[ChromiumRenderer, WeasyPrintRenderer], ids=["chromium", "weasyprint"]
)
def renderer(request):
    if request.param is WeasyPrintRenderer:
        pytest.importorskip(
            "weasyprint", reason="optional WeasyPrint runtime unavailable"
        )
    return request.param()


def pdf(report, renderer):
    return PdfReader(io.BytesIO(report.to_pdf(renderer=renderer)))


def text(reader):
    return unicodedata.normalize(
        "NFKC", "\n".join(p.extract_text() for p in reader.pages)
    )


def test_reference_for_each_renderer(renderer):
    r = pdf(build_report(), renderer)
    assert len(r.pages) == 1
    assert abs(float(r.pages[0].mediabox.width) - 1600) < 0.3
    for label in (
        "Campaign progress",
        "Contact funnel",
        "Call attempt results",
        "Conversation outcomes",
        "40.0%",
        "60.0%",
        "2026-11-04",
        "Identity confirmed",
        "No answer / busy / voicemail",
        "34",
        "24",
        "21",
    ):
        assert label in text(r)
    from cardreport._pdf_checks import resource_scopes

    for resources in resource_scopes(r.pages[0]["/Resources"]):
        assert not any(
            x.get_object().get("/Subtype") == "/Image"
            for x in resources.get("/XObject", {}).values()
        )
        for f in resources.get("/Font", {}).values():
            f = f.get_object()
            if "/DescendantFonts" in f:
                f = f["/DescendantFonts"][0].get_object()
            descriptor = f["/FontDescriptor"].get_object()
            font = TTFont(io.BytesIO(descriptor["/FontFile2"].get_data()))
            assert any(
                "DejaVu" in n.toUnicode() for n in font["name"].names if n.nameID == 1
            )


def test_literal_svg_or_plotly_labels(renderer):
    phrase = "</script><b>&amp; $x$ 'DejaVu Sans' Пример"
    r = pdf(
        Report(page=Page(orientation="landscape")).row(
            Card(BarChart([phrase], [2], orientation="horizontal")), height_mm=90
        ),
        renderer,
    )
    assert phrase in text(r)


@pytest.mark.parametrize(
    "report",
    [
        Report().row(Card(Text("word " * 200)), height_mm=20),
        Report().row(Card(KPI("tiny", 1)), height_mm=10),
        Report().add(Card(Text("word " * 1600))),
        Report().row(
            Column(Card(Text("word " * 200)), Card(KPI("x", 1)), heights=[1, 1]),
            height_mm=40,
        ),
        Report().row(
            Card(BarChart(["W" * 180], [1], orientation="horizontal")), height_mm=70
        ),
    ],
)
def test_overflow_is_geometric_and_does_not_publish(renderer, report, tmp_path):
    target = tmp_path / "keep.pdf"
    target.write_bytes(b"original")
    with pytest.raises(LayoutOverflowError, match="blocks|pages|report"):
        report.write_pdf(target, overwrite=True, renderer=renderer)
    assert target.read_bytes() == b"original"


def test_weighted_must_fit_and_explicit_pages(renderer):
    report = (
        Report()
        .new_page()
        .row(
            Column(Card(KPI("One", 1)), Card(KPI("Two", 2)), heights=[1, 1]),
            Card(Text("Fits")),
            widths=[1, 2],
            height_mm=90,
        )
        .new_page()
        .new_page()
        .add(KPI("Three", 3))
        .new_page()
    )
    r = pdf(report, renderer)
    assert len(r.pages) == 2
    assert all(x in text(r).replace(" ", "") for x in ("One", "Two", "Three", "Fits"))


def test_empty_report(renderer):
    assert len(pdf(Report(), renderer).pages) == 1


def test_validation_before_custom_renderer_and_frozen_snapshot():
    class Capture:
        doc = None

        def render_html(self, doc):
            self.doc = doc
            return "preview"

        def render_pdf(self, doc, *, deadline):
            assert deadline > time.monotonic()
            self.doc = doc
            return b"%PDF-test"

    renderer = Capture()
    report = Report("Before").add(BarChart(["A"], [1]))
    assert report.to_html(renderer=renderer) == "preview"
    snapshot = renderer.doc
    assert isinstance(snapshot, ReportDocument)
    report.title = "After"
    report.add(Text("New"))
    assert snapshot.title == "Before" and len(snapshot.blocks) == 1
    with pytest.raises(FrozenInstanceError):
        snapshot.title = "mutate"
    with pytest.raises(TypeError):
        snapshot.charts["other"] = snapshot.charts["blocks.0"]
    assert report.to_pdf(renderer=renderer) == b"%PDF-test"
    renderer.doc = None
    with pytest.raises(ValidationError):
        Report().add(Text("x" * 10001)).to_html(renderer=renderer)
    assert renderer.doc is None


def test_invalid_x_kind_has_correct_error():
    with pytest.raises(ValidationError, match="invalid x_kind"):
        Report().add(LineChart([123], [1], x_kind="wrong")).validate()


@pytest.mark.parametrize(
    "report",
    [
        Report(mode="flow"),
        Report().add(Funnel(["a"], [1])),
        Report().add(LineChart(["a"], [1])),
        Report().add(BarChart(["a"], series={"A": [1], "B": [2]})),
    ],
)
def test_weasy_unsupported_is_explicit(report):
    with pytest.raises(UnsupportedFeatureError):
        report.to_pdf(renderer=WeasyPrintRenderer())


def test_weasy_canary_fail_closed(monkeypatch):
    weasy = pytest.importorskip("weasyprint")
    from weasyprint.text.fonts import FontConfiguration

    import cardreport._weasy_boxes as boxes

    monkeypatch.setattr(boxes, "inspect", lambda *args: {})
    with pytest.raises(DependencyError, match="canary"):
        boxes.verify_adapter(weasy.HTML, FontConfiguration(), None)


def test_weasy_adapter_incompatible_and_version(monkeypatch):
    weasy = pytest.importorskip("weasyprint")
    from types import SimpleNamespace

    import cardreport._weasy_boxes as boxes

    with pytest.raises(DependencyError, match="incompatible"):
        boxes.inspect(SimpleNamespace(pages=[object()]), 1)
    monkeypatch.setattr(weasy, "__version__", "unexpected")
    with pytest.raises(DependencyError, match="requires"):
        boxes.verify_adapter(None, None, None)


def test_weasy_static_html():
    pytest.importorskip("weasyprint")
    html = (
        Report()
        .row(Card(BarChart(["A"], [1])), height_mm=90)
        .to_html(renderer=WeasyPrintRenderer())
    )
    assert "<svg" in html and "<script" not in html and "Plotly" not in html


def test_funnel_must_fit():
    report = Report(page=Page(orientation="landscape")).row(
        Card(Funnel(["Start", "Finish"], [10, 5])), height_mm=100
    )
    assert "Start" in text(pdf(report, ChromiumRenderer()))


def test_page_limit_is_layout_error(renderer):
    report = Report()
    for i in range(101):
        report.add(KPI("Page", i)).new_page()
    with pytest.raises(LayoutOverflowError, match="page limit"):
        report.to_pdf(renderer=renderer)


def test_oversized_text_is_validation_error():
    with pytest.raises(ValidationError, match="10000"):
        Report().add(Text("x" * 10001)).validate()


def test_weasy_deadline_cleans_up_and_preserves_file(monkeypatch, tmp_path):
    pytest.importorskip("weasyprint")
    import psutil

    import cardreport.pdf as process_module
    from cardreport import RenderTimeoutError

    stopped = []
    stop = process_module.stop_worker

    def record(process):
        stopped.append(psutil.Process(process.pid))
        stop(process)

    monkeypatch.setattr(process_module, "stop_worker", record)
    target = tmp_path / "report.pdf"
    target.write_bytes(b"keep")
    with pytest.raises(RenderTimeoutError):
        Report().add(KPI("x", 1)).write_pdf(
            target, renderer=WeasyPrintRenderer(), overwrite=True, timeout=0.1
        )
    assert target.read_bytes() == b"keep"
    assert stopped and not any(
        p.is_running() and p.status() != psutil.STATUS_ZOMBIE for p in stopped
    )


def test_weasy_blocks_resource_fetches():
    pytest.importorskip("weasyprint")
    import json

    from cardreport import RenderError
    from cardreport.pdf import run_worker

    payload = json.dumps(
        {
            "html": '<img src="https://example.invalid/private">',
            "charts": {},
            "pages": 1,
            "pdf": True,
        }
    ).encode()
    with pytest.raises(RenderError, match="external resource"):
        run_worker(
            "cardreport._weasy_worker", payload, [], deadline=time.monotonic() + 10
        )


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
def test_weasy_pdf_chart_character_bounds(orientation):
    pytest.importorskip("weasyprint")
    import pdfplumber

    label = "Long label 'DejaVu Sans' Пример near edge"
    report = Report(page=Page(size=(200, 150), margin_mm=10)).row(
        BarChart([label], [1234], orientation=orientation, show_labels=True),
        height_mm=80,
    )
    data = report.to_pdf(renderer=WeasyPrintRenderer())
    with pdfplumber.open(io.BytesIO(data)) as r:
        page = r.pages[0]
        assert label in unicodedata.normalize("NFKC", page.extract_text())
        assert page.chars
        scale = 72 / 25.4
        for char in page.chars:
            assert char["x0"] >= 10 * scale
            assert char["x1"] <= 190 * scale
            assert char["top"] >= 10 * scale
            assert char["bottom"] <= 90 * scale


def test_svg_font_rewrite_preserves_text_and_ignores_local_rc():
    pytest.importorskip("matplotlib")
    from xml.etree import ElementTree as ET

    from matplotlib import rc_context

    from cardreport._svg_charts import render_svg

    spec = {
        "labels": ["'DejaVu Sans'"],
        "values": [1],
        "value_labels": ["1"],
        "horizontal": True,
        "show_labels": True,
        "font_size": 10,
        "color": "#20a6c4",
        "text_color": "#222222",
        "format": "integer",
    }

    def labels():
        svg = ET.fromstring(render_svg(spec, 600, 300, "chart"))
        return [
            (e.text, e.attrib) for e in svg.iter("{http://www.w3.org/2000/svg}text")
        ]

    expected = labels()
    with rc_context({"font.sans-serif": ["fantasy"], "xtick.major.pad": 80}):
        assert labels() == expected
    assert any(t == "'DejaVu Sans'" for t, _ in expected)


def test_font_verification_reaches_nested_forms_and_rejects_substitution():
    from importlib.resources import files
    from types import SimpleNamespace

    from pypdf.generic import (
        ArrayObject,
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
    )

    from cardreport import RenderError
    from cardreport._pdf_checks import verify_fonts

    font = TTFont(
        io.BytesIO(
            files("cardreport").joinpath("assets", "DejaVuSans.ttf").read_bytes()
        )
    )
    for n in font["name"].names:
        if n.nameID == 5:
            n.string = "Version 99.0".encode(n.getEncoding())
    changed = io.BytesIO()
    font.save(changed)
    stream = DecodedStreamObject()
    stream.set_data(changed.getvalue())
    descriptor = DictionaryObject({NameObject("/FontFile2"): stream})
    descendant = DictionaryObject({NameObject("/FontDescriptor"): descriptor})
    f = DictionaryObject({NameObject("/DescendantFonts"): ArrayObject([descendant])})
    nested = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): f})}
    )
    form = DictionaryObject({NameObject("/Resources"): nested})
    root = DictionaryObject(
        {NameObject("/XObject"): DictionaryObject({NameObject("/Form"): form})}
    )
    reader = SimpleNamespace(pages=[DictionaryObject({NameObject("/Resources"): root})])
    with pytest.raises(RenderError, match="identity or version"):
        verify_fonts(reader)
