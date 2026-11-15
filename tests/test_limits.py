"""Resource policies can raise defaults without bypassing content validation."""

import io
import json
from datetime import date, timedelta

import pytest
from pypdf import PdfReader

from cardreport import (
    DataError,
    DataLimits,
    Dataset,
    LayoutOverflowError,
    LineChart,
    Report,
    ReportLimits,
    ReportTemplate,
    Table,
    TableColumn,
    TemplateError,
    Text,
    ValidationError,
    WeasyPrintRenderer,
    datasets_from_json,
    datasets_from_yaml,
    datasets_to_json,
)


def table_spec():
    return {
        "format": "cardreport.template/1",
        "datasets": {
            "transactions": {
                "fields": {"id": {"type": "integer"}},
                "cardinality": "many",
            }
        },
        "report": {
            "mode": "flow",
            "blocks": [
                {
                    "type": "table",
                    "dataset": "transactions",
                    "columns": [{"key": "id", "label": "ID"}],
                }
            ],
        },
    }


@pytest.mark.parametrize("cls", [DataLimits, ReportLimits])
@pytest.mark.parametrize("bad", [0, -1, True, 1.5, None])
def test_positive_budgets(cls, bad):
    key = "max_rows" if cls is DataLimits else "max_pages"
    with pytest.raises((DataError, ValidationError)):
        cls(**{key: bad})


def test_large_table_binding_and_serialization():
    limits = DataLimits(max_rows=2101)
    dataset = Dataset(["id"], [(i,) for i in range(2101)], limits=limits)
    payload = datasets_to_json({"transactions": dataset}, limits=limits)
    with pytest.raises(DataError):
        datasets_from_json(payload)
    template = ReportTemplate(table_spec())
    data = datasets_from_json(payload, limits=limits)
    with pytest.raises(ValidationError):
        template.bind(data, limits=limits)
    report = template.bind(
        data, limits=limits, report_limits=ReportLimits(max_table_rows=2101)
    )
    assert "2,100" in report.to_html()
    report.limits = ReportLimits(max_table_rows=2101, max_table_cells=2100)
    with pytest.raises(ValidationError, match="table cells"):
        report.validate()


@pytest.mark.parametrize("loader", [datasets_from_json, datasets_from_yaml])
def test_parser_nodes_follow_byte_budget(loader):
    # More than the old 500k value-tree nodes; JSON is also valid YAML.
    rows = [{"a": {"$type": "date", "value": "2026-01-01"}} for _ in range(126000)]
    payload = json.dumps(
        {
            "format": "cardreport.data/1",
            "datasets": {"x": {"columns": ["a"], "rows": rows}},
        }
    )
    limits = DataLimits(max_rows=len(rows), max_cells=len(rows))
    assert len(loader(payload, limits=limits)["x"].rows) == len(rows)


def test_template_size_roundtrip():
    # Unused named image assets are valid; source is generated, not an external fixture.
    from PIL import Image as PILImage

    from cardreport import Image

    buf = io.BytesIO()
    PILImage.new("RGB", (600, 600), "white").save(buf, format="PNG", compress_level=0)
    spec = {
        "format": "cardreport.template/1",
        "datasets": {},
        "assets": {"logo": Image.from_bytes(buf.getvalue()).to_asset()},
        "report": {"blocks": [{"type": "text", "text": "Size test"}]},
    }
    with pytest.raises(TemplateError):
        ReportTemplate(spec)
    template = ReportTemplate(spec, max_bytes=3 * 1024 * 1024)
    assert (
        ReportTemplate.from_json(
            template.to_json(), max_bytes=template.max_bytes
        ).to_dict()
        == spec
    )
    assert (
        ReportTemplate.from_yaml(
            template.to_yaml(), max_bytes=template.max_bytes
        ).to_dict()
        == spec
    )


@pytest.mark.parametrize("renderer", [None, WeasyPrintRenderer()])
def test_page_budget_both_engines(renderer):
    report = (
        Report(limits=ReportLimits(max_pages=1))
        .add(Text("First"))
        .new_page()
        .add(Text("Second"))
    )
    with pytest.raises(LayoutOverflowError):
        report.to_pdf(renderer=renderer)
    report.limits = ReportLimits(max_pages=2)
    assert len(PdfReader(io.BytesIO(report.to_pdf(renderer=renderer))).pages) == 2


def test_chart_budget():
    chart = LineChart(
        x=[date(2026, 1, 1) + timedelta(days=i) for i in range(501)],
        values=[1] * 501,
        x_kind="date",
    )
    report = Report().add(chart)
    with pytest.raises(ValidationError, match="chart points"):
        report.validate()
    report.limits = ReportLimits(max_chart_points=501)
    report.validate()


def test_long_flow_pdf():
    report = Report(mode="flow", limits=ReportLimits(max_table_rows=2101)).add(
        Table([TableColumn("id", "Transaction")], [{"id": i} for i in range(2101)])
    )
    pdf = PdfReader(io.BytesIO(report.to_pdf(timeout=90)))
    assert len(pdf.pages) > 1
    assert "2,100" in pdf.pages[-1].extract_text()


def test_template_columns_are_checked_at_bind():
    spec = table_spec()
    spec["datasets"]["transactions"]["fields"] = {
        f"c{i}": {"type": "integer"} for i in range(21)
    }
    spec["report"]["blocks"][0]["columns"] = [
        {"key": f"c{i}", "label": f"C{i}"} for i in range(21)
    ]
    template = ReportTemplate(spec)
    data = {"transactions": Dataset([f"c{i}" for i in range(21)], [list(range(21))])}
    with pytest.raises(ValidationError):
        template.bind(data)
    template.bind(data, report_limits=ReportLimits(max_table_columns=21)).validate()


def test_small_alias_expansion_does_not_inherit_large_transport_budget():
    from cardreport._yaml import load_yaml

    source = 'a0: &a0 [""]\n' + "".join(
        f"a{i}: &a{i} [*a{i - 1}, *a{i - 1}]\n" for i in range(1, 15)
    )
    with pytest.raises(ValueError, match="expanded-node"):
        load_yaml(source, 100 * 1024 * 1024)
