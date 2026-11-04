"""Checked by mypy, not executed: unused ignores detect weakened public typing."""

from datetime import date
from decimal import Decimal
from typing import assert_type

from pandas import DataFrame

from cardreport import (
    KPI,
    BarChart,
    BindingError,
    Card,
    Column,
    Component,
    Dataset,
    DatasetSchema,
    FieldSpec,
    LineChart,
    PageBreak,
    Report,
    ReportTemplate,
    Row,
    Table,
    TableColumn,
    Text,
    datasets_from_json,
    datasets_to_json,
)
from cardreport.adapters.csv import from_csv
from cardreport.adapters.pandas import from_pandas

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
