"""Display zones must never change instants or calendar-date semantics."""

import io
import json
from datetime import UTC, date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from jsonschema import Draft202012Validator
from pypdf import PdfReader

from cardreport import (
    KPI,
    BarChart,
    Card,
    Dataset,
    DatasetSchema,
    FieldSpec,
    Formatting,
    LineChart,
    Report,
    ReportTemplate,
    Table,
    TableColumn,
    TemplateError,
    ValidationError,
    datasets_from_json,
    datasets_from_yaml,
    datasets_to_json,
)
from cardreport.adapters.csv import from_csv
from cardreport.charts import chart_spec
from cardreport.model import format_value
from cardreport.schemas import json_schema
from cardreport.validation import validate_report
from cardreport.weasyprint import WeasyPrintRenderer
from tests.test_text_templates import data, definition


@pytest.mark.parametrize("suffix", ["", "Z", "+03:00"])
@pytest.mark.parametrize("zone", [None, "UTC", "Asia/Nicosia"])
def test_datetime_contract_matrix(suffix, zone):
    value = datetime.fromisoformat("2026-11-14T00:30:00" + suffix)
    source = value.replace(tzinfo=UTC) if not suffix else value
    expected = source if zone is None else source.astimezone(ZoneInfo(zone))
    assert format_value(value, timezone=zone) == expected.isoformat()
    assert format_value(value, "date", timezone=zone) == expected.date().isoformat()
    settings = Formatting(
        datetime_format="yyyy-MM-dd HH:mm XXX", date_format="yyyy-MM-dd"
    )
    assert (
        format_value(value, "date", settings, timezone=zone)
        == expected.date().isoformat()
    )
    doc = validate_report(
        Report(timezone=zone, formatting=settings).add(KPI("Time", value))
    )
    assert doc.timezone == zone
    assert (
        expected.strftime("%Y-%m-%d %H:%M")
        in Report(timezone=zone, formatting=settings)
        .add(Table([TableColumn("at", "Time")], [{"at": value}]))
        .to_html()
    )
    spec = definition("{{ datasets.summary.time | datetime('yyyy-MM-dd HH:mm XXX') }}")
    if zone is not None:
        spec["report"]["timezone"] = zone
    spec["report"]["subtitle"] = "{{ datasets.summary.time | date('yyyy-MM-dd') }}"
    report = ReportTemplate(spec).bind(data(time=value))
    assert report.title == format_value(value, formatting=settings, timezone=zone)
    assert report.subtitle == expected.date().isoformat()


@pytest.mark.parametrize("zone", [None, "UTC", "Asia/Nicosia", "America/Los_Angeles"])
def test_calendar_dates_never_shift(zone):
    value = date(2026, 11, 14)
    assert format_value(value, timezone=zone) == "2026-11-14"
    assert (
        format_value(value, "date", Formatting(date_format="dd.MM.yyyy"), timezone=zone)
        == "14.11.2026"
    )


@pytest.mark.parametrize(
    "zone",
    [
        "",
        "No/Such_Zone",
        "localtime",
        "Factory",
        "posixrules",
        "europe/berlin",
        "right/UTC",
        "../UTC",
        "/etc/passwd",
        1,
        [],
    ],
)
def test_invalid_zone_and_mutated_report(zone):
    with pytest.raises(ValidationError, match="timezone"):
        Report(timezone=zone)
    report = Report()
    report.timezone = zone
    with pytest.raises(ValidationError, match="timezone"):
        report.validate()
    spec = definition()
    spec["report"]["timezone"] = zone
    with pytest.raises(TemplateError) as caught:
        ReportTemplate(spec)
    assert "timezone" in caught.value.template_path


@pytest.mark.parametrize("suffix", ["", "Z", "+03:00"])
def test_transport_offset_preservation_and_naive_utc(tmp_path, suffix):
    text = "2026-11-14T00:30:00" + suffix
    native = datetime.fromisoformat(text)
    expected = native if suffix else native.replace(tzinfo=UTC)
    payload = {
        "format": "cardreport.data/1",
        "datasets": {
            "summary": {
                "columns": ["at"],
                "rows": [{"at": {"$type": "datetime", "value": text}}],
            }
        },
    }
    Draft202012Validator(json.loads(json_schema("data"))).validate(payload)
    csv = tmp_path / "summary.csv"
    csv.write_text("at\n" + text + "\n")
    schema = DatasetSchema({"at": FieldSpec("datetime")})
    yaml = f"format: cardreport.data/1\ndatasets:\n  summary:\n    columns: [at]\n    rows:\n      - at: {text}\n"
    for ds in (
        Dataset.single({"at": native}),
        datasets_from_json(json.dumps(payload))["summary"],
        datasets_from_yaml(yaml)["summary"],
        from_csv(csv, schema=schema),
    ):
        value = ds.rows[0][0]
        assert value.isoformat() == expected.isoformat()
        assert expected.isoformat() in datasets_to_json({"summary": ds})


def test_pandas_naive_is_utc():
    pd = pytest.importorskip("pandas")
    from cardreport.adapters.pandas import from_pandas

    ds = from_pandas(
        pd.DataFrame({"at": [pd.Timestamp("2026-11-14T00:30:00")]}),
        schema=DatasetSchema({"at": FieldSpec("datetime")}),
    )
    assert ds.rows[0][0].isoformat() == "2026-11-14T00:30:00+00:00"


@pytest.mark.parametrize("zone", [None, "UTC", "Asia/Nicosia"])
@pytest.mark.parametrize(
    "formatting", [None, Formatting(datetime_format="dd.MM HH:mm XXX")]
)
def test_chart_coordinates_are_independent_of_display_zone(zone, formatting):
    values = [
        datetime.fromisoformat(v)
        for v in ("2026-11-14T00:30:00+03:00", "2026-11-13T23:30:00+01:00")
    ]
    chart = LineChart(values, [1, 2], x_kind="date", fill="zero")
    report = Report(timezone=zone, formatting=formatting).row(Card(chart), height_mm=80)
    doc = validate_report(report)
    normalized = doc.charts["blocks.0.0.content"]
    assert normalized.labels == (
        "2026-11-13T21:30:00+00:00",
        "2026-11-13T22:30:00+00:00",
    )
    expected = tuple(
        format_value(v, formatting=formatting, timezone=zone) for v in values
    )
    assert normalized.tick_labels == expected
    spec = chart_spec(chart, doc.theme, "blocks.0.0.content", normalized, formatting)
    assert spec["layout"]["xaxis"]["ticktext"] == list(expected)
    assert spec["layout"]["xaxis"]["tickvals"] == list(normalized.labels)
    bars = validate_report(
        Report(timezone=zone, formatting=formatting).add(BarChart(values, [1, 2]))
    )
    assert bars.charts["blocks.0"].category_labels == expected


def test_dst_fold_stays_two_distinct_instants():
    values = [
        datetime.fromisoformat(v)
        for v in ("2026-10-25T00:30:00Z", "2026-10-25T01:30:00Z")
    ]
    report = Report(
        timezone="Europe/Berlin", formatting=Formatting(datetime_format="HH:mm XXX")
    )
    report.add(LineChart(values, [1, 2], x_kind="date", fill="zero"))
    chart = validate_report(report).charts["blocks.0"]
    assert chart.tick_labels == ("02:30 +02:00", "02:30 +01:00")
    assert chart.labels[0] != chart.labels[1]
    spring = datetime.fromisoformat("2026-03-29T01:30:00Z")
    assert format_value(spring, timezone="Europe/Berlin") == "2026-03-29T03:30:00+02:00"
    naive = datetime(2026, 11, 14)
    for chart in (
        BarChart([naive, naive.replace(tzinfo=UTC)], [1, 2]),
        LineChart([naive, naive.replace(tzinfo=UTC)], [1, 2], x_kind="date"),
    ):
        with pytest.raises(ValidationError, match="duplicate"):
            Report().add(chart).validate()


def test_datetime_filter_default_null_and_pattern_validation():
    spec = definition("{{ datasets.summary.time | datetime }}")
    spec["report"]["timezone"] = "UTC"
    spec["datasets"]["summary"]["fields"]["time"]["nullable"] = True
    template = ReportTemplate(spec)
    assert template.bind(data()).title == "13.11.2026 22:30"
    assert template.bind(data(time=None)).title == "—"
    for expression in (
        "{{ datasets.summary.day | datetime }}",
        "{{ datasets.summary.total | datetime }}",
        "{{ datasets.summary.time | datetime('unquoted') }}",
        "{{ datasets.summary.time | datetime('yyyy', 'HH') }}",
        "{{ datasets.summary.time | datetime(pattern='yyyy') }}",
    ):
        with pytest.raises(TemplateError) as caught:
            ReportTemplate(definition(expression))
        assert caught.value.template_path == "report.title"


def test_zone_conversion_overflow_is_validation_error():
    with pytest.raises(ValidationError, match="range"):
        format_value(datetime(1, 1, 1, tzinfo=UTC), timezone="America/New_York")
    value = datetime(2026, 11, 14, tzinfo=UTC)
    assert (
        format_value(
            value,
            formatting=Formatting(date_format="yyyy-MM-dd"),
            timezone="Asia/Nicosia",
        )
        == "2026-11-14 02:00:00+02:00"
    )


@pytest.mark.parametrize("renderer", [None, WeasyPrintRenderer()])
def test_both_engines_timezone_text_table_bar_and_line(renderer):
    values = [
        datetime(2026, 11, 14, h, 30, tzinfo=timezone(timedelta(hours=3)))
        for h in (0, 1)
    ]
    spec = definition("At {{ datasets.summary.time | datetime('dd.MM HH:mm') }}")
    spec["report"]["timezone"] = "Asia/Nicosia"
    report = ReportTemplate(spec).bind(data(time=values[0]))
    report.formatting = Formatting(
        datetime_format="dd.MM HH:mm", date_format="dd.MM.yyyy"
    )
    report.add(Table([TableColumn("at", "Recorded at")], [{"at": values[0]}]))
    report.row(Card(BarChart(values, [1, 2])), height_mm=65)
    report.row(Card(LineChart(values, [1, 2], x_kind="date")), height_mm=65)
    pdf = report.to_pdf(renderer=renderer, timeout=90)
    text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "At 13.11 23:30" in text
    assert text.count("13.11 23:30") >= 4  # Heading, table, bars and date line.
    assert text.count("14.11 00:30") >= 2


@pytest.mark.parametrize("value", ["2026-11-14T12:45:59", "2026-11-14T12:45:59.123456"])
def test_naive_fractional_parser(value):
    from cardreport._inputs import parse_scalar

    parsed = parse_scalar(value, "datetime")
    assert Dataset.single({"at": parsed}).rows[0][0].isoformat() == value + "+00:00"


@pytest.mark.parametrize(
    "value",
    ["2026-11-14T12:45:59+24:00", "2026-11-14T12:45:59+00:60", "2026-11-14T12:45:59z"],
)
def test_invalid_offsets_still_rejected(value):
    from cardreport._inputs import parse_scalar

    with pytest.raises(ValueError):
        parse_scalar(value, "datetime")


def test_half_hour_zone_and_named_zone_patterns():
    value = datetime(2026, 11, 14, 1, 30, tzinfo=UTC)
    assert (
        format_value(value, timezone="America/St_Johns") == "2026-11-13T22:00:00-03:30"
    )
    assert (
        format_value(
            value,
            formatting=Formatting(datetime_format="VV XXX"),
            timezone="Asia/Nicosia",
        )
        == "Asia/Nicosia +02:00"
    )


def test_default_date_ticks_do_not_collide_with_numeric_axis():
    from examples.series_report import build_report

    # With automatic Plotly ticks removed, the first full ISO date extends left.
    pdf = build_report().to_pdf(timeout=90)
    text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "2026-11-01" in text


@pytest.mark.parametrize("renderer", [None, WeasyPrintRenderer()])
def test_narrow_default_datetime_labels_have_checked_engine_outcomes(renderer):
    from cardreport import LayoutOverflowError, Text

    values = [datetime(2026, 11, 14, h, tzinfo=UTC) for h in range(6)]
    report = Report().row(
        Card(LineChart(values, range(6), x_kind="date")),
        Card(Text("Other column")),
        height_mm=80,
    )
    if renderer is None:
        pdf = report.to_pdf(timeout=90)
        text = "".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
        assert "2026-11-14T00:00:00+00:00" in text
    else:
        with pytest.raises(LayoutOverflowError, match="label"):
            report.to_pdf(renderer=renderer, timeout=90)


def test_pure_date_chart_zone_and_date_only_cells():
    values = [date(2026, 11, 14), date(2026, 11, 15)]
    for chart in (BarChart(values, [1, 2]), LineChart(values, [1, 2], x_kind="date")):
        assert (
            validate_report(Report(timezone="America/Los_Angeles").add(chart)).charts
            == validate_report(Report().add(chart)).charts
        )
    value = datetime.fromisoformat("2026-11-14T00:30:00+03:00")
    report = (
        Report(timezone="UTC")
        .add(KPI("Day", value, format="date"))
        .add(Table([TableColumn("at", "Day", format="date")], [{"at": value}]))
    )
    assert report.to_html().count("2026-11-13") == 2
    assert (
        format_value(value, formatting=Formatting(date_format="dd.MM.yyyy"))
        == "14.11.2026 00:30:00+03:00"
    )
    assert (
        format_value(
            value,
            formatting=Formatting(datetime_format="dd MMM HH:mm xxx"),
            timezone="UTC",
        )
        == "13 Nov 21:30 +00:00"
    )
