# CardReport design

> Update 2026-11-03: the owner authorized typed components, independent validation
> and a provisional renderer extension with an experimental SVG/WeasyPrint path.
> See [renderer extension](renderer-extension.md); the original decision below is historical.


Status: reviewed design baseline, implemented as local v0.1. Current delivered
behavior and explicit deltas are recorded in [implementation status](implementation-status.md)
and README; use those for executable setup and API usage. Candidate A was selected
through the comparison in [P0 results](p0-results.md). Design-stage wording below
is historical where superseded by the implementation status.

Date: 2026-11-03. Owner: Oleg Orlov. Working package name: `cardreport`.

## 1. Problem and agreed direction

Reproduce print-oriented dashboard reports similar to a supplied Superset report
without operating Superset or exposing a charting library to callers. The initial candidate was Python + Plotly + Jinja2 + Playwright. The user later
explicitly asked to retain a browser-free, JavaScript-free alternative for review.
No visual editor or interactive charts are required. Cards and explicit layout are first-class features.

The original attachment was supplied by the owner and inspected visually; see
[reference inventory](reference-report.md).
The shared conversation is requirements context, not verified output evidence:
The owner-supplied conversation is retained in private project context.
Synthetic reports support initial engine experiments. The owner requires the
original Superset report as the first public-API usage example; completion requires
the original PDF/source data and a recorded reference comparison. Never reconcile inconsistent business
metrics automatically (the conversation mentions KPI 2 vs table 3 promises).

This document specifies intended behavior. It does not claim working components,
verified fidelity or performance. Claude's advisory review is recorded separately;
reviewer agreement does not replace implementation verification or owner approval.

## 2. Goals and non-goals

Goals: a small typed Python API; consistent cards, charts and tables; constrained
layout; standalone HTML preview; PDF with selectable text and SVG-based charts;
no network at rendering time; actionable errors; reusable themes.

Non-goals for v0.1: BI/data loading, SQL, aggregates, visual editor, interactive
controls, web service, arbitrary HTML/CSS/JavaScript, remote resources, user
Jinja templates, custom Plotly figures/kwargs, arbitrary coordinates, chart plugin
registry, serializable public JSON schema or multiple rendering backends.
The application owns data access, authorization and metric correctness.

## 3. Proposed public API

This example defines the public API implemented in v0.1:

```python
from cardreport import (
    Report, Page, Row, Column, Card, KPI, Funnel, BarChart,
    Table, TableColumn, Theme,
)

report = Report(
    title="Campaign report",
    mode="dashboard",
    page=Page(size="A4", orientation="landscape", margin_mm=10),
    theme=Theme.light(),
)
report.row(
    Card(KPI("Clients", 21)),
    Card(KPI("Answered", 5)),
    Card(KPI("Promised to pay", 2)),
)
report.row(
    Card(Funnel(labels=["Attempted", "Answered", "Promised"],
                values=[21, 5, 2]), title="Contact funnel"),
    Column(
        Card(BarChart(labels=["Answered", "No answer"], values=[5, 16]),
             title="Call outcomes"),
        Card(KPI("Answer rate", 5 / 21, format="percent")),
        heights=[2, 1],
    ),
    widths=[2, 1],
    height_mm=100,
)
report.add(Card(Table(
    columns=[TableColumn("client", "Client"), TableColumn("status", "Status")],
    rows=[{"client": "Client A", "status": "Answered"}],
), title="Details"))
report.write_html("output/report.html")
report.write_pdf("output/report.pdf")
```

`Report.add(block)` and `Report.row(*children, **layout)` append and return the
report; `row` is convenience for `add(Row(...))`. A report starts with one page;
`report.new_page()` starts another in dashboard mode. In flow mode, `PageBreak()`
is a top-level block. Title/subtitle appear only at the beginning and count
against usable height. Page headers/footers and mixed page sizes are deferred.

`Page` is settings, not a content container. One page size/orientation applies to
the whole report. Input containers use immutable records and defensively copy
sequences; the Report builder is mutable, and export snapshots its content.
Building and mutating a report concurrently is unsupported.

Nesting: Report, Row and Column accept Card, Row, Column, Text and bare leaf
components; Card accepts one leaf, Row or Column (not another Card directly).
PageBreak is top-level and flow-only. Rows/Columns have at least one child.
An unweighted Column is top-aligned even when assigned extra height. Bare leaves
have no card decoration or padding. Cycles and unsupported containers fail validation.
Until Slice 2 is implemented, requesting flow mode raises a clear unsupported-mode
error. Dashboard tables never silently paginate.

### Components and data

- `Card(content, title=None)`: one child block, optionally a Column; themed border,
  background, radius and padding. It is a container, not a synonym for KPI.
- `KPI(label, value, format="number", note=None)`: value can be numeric or plain
  text. Optional explanatory note; trend/delta widgets deferred.
- `Text(text, style="body")`: plain escaped text; styles body, heading, caption.
- `BarChart(labels, values=None, series=None, orientation="vertical",
  mode="grouped", show_labels=False, legend=True, value_format="number")`.
  Exactly one of values or series; series is an ordered mapping of name to values.
  Supported modes: grouped and stacked.
- `LineChart(x, values=None, series=None, x_kind="category", legend=True,
  value_format="number")`: category or date axes, with an explicit SVG trace.
- `Funnel(labels, values, show_labels=True, value_format="number")`: stages are
  shown in caller order. Values must be nonnegative; increases are allowed and
  never interpreted automatically as conversion rates.
- `Table(columns, rows, empty_text="No data")`: rows are mappings; TableColumn
  contains key, label, format, alignment and optional positive width weight.

Inputs use sequences/mappings, strings, finite int/float/Decimal, dates and
aware datetimes where applicable; no pandas requirement. Decimal chart coordinates
are converted to float (loss documented); formatted table/KPI amounts retain
Decimal precision. Date/time axes use ISO representations and normalize aware
datetimes to UTC. Naive datetimes are rejected. Categories preserve input order.
Missing table keys, length mismatches, duplicate column keys, nonfinite values,
invalid enums and invalid size weights produce `ValidationError` with a block
path. Extra row keys are ignored. None renders an em dash in tables/KPIs and
is a gap in line charts; bar/funnel values cannot be None. Empty series produce a
"No data" panel; conflicting series lengths still fail. Booleans are not numbers.

Formats: number (grouped, up to two fractional digits), integer, percent (fraction
0..1 displayed as 0..100%, without clamping), currency with explicit currency
code via `Currency("USD")`, and date. Numeric formats use comma thousands,
dot decimals, ROUND_HALF_EVEN; integer has zero decimals, percent one, currency
two plus the supplied three-letter code (no currency-specific minor-unit inference).
Dates use ISO YYYY-MM-DD. Rounding and locale are fixed/documented for v0.1; no machine-locale
behavior. Text is never interpreted as markup, including chart labels.

## 4. Layout contract

The layout rules below describe the common desired behavior. Browser-specific
measurement/pagination is candidate A; candidate B must prove an equivalent or
explicitly revised contract through the backend decision gate.

Use physical millimeters for page margins, padding, gaps and optional row
height. Widths/heights arrays are positive relative weights, not percentages or
pixels. The renderer converts mm to CSS px at 96 px/inch for chart measurement.

`Row(*children, widths=None, height_mm=None)` divides available width after gaps.
Default widths are equal. Children stretch to equal outer height. With no explicit
height, use the largest child's intrinsic/default height. Card padding and title
are subtracted before allocating space to content.

`Column(*children, heights=None)` stacks children. Without heights it uses intrinsic
heights. With heights it requires a definite height allocated by its parent and
splits remaining height after gaps proportionally. A weighted Column in an
automatic-height Row is a validation error (no circular size inference).

Default theme: 4 mm gap and card padding, 28 mm KPI card minimum, 60 mm chart body
height when unconstrained, a 35 mm chart body minimum, and minimum 9 pt body text. Row height and
card minimums include padding, title and border; chart body sizes exclude them.
Weighted allocation never redistributes: a share below a minimum raises
LayoutOverflowError with the required and allocated size. Table/text measure natural
height. A constrained parent may allocate a different chart height, but may not
violate component minimums. Wrapped text increases intrinsic height. Table cells and ordinary text
wrap; unbreakable long tokens may break at any character. Data is never truncated
or silently hidden. Dense axes/legends must be bounded by tested limits in the
implementation; unsupported density fails, rather than silently omitting labels.

Dashboard mode: each explicit page is a fixed printable rectangle. Rows cannot
fragment. Export measures every block and page after fonts/charts settle; any
horizontal/vertical overflow fails with page and block path, required size and
available size. No automatic shrink-to-fit, page insertion or font reduction.

Flow mode (second implementation slice): top-level blocks flow over uniform pages.
Ordinary cards and rows are indivisible; move them to the next page when needed.
An indivisible block larger than an empty page fails. Only a top-level Table or
Card(Table(...)) may split between rows; repeat column headings and the card title
on continuation pages. Table rows do not split, and one row taller than the
available empty-page body fails. Tables inside Row/Column remain indivisible.
Blank pages, title-only fragments and lost/duplicate rows are test failures.
Candidate A flow uses an explicit browser-measured pagination pass, creating page containers
and table fragments, not merely hoping CSS break-inside handles all edge cases.

Theme provides named fonts, colors, spacing and component defaults; controlled
values only, no raw CSS. Package a licensed Latin/Cyrillic font with its notice
before rendering ships. Bundle identical font bytes into HTML and PDF input.
Missing supported glyphs must be caught by fixtures; wider Unicode coverage is
not promised for v0.1. Themes and layout are fixed at export; no responsive reflow
that changes the printed page at different viewport sizes.

## 5. Rendering architecture

Candidate A only: small concrete modules; no engine interfaces or dependency-injection framework:

- `model.py`: typed content records, Report builder, validation and exceptions.
- `layout.py`: static nesting, weights, minimum and limit validation; page/container metadata.
- `charts.py`: private component-to-Plotly conversion, SVG-only trace allowlist.
- `html.py`, `templates/`, `assets/`: Jinja composition, CSS, readiness script/fonts.
- `pdf.py`: optional Playwright import, context lifecycle, measurement and printing.

For candidate A, CSS plus the browser layout script is the only layout engine.
Python does not independently calculate text/table geometry. All measured fit
and pagination decisions happen in the browser.

Pipeline: snapshot -> validate -> build private figures -> Jinja HTML -> browser
layout/chart readiness -> overflow/pagination checks -> Chromium PDF bytes -> file.
For candidate A the HTML writer needs Jinja2 and Plotly, not Playwright. The standalone output embeds
Plotly JS once plus its data, styles and fonts, so it needs a JS-enabled browser
but offers no hover, zoom, selection or chart toolbar. `staticPlot` is enabled.
PDF is authoritative; candidate A only guarantees preview fit in the tested
Chromium revision. Screen and print use shared geometry rules, with @page for
printing. Manual browser printing is outside the supported output contract.
Generated HTML can contain every supplied chart datum and must be handled with
the same confidentiality as the input; it is not a sanitized export.

Rendering order: set print media and fixed viewport/page settings first; load
every bundled font face before the first chart render; allocate containers; await every Plotly.newPlot promise; perform
final sizing; await any Plotly resize/relayout promises; wait for document.fonts.ready
and a final layout frame; measure, paginate and revalidate. A namespaced readiness
object reports phase, completed charts and failures. No sleep-based readiness or
first-SVG heuristic. HTML preview uses this same layout script and displays errors.
`write_html` validates input but cannot guarantee browser-fit without executing it;
its documented fit validation happens when opened. PDF always checks fit before
writing a successful output.

Playwright exports using print media, explicit page geometry/CSS @page, background
printing and scale 1. No screenshots, Kaleido or intermediate PNG conversion.
The chart adapter constructs graph_objects SVG traces explicitly; no automatic
WebGL selection. v0.1 supports bar, SVG line and funnel only. For candidate A, pass the bundled font family explicitly, disable MathJax with
typesetMath=false, escape &, < and > in all Plotly text fields, and use explicit
category ticks. Chart labels do not wrap in v0.1; use bounded margins and reject
label overlap/overflow. Use fixed chart label sizes (uniformtext show or outside
placement), never Plotly auto-shrink/hide. Test $x$, &amp;, literal <br>, U+2028,
U+2029 and HTML comment/script delimiters; serialize them safely. No arbitrary images,
Canvas/WebGL or raw figure escape hatch. Vector fidelity is an acceptance gate,
not an assumption about Chromium. Inspect produced PDFs for raster image objects
and extract expected text; also inspect visual output for clipping and missing marks.

## 6. Runtime, errors and resource ownership

Candidate-A dependencies: Jinja2, Plotly and Playwright; Chromium is
installed separately through its supported command. Never download a browser at
import time or silently install OS packages. Missing extra/browser yields
`DependencyError` with the setup command. No global browser or application server.

`Report.write_pdf` is a synchronous convenience wrapper owning its short-lived
browser. A sync `PdfRenderer` context may reuse one browser sequentially across
reports; each export gets an isolated context/page closed in finally. No thread-safe
sharing or parallel rendering in v0.1. Active asyncio-loop callers use a worker
thread; a native async API is deferred and the sync wrapper must fail clearly in
an active loop instead of invoking nested asyncio.run.

Export deadline defaults to 30 seconds and covers browser launch, font/chart
readiness, layout and print. Exceeding it yields `RenderTimeoutError`; all owned
resources close. Error types: ValidationError, LayoutOverflowError,
DependencyError, RenderError, RenderTimeoutError, all under ReportError. Errors
identify component paths and phase without dumping report data by default.

File methods create missing parent directories, refuse existing targets unless
`overwrite=True`, render before publication, write to a sibling temporary file and
publish without clobbering on the default path. Preserve existing output on any
failure, including races. Bytes/HTML-string functions may be added alongside file
methods during implementation, without exposing backend objects. Do not promise
byte-identical PDFs: metadata and browser versions may vary.

## 7. Content and resource boundary

Enable Jinja HTML autoescape explicitly. Serialize chart data with an HTML-safe
JSON encoder, including protection against closing script tags. Plotly's label
markup must also be escaped/disabled so labels display literally, not merely
escaped for the outer HTML. Validate theme values rather than interpolating raw CSS.
No user templates, raw HTML, remote URLs, arbitrary scripts or local file paths.

PDF input is an in-memory document, not navigation to a user-controlled URL.
Use a fresh browser context with service workers blocked; deny HTTP(S), file and
other external fetches. Resources are inline or generated data/blob resources only.
Do not disable Chromium security mechanisms for convenience. This is bounded
report rendering, not an isolation service for hostile executable templates.
Set documented finite limits for rows, points, text, nesting and pages during the
first implementation slice; test exact limits. Limits must reject before partial
output, not drop data. Browser deadline also bounds expensive layout work.

## 8. Delivery and verification

[Implementation plan](implementation-plan.md) breaks these delivery slices into
ordered milestones and acceptance gates. All implementation remains pending.

Current delivery: uv src-layout scaffold, MIT license, README, design, review,
local PyCharm environment and CodexHome project registration. No release/remote.

Slice 1: model, cards, dashboard rows/columns, KPI/text, bar/line/funnel/table,
packaged assets, standalone HTML and PDF, bounded inputs and documented errors.
Acceptance fixtures: minimal KPI; synthetic campaign dashboard; nested weighted
layout; empty data; long English/Cyrillic text; deliberate overflow; literal hostile
labels including closing-script syntax; browser unavailable; JS/font failure.
Check PDF page count, text extraction, no raster image objects, visual alignment,
zero external requests, original output preservation and browser cleanup.

Slice 2: flow pagination and repeated table/card headings. Verify multiple pages,
exactly-once row identity, no split rows, oversized-row rejection, explicit breaks,
no blank pages and nested unsplittable table behavior.

Slice 3 only when needed: convenience sequential PdfRenderer, additional controlled
themes and stable packaging for distribution. No performance targets until measured.
Slice 1 adds a dev dependency group for the test runner and PDF parser.
Candidate A integration tests use the locked Playwright browser, packaged fonts and known page
size. Do not use fragile PDF byte hashes as the only regression signal. Build and
install the wheel in a clean environment to verify template/font/JS packaging.

## 9. References and unresolved validation

The [backend decision gate](backend-decision.md) takes precedence over candidate-A
implementation details. The initial Claude review and backend review are linked
from [the review disposition](reviews/2026-11-03-disposition.md).

- [Playwright page.pdf](https://playwright.dev/python/docs/api/class-page#page-pdf):
  PDF printing options and media selection.
- [Plotly export documentation](https://plotly.com/python/static-image-export/):
  WebGL traces can introduce raster content; the adapter must force SVG types.
- [Jinja autoescape](https://jinja.palletsprojects.com/en/stable/api/#autoescaping):
  configure escaping explicitly.

Remaining implementation gates: original-reference availability; browser/PDF vector
fidelity; exact font selection and redistribution notice; tested density/resource
limits; flow-pagination correctness; packaging of all offline resources. These are
release checks, not evidence of implemented behavior. No throughput, accessibility
conformance, PDF/A or arbitrary-script/glyph support is claimed.
