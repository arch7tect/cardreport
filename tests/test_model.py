from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from cardreport import *
from cardreport.model import format_value


def test_formats_and_dates():
    assert format_value(Decimal("2.345"), Currency("USD")) == "USD 2.34"
    assert format_value(0.4, "percent") == "40.0%"
    assert format_value(10000) == "10,000"
    assert format_value(None) == "—"
    assert format_value(date(2026, 11, 4), "date") == "2026-11-04"
    assert format_value(datetime(2026, 1, 1)) == "2026-01-01T00:00:00+00:00"
    assert "+00:00" in format_value(datetime(2026, 1, 1, tzinfo=UTC))


@pytest.mark.parametrize(
    "block",
    [
        Row(),
        Column(),
        Row(Text("x"), widths=[-1]),
        Row(Column(Text("a"), Text("b"), heights=[1, 1])),
        Card(Card(KPI("x", 1))),
        BarChart(["x"], [1, 2]),
        BarChart(["x", "x"], [1, 2]),
        BarChart(["x"], [float("nan")]),
        BarChart(["x"], [True]),
        Funnel(["x"], [-1]),
        Table([TableColumn("x", "X")], [{}]),
        Table([TableColumn("x", "X"), TableColumn("x", "Y")], []),
        Text("x", style="raw"),
        KPI("x", True),
    ],
)
def test_invalid_components(block):
    with pytest.raises(ValidationError):
        Report().add(block).to_html()


def test_defensive_copy_and_no_engine_leak():
    values = [1]
    labels = ["original"]
    rows = [{"x": 2}]
    chart = BarChart(labels, values)
    table = Table([TableColumn("x", "X")], rows)
    values[0] = 99
    labels[0] = "changed"
    rows[0]["x"] = 100
    assert chart.values == (1,) and chart.labels == ("original",)
    assert table.rows[0]["x"] == 2
    with pytest.raises(TypeError):
        table.rows[0]["x"] = 4
    import cardreport

    assert "plotly" not in cardreport.__all__


def test_safe_serialization():
    html = Report().add(BarChart(["</script><b>&amp;"], [1])).to_html()
    assert "</script><b>" not in html
    assert "\\u0026lt;" in html


def test_resource_caps():
    with pytest.raises(ValidationError):
        Report().add(BarChart([str(i) for i in range(31)], list(range(31)))).to_html()
    block = Text("leaf")
    for _ in range(14):
        block = Column(block)
    with pytest.raises(ValidationError):
        Report().add(block).to_html()


def test_design_example_builds():
    report = Report(page=Page(orientation="landscape"))
    report.row(Card(KPI("Clients", 21)), Card(KPI("Answered", 5)))
    report.row(
        Card(Funnel(["Attempted", "Answered"], [21, 5])),
        Column(
            Card(BarChart(["Answer"], [5])),
            Card(KPI("Rate", 0.24, format="percent")),
            heights=[2, 1],
        ),
        widths=[2, 1],
        height_mm=100,
    )
    assert "report-settings" in report.to_html()


@pytest.mark.parametrize(
    "create",
    [
        lambda: BarChart("label", [1]),
        lambda: BarChart(["a"], 1),
        lambda: BarChart(["a"], series=["wrong"]),
        lambda: Table([], ["bad"]),
        lambda: Row(Text("x"), widths=1),
        lambda: Report(page="bad"),
    ],
)
def test_invalid_container_types_are_validation_errors(create):
    with pytest.raises(ValidationError):
        create()


def test_currency_axes_and_numeric_chart_formats():
    from cardreport.charts import chart_spec

    spec = chart_spec(BarChart(["a"], [0.4], value_format="percent"), Theme(), "test")
    assert spec["layout"]["yaxis"]["tickformat"] == ".1%"
    with pytest.raises(ValidationError):
        Report().add(BarChart(["a"], [1], value_format="date")).to_html()


def test_negative_zero_and_custom_orientation():
    assert format_value(-0.001) == "0"
    assert format_value(-0.00001, "percent") == "0.0%"
    with pytest.raises(ValidationError):
        Page(size=(100, 200), orientation="landscape").dimensions()
