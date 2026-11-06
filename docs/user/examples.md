# Examples and integration

[Documentation home](../../README.md) · [Quickstart](quickstart.md)

Start with [examples/quickstart.py](../../examples/quickstart.py) for a small builder
that accepts application data. The complete examples below live in the repository;
`examples` is not an importable part of the installed wheel. Run their imports from
a checkout root, or copy the builder into your application. No renderer-library
imports are needed to compose reports.

For a self-contained JSON alternative, [quickstart_template.py](../../examples/quickstart_template.py)
keeps the template and named datasets in one Python file and creates the same
KPI/bar report as the [README component example](../../README.md#use-from-python).
Its `build_report(data_json)` accepts replacement data without changing the template.
Running the file generates HTML/PDF in memory and prints their sizes.

For a self-contained example of space-grouped values in a dense table/chart row
and a full-width alternative, see [dense grouped bars](guide.md#dense-grouped-bars-with-space-grouping).

## Reference report

The first complete example is [reference_report.py](../../examples/reference_report.py),
which reconstructs the original supplied dashboard: progress cards, contact funnel,
call outcomes, conversation table, promise-rate card and payment calendar.

```python
from examples.reference_report import build_report

report = build_report()
html = report.to_html()
pdf = report.to_pdf()
```

The example preserves the original 4:3 canvas and aggregate values. The source's
3-versus-2 promise discrepancy is preserved rather than reconciled. The contact
funnel is a horizontal BarChart, so the whole example works with both renderers.
The source PDF stays private; it is not required to run the example. The Python
file contains the transcribed aggregate data. See the
[reference inventory](../project/history/reference-report.md) for provenance.

### The same report from a template

[reference_template.json](../../examples/reference_template.json) contains the layout;
[reference_data.json](../../examples/reference_data.json) contains the aggregate data.
[reference_from_template.py](../../examples/reference_from_template.py) loads both:

```python
from examples.reference_from_template import EXAMPLES, build_report as bind_reference

report = bind_reference()
pdf = report.to_pdf()
second = bind_reference(EXAMPLES / "reference_data_second.json")
second_pdf = second.to_pdf()
```

The second dataset doubles counts and updates the complete dynamic labels while
retaining rates. Both use the same presentation, which produces the same normalized
model as the original Python builder. [Dataset adapters](datasets.md) can replace
the JSON inputs with CSV or pandas snapshots; the template is unchanged.

The same report is available as [YAML presentation](../../examples/reference_template.yaml)
and [YAML datasets](../../examples/reference_data.yaml). Use the installed CLI or
`ReportTemplate.from_yaml` with `datasets_from_yaml`; see the
[YAML embedding guide](yaml-and-schemas.md).

## Flow dashboard

For a dashboard that flows across pages, see the [flow dashboard guide](guide.md#dashboards-across-pages)
and [runnable example](../../examples/flow_dashboard.py).

```sh
uv run --extra pdf python examples/flow_dashboard.py
```

## Multiple series and funnel

[series_report.py](../../examples/series_report.py) composes grouped bars, horizontal
stacked bars, dated lines with a gap, and a funnel on one page. All values are
synthetic. The same builder works with both renderers, without engine-specific
chart options or renderer-library imports.

```python
from examples.series_report import build_report as build_series_report
from cardreport import WeasyPrintRenderer

report = build_series_report()
pdf = report.to_pdf(renderer=WeasyPrintRenderer())
assert pdf.startswith(b"%PDF-")
```

From a checkout, run `uv run --extra weasyprint python examples/series_report.py`;
add `--renderer chromium` with the PDF extra installed to compare engines. Outputs
are not overwritten unless `--overwrite` is supplied. See [renderer behavior](renderers.md#capabilities)
for stacked value-label fit and legend differences.

## Spanish reference report

[spanish_report.py](../../examples/spanish_report.py) binds
[spanish_template.json](../../examples/spanish_template.json) to
[spanish_data.json](../../examples/spanish_data.json). It translates the reference
labels, preserves the aggregate discrepancy, and adds a typed report-date KPI.
Both that KPI and the payment-calendar axis show a custom Spanish month-name pattern. The
payment category is a tagged date in data and a date field in the template.
Preformatted text categories and notes are translated by the application; the engine formats native numbers/dates.

```python
from examples.spanish_report import build_report as build_spanish
from cardreport import WeasyPrintRenderer

spanish = build_spanish()
html = spanish.to_html()
pdf = spanish.to_pdf()
static_pdf = spanish.to_pdf(renderer=WeasyPrintRenderer())
assert "4 de noviembre de 2026" in html
```

This uses the same public embedding API as the English reference. Installation
from a wheel provides the library; example source/JSON files live in the repository
and source distribution. See [language and formats](localization.md) for settings.

## Long table

[flow_report.py](../../examples/flow_report.py) demonstrates a 120-row table with
generated example transactions, repeated column headings and card titles. It
creates `Report("Account summary", mode="flow")` and adds a top-level `Card(Table(...))`.
The renderer determines page breaks; the application does not split the rows or
create a separate table per page. It requires Chromium:

```python
from examples.flow_report import build_report as build_flow_report

flow = build_flow_report()
pdf = flow.to_pdf()
```

Do not put the table inside a Row/Column when it needs automatic splitting.
See [flow layout](guide.md#long-tables-with-flow) for a self-contained Python
example and supported blocks. The [README gallery](../../README.md#reports-in-practice)
shows the first two PDF pages, including the transition from `ROW-027` to `ROW-028`.

## Async applications

Export methods are synchronous. Offload rendering from an event loop using
`asyncio.to_thread`; use an application-owned timeout and concurrency policy.
Build a separate report per job and do not mutate a report during export.

```python
import asyncio
from cardreport import Card, KPI, Report


async def make_pdf() -> bytes:
    report = Report("Job summary").add(Card(KPI("Completed", 12)))
    return await asyncio.to_thread(report.to_pdf, timeout=30)


pdf = asyncio.run(make_pdf())
```

The final line is for a standalone program. Inside an already-running event loop,
use `pdf = await make_pdf()` instead. Cancelling the awaiting coroutine does not
stop its background thread; the renderer's own deadline remains responsible for
bounding the work. There is no shared browser pool in the library.

For a web endpoint, return the resulting bytes with `Content-Type: application/pdf`;
framework response objects and storage clients stay in your application. See
[error handling](quickstart.md#handle-errors-at-the-application-boundary).


## Operations dashboard

[operations_report.py](../../examples/operations_report.py) builds a dashboard with
large KPIs, compact LineCharts and a category-colored ranking with a left legend.
Both renderers support it. The [template](../../examples/operations_template.json)
and [data](../../examples/operations_data.json) are separate and import-safe.
Snapshot numbers come from an operations dashboard screenshot; trend data is explicitly
synthetic, and the unavailable fifth agent name is marked.

See the [dashboard tutorial](dashboards.md) for Python embedding and layout rules.
