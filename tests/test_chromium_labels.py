"""Regression fixtures for case 17b14794-f35a-48b7-9d15-c447cf59b796.

Synthetic, test-owned reduction linked to the canonical diagnostic case.
"""

import io
import unicodedata

import pytest
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

from cardreport import (
    BarChart,
    Card,
    Currency,
    Formatting,
    Funnel,
    LayoutOverflowError,
    Page,
    Report,
    Text,
    Theme,
)


def narrow_report(funnel=False):
    chart = BarChart(
        ["busy", "completed", "net_err", "declined"],
        series={
            "день A": [20840, 15910, 5020, 1120],
            "день B": [17950, 14520, 3910, 980],
        },
        value_format="integer",
        show_labels=False,
    )
    report = Report(
        "Synthetic layout regression",
        page=Page(margin_mm=10),
        theme=Theme(font_size_pt=9.5, gap_mm=3.5, padding_mm=3.5),
        language="ru",
        formatting=Formatting(group="space", decimal=","),
    )
    if funnel:
        return report.row(
            Card(chart, title="Comparison"),
            Card(
                Funnel(
                    ["Звонки", "completed", "Люди", "Целевые"],
                    [43210, 15840, 2410, 512],
                ),
                title="Funnel",
            ),
            widths=[1.3, 1],
            height_mm=88,
        )
    return report.row(
        Card(Text("Companion block")),
        Card(chart, title="Comparison"),
        widths=[1.55, 1],
        height_mm=95,
    )


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


def open_report(browser, html):
    page = browser.new_page()
    page.emulate_media(media="print")
    page.set_content(html)
    page.wait_for_function(
        "window.cardreport && (cardreport.ready || cardreport.error)"
    )
    return page


@pytest.mark.parametrize("funnel", [False, True])
def test_narrow_report_pdf_and_checked_html(browser, funnel):
    report = narrow_report(funnel)
    reader = PdfReader(io.BytesIO(report.to_pdf()))
    assert len(reader.pages) == 1 and not reader.pages[0].images
    text = unicodedata.normalize("NFKC", reader.pages[0].extract_text())
    for value in ["completed", "день A", "день B"] + (
        ["43 210", "15 840", "512"] if funnel else []
    ):
        assert value in text
    page = open_report(browser, report.to_html())
    try:
        assert page.evaluate("cardreport.error") is None
        if not funnel:
            angles = page.locator(".xtick text").evaluate_all(
                "els => els.map(e=>e.getAttribute('transform'))"
            )
            assert any(
                "rotate(30" in angle or "rotate(29.99" in angle for angle in angles
            )
            assert page.locator(".xtick text").evaluate_all("""labels => {
                const rs=labels.map(e=>e.getBoundingClientRect());
                return rs.some((a,i)=>rs.slice(i+1).some(b=>
                    Math.min(a.right,b.right)-Math.max(a.left,b.left)>1 &&
                    Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1));
            }""")
        else:
            assert (
                page.locator('.chart[data-path="blocks.0.1.content"]').evaluate(
                    "chart=>chart._fullLayout._size.r"
                )
                > 35
            )
        assert page.locator(".chart").evaluate_all("""charts => charts.every(chart => {
            const cr=chart.getBoundingClientRect();
            return [...chart.querySelectorAll('svg text')].every(e=>{
                const r=e.getBoundingClientRect();
                return !r.width || (r.left>=cr.left-1 && r.right<=cr.right+1 && r.top>=cr.top-1 && r.bottom<=cr.bottom+1);
            });
        })""")
    finally:
        page.close()


@pytest.mark.parametrize("target", ["tick", "legend"])
def test_actual_rotated_text_collisions_are_rejected(browser, target):
    # No value labels here: margin relayout cannot erase the injected collision.
    html = narrow_report().to_html()
    injection = """(() => {
        const draw=Plotly.newPlot;
        Plotly.newPlot=async (...args)=>{
            const chart=await draw(...args), ticks=chart.querySelectorAll('.xtick text');
            TARGET
            return chart;
        };
    })();
    """
    mutation = (
        "ticks[1].setAttribute('transform', ticks[0].getAttribute('transform'));"
        if target == "tick"
        else """const legend=chart.querySelector('.legendtext');
            const a=ticks[1].getBoundingClientRect(), b=legend.getBoundingClientRect();
            legend.style.transform=`translate(${a.left-b.left}px,${a.top-b.top}px)`;"""
    )
    start = "(() => {\n  const state = window.cardreport"
    assert html.count(start) == 1
    html = html.replace(start, injection.replace("TARGET", mutation) + start)
    page = open_report(browser, html)
    try:
        error = page.evaluate("cardreport.error")
        assert error["kind"] == "LayoutOverflowError"
        assert "chart labels overlap:" in error["message"]
        assert "xtick" in error["message"]
        diagnostic = error["diagnostic"]
        assert diagnostic["reason"] == "label_overlap" and diagnostic["page"] == 1
        assert "completed" not in str(diagnostic) and "день" not in str(diagnostic)
        assert ("legend" if target == "legend" else "completed") in error["message"]
    finally:
        page.close()


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
@pytest.mark.parametrize("value", [1234567, -1234567])
def test_outside_bar_values_survive_pdf(orientation, value):
    report = Report().row(
        Card(
            BarChart(
                ["A", "B"],
                [value, value / 2],
                orientation=orientation,
                show_labels=True,
                category_labels=False,
                color_by="category",
                value_format=Currency("USD"),
            )
        ),
        height_mm=80,
    )
    reader = PdfReader(io.BytesIO(report.to_pdf()))
    assert "1,234,567.00" in reader.pages[0].extract_text()


def test_unfittable_value_still_rejects_without_publishing(tmp_path):
    report = Report(page=Page(size=(65, 160), margin_mm=10)).row(
        Card(Funnel(["A", "B"], [10**15, 1], value_format=Currency("USD"))),
        height_mm=90,
    )
    path = tmp_path / "existing.pdf"
    path.write_bytes(b"original")
    with pytest.raises(
        LayoutOverflowError, match="plotting area|exceeds available space"
    ):
        report.write_pdf(path, overwrite=True)
    assert path.read_bytes() == b"original"


def test_value_overlapping_category_label_still_rejects():
    report = Report().row(
        Card(
            BarChart(
                ["A", "B"],
                [-1234567, -1234567 / 2],
                orientation="horizontal",
                show_labels=True,
                value_format=Currency("USD"),
            )
        ),
        height_mm=80,
    )
    with pytest.raises(LayoutOverflowError, match="chart labels overlap:.*ytick"):
        report.to_pdf()


def test_flow_dashboard_preserves_records_and_whole_chart_row():
    from examples.flow_dashboard import build_report

    pdf = PdfReader(io.BytesIO(build_report().to_pdf()))
    assert len(pdf.pages) > 1
    texts = [page.extract_text() for page in pdf.pages]
    all_text = "\n".join(texts)
    assert all(all_text.count(f"REQ-{i:03d}") == 1 for i in range(1, 121))
    assert sum("Daily requests" in text for text in texts) == 1
    assert any("Daily requests" in text and "Outcomes" in text for text in texts)
    assert "Resolution rate" in texts[-1]


def test_negative_child_bounds_are_measured(browser):
    report = Report().row(Card(Text("bounds fixture")), height_mm=60)
    html = report.to_html().replace(
        "</head>",
        """<style>
    .card-content{position:relative;overflow:visible!important}
    .card-content>.text{position:absolute;left:-50px;top:-60px;width:20px;height:20px}
    </style></head>""",
    )
    page = open_report(browser, html)
    try:
        error = page.evaluate("cardreport.error")
        assert error["kind"] == "LayoutOverflowError"
        d = error["diagnostic"]
        assert d["box"] == "border"
        assert d["overflow_left_mm"] > 0 and d["overflow_top_mm"] > 0
        assert d["page"] == 1
    finally:
        page.close()
