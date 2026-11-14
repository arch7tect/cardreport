from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader

from cardreport import (
    BindingError,
    Dataset,
    Report,
    ReportTemplate,
    TemplateError,
    Text,
)
from cardreport.weasyprint import WeasyPrintRenderer


def definition(title="Daily report for {{ datasets.summary.day }}"):
    return {
        "format": "cardreport.template/1",
        "datasets": {
            "summary": {
                "cardinality": "one",
                "fields": {
                    "day": {"type": "date"},
                    "time": {"type": "datetime"},
                    "total": {"type": "integer"},
                    "amount": {"type": "decimal"},
                    "rate": {"type": "number"},
                    "label": {"type": "text"},
                    "optional": {"type": "date", "nullable": True},
                },
            }
        },
        "report": {
            "title": title,
            "language": "es",
            "formatting": {
                "date_format": "dd.MM.yyyy",
                "datetime_format": "dd.MM.yyyy HH:mm",
                "group": "space",
                "decimal": ",",
            },
            "blocks": [{"type": "text", "text": "Total: {{ datasets.summary.total }}"}],
        },
    }


def data(**changes):
    values = {
        "day": date(2026, 11, 14),
        "time": datetime(2026, 11, 14, 1, 30, tzinfo=timezone(timedelta(hours=3))),
        "total": 12540,
        "amount": Decimal("1234.50"),
        "rate": 0.125,
        "label": "<script>{{ literal }}</script>",
        "optional": None,
    }
    values.update(changes)
    return {"summary": Dataset.single(values)}


def test_defaults_filters_and_roundtrip():
    spec = definition()
    spec["report"]["subtitle"] = (
        '{{ datasets.summary.time }} | {{ datasets.summary.day | date("d MMMM yyyy") }}'
    )
    spec["report"]["blocks"][0]["text"] = (
        '{{ datasets.summary.amount | currency("EUR") }} / {{ datasets.summary.rate | percent }} / {{ datasets.summary.total | integer }} / {{ datasets.summary.optional | date }} / {{ datasets.summary.amount | number }}'
    )
    template = ReportTemplate(spec)
    report = template.bind(data())
    assert report.title == "Daily report for 14.11.2026"
    assert report.subtitle == "13.11.2026 22:30 | 14 noviembre 2026"
    assert (
        report.blocks[0].text
        == "EUR 1\u00a0234,50 / 12,5% / 12\u00a0540 / — / 1\u00a0234,5"
    )
    for loaded in (
        ReportTemplate.from_json(template.to_json()),
        ReportTemplate.from_yaml(template.to_yaml()),
    ):
        assert loaded.to_dict() == spec
        assert loaded.bind(data()).title == report.title
    assert template.bind(data(day=date(2026, 11, 15))).title.endswith("15.11.2026")


def test_every_text_position_and_literal_bound_values():
    spec = definition("{{ datasets.summary.label }}")
    spec["report"]["subtitle"] = {"bind": {"dataset": "summary", "field": "label"}}
    spec["report"]["blocks"] = [
        {
            "type": "card",
            "title": "{{ datasets.summary.day }}",
            "content": {
                "type": "kpi",
                "label": "{{ datasets.summary.label }}",
                "value": {"bind": {"dataset": "summary", "field": "total"}},
                "note": "{{ datasets.summary.day | date }}",
            },
        }
    ]
    report = ReportTemplate(spec).bind(data())
    assert report.title == report.subtitle == "<script>{{ literal }}</script>"
    assert report.blocks[0].title == report.blocks[0].content.note == "14.11.2026"
    assert report.blocks[0].content.label == report.title
    html = report.to_html()
    assert "&lt;script&gt;{{ literal }}&lt;/script&gt;" in html
    assert "<script>{{ literal }}</script>" not in html
    assert (
        Report("{{ unchanged }}").add(Text("{% unchanged %}")).title
        == "{{ unchanged }}"
    )


@pytest.mark.parametrize(
    "key", ["items", "keys", "get", "__class__", "report date", "a.b"]
)
def test_mapping_keys(key):
    spec = definition('{{ datasets["' + key + '"]["' + key + '"] }}')
    spec["datasets"] = {key: {"cardinality": "one", "fields": {key: {"type": "text"}}}}
    spec["report"]["blocks"] = []
    assert (
        ReportTemplate(spec).bind({key: Dataset.single({key: "value"})}).title
        == "value"
    )
    if key.isidentifier():
        spec["report"]["title"] = "{{ datasets." + key + "." + key + " }}"
        assert (
            ReportTemplate(spec).bind({key: Dataset.single({key: "value"})}).title
            == "value"
        )


@pytest.mark.parametrize(
    "expression",
    [
        "{{ datasets.unknown.day }}",
        "{{ datasets.summary.unknown }}",
        "{{ unknown }}",
        "{{ datasets.summary }}",
        "{{ datasets.summary.day.year }}",
        "{{ datasets.summary[1] }}",
        "{{ datasets.summary.day | upper }}",
        "{{ datasets.summary.day | integer }}",
        "{{ datasets.summary.total | date }}",
        '{{ datasets.summary.day | date("HH:mm") }}',
        '{{ datasets.summary.day | date("unquoted") }}',
        '{{ datasets.summary.amount | currency("bad") }}',
        '{{ datasets.summary.total | number("integer") }}',
        '{{ datasets.summary.day | date(pattern="yyyy") }}',
        "{{ datasets.summary.label.upper() }}",
        '{{ "x" * 1000000 }}',
        "{{ 2026 }}",
        "{% for x in datasets %}{{ x }}{% endfor %}",
        '{% include "file" %}',
        '{{ datasets.summary.day if true else "x" }}',
        "{{ datasets.summary.day | date | number }}",
        "{{",
    ],
)
def test_invalid_expressions_have_paths(expression):
    with pytest.raises(TemplateError) as caught:
        ReportTemplate(definition(expression))
    assert caught.value.template_path == "report.title"


def test_many_dataset_rejected():
    spec = definition()
    spec["datasets"]["summary"]["cardinality"] = "many"
    with pytest.raises(TemplateError, match="cardinality one"):
        ReportTemplate(spec)


def test_static_length_uses_literals_not_sample_values():
    spec = definition("x" * 499 + "{{ datasets.summary.label }}")
    template = ReportTemplate(spec)
    assert len(template.bind(data(label="A")).title) == 500
    with pytest.raises(BindingError) as caught:
        template.bind(data(label="AB"))
    assert caught.value.template_path == "report.title"
    spec["report"]["title"] = "x" * 501 + "{{ datasets.summary.label }}"
    with pytest.raises(TemplateError):
        ReportTemplate(spec)


def test_escapes_plain_strings_and_technical_fields():
    spec = definition('{% raw %}{{ unchanged }}{% endraw %} {{ "{{" }}')
    spec["report"]["subtitle"] = "literal\r\n"
    spec["report"]["empty_text"] = "{{ unchanged }}"
    report = ReportTemplate(spec).bind(data())
    assert report.title == "{{ unchanged }} {{"
    assert report.subtitle == "literal\r\n"
    assert report.empty_text == "{{ unchanged }}"
    spec["report"]["title"] = "{{ datasets.summary.day }}\n"
    assert ReportTemplate(spec).bind(data()).title.endswith("\n")


def test_date_like_text_and_no_formatting():
    spec = definition(
        "{{ datasets.summary.label }} / {{ datasets.summary.day }} / {{ datasets.summary.time }}"
    )
    del spec["report"]["formatting"]
    assert (
        ReportTemplate(spec).bind(data(label="2026-11-14")).title
        == "2026-11-14 / 2026-11-14 / 2026-11-13T22:30:00+00:00"
    )


@pytest.mark.parametrize("renderer", [None, WeasyPrintRenderer()])
def test_both_pdf_engines(renderer):
    if renderer is not None:
        pytest.importorskip("weasyprint")
    spec = definition()
    spec["report"]["language"] = "en"
    report = ReportTemplate(spec).bind(data())
    pdf = report.to_pdf(renderer=renderer)
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert "Daily report for 14.11.2026" in text
    assert "Total:12540" in "".join(text.split())


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("{{ datasets.summary.time | date }}", "13.11.2026"),
        ("{{ datasets.summary.time | date('yyyy-MM-dd') }}", "2026-11-13"),
        ("Date\r\n{{ datasets.summary.day }}\r\n", "Date\n14.11.2026\n"),
        ("{{ datasets.summary.total | currency('EUR') }}", "EUR 12\u00a0540,00"),
    ],
)
def test_date_filters_and_parsed_newlines(expression, expected):
    assert ReportTemplate(definition(expression)).bind(data()).title == expected


@pytest.mark.parametrize("source", ["Issue {#42}", "Literal {% example"])
def test_legacy_delimiters_need_escaping(source):
    with pytest.raises(TemplateError) as caught:
        ReportTemplate(definition(source))
    assert caught.value.template_path == "report.title"


def test_cli_csv_date_substitution(tmp_path):
    from cardreport.cli import main
    from examples.daily_report import TEMPLATE_YAML

    template = tmp_path / "daily.yaml"
    template.write_text(TEMPLATE_YAML)
    csv = tmp_path / "summary.csv"
    csv.write_text("report_date,total,rate\n2026-11-14,12540,0.976\n")
    output = tmp_path / "daily.html"
    assert (
        main(
            [
                "render",
                "--template",
                str(template),
                "--csv",
                str(csv),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    html = output.read_text()
    assert "Daily report for 14.11.2026" in html
    assert "Month: November 2026" in html
    assert "Automation: 97.6%" in html
