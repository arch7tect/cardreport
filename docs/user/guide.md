# User guide

[Documentation home](../../README.md) · [API reference](api.md)

## Content and containers

Build leaf components from application data. A Card adds a frame and optional
title. To put several components in a card, give it a Column or Row:

```python
from cardreport import Card, Column, KPI, Report, Row, Text

report = Report("Campaign")
report.add(Card(
    Column(KPI("Clients", 21), Row(KPI("Answered", 5), KPI("Promises", 2)),
           Text("Daily summary", style="caption")),
    title="Progress",
))
report.validate()
```

Text and chart labels are literal. Your application owns data loading, aggregation
and business consistency; the library does not calculate totals or reconcile values.

## Control the layout

Page sizes, margins, gaps, padding and row heights use millimeters; font sizes use
points. Widths/heights are relative weights after gaps, not percentages.

```python
from cardreport import BarChart, Card, Column, KPI, Page, Report, Theme

report = Report("Results", page=Page(orientation="landscape"),
                theme=Theme(gap_mm=5))
report.row(
    Card(BarChart(["Answered", "No answer"], [24, 10])),
    Column(Card(KPI("Clients", 21)), Card(KPI("Promises", 2)), heights=[1, 1]),
    widths=[2, 1], height_mm=100,
)
report.validate()
```

The first column gets twice the available width of the second. The fixed row
height allows the inner Column to divide its available height equally.
Without `heights`, Column keeps natural child heights and aligns them at the top.
Card titles and padding consume space. Charts default to the theme's chart height
when no definite height is supplied.

If export raises `LayoutOverflowError`, increase the allocated width/height,
choose a larger page or reduce content. The engine does not silently shrink fonts.
For custom page dimensions, pass `(width_mm, height_mm)` and leave orientation at
its default. See the [layout API](api.md#row) for precise constraints.

## Format values

```python
from decimal import Decimal
from cardreport import Currency, KPI, Table, TableColumn

amount = KPI("Promised", Decimal("1234.50"), format=Currency("EUR"))
rate = KPI("Promise rate", 2 / 5, format="percent")
table = Table(
    [TableColumn("outcome", "Outcome"),
     TableColumn("rate", "Rate", format="percent", align="right")],
    [{"outcome": "Promised", "rate": 0.4}],
)
```

Use fractions for percentages. None displays an em dash in KPI/table cells and a
gap in line charts; it is invalid in bar/funnel values. Dates and aware datetimes
are supported, with datetime normalization to UTC. Formatting uses fixed separators
and half-even rounding, independent of the machine locale. See [formats](api.md#currency-and-formatting).

## Explicit dashboard pages

```python
from cardreport import Card, KPI, Report

pages = Report("Campaign")
pages.add(Card(KPI("Clients", 21)))
pages.new_page().add(Card(KPI("Promises", 2)))
```

Dashboard is the default mode. It only creates explicit pages, and rejects
content that exceeds one. All pages share a Page configuration. Leading,
consecutive and trailing page breaks do not create blank pages.

## Long tables with flow

```python
from cardreport import Card, Report, Table, TableColumn

flow = Report("Records", mode="flow").add(Card(
    Table([TableColumn("id", "Record"), TableColumn("amount", "Amount")],
          [{"id": f"ROW-{i:03d}", "amount": i} for i in range(120)]),
    title="Details",
))
flow.validate()
```

Flow currently requires Chromium. A top-level Table or Card(Table) can split
between rows, repeating headings and the card title. A table inside Row/Column
cannot split. Other blocks move whole to the next page; a block or row taller
than an empty page is rejected. The report title cannot be stranded alone on a page.

## Choose an output

- `to_html()` / `to_pdf()` return values for application integration.
- `write_html()` / `write_pdf()` save files, with explicit overwrite control.
- HTML is a preview; PDF completes renderer-specific layout checks.

See [quickstart export](quickstart.md#return-html-or-pdf-to-the-application),
[renderer capabilities](renderers.md#capabilities) and [complete examples](examples.md).
