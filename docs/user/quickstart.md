# Quickstart: embed CardReport in Python

[Documentation home](../../README.md) · [API reference](api.md)

This walkthrough creates a report from application data and returns its contents
in memory. Data loading and aggregation remain in your application.

## Install

In an existing uv project, install from PyPI:

```sh
uv add "cardreport[pdf]"
uv run python -m playwright install chromium
```

Python 3.12+ is required. Retain your project’s `uv.lock` to pin dependencies.
For the exact wheel also distributed on GitHub, use:

```sh
uv add "cardreport[pdf] @ https://github.com/arch7tect/cardreport/releases/download/v0.2.1/cardreport-0.2.1-py3-none-any.whl"
```

To use a local checkout instead:

```sh
uv add --editable /path/to/cardreport --extra pdf
uv run python -m playwright install chromium
```

For a built wheel, add its actual path and request the same extra:

```sh
uv add /path/to/cardreport-0.2.1-py3-none-any.whl --extra pdf
```

Install Chromium in the wheel environment as above. These are alternative install
routes. Package import never downloads a browser. For HTML-only use, omit the
`pdf` extra and browser setup. Browser-free PDF setup is covered under
[WeasyPrint](renderers.md#weasyprint).

## Build a report from your data

```python
from collections.abc import Mapping

from cardreport import BarChart, Card, KPI, Report


def build_report(counts: Mapping[str, int]) -> Report:
    report = Report("Call results")
    report.add(Card(KPI("Total", sum(counts.values()))))
    report.row(
        Card(
            BarChart(labels=list(counts), values=list(counts.values())),
            title="Results",
        ),
        height_mm=70,
    )
    return report


report = build_report({"Answered": 24, "No answer": 10})
```

`Card` provides the frame; `KPI` and `BarChart` provide its content. `row()` places
components side by side. Its height is in millimeters. The builder function is
also available in [examples/quickstart.py](../../examples/quickstart.py).

## Return HTML or PDF to the application

```python
report.validate()
html: str = report.to_html()
pdf: bytes = report.to_pdf(timeout=30)
```

`validate()` checks data and structure without a browser. It does not prove the
layout fits. PDF export completes layout checks before returning bytes. A web
application can use `pdf` as the response body with `Content-Type: application/pdf`;
HTML uses `text/html; charset=utf-8` when encoded as UTF-8.

HTML is self-contained and includes the supplied data. Chromium HTML requires
JavaScript when opened and reports layout failures then. The checked PDF is the
authoritative output. Rendering is synchronous; see the
[async integration example](examples.md#async-applications) for event-loop applications.

## Save a file when needed

```python
from pathlib import Path

pdf_path: Path = report.write_pdf("reports/calls.pdf")
html_path: Path = report.write_html("reports/calls.html")
```

Parent directories are created. Existing files raise `FileExistsError`; use
`overwrite=True` only when you intend replacement. A failed render leaves an
existing output untouched. See [export behavior](api.md#export-methods) for the
filesystem requirements.

## Handle errors at the application boundary

```python
from cardreport import LayoutOverflowError, RenderTimeoutError, ValidationError

try:
    report = build_report({"Answered": 24, "No answer": 10})
    pdf = report.to_pdf(timeout=30)
except ValidationError:
    # Correct invalid input or component settings before retrying.
    raise
except LayoutOverflowError:
    # Allocate more space or reduce content; do not retry unchanged input.
    raise
except RenderTimeoutError:
    # Apply the application's retry or failure policy.
    raise
```

The snippet re-raises after identifying where application handling belongs.
The boundary includes composition because constructors can reject malformed input.
Other report failures derive from [ReportError](api.md#errors). File I/O failures
use ordinary Python exceptions. Next: [layout and formatting](guide.md), then the
[original complete report](examples.md#reference-report).

## Embed a stored presentation with separate data

For reusable presentation, save a template as JSON and supply named datasets.
This complete function accepts JSON text from a file, database or request; I/O stays
in your application. It returns the same bytes as the direct Python API:

```python
from cardreport import Dataset, ReportTemplate


def render_template(template_json: str, datasets: dict[str, Dataset]) -> bytes:
    report = ReportTemplate.from_json(template_json).bind(datasets)
    return report.to_pdf()


# Repository fixture for this demonstration; use your stored JSON in production.
from examples.reference_from_template import EXAMPLES
from cardreport import datasets_from_json

template_json = (EXAMPLES / "reference_template.json").read_text(encoding="utf-8")
datasets = datasets_from_json((EXAMPLES / "reference_data.json").read_bytes())
pdf = render_template(template_json, datasets)
```

See the [template guide](templates.md) for a small complete definition and
[datasets](datasets.md) for native rows, typed JSON, single-file CSV and pandas.
The examples package is checkout-only; the function above uses installed public APIs.

For report language tags and custom number/date display, see
[language and formatting](localization.md). The [Spanish reference](examples.md#spanish-reference-report)
shows the same settings in JSON and application embedding.
