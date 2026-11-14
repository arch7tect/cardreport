import io
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pypdf import PdfReader

from cardreport import (
    KPI,
    BarChart,
    Card,
    ChromiumRenderer,
    Currency,
    Formatting,
    LineChart,
    Page,
    Report,
    ReportTemplate,
    Table,
    TableColumn,
    TemplateError,
    ValidationError,
    WeasyPrintRenderer,
)
from cardreport.charts import chart_spec
from cardreport.model import format_value
from cardreport.validation import validate_report


def test_number_formats_and_rounding():
    f = Formatting(
        decimal=",",
        group="space",
        number_decimals=3,
        percent_decimals=2,
        currency_decimals=3,
    )
    assert format_value(Decimal("1234.5000"), formatting=f) == "1\u00a0234,5"
    assert format_value(Decimal("2.3455"), Currency("EUR"), f) == "EUR 2,346"
    assert format_value(Decimal("2.3445"), Currency("EUR"), f) == "EUR 2,344"
    assert format_value(0.12345, "percent", f) == "12,34%"
    assert format_value(-0.00001, "percent", f) == "0,00%"
    assert format_value(12345, "integer", f) == "12\u00a0345"
    assert (
        format_value(1234.5, formatting=Formatting(decimal=",", group=".")) == "1.234,5"
    )
    assert (
        format_value(1234.5, formatting=Formatting(group="none", number_decimals=0))
        == "1234"
    )
    assert format_value(None, formatting=f) == "—"
    assert format_value("1.234,5", formatting=f) == "1.234,5"
    assert (
        format_value(10**15, Currency("EUR"), Formatting(currency_decimals=6))
        == "EUR 1,000,000,000,000,000.000000"
    )
    with pytest.raises(FrozenInstanceError):
        f.decimal = "."


@pytest.mark.parametrize(
    "kwargs",
    [
        {"decimal": ","},
        {"group": "<>"},
        {"number_decimals": True},
        {"currency_decimals": 7},
        {"percent_decimals": -1},
        {"number_decimals": 2.5},
        {"date_format": "yyyy 'oops"},
        {"date_format": "HH:mm"},
        {"datetime_format": "VVVVV"},
        {"date_format": "g"},
        {"datetime_format": "O"},
        {"datetime_format": "yyyy-MM-ddTHH:mm"},
        {"date_format": "x" * 201},
    ],
)
def test_invalid_formatting(kwargs):
    with pytest.raises(ValidationError):
        Formatting(**kwargs)


def test_dates_locale_and_lossless_default_time():
    v = datetime(2026, 11, 4, 23, 30, 45, 123456, tzinfo=timezone(timedelta(hours=-2)))
    f = Formatting(date_format="d 'de' MMMM 'de' yyyy")
    assert format_value(v, "date", f, "es-MX") == "4 de noviembre de 2026"
    assert (
        format_value(v, "number", f, "es-MX")
        == "4 de noviembre de 2026 23:30:45.123456-02:00"
    )
    assert format_value(v, formatting=Formatting()) == v.isoformat()
    assert (
        format_value(
            v, formatting=Formatting(datetime_format="yyyy-MM-dd HH:mm:ss.SSSSSS XXX")
        )
        == "2026-11-04 23:30:45.123456 -02:00"
    )
    assert (
        format_value(
            date(2026, 11, 4),
            formatting=Formatting(date_format="MMMM", locale="fr"),
            language="en",
        )
        == "novembre"
    )
    assert format_value(v, "date", Formatting(datetime_format="HH:mm")) == "2026-11-04"
    with pytest.raises(ValidationError):
        Report(language="xx", formatting=f).validate()
    # Metadata accepts private-use and unknown languages, independently of Babel.
    assert validate_report(Report(language="x-project")).language == "x-project"
    assert validate_report(Report(language="xx")).language == "xx"


@pytest.mark.parametrize(
    "tag", ["de-DE", "fr-CA", "pt-BR", "zh-Hant-TW", "es-MX-u-nu-latn"]
)
def test_language_not_limited_to_translations(tag):
    assert f'lang="{tag}"' in Report(language=tag).to_html()


def test_empty_text_resolution_and_hostile_metadata():
    table = Table([TableColumn("n", "N")], [])
    assert "Sin datos" in Report(language="es-MX").add(table).to_html()
    assert "Нет данных" in Report(language="ru").add(table).to_html()
    assert "No data" in Report(language="pt-BR").add(table).to_html()
    assert (
        "Sem dados"
        in Report(language="pt-BR", empty_text="Sem dados")
        .add(BarChart([], []))
        .to_html()
    )
    html = Report(language="es", empty_text="<vacío>").add(table).to_html()
    assert "&lt;vacío&gt;" in html
    assert (
        "Sin datos"
        not in Report(language="es")
        .add(Table(table.columns, [], empty_text=""))
        .to_html()
    )
    with pytest.raises(ValidationError):
        Report(language='en" onclick="bad')
    report = Report()
    report.language = "bad<script>"
    with pytest.raises(ValidationError):
        report.to_html()


@pytest.mark.parametrize("n", [1, 2, 6, 7, 500])
def test_date_axis_coordinates_sampling_and_glyph_validation(n):
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(n)]
    obj = LineChart(dates, list(range(n)), x_kind="date")
    report = Report(
        language="es", formatting=Formatting(date_format="dd MMM yyyy")
    ).add(obj)
    doc = validate_report(report)
    chart = doc.charts["blocks.0"]
    assert chart.labels == tuple(d.isoformat() for d in dates)
    assert len(chart.tick_values) == min(n, 6)
    assert chart.tick_values[0] == dates[0].isoformat()
    assert chart.tick_values[-1] == dates[-1].isoformat()
    spec = chart_spec(obj, doc.theme, "blocks.0", chart, doc.formatting)
    assert spec["layout"]["xaxis"]["type"] == "date"
    assert spec["layout"]["xaxis"]["tickvals"] == list(chart.tick_values)
    assert spec["categoryCount"] == min(n, 6)
    with pytest.raises(ValidationError, match="glyph"):
        Report(formatting=Formatting(date_format="'漢' yyyy")).add(obj).validate()


def test_axes_default_and_explicit_settings():
    obj = BarChart(["A"], [1234])
    doc = validate_report(Report().add(obj))
    legacy = chart_spec(obj, doc.theme, "blocks.0", doc.charts["blocks.0"])
    assert "tickformat" not in legacy["layout"]["yaxis"]
    for group, flag in [("none", ""), ("space", ",")]:
        f = Formatting(decimal=",", group=group, number_decimals=3)
        spec = chart_spec(obj, doc.theme, "blocks.0", formatting=f)
        assert spec["layout"]["yaxis"]["tickformat"] == flag + ".3~f"
        assert spec["layout"]["separators"][0] == ","


def template(**settings):
    return {
        "format": "cardreport.template/1",
        "datasets": {},
        "report": {"blocks": [], **settings},
    }


def test_template_extended_without_new_version():
    original = template()
    assert ReportTemplate(original).to_dict() == original
    for settings in [
        {},
        {"formatting": {}},
        {
            "language": "es-MX",
            "empty_text": "Nada",
            "formatting": {"date_format": "dd/MM/yyyy", "number_decimals": 3},
        },
    ]:
        source = template(**settings)
        parsed = ReportTemplate.from_json(ReportTemplate(source).to_json())
        assert parsed.to_dict() == source
        report = parsed.bind({})
        assert (report.formatting is None) == ("formatting" not in settings)
        report.validate()
    for settings in [
        {"language": 3},
        {"formatting": None},
        {"formatting": {"number_decimals": True}},
        {"formatting": {"unknown": 1}},
    ]:
        with pytest.raises(TemplateError):
            ReportTemplate(template(**settings))
    with pytest.raises(TemplateError) as error:
        ReportTemplate(template(formatting={"date_format": "HH"}))
    assert error.value.template_path == "report.formatting.date_format"


@pytest.mark.parametrize("renderer", [ChromiumRenderer, WeasyPrintRenderer])
def test_localized_rendering_and_settings_isolation(renderer):
    def build(language, f):
        return (
            Report(
                "Información / Отчёт",
                page=Page(orientation="landscape"),
                language=language,
                formatting=f,
            )
            .row(
                Card(KPI("Importe", Decimal("1234.5"))),
                Card(Table([TableColumn("d", "Fecha")], [{"d": date(2026, 11, 4)}])),
                height_mm=40,
            )
            .row(
                Card(BarChart(["España", "Россия"], [1000, 2000], show_labels=True)),
                height_mm=75,
            )
            .row(Card(Table([TableColumn("x", "Estado")], [])), height_mm=30)
        )

    for language, f, expected in [
        (
            "es-MX",
            Formatting(decimal=",", group=".", date_format="d 'de' MMMM 'de' yyyy"),
            ["1.234,5", "4 de noviembre de 2026", "Sin datos", "1.000"],
        ),
        ("en", None, ["1,234.5", "2026-11-04", "No data"]),
    ]:
        r = build(language, f)
        html = r.to_html(renderer=renderer())
        assert f'lang="{language}"' in html
        pdf = PdfReader(io.BytesIO(r.to_pdf(renderer=renderer())))
        text = "\n".join(p.extract_text() for p in pdf.pages)
        assert len(pdf.pages) == 1
        for value in expected + ["España", "Россия"]:
            assert value in text, text
        assert pdf.trailer["/Root"].get("/Lang") == language


def test_custom_date_axis_pdf_and_literal_pattern():
    dates = [date(2026, 11, i) for i in (4, 5, 6)]
    report = Report(
        language="es", formatting=Formatting(date_format="dd MMM yyyy")
    ).row(Card(LineChart(dates, [1, 3, 2], x_kind="date")), height_mm=80)
    pdf = PdfReader(io.BytesIO(report.to_pdf()))
    assert "04 nov 2026" in pdf.pages[0].extract_text()
    doc = validate_report(
        Report(formatting=Formatting(date_format="'<b>' yyyy")).add(
            LineChart(dates, [1, 3, 2], x_kind="date")
        )
    )
    spec = chart_spec(
        doc.blocks[0], doc.theme, "blocks.0", doc.charts["blocks.0"], doc.formatting
    )
    assert spec["layout"]["xaxis"]["ticktext"][0] == "&lt;b&gt; 2026"


def test_parallel_report_settings_and_dataset_preservation():
    from concurrent.futures import ThreadPoolExecutor

    from cardreport import Dataset, datasets_to_json

    dataset = Dataset.single({"n": Decimal("1234.50"), "d": date(2026, 11, 4)})
    before = datasets_to_json({"summary": dataset})

    def render(language):
        report = Report(language=language, formatting=Formatting(date_format="MMMM"))
        report.add(KPI("Date", dataset.rows[0][1]))
        return report.to_html()

    with ThreadPoolExecutor(max_workers=2) as pool:
        spanish, french = list(pool.map(render, ["es", "fr"]))
    assert "noviembre" in spanish and "novembre" not in spanish
    assert "novembre" in french and "noviembre" not in french
    assert datasets_to_json({"summary": dataset}) == before


@pytest.mark.parametrize("renderer", [ChromiumRenderer, WeasyPrintRenderer])
def test_long_localized_text_keeps_overflow_contract(renderer):
    from cardreport import LayoutOverflowError

    report = Report(
        formatting=Formatting(date_format="'" + "Very long literal " * 9 + "' yyyy")
    )
    report.row(Card(KPI("Date", date(2026, 11, 4))), height_mm=30)
    with pytest.raises(LayoutOverflowError):
        report.to_pdf(renderer=renderer())


def test_custom_pattern_utc_zones_and_unknown_locale():
    v = datetime(2026, 11, 4, tzinfo=UTC)
    expected = {
        "z": "UTC",
        "zzzz": "Coordinated Universal Time",
        "Z": "+0000",
        "ZZZZZ": "Z",
        "OOOO": "GMT+00:00",
        "v": "Unknown Region (UTC) Time",
        "vvvv": "Unknown Region (UTC) Time",
        "V": "Unknown Region (UTC) Time",
        "VV": "Etc/UTC",
        "VVV": "UTC",
        "VVVV": "Unknown Region (UTC) Time",
        "XXX": "Z",
        "xxx": "+00:00",
    }
    for pattern, label in expected.items():
        assert format_value(v, formatting=Formatting(datetime_format=pattern)) == label
    with pytest.raises(ValidationError, match="locale"):
        Report(formatting=Formatting(locale="xx", date_format="yyyy")).validate()


@pytest.mark.parametrize(
    "settings,path",
    [
        ({"language": 123}, "report.language"),
        ({"formatting": {"decimal": "!"}}, "report.formatting.decimal"),
        ({"formatting": {"group": "?"}}, "report.formatting.group"),
        ({"formatting": {"date_format": 123}}, "report.formatting.date_format"),
        ({"formatting": {"locale": "bad<script>"}}, "report.formatting.locale"),
        (
            {"formatting": {"locale": "xx", "date_format": "yyyy"}},
            "report.formatting.locale",
        ),
        ({"language": "xx", "formatting": {"date_format": "yyyy"}}, "report.language"),
    ],
)
def test_template_locale_errors_point_to_actual_setting(settings, path):
    with pytest.raises(TemplateError) as error:
        ReportTemplate(template(**settings))
    assert error.value.template_path == path


def test_fractional_seconds_truncate_without_rounding_or_precision_loss():
    f = Formatting(datetime_format="ss.SSSSSS")
    micros = sorted(
        {0, 1, 570000, 999499, 999500, 999600, 999999, *range(0, 1000000, 997)}
    )
    for microsecond in micros:
        value = datetime(2026, 11, 4, 12, 0, 45, microsecond, tzinfo=UTC)
        expected = value.isoformat(timespec="microseconds").split(":")[-2]
        assert format_value(value, formatting=f) == expected[:-3]
    value = datetime(2026, 11, 4, 12, 0, 45, 999600, tzinfo=UTC)
    assert (
        format_value(value, formatting=Formatting(datetime_format="ss.SSS")) == "45.999"
    )
    assert (
        format_value(value, formatting=Formatting(datetime_format="S SSSSSSSSS"))
        == "9 999600000"
    )


def test_locale_specific_runtime_errors_are_located(monkeypatch):
    from cardreport.formatting import DateTimeFormat

    settings = Formatting(datetime_format="B")
    report = Report(language="es", formatting=settings).add(
        KPI("Time", datetime(2026, 11, 4, tzinfo=UTC))
    )

    def fail(self, key):
        raise ValueError("locale-specific missing day period")

    monkeypatch.setattr(DateTimeFormat, "__getitem__", fail)
    with pytest.raises(
        ValidationError, match=r"blocks.0.value: formatting.datetime_format"
    ):
        report.validate()


def test_decimal_context_isolation_and_naive_datetime_utc():
    from decimal import Inexact, localcontext

    f = Formatting(currency_decimals=6)
    with localcontext() as context:
        context.prec = 3
        context.traps[Inexact] = True
        assert (
            format_value(Decimal("123456.9876544"), Currency("USD"), f)
            == "USD 123,456.987654"
        )
        assert format_value(Decimal("0.12345"), "percent", f) == "12.3%"
        assert context.prec == 3 and context.traps[Inexact]
    assert (
        f.dates(datetime(2026, 11, 4), date_only=False, language="en")
        == "2026-11-04T00:00:00+00:00"
    )


def test_datetime_axis_keeps_utc_coordinates_and_formats_time():
    dates = [
        datetime(2026, 11, 4, 8 + i, tzinfo=timezone(timedelta(hours=-2)))
        for i in range(3)
    ]
    report = Report(
        language="es", formatting=Formatting(datetime_format="dd MMM HH:mm")
    ).row(Card(LineChart(dates, [1, 3, 2], x_kind="date")), height_mm=80)
    doc = validate_report(report)
    chart = doc.charts["blocks.0.0.content"]
    assert chart.tick_values[0] == "2026-11-04T10:00:00+00:00"
    assert chart.tick_labels[0] == "04 nov 08:00"
    pdf = PdfReader(io.BytesIO(report.to_pdf()))
    assert "04 nov 08:00" in pdf.pages[0].extract_text()


def test_extended_year_is_not_abbreviated():
    f = Formatting(date_format="uu 'it''s' yyyy")
    assert format_value(date(2026, 11, 4), formatting=f) == "2026 it's 2026"
    assert format_value(date(5, 1, 1), formatting=Formatting(date_format="uu")) == "05"


def test_date_pattern_rejects_nul_instead_of_turning_it_into_quote():
    with pytest.raises(ValidationError, match="control"):
        Formatting(date_format="yyyy\x00MM")
