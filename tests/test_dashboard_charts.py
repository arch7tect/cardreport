import io
from datetime import UTC, date, datetime, timedelta

import pytest
from pypdf import PdfReader

from cardreport import (
    KPI,
    BarChart,
    Card,
    ChromiumRenderer,
    Column,
    Dataset,
    Formatting,
    LayoutOverflowError,
    LineChart,
    Page,
    Report,
    ReportTemplate,
    Theme,
    ValidationError,
    WeasyPrintRenderer,
)
from cardreport._chart_display import (
    category_colors,
    date_positions,
    marker_sizes,
    segments,
)
from cardreport.charts import chart_spec
from cardreport.validation import validate_report


@pytest.fixture(params=[ChromiumRenderer, WeasyPrintRenderer])
def renderer(request):
    return request.param()


def read_pdf(report, renderer):
    pdf = PdfReader(io.BytesIO(report.to_pdf(renderer=renderer)))
    assert len(pdf.pages) == 1
    assert not pdf.pages[0].images
    return pdf.pages[0].extract_text()


def test_line_segments_and_default_compatibility():
    values = [None, 1, 2, None, -3, None, 4, 5, None]
    assert segments(values) == [[1, 2], [4], [6, 7]]
    assert marker_sizes(values, False) == [0, 0, 0, 0, 6, 0, 0, 0, 0]
    obj = LineChart(
        [str(i) for i in range(9)], values, axes=False, markers=False, fill="zero"
    )
    spec = chart_spec(obj, Theme(), "chart")
    assert len(spec["data"]) == 3
    assert all(trace["cliponaxis"] is False for trace in spec["data"])
    assert [s["x"] for s in spec["data"]] == [["1", "2"], ["4"], ["6", "7"]]
    assert all(s["fill"] == "tozeroy" for s in spec["data"])
    assert spec["categoryCount"] is None
    assert spec["layout"]["yaxis"]["range"][0] < -3
    legacy = chart_spec(LineChart(["a", "b"], [1, 2]), Theme(), "chart")
    assert legacy["data"][0]["mode"] == "lines+markers"
    assert "range" not in legacy["layout"]["yaxis"]
    assert legacy["layout"]["margin"] == {"l": 10, "r": 35, "t": 15, "b": 30}


@pytest.mark.parametrize(
    "chart",
    [
        LineChart(["a"], [1], axes="no"),
        LineChart(["a"], [1], fill=True),
        LineChart(["a"], series={"a": [1], "b": [2]}, fill="zero"),
        BarChart(["a"], [1], color_by="bad"),
        BarChart(["a"], [1], category_labels=False),
        BarChart(["a"], [1], legend_position="left"),
        BarChart(["a"], series={"a": [1], "b": [2]}, color_by="category"),
        LineChart(
            [date(2026, 1, 2), date(2026, 1, 1)], [1, 2], x_kind="date", axes=False
        ),
        LineChart(
            [date(2026, 1, 1), datetime(2026, 1, 1, tzinfo=UTC)],
            [1, 2],
            x_kind="date",
            fill="zero",
        ),
    ],
)
def test_invalid_new_options(chart):
    with pytest.raises(ValidationError):
        Report().add(chart).validate()


def test_utc_positions_and_palette_identity():
    x = date_positions(["2026-11-01", "2026-11-01T12:00:00+00:00", "2026-11-03"])
    assert x[1] - x[0] == 0.5 and x[2] - x[0] == 2
    colors = category_colors(
        BarChart([], [], color_by="category"), Theme(accent="#4263eb"), 8
    )
    assert len(set(colors)) == 8 and colors[0] == "#4263eb"
    with pytest.raises(ValidationError, match="distinct"):
        Report().add(
            BarChart([str(i) for i in range(10)], list(range(10)), color_by="category")
        ).validate()


@pytest.mark.parametrize(
    "values",
    [
        [1, 2, None, -1, None, 3, 4, None],
        [2] * 8,
        [None] * 8,
        [None, None, 2, None, None, None, None, None],
    ],
)
def test_compact_lines_in_kpi_cards(renderer, values):
    days = [date(2026, 11, 1) + timedelta(days=i) for i in range(8)]
    report = Report(theme=Theme(kpi_value_size_pt=32)).row(
        Card(
            Column(
                KPI("Sessions", 58837),
                LineChart(
                    days, values, x_kind="date", axes=False, markers=False, fill="zero"
                ),
                heights=[2, 1],
            )
        ),
        height_mm=52,
    )
    text = read_pdf(report, renderer)
    assert "58,837" in text and "Sessions" in text
    if all(v is None for v in values):
        assert "No data" in text
    else:
        assert "No data" not in text and "Nov" not in text


def test_single_point_compact_and_too_small_tracks(renderer):
    chart = LineChart(["only"], [2], axes=False, markers=False)
    report = Report().row(Card(chart), height_mm=25)
    read_pdf(report, renderer)
    with pytest.raises(LayoutOverflowError):
        Report().row(Card(chart), height_mm=12).to_pdf(renderer=renderer)
    with pytest.raises(LayoutOverflowError):
        Report(page=Page(size=(100, 100)), empty_text="Long empty message " * 20).row(
            Card(LineChart([], [], axes=False)), height_mm=25
        ).to_pdf(renderer=renderer)


def test_full_line_dates_gaps_and_labels(renderer):
    days = [date(2026, 11, 1) + timedelta(days=i) for i in range(8)]
    report = Report(
        language="es",
        formatting=Formatting(date_format="dd MMM"),
        page=Page(orientation="landscape"),
    ).row(
        Card(
            LineChart(
                days, [None, 1, 2, None, -1, 3, 2, None], x_kind="date", fill="zero"
            )
        ),
        height_mm=95,
    )
    text = read_pdf(report, renderer)
    assert "01 nov" in text and "08 nov" in text
    text = read_pdf(
        Report().row(Card(LineChart(["<A>&", "B"], [1, 2])), height_mm=70), renderer
    )
    assert "<A>&" in text and "B" in text


@pytest.mark.parametrize(
    "position,orientation",
    [("left", "vertical"), ("bottom", "vertical"), ("left", "horizontal")],
)
def test_category_legend_pdf_labels_and_colors(renderer, position, orientation):
    chart = BarChart(
        ["<Sales A>&", "Sales B", "Sales C"],
        [10, 20, 15],
        orientation=orientation,
        color_by="category",
        legend_position=position,
        category_labels=False,
        show_labels=True,
    )
    report = Report().row(Card(chart), height_mm=90)
    text = read_pdf(report, renderer)
    assert text.count("<Sales A>&") == 1 and text.count("Sales B") == 1
    assert "20" in text
    spec = chart_spec(chart, report.theme, "chart")
    assert len(spec["data"]) == 1
    assert len(set(spec["data"][0]["marker"]["color"])) == 3
    assert spec["categoryCount"] is None


def test_legend_and_large_kpi_overflow(renderer):
    with pytest.raises(LayoutOverflowError):
        Report(page=Page(size=(120, 120))).row(
            Card(
                BarChart(
                    ["Long category " * 12, "B"],
                    [1, 2],
                    color_by="category",
                    legend_position="left",
                    category_labels=False,
                )
            ),
            height_mm=45,
        ).to_pdf(renderer=renderer)
    with pytest.raises(LayoutOverflowError):
        Report(page=Page(size=(100, 100)), theme=Theme(kpi_value_size_pt=60)).row(
            Card(KPI("Amount", 1234567890)), height_mm=70
        ).to_pdf(renderer=renderer)


def test_new_template_options_match_python():
    source = {
        "format": "cardreport.template/1",
        "datasets": {
            "trend": {
                "cardinality": "many",
                "fields": {
                    "day": {"type": "date"},
                    "n": {"type": "number", "nullable": True},
                },
            }
        },
        "report": {
            "theme": {"kpi_value_size_pt": 36},
            "blocks": [
                {
                    "type": "line",
                    "dataset": "trend",
                    "x": "day",
                    "value": "n",
                    "x_kind": "date",
                    "axes": False,
                    "markers": False,
                    "fill": "zero",
                }
            ],
        },
    }
    template = ReportTemplate(source)
    dataset = Dataset.from_records(
        ["day", "n"], [(date(2026, 11, 1), 1), (date(2026, 11, 2), None)]
    )
    report = template.bind({"trend": dataset})
    obj = report.blocks[0]
    assert obj == LineChart(
        [date(2026, 11, 1), date(2026, 11, 2)],
        [1, None],
        x_kind="date",
        axes=False,
        markers=False,
        fill="zero",
    )
    assert report.theme.kpi_value_size_pt == 36
    assert template.to_dict() == source
    assert validate_report(report).charts["blocks.0"].tick_labels == (
        "2026-11-01",
        "2026-11-02",
    )


def test_exact_chronology_and_located_palette_error():
    start = datetime(2500, 1, 1, tzinfo=UTC)
    Report().add(
        LineChart(
            [start, start + timedelta(microseconds=1)],
            [1, 2],
            x_kind="date",
            axes=False,
        )
    ).validate()
    with pytest.raises(ValidationError, match=r"blocks.0.color_by"):
        Report().add(
            BarChart([str(i) for i in range(10)], list(range(10)), color_by="category")
        ).validate()
    spec = chart_spec(
        LineChart(["a"], series={"A": [1], "B": [2]}), Theme(accent="#4263eb"), "chart"
    )
    assert spec["data"][0]["line"]["color"] != spec["data"][1]["line"]["color"]


def test_category_fill_keeps_missing_end_categories(renderer):
    report = Report().row(
        Card(LineChart(["Start", "Middle", "End"], [None, 3, None], fill="zero")),
        height_mm=70,
    )
    text = read_pdf(report, renderer)
    assert all(label in text for label in ("Start", "Middle", "End"))


def test_single_date_filled_chart_and_default_svg_ticks(renderer):
    report = Report().row(
        Card(LineChart([date(2026, 11, 4)], [3], x_kind="date", fill="zero")),
        height_mm=70,
    )
    read_pdf(report, renderer)
    spec = chart_spec(report.blocks[0].children[0].content, Theme(), "chart")
    assert (
        spec["layout"]["xaxis"]["range"][1] - spec["layout"]["xaxis"]["range"][0]
        == 86400000
    )


def test_compact_edge_markers_and_legend_swatches_are_vector(renderer):
    import pdfplumber

    report = Report().row(
        Card(
            LineChart(
                ["first", "gap", "last"], [1, None, -1], axes=False, markers=False
            )
        ),
        height_mm=19,
    )
    data = report.to_pdf(renderer=renderer)
    if isinstance(renderer, WeasyPrintRenderer):
        import re
        from xml.etree import ElementTree as ET

        svg = ET.fromstring(
            re.search(r"<svg.*?</svg>", report.to_html(renderer=renderer), re.S).group()
        )
        scatter = next(
            node
            for node in svg.iter()
            if node.get("id", "").startswith("PathCollection")
        )
        assert all("clip-path" not in node.attrib for node in scatter.iter())
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        accent = (32 / 255, 166 / 255, 196 / 255)
        points = [
            c
            for c in pdf.pages[0].curves
            if c["fill"]
            and c["non_stroking_color"]
            and len(c["non_stroking_color"]) == 3
            and all(
                abs(a - b) < 0.01
                for a, b in zip(c["non_stroking_color"], accent, strict=True)
            )
        ]
        assert len(points) == 2
        assert all(p["width"] >= 4 and p["height"] >= 4 for p in points)
    report = Report().row(
        Card(BarChart(["A", "B"], [1, 2], color_by="category", category_labels=False)),
        height_mm=70,
    )
    with pdfplumber.open(io.BytesIO(report.to_pdf(renderer=renderer))) as pdf:
        swatches = [
            shape
            for shape in [*pdf.pages[0].rects, *pdf.pages[0].curves]
            if shape["fill"] and 10 < shape["width"] < 13 and 7 < shape["height"] < 10
        ]
        assert len(swatches) >= 2


def test_bottom_legend_overflow(renderer):
    report = Report(page=Page(size=(120, 120))).row(
        Card(
            BarChart(
                ["Long name " * 15, "Other name " * 15],
                [1, 2],
                color_by="category",
                category_labels=False,
            )
        ),
        height_mm=50,
    )
    with pytest.raises(LayoutOverflowError):
        report.to_pdf(renderer=renderer)
