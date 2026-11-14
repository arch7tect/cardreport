import io
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pypdf import PdfReader

from cardreport import (
    BarChart,
    Card,
    ChromiumRenderer,
    Dataset,
    Formatting,
    LayoutOverflowError,
    Report,
    ReportTemplate,
    TemplateError,
    ValidationError,
    WeasyPrintRenderer,
    datasets_from_json,
    datasets_to_json,
)
from cardreport.charts import chart_spec
from cardreport.validation import validate_report


@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
@pytest.mark.parametrize("mode", ["grouped", "stacked"])
def test_categories_have_distinct_identity_and_literal_strings(orientation, mode):
    labels = [date(2026, 11, 5), date(2026, 11, 4), "noviembre", "2026-11-04"]
    obj = BarChart(
        labels,
        series={"A": [1, 2, 3, 4], "B": [4, 3, 2, 1]},
        orientation=orientation,
        mode=mode,
    )
    report = Report(language="es", formatting=Formatting(date_format="MMMM")).add(obj)
    doc = validate_report(report)
    data = doc.charts["blocks.0"]
    assert data.category_labels == ("noviembre", "noviembre", "noviembre", "2026-11-04")
    assert len(set(data.labels)) == 4
    spec = chart_spec(obj, doc.theme, "blocks.0", data, doc.formatting)
    axis = "y" if orientation == "horizontal" else "x"
    for trace in spec["data"]:
        assert trace[axis] == list(data.labels)
    assert spec["layout"][axis + "axis"]["ticktext"] == list(data.category_labels)
    assert spec["layout"][axis + "axis"]["categoryarray"] == list(data.labels)
    assert spec["categoryCount"] == 4
    assert tuple(labels) == obj.labels


def test_bar_datetime_offset_defaults_validation_and_escaping():
    value = datetime(2026, 11, 4, 23, 30, tzinfo=timezone(timedelta(hours=-2)))
    obj = BarChart([value, date(2026, 11, 5), "2026-11-05"], [1, 2, 3])
    data = validate_report(Report().add(obj)).charts["blocks.0"]
    assert data.category_labels == (
        "2026-11-04T23:30:00-02:00",
        "2026-11-05",
        "2026-11-05",
    )
    doc = validate_report(
        Report(
            formatting=Formatting(
                datetime_format="dd MMM HH:mm", date_format="'<b>' yyyy"
            ),
            language="es",
        ).add(obj)
    )
    assert doc.charts["blocks.0"].category_labels[0] == "04 nov 23:30"
    spec = chart_spec(obj, doc.theme, "blocks.0", doc.charts["blocks.0"])
    assert spec["layout"]["xaxis"]["ticktext"][1] == "&lt;b&gt; 2026"
    for labels, message in [
        ([value, value.astimezone(UTC)], "duplicate"),
        ([date(2026, 11, 4)] * 2, "duplicate"),
        ([42], "expected text"),
    ]:
        with pytest.raises(ValidationError, match=message):
            Report().add(BarChart(labels, [1] * len(labels))).validate()
    with pytest.raises(ValidationError, match="glyph"):
        Report(formatting=Formatting(date_format="'漢' yyyy")).add(obj).validate()


@pytest.mark.parametrize(
    "kind,value",
    [("date", date(2026, 11, 4)), ("datetime", datetime(2026, 11, 4, 12, tzinfo=UTC))],
)
def test_template_date_categories_and_data_roundtrip(kind, value):
    source = {
        "format": "cardreport.template/1",
        "datasets": {
            "d": {
                "cardinality": "many",
                "fields": {"day": {"type": kind}, "n": {"type": "integer"}},
            }
        },
        "report": {
            "language": "es",
            "formatting": {
                "date_format": "dd MMM yyyy",
                "datetime_format": "dd MMM HH:mm",
            },
            "blocks": [
                {"type": "bar", "dataset": "d", "category": "day", "value": "n"}
            ],
        },
    }
    template = ReportTemplate.from_json(ReportTemplate(source).to_json())
    datasets = {"d": Dataset.from_records(["day", "n"], [(value, 2)])}
    before = datasets_to_json(datasets)
    report = template.bind(datasets_from_json(before))
    data = validate_report(report).charts["blocks.0"]
    assert data.category_labels == (
        ("04 nov 2026" if kind == "date" else "04 nov 12:00"),
    )
    assert datasets_to_json(datasets) == before
    assert template.to_dict() == source
    source["report"]["blocks"][0]["type"] = "funnel"
    with pytest.raises(TemplateError, match="incompatible"):
        ReportTemplate(source)


@pytest.mark.parametrize("renderer", [ChromiumRenderer, WeasyPrintRenderer])
@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
def test_pdf_duplicate_date_labels_remain_visible(renderer, orientation):
    report = Report(language="es", formatting=Formatting(date_format="MMMM")).row(
        Card(
            BarChart(
                [date(2026, 11, 4), date(2026, 11, 5)],
                [2, 7],
                orientation=orientation,
                show_labels=True,
            )
        ),
        height_mm=95,
    )
    pdf = PdfReader(io.BytesIO(report.to_pdf(renderer=renderer())))
    text = pdf.pages[0].extract_text()
    assert text.count("noviembre") == 2, text
    assert "2" in text and "7" in text


def test_spanish_fixture_calendar_is_typed_and_formatted():
    examples = Path(__file__).resolve().parents[1] / "examples"
    report = ReportTemplate.from_json(
        (examples / "spanish_template.json").read_bytes()
    ).bind(datasets_from_json((examples / "spanish_data.json").read_bytes()))
    calendar = validate_report(report).charts["blocks.2.0.content"]
    assert calendar.category_labels == ("4 de noviembre de 2026",)


@pytest.mark.parametrize("renderer", [ChromiumRenderer, WeasyPrintRenderer])
def test_formatted_bar_category_overflow_is_rejected(renderer):
    report = Report(formatting=Formatting(date_format="'" + "x" * 120 + "' yyyy"))
    report.row(Card(BarChart([date(2026, 11, 4)], [1])), height_mm=65)
    with pytest.raises(LayoutOverflowError):
        report.to_pdf(renderer=renderer())


def test_formatted_bar_category_length_is_bounded():
    report = Report(formatting=Formatting(date_format="MMMM " * 30)).add(
        BarChart([date(2026, 11, 4)], [1])
    )
    with pytest.raises(ValidationError, match="200"):
        report.validate()


@pytest.mark.parametrize("renderer", [ChromiumRenderer, WeasyPrintRenderer])
def test_typed_bar_defaults_and_literal_escaping(renderer):
    obj = BarChart(
        [date(2026, 11, 4), datetime(2026, 11, 4, tzinfo=UTC), "<x>&"], [1, 2, 3]
    )
    report = Report().row(Card(obj), height_mm=95)
    doc = validate_report(report)
    data = doc.charts["blocks.0.0.content"]
    assert data.category_labels == ("2026-11-04", "2026-11-04T00:00:00+00:00", "<x>&")
    spec = chart_spec(obj, doc.theme, "blocks.0.0.content", data)
    assert spec["layout"]["xaxis"]["ticktext"][2] == "&lt;x&gt;&amp;"
    pdf = PdfReader(io.BytesIO(report.to_pdf(renderer=renderer())))
    text = pdf.pages[0].extract_text()
    for label in data.category_labels:
        assert label in text
