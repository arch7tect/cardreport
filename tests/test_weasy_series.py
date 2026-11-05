import io
import json
from datetime import date
from unittest.mock import patch

import pytest
from pypdf import PdfReader

from cardreport import (
    BarChart,
    Card,
    ChromiumRenderer,
    Funnel,
    LayoutOverflowError,
    LineChart,
    Page,
    Report,
    WeasyPrintRenderer,
)
from cardreport._chart_display import series_colors
from cardreport._svg_charts import render_svg
from examples.series_report import build_report


def payload(chart):
    captured = {}

    def capture(module, source, *args, **kwargs):
        captured.update(json.loads(source))
        return b"html"

    with patch("cardreport.weasyprint.run_worker", capture):
        Report().row(Card(chart), height_mm=90).to_html(renderer=WeasyPrintRenderer())
    return next(iter(captured["charts"].values()))


def render(chart):
    data = (
        Report(page=Page(orientation="landscape"))
        .row(Card(chart), height_mm=100)
        .to_pdf(renderer=WeasyPrintRenderer())
    )
    reader = PdfReader(io.BytesIO(data))
    assert len(reader.pages) == 1 and not reader.pages[0].images
    return reader.pages[0].extract_text()


@pytest.mark.parametrize("horizontal", [False, True])
@pytest.mark.parametrize("mode", ["grouped", "stacked"])
def test_actual_bar_geometry(horizontal, mode, monkeypatch):
    from matplotlib.axes import Axes

    containers = []
    method = "barh" if horizontal else "bar"
    original = getattr(Axes, method)

    def capture(self, *args, **kwargs):
        bars = original(self, *args, **kwargs)
        containers.append(bars)
        return bars

    monkeypatch.setattr(Axes, method, capture)
    chart = BarChart(
        ["A", "B"],
        series={"First": [10, -10], "Second": [-4, 4], "Third": [2, -2]},
        mode=mode,
        orientation="horizontal" if horizontal else "vertical",
    )
    render_svg(payload(chart), 650, 350, "chart")
    bases = [
        [bar.get_x() if horizontal else bar.get_y() for bar in bars]
        for bars in containers
    ]
    assert bases == (
        [[0, 0], [10, -10], [6, -6]] if mode == "stacked" else [[0, 0]] * 3
    )
    sizes = [
        [bar.get_width() if horizontal else bar.get_height() for bar in bars]
        for bars in containers
    ]
    assert sizes == [[10, -10], [-4, 4], [2, -2]]
    locations = [
        bars[0].get_y() if horizontal else bars[0].get_x() for bars in containers
    ]
    assert (
        locations[0] == locations[1]
        if mode == "stacked"
        else locations[0] < locations[1] < locations[2]
    )


def test_chromium_signed_stack_contract():
    from playwright.sync_api import sync_playwright
    from plotly.offline import get_plotlyjs

    from cardreport import Theme
    from cardreport.charts import chart_spec

    spec = chart_spec(
        BarChart(
            ["A"], series={"First": [10], "Second": [-4], "Third": [2]}, mode="stacked"
        ),
        Theme(),
        "chart",
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content('<div id="chart"></div>')
            page.add_script_tag(content=get_plotlyjs())
            bases = page.evaluate(
                "async s => { const el=document.getElementById('chart'); await Plotly.newPlot(el,s.data,s.layout); return el.calcdata.map(t=>t[0].b); }",
                spec,
            )
            assert bases == [0, 10, 6]
        finally:
            browser.close()


@pytest.mark.parametrize("values", [[0], [0, 0, 0], [10, 0, 4], [4, 10, 2]])
@pytest.mark.parametrize("show_labels", [False, True])
def test_funnel_centered_geometry_and_zero_stages(values, show_labels, monkeypatch):
    from matplotlib.axes import Axes

    captured = []
    original = Axes.barh

    def capture(self, *args, **kwargs):
        bars = original(self, *args, **kwargs)
        captured.extend(bars)
        return bars

    monkeypatch.setattr(Axes, "barh", capture)
    chart = Funnel(
        [f"Stage {i}" for i in range(len(values))], values, show_labels=show_labels
    )
    svg = render_svg(payload(chart), 600, 350, "chart")
    assert [bar.get_x() for bar in captured] == [-v / 2 for v in values]
    assert [bar.get_width() for bar in captured] == values
    assert "Stage 0" in svg


def test_gallery_pdf_vector_text_and_series_colors():
    report = build_report()
    pdf = PdfReader(io.BytesIO(report.to_pdf(renderer=WeasyPrintRenderer())))
    assert len(pdf.pages) == 1 and not pdf.pages[0].images
    text = pdf.pages[0].extract_text()
    for label in [
        "Previous",
        "Current",
        "Resolved",
        "Escalated",
        "Voice",
        "Chat",
        "Contacted",
        "Converted",
        "335",
        "125",
        "145",
    ]:
        assert label in text
    html = report.to_html(renderer=WeasyPrintRenderer())
    assert "<script" not in html and "Plotly" not in html
    for color in series_colors(report.theme)[:2]:
        assert color in html
    assert html.count('data-legend-count="2"') == 3
    chromium_html = report.to_html(renderer=ChromiumRenderer())
    assert "data-legend-count=" not in chromium_html


@pytest.mark.parametrize(
    "axes,legend,series",
    [
        (True, True, {"A": [None, 2, None], "B": [1, None, 3]}),
        (True, True, {"A": [None] * 3, "B": [1, 2, 3]}),
        (True, True, {"A": [None] * 3, "B": [None] * 3}),
        (False, True, {"A": [1, 2, 3], "B": [3, 2, 1]}),
        (False, False, {"A": [1, 2, 3], "B": [3, 2, 1]}),
        (False, True, {"A": [None] * 3, "B": [None] * 3}),
    ],
)
def test_multiseries_lines_dates_gaps_and_hidden_axes(axes, legend, series):
    chart = LineChart(
        [date(2026, 11, i) for i in [1, 2, 3]],
        series=series,
        x_kind="date",
        axes=axes,
        legend=legend,
        markers=False,
    )
    text = render(chart)
    if not axes and all(v is None for values in series.values() for v in values):
        assert "No data" in text
    elif legend:
        assert "A" in text and "B" in text


def test_max_series_and_literal_legend():
    names = ["<b>&amp; $x$ Пример", *[f"Channel {i}" for i in range(7)]]
    text = render(
        BarChart(
            ["A", "B"], series={name: [i + 1, i + 2] for i, name in enumerate(names)}
        )
    )
    for name in names:
        assert name in text


def test_legend_overflow_preserves_file(tmp_path):
    report = Report(page=Page(size=(100, 100))).row(
        Card(LineChart(["A"], series={str(i) + "W" * 99: [1] for i in range(8)})),
        height_mm=45,
    )
    destination = tmp_path / "keep.pdf"
    destination.write_bytes(b"original")
    with pytest.raises(LayoutOverflowError):
        report.write_pdf(destination, renderer=WeasyPrintRenderer(), overwrite=True)
    assert destination.read_bytes() == b"original"


def test_stacked_labels_fit_and_tiny_segment_fails():
    chart = BarChart(
        ["A"], series={"First": [100], "Second": [50]}, mode="stacked", show_labels=True
    )
    text = render(chart)
    assert "100" in text and "50" in text
    with pytest.raises(LayoutOverflowError, match="stacked value label"):
        render_svg(
            payload(
                BarChart(
                    ["A"],
                    series={"First": [100], "Second": [0.001]},
                    mode="stacked",
                    show_labels=True,
                )
            ),
            600,
            350,
            "chart",
        )
    # A zero at the outer edge may be labelled outside; coincident labels fail.
    render_svg(
        payload(
            BarChart(
                ["A"],
                series={"First": [100], "Second": [0]},
                mode="stacked",
                show_labels=True,
            )
        ),
        600,
        350,
        "chart",
    )
    with pytest.raises(LayoutOverflowError, match="overlap"):
        render_svg(
            payload(
                BarChart(
                    ["A"],
                    series={"First": [0], "Second": [0]},
                    mode="stacked",
                    show_labels=True,
                )
            ),
            600,
            350,
            "chart",
        )


def test_grouped_label_cannot_cover_neighbor():
    spec = payload(
        BarChart(["A"], series={"First": [1], "Second": [10]}, show_labels=True)
    )
    spec["series"][0]["value_labels"] = ["a long value label"]
    with pytest.raises(LayoutOverflowError, match="another bar"):
        render_svg(spec, 250, 300, "chart")


@pytest.mark.parametrize(
    "chart",
    [
        Funnel([], []),
        Funnel(["Only"], [0]),
        Funnel(["Zero", "End"], [0, 0], show_labels=False),
    ],
)
def test_empty_and_zero_funnel_pdf(chart):
    text = render(chart)
    assert ("No data" if not chart.labels else chart.labels[0]) in text


def test_yaml_template_and_data_multiseries_funnel():
    from cardreport import Dataset, ReportTemplate, datasets_from_yaml, datasets_to_yaml

    spec = {
        "format": "cardreport.template/1",
        "datasets": {
            "items": {
                "cardinality": "many",
                "fields": {
                    "name": {"type": "text"},
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
            }
        },
        "report": {
            "page": {"size": [300, 230]},
            "blocks": [
                {
                    "type": "row",
                    "height_mm": 100,
                    "children": [
                        {
                            "type": "bar",
                            "dataset": "items",
                            "category": "name",
                            "series": [
                                {"field": "a", "label": "First"},
                                {"field": "b", "label": "Second"},
                            ],
                        },
                        {
                            "type": "line",
                            "dataset": "items",
                            "x": "name",
                            "series": [
                                {"field": "a", "label": "First"},
                                {"field": "b", "label": "Second"},
                            ],
                        },
                        {
                            "type": "funnel",
                            "dataset": "items",
                            "category": "name",
                            "value": "a",
                        },
                    ],
                }
            ],
        },
    }
    template = ReportTemplate.from_yaml(
        ReportTemplate.from_json(json.dumps(spec)).to_yaml()
    )
    data = datasets_from_yaml(
        datasets_to_yaml(
            {"items": Dataset(["name", "a", "b"], [["Start", 10, 8], ["End", 5, 4]])}
        )
    )
    result = PdfReader(
        io.BytesIO(template.bind(data).to_pdf(renderer=WeasyPrintRenderer()))
    )
    assert len(result.pages) == 1
    text = result.pages[0].extract_text()
    assert "First" in text and "Second" in text and "Start" in text and "End" in text


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
@pytest.mark.parametrize("values", [[100, 0, 100], [-100, 0], [100, -40, 20]])
def test_stacked_label_cannot_cover_other_segment(orientation, values):
    chart = BarChart(
        ["A"],
        series={f"Series {i}": [v] for i, v in enumerate(values)},
        mode="stacked",
        show_labels=True,
        orientation=orientation,
    )
    with pytest.raises(LayoutOverflowError, match="overlap"):
        render_svg(payload(chart), 600, 350, "chart")


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
def test_negative_stacked_labels_fit_nonoverlapping_segments(orientation):
    chart = BarChart(
        ["A"],
        series={"First": [-100], "Second": [-50]},
        mode="stacked",
        show_labels=True,
        orientation=orientation,
    )
    assert "-100" in render_svg(payload(chart), 600, 350, "chart")


@pytest.mark.filterwarnings("ignore:constrained_layout not applied:UserWarning")
def test_funnel_long_value_label_overflow():
    from cardreport import Currency

    chart = Funnel(["Stage"], [400_000_000_000_000], value_format=Currency("USD"))
    with pytest.raises(LayoutOverflowError, match="label"):
        render_svg(payload(chart), 250, 300, "chart")


def test_dense_grouped_values_fail_without_shrinking():
    chart = BarChart(
        ["A", "B", "C"],
        series={str(i): [1001, 1002, 1003] for i in range(8)},
        show_labels=True,
    )
    with pytest.raises(LayoutOverflowError):
        render_svg(payload(chart), 350, 300, "chart")
