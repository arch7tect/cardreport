"""Checked by mypy, not executed: unused ignores detect weakened public typing."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import assert_type

from pandas import DataFrame

from cardreport import (
    KPI,
    BarChart,
    BindingError,
    Card,
    ChromiumRenderer,
    Column,
    Component,
    Dataset,
    DatasetSchema,
    FieldSpec,
    Formatting,
    LineChart,
    PageBreak,
    Renderer,
    Report,
    ReportTemplate,
    Row,
    Table,
    TableColumn,
    Text,
    datasets_from_json,
    datasets_from_yaml,
    datasets_to_json,
    datasets_to_yaml,
    json_schema,
)
from cardreport.adapters.csv import from_csv
from cardreport.adapters.pandas import from_pandas
from cardreport.document import ReportDocument

report = Report().row(Card(KPI("Clients", 21)), widths=[1], height_mm=60)
assert_type(report, Report)
child: Component = Column(Text("Details"), Row(KPI("Rate", Decimal("0.5"))))
report.add(child).add(PageBreak())
report.add(LineChart([date(2026, 1, 1)], [None], x_kind="date"))
report.add(Table([TableColumn("value", "Value")], [{"value": "hello"}]))
report.add(123)  # type: ignore[arg-type]
Card("not a component")  # type: ignore[arg-type]
Card(Card(Text("nested card")))  # type: ignore[arg-type]
Row(PageBreak())  # type: ignore[arg-type]
Column(42)  # type: ignore[arg-type]
report.row(Text("typo"), width_mm=20)  # type: ignore[call-arg]
Text("x", style="raw")  # type: ignore[arg-type]
BarChart(["a"], ["not numeric"])  # type: ignore[list-item]
BarChart(["a"], [None])  # type: ignore[list-item]
BarChart([date(2026, 11, 4), datetime(2026, 11, 5, tzinfo=UTC), "literal"], [1, 2, 3])
BarChart([42], [1])  # type: ignore[list-item]
KPI("bad", [])  # type: ignore[arg-type]
report.to_pdf(renderer=object())  # type: ignore[arg-type]

native = Dataset.from_records(["total"], [(12,)])
assert_type(native, Dataset)
schema = DatasetSchema({"total": FieldSpec("integer")}, cardinality="one")
assert_type(
    datasets_from_json(datasets_to_json({"summary": native})), dict[str, Dataset]
)
template = ReportTemplate.from_json("{}")
assert_type(template.bind({"summary": native}), Report)
assert_type(from_csv("summary.csv", schema=schema), Dataset)
assert_type(from_pandas(DataFrame({"total": [12]}), schema=schema), Dataset)
assert_type(BindingError("bad").dataset, str | None)
FieldSpec("float")  # type: ignore[arg-type]
DatasetSchema({"n": "integer"})  # type: ignore[dict-item]
template.bind({"summary": [{"total": 12}]})  # type: ignore[dict-item]
from_csv("x.csv")  # type: ignore[call-arg]
from_pandas([], schema=schema)  # type: ignore[arg-type]

f = Formatting(date_format="dd/MM/yyyy", number_decimals=3)
assert_type(Report(language="es-MX", formatting=f).formatting, Formatting | None)
Formatting(number_decimals="2")  # type: ignore[arg-type]
Report(formatting={})  # type: ignore[arg-type]

LineChart([date(2026, 11, 4)], [1], axes=False, markers=False, fill="zero")
LineChart(["a"], [1], fill=True)  # type: ignore[arg-type]
BarChart(["a"], [1], color_by="category", legend_position="left", category_labels=False)
BarChart(["a"], [1], color_by="value")  # type: ignore[arg-type]


assert_type(ReportTemplate.from_yaml("{}"), ReportTemplate)
assert_type(template.to_yaml(), str)
assert_type(
    datasets_from_yaml(datasets_to_yaml({"summary": native})), dict[str, Dataset]
)
assert_type(json_schema("template"), str)
json_schema("other")  # type: ignore[arg-type]
ReportTemplate.from_yaml({})  # type: ignore[arg-type]


class ApplicationRenderer(Renderer):
    def render_html(self, doc: ReportDocument) -> str:
        return "preview"

    def render_pdf(self, doc: ReportDocument, *, deadline: float) -> bytes:
        return b"pdf"


class StructuralRenderer:
    def render_html(self, doc: ReportDocument) -> str:
        return "preview"

    def render_pdf(self, doc: ReportDocument, *, deadline: float) -> bytes:
        return b"pdf"


report.to_html(renderer=ApplicationRenderer())
report.to_html(renderer=ChromiumRenderer())
report.to_html(renderer=StructuralRenderer())  # type: ignore[arg-type]
Renderer()  # type: ignore[abstract]
