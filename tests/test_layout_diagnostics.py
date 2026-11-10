import json
import pickle
import time

import pytest

from cardreport import (
    Card,
    ChromiumRenderer,
    LayoutDiagnostic,
    LayoutOverflowError,
    Report,
    Text,
    WeasyPrintRenderer,
)
from cardreport.layout import decode_diagnostic, measured_overflow
from cardreport.pdf import run_worker


def test_measurement_units_roundtrip_and_pickle():
    d = measured_overflow(
        "blocks.2", (10, 20, 106, 116), (0, 15, 130, 164), box="content", page=2
    )
    assert d is not None
    assert d.available_height_mm == pytest.approx(25.4)
    assert d.overflow_bottom_mm == pytest.approx(12.7)
    assert d.overflow_left_mm == pytest.approx(10 * 25.4 / 96)
    assert LayoutDiagnostic.from_dict(json.loads(json.dumps(d.to_dict()))) == d
    error = LayoutOverflowError("old message", diagnostic=d)
    assert str(error) == "old message"
    assert pickle.loads(pickle.dumps(error)).diagnostic == d
    points = measured_overflow(
        "blocks.0",
        (0, 0, 72, 72),
        (0, 0, 72, 108),
        box="viewport",
        mm_per_unit=25.4 / 72,
    )
    assert points.overflow_bottom_mm == pytest.approx(12.7)


@pytest.mark.parametrize(
    "change",
    [
        {"overflow_bottom_mm": float("nan")},
        {"overflow_bottom_mm": float("inf")},
        {"overflow_bottom_mm": 10**400},
        {"overflow_bottom_mm": True},
        {"overflow_bottom_mm": -1},
        {"page": True},
        {"page": 0},
        {"reason": "secret"},
        {"path": "<script>secret</script>"},
        {"label": "secret"},
        {"box": None},
        {"path": "blocks." + "1" * 600},
    ],
)
def test_invalid_optional_metadata_is_discarded(change):
    raw = {
        "reason": "content_overflow",
        "path": "blocks.0",
        "box": "content",
        "overflow_bottom_mm": 1,
    }
    assert decode_diagnostic(raw | change) is None


def test_invalid_measurement_does_not_replace_error():
    assert (
        measured_overflow("canary", (0, 0, 10, 10), (0, 0, 10, 20), box="content")
        is None
    )
    assert (
        measured_overflow(
            "blocks.0", (0, 0, float("nan"), 10), (0, 0, 10, 20), box="content"
        )
        is None
    )


@pytest.mark.parametrize(
    "diagnostic",
    [
        None,
        {"reason": "label_overlap", "path": "blocks.0"},
        {"reason": "secret"},
        {
            "reason": "content_overflow",
            "path": "blocks.0",
            "box": "content",
            "overflow_bottom_mm": 10**400,
        },
    ],
)
def test_worker_error_transport(tmp_path, monkeypatch, diagnostic):
    payload = {"kind": "LayoutOverflowError", "message": "old error"}
    if diagnostic is not None:
        payload["diagnostic"] = diagnostic
    (tmp_path / "error_fixture.py").write_text(
        "import sys\nsys.stderr.write(" + repr(json.dumps(payload)) + ")\nsys.exit(1)\n"
    )
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    with pytest.raises(LayoutOverflowError, match="old error") as caught:
        run_worker("error_fixture", b"", [], deadline=time.monotonic() + 10, pdf=False)
    assert caught.value.diagnostic == decode_diagnostic(diagnostic)


@pytest.mark.parametrize("height,overflows", [(101, False), (101.1, True), (140, True)])
def test_weasy_real_boxes_tolerance_and_maximum(height, overflows):
    from weasyprint import HTML

    from cardreport._weasy_boxes import inspect

    html = f"""<style>@page{{size:500px 500px;margin:0}}body{{margin:0}}
    .parent{{position:relative;width:100px;height:100px}}
    .child{{position:absolute;left:0;top:0;width:100px}}
    </style><div class="parent" data-path="blocks.0"><div class="child" style="height:101px"></div><div class="child" style="height:{height}px"></div></div>"""
    document = HTML(string=html).render()
    if not overflows:
        inspect(document, 1)
    else:
        with pytest.raises(LayoutOverflowError) as caught:
            inspect(document, 1)
        d = caught.value.diagnostic
        assert d.path == "blocks.0" and d.page == 1 and d.box == "content"
        assert d.available_height_mm == pytest.approx(100 * 25.4 / 96)
        assert d.overflow_bottom_mm == pytest.approx((height - 100) * 25.4 / 96)
        assert d.overflow_left_mm == 0


@pytest.mark.parametrize("renderer", [ChromiumRenderer(), WeasyPrintRenderer()])
def test_actual_render_preserves_measurement_without_text(renderer):
    report = Report().row(Card(Text("PRIVATE_DATA_" * 100)), height_mm=15)
    with pytest.raises(LayoutOverflowError) as caught:
        report.to_pdf(renderer=renderer)
    d = caught.value.diagnostic
    assert d is not None and d.page == 1 and d.path.startswith("blocks.0")
    assert d.overflow_bottom_mm > 0
    assert "PRIVATE_DATA" not in json.dumps(d.to_dict())
    if isinstance(renderer, ChromiumRenderer) and d.box == "padding":
        assert d.overflow_left_mm is None and d.overflow_top_mm is None


def test_native_glyph_diagnostics_units_maxima_and_page(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    import pdfplumber

    from cardreport._pdf_checks import verify_chart_bounds

    pdf = MagicMock()
    pdf.__enter__.return_value.pages = [
        SimpleNamespace(
            chars=[
                {"x0": -2, "top": -3, "x1": 76, "bottom": 80},
                {"x0": -5, "top": -7, "x1": 82, "bottom": 90},
            ]
        )
    ]
    monkeypatch.setattr(pdfplumber, "open", lambda _: pdf)
    with pytest.raises(LayoutOverflowError) as caught:
        verify_chart_bounds(b"fixture", 96, 96, "blocks.0", page=3)
    d = caught.value.diagnostic
    assert d.page == 3 and d.reason == "label_outside"
    assert d.available_width_mm == pytest.approx(25.4)
    assert d.overflow_left_mm == pytest.approx(5 * 25.4 / 72)
    assert d.overflow_top_mm == pytest.approx(7 * 25.4 / 72)
    assert d.overflow_right_mm == pytest.approx(10 * 25.4 / 72)
    assert d.overflow_bottom_mm == pytest.approx(18 * 25.4 / 72)


def test_weasy_left_top_and_optional_page_lookup():
    from weasyprint import HTML

    from cardreport._weasy_boxes import inspect, page_for_path

    doc = HTML(
        string="""<style>@page{size:500px 500px;margin:0}body{margin:0}
    .parent{position:relative;width:100px;height:100px}
    .child{position:absolute;left:-10px;top:-20px;width:100px;height:100px}
    </style><div class="parent" data-path="blocks.0"><div class="child"></div></div>"""
    ).render()
    with pytest.raises(LayoutOverflowError) as caught:
        inspect(doc, 1)
    d = caught.value.diagnostic
    assert d.overflow_left_mm == pytest.approx(10 * 25.4 / 96)
    assert d.overflow_top_mm == pytest.approx(20 * 25.4 / 96)
    assert page_for_path(doc, "blocks.0") == 1
    assert page_for_path(object(), "blocks.0") is None


def test_reason_metadata_with_private_path_cannot_mask_error():
    from cardreport.layout import reason_diagnostic

    assert reason_diagnostic("label_overlap", "private label") is None


def test_matplotlib_bbox_scalars_are_serializable_measurements():
    from matplotlib.transforms import Bbox

    b = Bbox.from_extents(-10, -20, 120, 140)
    d = measured_overflow(
        "blocks.0",
        (0, 0, 100, 100),
        (b.x0, b.y0, b.x1, b.y1),
        box="viewport",
        reason="label_outside",
    )
    assert d is not None
    assert d.overflow_bottom_mm == pytest.approx(40 * 25.4 / 96)
    assert d.overflow_left_mm == pytest.approx(10 * 25.4 / 96)
    assert LayoutDiagnostic.from_dict(json.loads(json.dumps(d.to_dict()))) == d
