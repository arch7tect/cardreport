# API reference

[Documentation home](../../README.md) · [Quickstart](quickstart.md) · [User guide](guide.md)

Names are imported from `cardreport` unless another import location is shown. Signatures describe the current checkout; use a release tag for its exact API.
Annotations such as `Number`, `Value` and `Format` are defined in [types](#types).
Values not expressible by static typing are checked at runtime: for example,
`bool` is rejected as a number even though Python considers it an `int`.
Some malformed inputs raise `ValidationError` in component constructors; other
checks run during `validate()` or export. Handle errors around composition too.

- [Datasets and data JSON](#datasets-and-data-json), [ReportTemplate](#reporttemplate), [adapters](#data-adapters)
- [Report](#report) and [export methods](#export-methods)
- [Page](#page) and [Theme](#theme)
- [Card](#card), [Row](#row), [Column](#column), [PageBreak](#pagebreak)
- [Text](#text), [KPI](#kpi), [TableColumn](#tablecolumn), [Table](#table)
- [BarChart](#barchart), [LineChart](#linechart), [Funnel](#funnel)
- [Currency and formatting](#currency-and-formatting), [types](#types), [limits](#limits)
- [Renderers](#renderers), [extension data](#extension-data), [errors](#errors)

## Report

```text
Report(title: str = "", *, subtitle: str = "",
       mode: Literal["dashboard", "flow"] = "dashboard",
       page: Page | None = None, theme: Theme | None = None,
       language: str = "en", formatting: Formatting | None = None,
       empty_text: str | None = None)

add(block: Block) -> Self
row(*children: Component, widths: Sequence[float] | None = None,
    height_mm: float | None = None) -> Self
new_page() -> Self
validate() -> None
blocks: tuple[Block, ...]  # read-only property
title: str
subtitle: str
mode: Literal["dashboard", "flow"]
page: Page
theme: Theme
```

`None` selects `Page()` / `Theme()`. `add`, `row` and `new_page` append blocks and
return the same report. `row` is shorthand for `add(Row(...))`. Title and subtitle
appear only at the beginning and consume page space. `blocks` is a tuple snapshot.
The Report builder is mutable: `title`, `subtitle`, `mode`, `page` and `theme`
can be reassigned. Export validates their current values. Do not mutate a report
concurrently with export.
Components are frozen records with copied sequences and read-only table-row mappings.

`dashboard` uses explicit pages and rejects overflow. `flow` automatically moves
indivisible blocks and splits only top-level `Table` or `Card(Table)` between rows.
Flow requires Chromium. Nested tables never split. `validate()` checks semantics,
formats and input limits, not geometric fit or a selected renderer's capabilities.

```python
from cardreport import Card, KPI, Report

report = Report("Summary").add(Card(KPI("Clients", 21)))
report.new_page().row(Card(KPI("Answered", 5)))
report.validate()
```

### Export methods

```text
to_html(*, renderer: Renderer | None = None) -> str
to_pdf(*, timeout: float = 30, renderer: Renderer | None = None) -> bytes
write_html(path: str | Path, *, overwrite: bool = False,
           renderer: Renderer | None = None) -> Path
write_pdf(path: str | Path, *, overwrite: bool = False, timeout: float = 30,
          renderer: Renderer | None = None) -> Path
```

These are methods of `Report`. `None` selects `ChromiumRenderer`. `timeout` is
seconds in `(0, 300]`, including validation/preparation and worker execution;
owned processes are cleaned up on timeout. The calls are synchronous.
WeasyPrint HTML rendering has its own fixed 30-second worker deadline.

HTML is a preview: semantic validation completes before return, while Chromium
geometric checks run when it opens. PDF completes geometric checks before return.
Missing runtimes raise `DependencyError`; unsupported features raise
`UnsupportedFeatureError`. See the [capability table](renderers.md#capabilities).

File methods create parent directories and atomically publish completed output.
Existing files raise `FileExistsError` unless `overwrite=True`; failed rendering
preserves existing files. Output is private to the creating user (0600). Default
no-clobber writes require hard-link support, e.g. APFS/ext4; exFAT and some network
filesystems are unsupported. Ordinary I/O exceptions are not wrapped in ReportError.

## Page

```text
Page(size: Literal["A4", "A3", "Letter"] | tuple[float, float] = "A4",
     orientation: Literal["portrait", "landscape"] = "portrait",
     margin_mm: float = 10)
dimensions() -> tuple[float, float]
```

Named sizes are A4 (210 × 297 mm), A3 (297 × 420 mm), Letter (215.9 × 279.4 mm).
`landscape` swaps named dimensions. A custom tuple is `(width_mm, height_mm)` as
written; nondefault orientation with custom sizes raises `ValidationError`.
Each dimension must be 40–1000 mm. Margin is nonnegative and must leave a positive
content area.
One size and margin apply to all pages. `dimensions()` returns the effective size.

```python
from cardreport import Page

page = Page(size=(300, 200), margin_mm=8)
```

## Theme

```text
Theme(accent: str = "#20a6c4", background: str = "#f5f5f5",
      card_background: str = "#ffffff", text: str = "#222222",
      gap_mm: float = 4, padding_mm: float = 4,
      font_size_pt: float = 10, chart_height_mm: float = 60,
      kpi_value_size_pt: float = 24)
Theme.light() -> Theme
```

Colors must be `#RRGGBB`. Gap/padding are 0–20 mm, body font size 9–24 pt and default
chart height 35–200 mm. KPI value size is 12–72 pt; non-default sizes keep the
value on one line and reject overflow (default 24 retains legacy wrapping). `light()` returns the default theme. DejaVu Sans regular/bold
are bundled; arbitrary fonts, CSS and theme templates are not supported.

```python
from cardreport import Theme

theme = Theme(accent="#4263eb", gap_mm=5, font_size_pt=11)
```

## Card

```text
Card(content: CardContent, title: str | None = None)
```

A frame with background, border, padding and optional title. It accepts one leaf,
Row or Column. Put multiple children in a Row/Column; a Card cannot directly
contain another Card. Titles consume content height; nested layouts can contain cards.

```python
from cardreport import Card, Column, KPI, Text

card = Card(Column(KPI("Clients", 21), Text("Completed")), title="Progress")
```

## Row

```text
Row(*children: Component, widths: Sequence[float] | None = None,
    height_mm: float | None = None)
```

At least one child. Widths are relative positive weights (each ≤ 10000), one per
child; default is equal widths. Gaps are subtracted before division. Children
stretch vertically. `height_mm` is a fixed outer height, 1–1000 mm; otherwise
content determines height. Weighting never shrinks fonts or ignores minimum sizes.

```python
from cardreport import Card, KPI, Row

row = Row(Card(KPI("Clients", 21)), Card(KPI("Answered", 5)),
          widths=[2, 1], height_mm=50)
```

## Column

```text
Column(*children: Component, heights: Sequence[float] | None = None)
```

At least one child. Without weights, children use natural height and are top-aligned.
`heights` uses the same positive-weight rules as Row, but requires a definite parent
height. For example, place it in a Row with `height_mm`. It does not infer an
available height from the page. Too-small allocations fail at rendering time.

```python
from cardreport import Card, Column, KPI, Row

weighted = Row(
    Column(Card(KPI("One", 1)), Card(KPI("Two", 2)), heights=[1, 1]),
    height_mm=90,
)
```

## PageBreak

```text
PageBreak()
```

A top-level block only, equivalent to `Report.new_page()`. Supported in dashboard
and Chromium flow. Leading, repeated and trailing breaks do not create blank
pages. Empty reports produce one blank page. A report title cannot be left alone
on a page by automatic pagination.

```python
from cardreport import KPI, PageBreak, Report

pages = Report().add(KPI("First", 1)).add(PageBreak()).add(KPI("Second", 2))
```

## Text

```text
Text(text: str, style: Literal["body", "heading", "caption"] = "body")
```

Literal text, not HTML or Markdown. Newlines are preserved; text wraps within its
allocation. Unsupported font glyphs fail validation. See [limits](#limits).

```python
from cardreport import Text

note = Text("Ready for review\nExample text", style="caption")
```

## KPI

```text
KPI(label: str, value: Value, format: Format = "number", note: str | None = None)
```

A value with its label underneath and optional smaller note. Use Card to add a
frame. Formatting does not calculate aggregates, percentages or conversion rates.

```python
from cardreport import KPI

rate = KPI("Promise rate", 0.4, format="percent", note="2 of 5 clients")
```

## TableColumn

```text
TableColumn(key: str, label: str, format: Format = "number",
            align: Literal["left", "center", "right"] = "left",
            width: float | None = None)
```

`key` identifies a field in every row; `label` is the displayed heading. Width is a
positive relative weight, default 1. Keys must be unique across the table. Formats
apply to numeric/date values; strings remain literal even with the default format.

## Table

```text
Table(columns: Sequence[TableColumn], rows: Sequence[Mapping[str, Value]],
      empty_text: str | None = None)
```

One to 20 columns; every row must contain each column key. Extra keys are ignored.
An empty row sequence displays `empty_text`. In Chromium flow, top-level tables
split between rows and repeat headings; Card(Table) also repeats its card title.
Rows never split; nested tables are indivisible. Column definitions and rows are copied.

```python
from cardreport import Currency, Table, TableColumn

table = Table(
    columns=[TableColumn("name", "Name"),
             TableColumn("amount", "Amount", format=Currency("EUR"), align="right")],
    rows=[{"name": "Example", "amount": 12.5}],
)
```

## BarChart

```text
BarChart(labels: Sequence[str | date | datetime], values: Sequence[Number] | None = None,
         series: Mapping[str, Sequence[Number]] | None = None,
         orientation: Literal["vertical", "horizontal"] = "vertical",
         mode: Literal["grouped", "stacked"] = "grouped",
         show_labels: bool = False, legend: bool = True,
         value_format: Format = "number",
         color_by: Literal["series", "category"] = "series",
         legend_position: Literal["bottom", "left"] = "bottom",
         category_labels: bool = True)
```

Provide exactly one of `values` or `series`. All series lengths match unique
category values (strings, dates or aware datetimes). Values may be negative or zero, but never None/bool/nonfinite.
Dates use the report date pattern; datetimes use the datetime pattern after UTC
normalization. Strings stay literal. Different category values remain separate
even when their formatted labels match; a date and its literal ISO string are
distinct categories. Duplicate datetimes are checked after UTC normalization.
Category order is preserved. `show_labels` controls value labels, not category
labels. With default series coloring, the legend appears for multiple series
when enabled. Category coloring requires one series and assigns distinct colors
from the deduplicated accent/palette (8 or 9 colors); exhaustion is a validation
error. Its HTML legend supports bottom/left placement. Hiding category labels
requires that legend; left placement also requires the category legend. See
[dashboard layouts](dashboards.md#category-colors-and-a-left-legend). `date` is not a valid
chart value format. Empty categories with matching empty values display "No data".
WeasyPrint supports only one series; other bar modes/features are subject to the
[renderer capability table](renderers.md#capabilities).

```python
from cardreport import BarChart

bars = BarChart(["Answered", "No answer"], [24, 10],
                orientation="horizontal", show_labels=True)
```

## LineChart

```text
LineChart(x: Sequence[str | date | datetime],
          values: Sequence[Number | None] | None = None,
          series: Mapping[str, Sequence[Number | None]] | None = None,
          x_kind: Literal["category", "date"] = "category",
          legend: bool = True, value_format: Format = "number",
          axes: bool = True, markers: bool = True,
          fill: Literal["none", "zero"] = "none")
```

Chromium supports multiple series; WeasyPrint supports one. Exactly one of
values/series, matching x lengths. Category axes
require unique strings; date axes require dates or timezone-aware datetimes.
Datetimes normalize to UTC; naive datetimes are rejected. None creates a gap,
not an interpolated segment. Other numeric/format rules match BarChart.

`axes=False` hides both axes/grid. `markers=False` retains a dot only for isolated
values that have no adjacent non-null value. `fill="zero"` requires one series,
fills each non-null segment separately to zero and includes zero in the y range.
Any non-default axes/markers/fill option requires strictly increasing UTC date
coordinates on date axes, without sorting input. Hidden-axis all-null input shows
the empty message. Text-free charts allow a 10 mm container under a definite
weighted layout; ordinary charts retain 35 mm. See [compact charts](dashboards.md).

SVG date axes use up to six sampled input ticks and report formatting (ISO when
omitted), while Chromium keeps automatic date ticks when formatting is omitted.
Long labels still fail overflow checks. No smoothing or gradient is supported.

```python
from datetime import date
from cardreport import LineChart

line = LineChart([date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 3)],
                 [3, None, 5], x_kind="date")
```

## Funnel

```text
Funnel(labels: Sequence[str], values: Sequence[Number],
       show_labels: bool = True, value_format: Format = "number")
```

Chromium only. Unique stage labels and matching nonnegative values. Stages retain
caller order; increases are allowed and no conversion rates are inferred.
Other numeric/format rules match BarChart. A horizontal BarChart is an alternative
when stages should be represented as independent bars.

```python
from cardreport import Funnel

funnel = Funnel(["Attempted", "Answered", "Promised"], [21, 5, 2])
```

## Currency and formatting

```text
Currency(code: str)
```

Code is exactly three uppercase ASCII letters, e.g. `Currency("EUR")`; recognition
against a currency registry is not performed. Numeric rounding is half-even.

| Format | Example input | Display |
| --- | --- | --- |
| `"number"` | `1234.5` | `1,234.5` (up to two decimals) |
| `"integer"` | `12.5` | `12` |
| `"percent"` | `0.4` | `40.0%` (fraction, not already multiplied) |
| `Currency("EUR")` | `12.5` | `EUR 12.50` |
| `"date"` | `date(2026, 11, 4)` | `2026-11-04` |

None displays an em dash in KPI/tables. Strings pass through literally; they are
not parsed as numbers/dates. Dates display ISO dates. Aware datetimes normalize
to UTC, displaying an ISO timestamp except with `date`, which displays its date.
Numeric values cannot use `date`. These are the defaults without report formatting.
Precision and date patterns can be customized through [Formatting](#language-and-formatting);
currency-specific minor-unit rules are not inferred. Chart coordinates convert
to floats, while value labels are formatted from the original values.

## Language and formatting

```text
Formatting(decimal: Literal[".", ","] = ".",
           group: Literal[",", ".", "'", "space", "none"] = ",",
           number_decimals: int = 2, percent_decimals: int = 1,
           currency_decimals: int = 2,
           date_format: str | None = None, datetime_format: str | None = None,
           locale: str | None = None)
```

A frozen, typed display-settings record. `Report(language="en", formatting=None,
empty_text=None)` owns these options, and its validated `ReportDocument` stores
canonical language, optional formatting and resolved empty text as trailing fields
with defaults. `ChartData` adds default-empty `tick_values` and `tick_labels` tuples
for preformatted line date-axis labels (populated for every date line since 0.4.0),
plus `category_labels` for formatted bar
category text. Renderer protocol signatures are unchanged.

Language tags are not restricted to a product allowlist. Decimal precision is 0..6;
number precision is a maximum, percent/currency precision is fixed. Date patterns
use Babel LDML, up to 200 characters. The effective date locale is the explicit
Formatting locale or the report language. No system locale, currency or timezone
is inferred. Custom datetime patterns intentionally select the displayed precision.

`Table.empty_text=None` inherits the report message; explicit strings, including
empty strings, override it. Built-in English/Spanish/Russian empty labels fall back
to English for other languages; `Report.empty_text` customizes empty charts too.

Omitted formatting preserves legacy axes; explicit settings control their labels.
See [language and display formats](localization.md) for language/font boundaries,
date/time rules, examples, sampled date ticks and scalar/axis rounding differences.

## Types

```text
Number = int | float | Decimal
Value = Number | str | date | datetime | None
Format = Literal["number", "integer", "percent", "date"] | Currency
CardContent = Text | KPI | Table | BarChart | LineChart | Funnel | Row | Column
Component = CardContent | Card
Block = Component | PageBreak
```

These are exported type aliases, not base classes or custom-component extension
points. Runtime semantic validation is still required for input values and layouts.

## Limits

| Input | Limit |
| --- | --- |
| Components across all nesting levels / maximum depth | 500 / 12 (top level is depth 0) |
| Output pages | 100 |
| Rows / columns per table | 2000 / 20 |
| Total table cells across the report | 20000 |
| Points per chart / category labels | 500 / 30 |
| Series per chart | 1–8 |
| Chart category text / series name | 200 / 100 characters |
| Text / report title / subtitle | 10000 / 500 / 1000 characters |
| Card title, KPI label/note, table heading/empty text | 500 characters |
| Table column key | 100 characters |
| Numbers | finite, absolute value ≤ 10¹⁵; bool excluded |

Limits are validation bounds, not a guarantee that content fits. Component counts
include containers, their contents and PageBreaks. Formatting and font coverage
are checked too. Dense charts may require fewer labels. Latin and
Cyrillic are supported by the bundled fonts; arbitrary scripts are not promised.

## Renderers

```text
ChromiumRenderer()
WeasyPrintRenderer()

Renderer.render_html(doc: ReportDocument) -> str
Renderer.render_pdf(doc: ReportDocument, *, deadline: float) -> bytes
```

Pass a renderer to Report export methods. `Renderer` is a provisional Protocol;
implement its methods without subclassing or registration. Direct renderer calls
expect an already validated export snapshot. `deadline` is an absolute
`time.monotonic()` value, not a duration. See [extension guidance](renderers.md#custom-renderers).
Test custom renderers through `Report.to_html(renderer=...)` and
`Report.to_pdf(renderer=...)`; these methods prepare the validated snapshot.
There is no public standalone snapshot-building method.

## Extension data

These frozen records serve renderer implementers. Normal application code should
build Report rather than construct snapshots manually.

```text
ChartSeries(name: str, values: tuple[float | None, ...], labels: tuple[str, ...])
ChartData(labels: tuple[str, ...], series: tuple[ChartSeries, ...],
          tick_values: tuple[str, ...] = (), tick_labels: tuple[str, ...] = (),
          category_labels: tuple[str, ...] = ())
ReportDocument(title: str, subtitle: str, mode: Literal["dashboard", "flow"],
               page: Page, theme: Theme, blocks: tuple[Block, ...],
               charts: Mapping[str, ChartData], language: str = "en",
               formatting: Formatting | None = None, empty_text: str = "No data")
```

`ChartData.labels` contains category coordinates or normalized ISO line dates.
For bars containing typed dates/datetimes, coordinates are positional string keys
and `category_labels` contains formatted display text. Renderers must keep those
keys separate from display text to avoid merging equal labels. When
`category_labels` is empty, use `labels` as display text (legacy string categories).
Series values
are plotting floats; `ChartSeries.labels` contains value labels formatted from the
original values. `charts` is keyed by component path, e.g. `blocks.0.content`.
Export-produced snapshots use read-only mappings. Strings are unescaped; each
renderer must escape for its own target format. Component blocks retain their
public types; there is no geometry model in the snapshot.

## Errors

```text
ReportError
├── DataError
├── ValidationError
│   ├── TemplateError
│   └── BindingError
├── LayoutOverflowError
├── UnsupportedFeatureError
├── DependencyError
└── RenderError
    └── RenderTimeoutError
```

| Error | Meaning / action |
| --- | --- |
| `DataError` | Invalid dataset, transport or CSV/pandas input |
| `TemplateError` | Invalid template definition; inspect template_path |
| `BindingError` | Input does not satisfy template/semantic contracts; inspect location attributes |
| `ValidationError` | Invalid data/settings/structure; fix input before export |
| `LayoutOverflowError` | Content, chart labels or pages do not fit; allocate space or reduce content |
| `UnsupportedFeatureError` | Selected renderer cannot handle the feature; select a supporting renderer |
| `DependencyError` | Missing runtime or incompatible experimental adapter; follow renderer setup |
| `RenderTimeoutError` | Rendering deadline expired; apply an application retry/failure policy |
| `RenderError` | Other rendering/verification failure |

Export fails rather than silently clipping/shrinking output. I/O failures such as
`FileExistsError` and `PermissionError` remain ordinary Python exceptions.

## Datasets and data JSON

All names in this section are exported from cardreport. See the
[dataset guide](datasets.md) for schema rules and transport examples.

```text
DataLimits(max_rows=2000, max_columns=100, max_datasets=32, max_cells=100000,
           max_string_chars=10000, max_text_bytes=16777216, max_json_bytes=16777216)
Dataset(columns: Sequence[str], rows: Iterable[Sequence[object]], *, limits=DataLimits())
Dataset.from_records(columns: Sequence[str], records: Iterable[Sequence[object]],
                     *, limits=DataLimits()) -> Dataset
Dataset.from_dicts(rows: Iterable[Mapping[str, object]], *, columns: Sequence[str] | None = None,
                   limits=DataLimits()) -> Dataset
Dataset.single(values: Mapping[str, object], *, limits=DataLimits()) -> Dataset
FieldType = Literal["text", "integer", "number", "decimal", "date", "datetime"]
FieldSpec(type: FieldType, nullable: bool = False)
DatasetSchema(fields: Mapping[str, FieldSpec], cardinality: Literal["one", "many"] = "many")
DatasetSchema.validate(dataset: Dataset) -> None

datasets_from_json(source: str | bytes, *, limits=DataLimits()) -> dict[str, Dataset]
datasets_from_yaml(source: str | bytes, *, limits=DataLimits()) -> dict[str, Dataset]
datasets_to_yaml(data: Mapping[str, Dataset], *, limits=DataLimits()) -> str
datasets_to_json(data: Mapping[str, Dataset], *, limits=DataLimits()) -> str
```

Dataset exposes frozen columns: tuple[str, ...] and rows: tuple[tuple[Value, ...], ...].
Schema exposes copied read-only fields and cardinality one/many. Limits only decrease
the listed caps. Direct/native inputs are checked as well as JSON. DataError derives
from ReportError and carries optional dataset, row, field and template_path.
No constructor stores a connection or a lazy iterator.

## ReportTemplate

```text
ReportTemplate(spec: Mapping[str, object])
ReportTemplate.from_dict(spec: Mapping[str, object]) -> ReportTemplate
ReportTemplate.from_json(source: str | bytes) -> ReportTemplate
ReportTemplate.from_yaml(source: str | bytes) -> ReportTemplate
ReportTemplate.to_dict() -> dict[str, object]
ReportTemplate.to_json() -> str
ReportTemplate.to_yaml() -> str
ReportTemplate.datasets: Mapping[str, DatasetSchema]  # read-only
ReportTemplate.bind(data: Mapping[str, Dataset], *, limits=DataLimits()) -> Report
```

TemplateError and BindingError derive from ValidationError; both have optional
location attributes like DataError. Binding checks data and existing semantic
contracts, then returns a fresh mutable Report. Template/dataset inputs are never
modified. PDF geometry/capability checks happen on export. Formats and the complete
binding vocabulary are described in the [template guide](templates.md).

## Data adapters

Import `from_csv` from `cardreport.adapters.csv` and `from_pandas` from
`cardreport.adapters.pandas`; they are not top-level exports.

```text
from_csv(path: str | Path, *, schema: DatasetSchema,
         encoding: str = "utf-8", delimiter: str = ",",
         null_values: Sequence[str] = (), limits: DataLimits = DataLimits()) -> Dataset
from_pandas(frame: pandas.DataFrame, *, schema: DatasetSchema,
            index: Literal["error", "drop"] = "error",
            limits: DataLimits = DataLimits()) -> Dataset
```

Both require an explicit schema and return an immutable snapshot. Extra columns
are retained and must contain supported cells. CSV extra columns are text; numeric
CSV fields parse as int (integer) or Decimal (number/decimal). CSV reads at most
`max_json_bytes + 1` bytes to detect excess input. Adapter errors are DataError;
CSV I/O/decoding errors preserve the original exception as their cause.
The pandas adapter imports pandas only when called; absence raises DependencyError.
See [datasets](datasets.md) for null, index, precision, encoding and lexical rules.


## Command-line interface

The installed `cardreport` command and `python -m cardreport` use the same
[documented CLI contract](command-line.md). They load template/data files, bind
through this Python API and call the existing atomic file writers. Python
applications should use ReportTemplate and Report directly rather than invoke
the argument parser.


## JSON Schema resources

```text
json_schema(kind: Literal["template", "data"]) -> str
```

Returns the installed JSON Schema 2020-12 text used by the JSON/YAML loaders
and external editors, without network access. Invalid kinds raise ValueError.
Structural errors retain `TemplateError`/`DataError` and their location attributes;
message wording is not stable. Native model and binding semantics remain separate. Both interchange envelopes accept optional string `$schema`
metadata. See [YAML and JSON Schema](yaml-and-schemas.md) for scalar conversion,
serialization, editor setup and the distinction between structural/semantic checks.
