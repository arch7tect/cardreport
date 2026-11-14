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
Cards without a parent-supplied height grow with their contents, including in
WeasyPrint. A standalone `Card(Table(...))` needs no fixed-height wrapper to fit
its own table; it must still fit on the page in dashboard mode.
Card titles and padding consume space. Charts default to the theme's chart height
when no definite height is supplied.

If export raises `LayoutOverflowError`, increase the allocated width/height,
choose a larger page or reduce content. The engine does not silently shrink fonts.
For custom page dimensions, pass `(width_mm, height_mm)` and leave orientation at
its default. See the [layout API](api.md#row) for precise constraints.

### Budget an A4 page

Portrait A4 is 210 × 297 mm. With `Page(size="A4", margin_mm=10)`, the page body
is 190 × 277 mm. Budget the whole blocks inside that body:

| Item | Space to allow |
| --- | --- |
| Report title and subtitle | Their rendered height; wrapping changes it |
| Gaps between top-level blocks, including the report header | `theme.gap_mm` per gap |
| A fixed-height row | Its entire `height_mm`, including cards and their contents |
| Card padding | Twice `theme.padding_mm` on each axis |
| Card border, Chromium | 0.4 mm total on each axis in the current stylesheet |
| Card title, Chromium | Its rendered height plus the 3 mm title/content gap |
| Chart axes, legend and outside values | Additional space inside the chart box |

For example, choose `Theme(gap_mm=3.5, padding_mm=3.5)`. A planning allowance of
25 mm for the report header plus three 70 mm rows and three 3.5 mm gaps totals
245.5 mm, leaving 31.5 mm of the 277 mm body. The 25 mm is an allowance, not a
fixed header height: render the actual title/subtitle to verify it. An untitled
95 mm card leaves 87.6 mm vertically after padding and borders in Chromium;
a titled card leaves less, and the chart still needs its own axes and legend.
These inner deductions are already included in the row height; do not subtract
them a second time from the page budget. The default theme uses 4 mm gaps/padding,
so set smaller values explicitly when using this example budget.

Empty space on a final flow page does not mean the report can fit on fewer pages.
Flow preserves block order, moves whole rows and splits only supported top-level
tables; it does not repack earlier pages. Validate the actual PDF rather than
promising a page count from the total area alone.

### Fit chart labels

Dense vertical grouped bars with several series and long formatted values may
need value labels disabled. `BarChart` already defaults to `show_labels=False`;
set it explicitly when documenting a layout choice. `Funnel` defaults to values
on. Turning values off keeps category ticks and legends, which can still collide.

When Chromium reports `chart labels overlap`, read the named types and texts:

1. For value/value collisions in vertical grouped bars, increase the chart's
   share of the row or move it to a full-width row. More height alone is not a
   reliable fix for adjacent values. For horizontal grouped bars, more height
   separates adjacent bars, while long outside values also need enough width.
2. For tick or legend collisions, allow room for those elements. Widen the chart,
   use shorter unambiguous category names, or adjust supported legend settings
   from the [chart API](api.md#barchart). Inspect the named elements rather than
   assuming `show_labels=False` resolves every overlap.
3. If compactness matters and exact values are available in a nearby table,
   use `show_labels=False`. Otherwise give the chart more room or explicitly
   reorganize the information into several charts; do not silently drop records
   or series to make an export pass.
4. Render again with the intended engine and inspect the result. Each change can
   reveal another collision. Chromium's outside-value margin adjustment also
   consumes plotting space; it cannot make every narrow chart fit.

An overlap distance is not the required increase in row width or height. Resizing
can change ticks, label angles, legends and other collisions, so a guaranteed
minimum size requires further layout checks. The sizing principles also help
with WeasyPrint, but its measurements and errors differ: success in one renderer
does not guarantee success in the other. Neither engine silently hides values.

### Dense grouped bars with space grouping

This self-contained Chromium example uses English labels and synthetic counts.
`group="space"` displays thousands with U+00A0 nonbreaking spaces independently
of the report language. The compact chart omits values already present in its
table. The intentional second page demonstrates the same data at full width
with values enabled; it is a comparison of layouts, not a requirement to insert
a page break when a chart fails.

```python
from cardreport import BarChart, Card, Formatting, Page, Report, Table, TableColumn, Theme

# Synthetic counts; exact values remain in the table beside the compact chart.
categories = ["Busy", "Completed", "Network error", "Declined"]
current = [21600, 16700, 5200, 1100]
previous = [18400, 14900, 3900, 950]
rows = [
    {"status": label, "current": now, "previous": before}
    for label, now, before in zip(categories, current, previous, strict=True)
]

def status_chart(*, labels: bool) -> BarChart:
    return BarChart(
        categories,
        series={"Current": current, "Previous": previous},
        value_format="integer",
        show_labels=labels,
    )

report = Report(
    "Grouped bars in a dense layout",
    subtitle="Synthetic data: compact and full-width alternatives",
    page=Page(size="A4", margin_mm=10),
    theme=Theme(font_size_pt=9.5, gap_mm=3.5, padding_mm=3.5),
    formatting=Formatting(decimal=",", group="space"),
)
report.row(
    Card(Table(
        [TableColumn("status", "Status", width=2),
         TableColumn("current", "Current", format="integer", align="right"),
         TableColumn("previous", "Previous", format="integer", align="right")],
        rows,
    ), title="Exact counts"),
    Card(status_chart(labels=False), title="Comparison"),
    widths=[1.55, 1], height_mm=95,
)
# An intentional comparison page, not an overflow workaround.
report.new_page().row(
    Card(status_chart(labels=True), title="Full-width comparison with values"),
    height_mm=95,
)
pdf = report.to_pdf()
assert pdf.startswith(b"%PDF-")
```

These dimensions work for these data and labels, not for every dataset. In tables,
narrow numeric cells can still wrap, including between a percentage and `%`,
because cells permit wrapping within long content. Increase the numeric
`TableColumn(width=...)` weights or widen the card; inspect rendered numbers as
well as row counts. Nonbreaking group separators do not guarantee an unbroken cell.

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
gap in line charts; it is invalid in bar/funnel values. Dates and datetimes
are supported; [timezone settings](localization.md#timezones) control display. Formatting uses fixed separators
and half-even rounding, independent of the machine locale. Report-wide [display settings](localization.md)
customize separators, precision and date patterns. See [formats](api.md#currency-and-formatting).

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

### Dashboards across pages

Use `mode="flow"` when rows of cards should move to the next page automatically.
Keep a table at the top level as `Card(Table(...))`, without a fixed row height,
to let its records continue across pages. Explicit `new_page()` calls still force
breaks in flow mode. Flow does not shrink rows or rebalance their contents to
reach a requested page count; dashboard mode keeps your explicit page layout.

The [flow dashboard example](../../examples/flow_dashboard.py) combines KPI cards,
a row of charts, a long table and a final KPI row without manual page breaks:

```python
from examples.flow_dashboard import build_report as build_flow_dashboard

dashboard = build_flow_dashboard()
pdf = dashboard.to_pdf()
assert pdf.startswith(b"%PDF-")
```

Use the [A4 budget](#budget-an-a4-page) and [label-sizing recipe](#fit-chart-labels)
when allocating rows. `validate()` checks the model, while
Chromium `to_html()` returns a document whose geometry checks run when opened in
a browser; `to_pdf()` waits for those checks and raises any layout error.

## Choose an output

- `to_html()` / `to_pdf()` return values for application integration.
- `write_html()` / `write_pdf()` save files, with explicit overwrite control.
- HTML is a preview; PDF completes renderer-specific layout checks.

See [quickstart export](quickstart.md#return-html-or-pdf-to-the-application),
[renderer capabilities](renderers.md#capabilities) and [complete examples](examples.md).
