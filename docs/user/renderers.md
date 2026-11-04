# Renderers

[Documentation home](../../README.md) · [API reference](api.md#renderers)

A Report uses Chromium by default. Pass a renderer to an export method to choose
another implementation; the component model stays the same. Reports returned by
ReportTemplate.bind have exactly these capabilities and geometric checks.

## Capabilities

| Feature | ChromiumRenderer | WeasyPrintRenderer |
| --- | --- | --- |
| Status | Default | Experimental subset |
| PDF runtime | Chromium via Playwright | WeasyPrint native libraries; no browser |
| HTML | Self-contained, requires JavaScript | Self-contained static preview |
| Dashboard / explicit pages | Yes | Yes |
| Cards, text, KPI, unsplit tables | Yes | Yes |
| Weighted rows/columns | Yes | Yes |
| Automatic flow / split tables | Yes | Unsupported |
| Single-series bars | Yes | Yes |
| Multi-series bars | Yes | Unsupported |
| Lines / funnels | Yes | Unsupported |

A one-series `series` mapping is also supported by WeasyPrint. Grouped/stacked mode
has no multi-series distinction in that case. Unsupported features raise
`UnsupportedFeatureError`; there is no automatic fallback to another renderer.
Long unbreakable text may be rejected rather than wrapped by WeasyPrint.

PDF is the authoritative checked result. Chromium HTML validates layout when
opened; WeasyPrint HTML can lay out differently in another browser. Rendering
is offline with bundled fonts; labels are literal and charts are noninteractive.
Only macOS/Python 3.12 has been verified locally. See the upstream installation
instructions for other platforms; support there is not yet claimed.

## Chromium

For an existing project, use the [quickstart installation](quickstart.md#install).
For a checkout, use:

```sh
uv sync --extra pdf --locked
uv run --extra pdf python -m playwright install chromium
```

The browser install is explicit, never performed at import time. Linux browser
system dependencies are described in the
[Playwright installation documentation](https://playwright.dev/python/docs/browsers#install-system-dependencies).

```python
from cardreport import Card, ChromiumRenderer, KPI, Report

report = Report("Summary").row(Card(KPI("Clients", 21)), height_mm=50)
pdf = report.to_pdf(renderer=ChromiumRenderer())
```

Omitting `renderer` gives the same default. HTML-only export needs the core package
but no Playwright/Chromium installation; opening that HTML still requires JavaScript.

## WeasyPrint

Install the optional extra in an existing uv project:

```sh
uv add "cardreport[weasyprint] @ https://github.com/arch7tect/cardreport/releases/download/v0.2.1/cardreport-0.2.1-py3-none-any.whl"
```

Or, from a checkout, use `uv sync --extra weasyprint --locked`. Follow the
[WeasyPrint native-library installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).
On macOS, Pango must be installed. If the loader cannot find Homebrew libraries,
set the path in the environment that starts your application, for example:

```sh
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"
```

CardReport does not install native libraries or modify environment variables.
The extra pins WeasyPrint 70.0 because its experimental geometry adapter depends
on that version. An incompatible adapter fails explicitly.

```python
from cardreport import Card, KPI, Report, WeasyPrintRenderer

report = Report("Summary").row(Card(KPI("Clients", 21)), height_mm=50)
pdf = report.to_pdf(renderer=WeasyPrintRenderer())
html = report.to_html(renderer=WeasyPrintRenderer())
```

WeasyPrint HTML rendering has a fixed 30-second
worker deadline. PDF uses the export method's `timeout`, default 30 seconds.
Ticks and layout can differ between engines; pixel parity is not promised.
Give KPI cards an explicit row height as above: their natural-height layout can
fail the experimental engine's geometry check.

## Custom renderers

The extension interface is provisional. Implement its two methods; no registry
or base class is required. This complete example delegates to the default engine
while exposing a place for application-specific behavior:

```python
from cardreport import Card, ChromiumRenderer, KPI, Renderer, Report, ReportDocument


class ApplicationRenderer:
    def render_html(self, doc: ReportDocument) -> str:
        return ChromiumRenderer().render_html(doc)

    def render_pdf(self, doc: ReportDocument, *, deadline: float) -> bytes:
        return ChromiumRenderer().render_pdf(doc, deadline=deadline)


renderer: Renderer = ApplicationRenderer()
report = Report("Summary").row(Card(KPI("Clients", 21)), height_mm=50)
pdf = report.to_pdf(renderer=renderer)
```

Export methods validate first, then pass a frozen snapshot containing public
component blocks and normalized chart data. The deadline is an absolute
`time.monotonic()` value, including time already spent preparing the snapshot.
Each renderer owns pagination, chart drawing, font readiness and geometric checks.
It must return checked PDF bytes or a documented ReportError subclass, reject
unsupported features explicitly and clean up owned processes on failure.
Strings are unescaped; escape for the output format. Do not expose private renderer
objects through public components. See [extension data](api.md#extension-data).
Implementation rationale belongs in [project architecture](../project/architecture.md).
