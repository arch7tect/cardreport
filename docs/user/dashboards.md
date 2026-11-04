# KPI dashboards and compact charts

[Documentation home](../../README.md) · [API reference](api.md)

A small trend chart is an ordinary LineChart with axes hidden. Compose it with a
KPI in a Column; the same chart can be used at full size with axes. Both renderers
support single-series lines, including date coordinates, gaps and zero fill.

## A KPI with a trend

```python
from datetime import date
from cardreport import Card, Column, Formatting, KPI, LineChart, Page, Report, Theme

report = Report(
    "Operations",
    page=Page(orientation="landscape"),
    theme=Theme(kpi_value_size_pt=32),
    formatting=Formatting(date_format="dd MMM"),
)
trend = LineChart(
    x=[date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 4)],
    values=[12, 18, 16],
    x_kind="date",
    axes=False,
    markers=False,
    legend=False,
    fill="zero",
)
report.row(
    Card(Column(KPI("Active agents", 16), trend, heights=[2, 1])),
    height_mm=60,
)
pdf = report.to_pdf()
```

`axes=False` hides ticks, grid and axis lines. It does not change the data into
equally spaced categories: use `x_kind="date"` when time intervals matter.
With any non-default axes/markers/fill option, date coordinates must be strictly
increasing after UTC normalization. Inputs are never silently sorted. Date validation preserves microseconds; rendered
positions are limited by the backend (Plotly uses millisecond date coordinates)
and physical pixel resolution. Sub-millisecond separation is not guaranteed. Default
line options retain the existing input-order behavior.

`markers=False` hides markers where a line segment already shows the value.
Isolated points, including a one-point dataset, retain a dot. `None` breaks both
the line and the filled area. With hidden axes, an all-null series shows the report
empty message. Empty text is still measured and can overflow a very small card.

`fill="zero"` fills to zero and includes zero in the value range, for positive and
negative values. It supports one series. `fill="none"` uses the observed range;
a nearly constant rate will look flatter when filled to zero. Both engines use
straight segments and a solid light fill; there is no smoothing or gradient.

## Size belongs to the layout

Use `Row(height_mm=...)` and `Column(heights=[...])` to allocate space. The numbers
in `heights` are weights, not millimetres. Account for card padding, title and gaps.
Text-free lines (hidden axes, no drawn legend) allow a 10 mm plot container;
ordinary charts need 35 mm. The actual plot must still have enough room for its
stroke. No content is shrunk or silently omitted to make it fit.

An unweighted Column uses the theme's ordinary `chart_height_mm`; hiding axes alone
does not reduce that height. A category legend shares the chart's allocation with
the plot. Long legend names wrap; insufficient remaining space raises
LayoutOverflowError.

`Theme.kpi_value_size_pt` controls value text independently of body text (12–72 pt,
default 24). Non-default sizes keep the entire value on one line and reject overflow.
At the default size, legacy wrapping is retained. Labels/notes still wrap normally.

## Category colors and a left legend

```python
from cardreport import BarChart

ranking = BarChart(
    labels=["Sales A", "Sales B", "Sales C"],
    values=[11683, 11663, 7226],
    color_by="category",
    legend=True,
    legend_position="left",
    category_labels=False,
    show_labels=True,
    value_format="integer",
)
report = Report("Top agents", page=Page(orientation="landscape"))
report.row(Card(ranking), height_mm=90)
pdf = report.to_pdf()
```

The default `color_by="series"` preserves existing series colors and legends.
`color_by="category"` requires one series (`values` or a one-entry `series` mapping).
Each category gets a distinct color from the accent plus the built-in palette,
with duplicates removed. If there are more categories than available distinct
colors (8 or 9 depending on the accent), validation fails. Use ordinary category
ticks and series coloring for larger charts.

With category coloring, `legend=True` displays a shared HTML legend; positions
are `"bottom"` (default, up to three columns) or `"left"`. Category ticks remain on
unless `category_labels=False`; hiding them requires a category legend so names
are never lost. `legend_position="left"` requires a category legend. Different date categories can have identical formatted names; use a date pattern
that distinguishes them when the distinction matters. Value-axis
labels remain visible, and `show_labels` controls numbers on the bars.

## Templates and the operations example

The same optional keys are accepted in `cardreport.template/1`: line `axes`,
`markers`, `fill`; bar `color_by`, `legend_position`, `category_labels`; theme
`kpi_value_size_pt`. Dataset schemas and `cardreport.data/1` are unchanged.

The [operations template](../../examples/operations_template.json),
[data](../../examples/operations_data.json) and
[builder](../../examples/operations_report.py) recreate an operations dashboard screenshot's
snapshot values. Historical curves were not available, so the example explicitly
labels all trend series as synthetic. The fifth agent name was not visible and
is marked as unavailable; its count is retained. The raw screenshot is not bundled.

```python
from examples.operations_report import build_report
from cardreport import WeasyPrintRenderer

report = build_report()  # Repository example; files are next to the builder.
html = report.to_html()
pdf = report.to_pdf(renderer=WeasyPrintRenderer())
```

For application embedding, load your own template and named datasets with
[ReportTemplate](templates.md). The experimental renderer still rejects multiple
line series, Funnel and automatic flow; it never falls back to a browser.
