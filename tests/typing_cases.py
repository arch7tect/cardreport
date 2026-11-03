"""Checked by mypy, not executed: unused ignores detect weakened public typing."""

from datetime import date
from decimal import Decimal
from typing import assert_type

from cardreport import (
    KPI,
    BarChart,
    Card,
    Column,
    Component,
    LineChart,
    PageBreak,
    Report,
    Row,
    Table,
    TableColumn,
    Text,
)

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
