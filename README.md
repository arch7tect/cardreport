# CardReport

Compose static reports in Python with cards, KPIs, charts, tables and explicit
layout. Write a standalone HTML preview or a PDF with selectable text and vector
charts. No BI service, chart-library code or visual designer is needed.

The default renderer uses Plotly, Jinja2 and Chromium internally. A provisional
renderer protocol also supports an experimental SVG/WeasyPrint implementation. The renderer
comparison and choice are recorded in [P0 results](docs/p0-results.md).
Initial version 0.1.0. Not published to a package registry.

## Setup

Python 3.12+ and uv are required. From this checkout:

```sh
uv sync --extra pdf --locked
uv run --extra pdf playwright install chromium
```

Chromium is a separate, explicit install. Package import never downloads it.
For HTML only, use `uv sync --locked`; Playwright and Chromium are unnecessary.
For an installed wheel, request its `pdf` extra and run
`python -m playwright install chromium` once in that environment.

Verified locally on macOS with Python 3.12. Linux and Windows are not yet verified.
Linux browser system dependencies are described by
[Playwright](https://playwright.dev/python/docs/browsers#install-system-dependencies).

## First example: the original report

```sh
uv run --extra pdf python examples/reference_report.py
```

This reproduces the original Superset report using only the public CardReport API:
campaign cards, contact funnel, call outcomes, conversation table, promise-rate
card and payments calendar. It writes `output/reference_report.pdf` and
`output/reference_report.html`. The source's 4:3 page, aggregate values and
3-versus-2 promise discrepancy are preserved. Superset menu/filter icons are omitted.
See [the reference inventory](docs/reference-report.md) for provenance and comparison.

The source attachment is kept privately outside distributable files. Example
values are transcribed aggregate counts, not customer records. The supplied source
is raster-only; the new PDF uses selectable text and vector graphics. Styling uses
the bundled DejaVu Sans font, so it is not a pixel-identical screenshot.

Existing files are preserved. To deliberately regenerate your own output:

```sh
uv run --extra pdf python examples/reference_report.py --overwrite
```

## Browser-free experimental renderer

Install the optional dependencies and native libraries described in the
[WeasyPrint installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).
For example, on macOS with Homebrew, Pango must be installed and its library
folder visible to the dynamic linker. CardReport never installs system packages
or changes loader environment variables itself.

```sh
uv sync --extra weasyprint --locked
# macOS, when the native loader cannot find Homebrew libraries:
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"
uv run --extra weasyprint python examples/reference_report.py --renderer weasyprint --output output/weasyprint
```

This runs the **same reference model**, producing static HTML and PDF without
JavaScript or Chromium. It supports dashboard pages, explicit page breaks,
text/KPIs/cards, weighted rows/columns, unsplit tables and single-series bars.
Flow, line/funnel charts and multi-series bars raise `UnsupportedFeatureError`.
The reference's "Contact funnel" is a horizontal BarChart, so it is supported.
This is an experimental subset, not feature-equivalent to Chromium. Long
unbreakable text may be rejected rather than wrapped.

WeasyPrint is pinned to 70.0. Its private box-tree adapter checks actual content
bounds, with overflow canaries that fail closed on incompatibility. Matplotlib
provides SVG bars and label measurement. A native SVG preflight additionally
checks actual PDF character bounds with pdfplumber before inserting the chart. PDF fonts are verified against embedded
DejaVu identities and versions, including fonts in nested PDF resources. Layout and ticks differ between
engines; pixel parity is not promised. SVG/WeasyPrint HTML is a static preview and
may lay out differently in a browser; the checked PDF is authoritative.

## Compose a report

```python
from cardreport import Report, Page, Card, KPI, BarChart, Table, TableColumn

report = Report("Campaign", page=Page(orientation="landscape"))
report.row(Card(KPI("Clients", 21)), Card(KPI("Answered", 5)))
report.row(
    Card(BarChart(labels=["Answered", "No answer"], values=[5, 16],
                  show_labels=True), title="Outcomes"),
    Card(Table(columns=[TableColumn("name", "Name"), TableColumn("count", "Count")],
               rows=[{"name": "Promises", "count": 2}]), title="Summary"),
    widths=[2, 1], height_mm=90,
)
report.write_pdf("output/campaign.pdf")
report.write_html("output/campaign.html")
```

`Report.add` and `Report.row` return the report for chaining. `to_html()` returns
text; `to_pdf(timeout=30)` returns bytes. File methods default to `overwrite=False`;
complete output is published atomically. Files are private to the creating user
(mode 0600). The no-clobber path requires a filesystem supporting hard links
(such as APFS/ext4); exFAT and some network mounts are not supported. Rendering failure preserves an existing file.

## Components and layout

- `Card(content, title=None)` contains a leaf, Row or Column. `KPI` is content,
  not a container. `Text` has body, heading and caption styles.
- `Row(*children, widths=[...], height_mm=...)` uses relative widths after gaps.
  Without explicit height, content determines height.
- `Column(*children, heights=[...])` uses relative heights only when its parent
  supplies a fixed height. An unweighted Column is top-aligned.
- `Page(size="A4", orientation="portrait", margin_mm=10)` also supports A3, Letter,
  or explicit `(width_mm, height_mm)`. Explicit dimensions are used as given; do not also set `orientation="landscape"`.
- `Theme` controls colors, spacing, body font size and default chart height.
  The font is bundled; arbitrary CSS or font resources are not accepted.
- `BarChart` supports horizontal/vertical and grouped/stacked bars. `LineChart`
  supports categories or Python date/aware-datetime axes and `None` gaps.
  `Funnel` preserves stage order. Pass either `values` or a `series` mapping.
- `Table` takes TableColumn objects and dictionary rows. Columns support alignment,
  relative width and formats. `Currency("EUR")`, number, integer, percent and date
  are built in. Percent values are fractions, not already multiplied by 100.

Content is escaped and rendered literally. Missing values show an em dash in
KPI/table cells. Empty charts show "No data". Booleans, nonfinite chart values,
missing table keys, duplicate chart categories and naive datetimes are rejected.
Numbers use comma grouping, a dot decimal separator and half-even rounding.

## Typed API and custom renderers

Components use closed recursive unions (`Component`, `CardContent`, `Block`),
scalar aliases (`Number`, `Value`, `Format`) and Literal options. `Report.row`
has explicit `widths` and `height_mm` keywords for IDE completion. Runtime checks
remain necessary for values such as nonfinite numbers and invalid proportions.
`report.validate()` checks semantics without creating HTML or requiring a browser.

```python
from cardreport import WeasyPrintRenderer

report.write_pdf("output/static.pdf", renderer=WeasyPrintRenderer())
report.write_html("output/static.html", renderer=WeasyPrintRenderer())
```

A custom renderer implements `Renderer.render_html(doc) -> str` and
`Renderer.render_pdf(doc, *, deadline) -> bytes`. `doc` is a frozen `ReportDocument`
with immutable component blocks and normalized `ChartData`; values used for labels
are formatted before conversion to plotting floats. Strings are unescaped: each
renderer escapes for its own output format. `deadline` is an absolute
`time.monotonic()` value including prior validation work. Return checked PDF bytes
or raise a `ReportError` subclass. Geometry errors use `LayoutOverflowError`, missing
dependencies `DependencyError`, unsupported features `UnsupportedFeatureError`, and
expired deadlines `RenderTimeoutError`. A renderer must clean up its owned processes.

WeasyPrint HTML export has a fixed 30-second deadline.

The interface is provisional. There is no plugin registry or required base class.
Shared validation and file publication stay outside engine implementations;
pagination, chart drawing and geometric checks belong to each engine.

## Long reports

```sh
uv run --extra pdf python examples/flow_report.py
```

With the default Chromium renderer, use `Report(mode="flow")` to paginate blocks automatically. Top-level Table or
Card(Table) splits between rows and repeats headings/card titles. Rows never split;
nested tables and other cards stay intact. Oversized rows or blocks raise an error.
`report.new_page()` (or top-level `PageBreak()`) inserts an explicit break in either
mode. Leading, consecutive and trailing breaks do not produce blank pages.
An empty report produces one blank page.

Dashboard mode never inserts an automatic page or shrinks fonts. Overflow raises
`LayoutOverflowError`; increase page/card space or reduce content. Chart categories
and legends are also checked for missing/overlapping labels. User requests for
hidden value labels are respected; required category labels are not silently dropped.

## Runtime and limits

Chromium HTML is self-contained, needs JavaScript to draw charts, and has no interactive
controls. It shows layout errors when opened; `write_html` cannot prove browser fit.
PDF export executes the same layout with the pinned Chromium, enforces fit and
blocks external requests. PDF is authoritative; preview parity is tested in Chromium.
The HTML contains supplied data and should be treated with the same confidentiality.

A PDF call owns a short-lived worker and browser. The deadline (default 30 seconds,
maximum 300) covers preparation and the worker; a timed-out worker process tree is
stopped. Calls are synchronous; async applications should use `asyncio.to_thread`.
There is no shared browser, daemon or async abstraction. Install the package
(including editable installs) rather than relying on temporary `sys.path` edits,
so the worker can import it.

Current input bounds: 500 blocks, 12 nesting levels, 100 output pages, 2,000 rows
per table, 20 columns, 20,000 table cells per report, 500 points per chart, 30
category labels, 8 series, 200 characters per chart label. Density can require
smaller inputs. Unavailable font glyphs are rejected. Latin/Cyrillic are supported;
arbitrary Unicode scripts, PDF/A and accessibility conformance are not claimed.

Errors derive from `ReportError`: `ValidationError`, `LayoutOverflowError`,
`DependencyError`, `UnsupportedFeatureError`, `RenderError`, `RenderTimeoutError`. Missing Chromium yields an
installation hint rather than a download. No arbitrary templates or remote assets.

## Development

```sh
uv run --extra pdf pytest -q
uv run mypy
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv build

# Both renderers; native WeasyPrint libraries must be available:
uv run --all-extras pytest -q
```

The default suite skips optional WeasyPrint cases when its Python package is absent.
The full local validation runs both engines with no skips. Mypy strict mode checks
source and positive/negative consumer examples; unused expected-error annotations
fail if public typing weakens.

Open this directory in PyCharm with `.venv/bin/python`. Experiments and generated
reports are excluded from distributions. Keep local `.idea` settings out of Git.

See [design](docs/design.md), [implementation plan](docs/implementation-plan.md)
and [implementation status](docs/implementation-status.md). Compare original and
regenerated PDFs visually in addition to automated content/geometry checks.

## License

[MIT](LICENSE). Bundled DejaVu fonts retain their
[font license](src/cardreport/assets/LICENSE_DEJAVU). Plotly/Jinja2/Playwright and
Chromium retain their own licenses; Plotly's inline JavaScript includes its notice.
