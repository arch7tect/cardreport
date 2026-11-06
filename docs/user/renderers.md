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
| Multi-series bars (grouped / stacked) | Yes | Yes |
| Single-series lines (axes, markers, fill) | Yes | Yes |
| Multi-series lines | Yes | Yes |
| Funnel | Yes | Yes |
| Category colors / left or bottom category legend | Yes | Yes |
| Compact line charts in KPI cards | Yes | Yes |

Both engines support up to eight bar/line series with the same input order and
colors. WeasyPrint uses a bottom HTML swatch legend for multiple series. Legend
appearance, tick placement and value-label positions can differ between engines.
Stacked bars accumulate signed values in series order (Plotly's stack semantics),
not separate positive/negative stacks. WeasyPrint centers labels inside nonzero
stack segments and rejects labels that do not fit. Zero-segment labels sit just after
the cumulative position. All bar value labels, including single-series labels,
are rejected if they cover another bar or collide with another label.
This includes a zero label placed back inside a negative stack. Use more space or disable value labels when necessary.

Funnel stages are centered horizontal bars with connectors, category labels and
optional outside values; there is no numeric axis. Zero values and increases
are supported. Zero fill for lines and category colors for bars still require
one series in both engines. Automatic flow remains unsupported in WeasyPrint and
raises `UnsupportedFeatureError`; there is no automatic fallback.
Long unbreakable text may be rejected rather than wrapped by WeasyPrint.

Chromium checks rotated chart labels using their rotated bounds, including
collisions between category labels, values and series legends. It reserves space
for outside bar/funnel value labels with at most two measured margin adjustments.
This may reduce the plotting area; labels are not hidden, clipped or made smaller.
If labels still do not fit, collide, or leave too little plotting area, export
raises `LayoutOverflowError`. Label collision errors identify the text and its
role (`xtick`, `ytick`, `legend` or `value`). These adjustments are specific to
Chromium; WeasyPrint retains its own measured SVG layout.

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

Install the native libraries for your system, then the Python extra. CardReport
requires Python 3.12 or newer and pins WeasyPrint 70.0 because its experimental
geometry adapter depends on that version. The extra installs the matching Python
packages; system packages supply Pango and its native dependencies.

### Linux

For Ubuntu 24.04+ or Debian 12+:

```sh
sudo apt-get update
sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0
```

For Fedora 39+:

```sh
sudo dnf install -y pango
```

Then, in an existing uv project with Python 3.12+, install and inspect the runtime:

```sh
uv add "cardreport[weasyprint]"
uv run python -m weasyprint --info
```

For a CardReport checkout, use `uv sync --extra weasyprint --locked` instead of
`uv add`. These native package lists follow the
[upstream Linux instructions](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#linux)
for installing Python wheels. That guide also covers other distributions and
additional development packages needed when a dependency must build from source.
The PDF example below checks the complete CardReport renderer on your machine.

### macOS

Install Pango with Homebrew, set the library search path in the same terminal,
then install and check the Python runtime:

```sh
brew install pango
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"
uv add "cardreport[weasyprint]"
uv run python -m weasyprint --info
```

Homebrew installs Pango and its dependencies, but Python may not search Homebrew's
library directory automatically. An error mentioning `libgobject-2.0-0` can mean
the installed libraries are not on the search path; it does not necessarily mean
you need to reinstall them. `brew --prefix` selects your Homebrew installation
without hard-coding an Apple Silicon or Intel path.

For a CardReport checkout, run this from the repository root instead of `uv add`:

```sh
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"
uv sync --extra weasyprint --locked
uv run --extra weasyprint python -m weasyprint --info
uv run --extra weasyprint python examples/reference_report.py --renderer weasyprint --output output/weasyprint
```

The `export` applies to the current terminal and its child processes. Repeat it
in a new terminal, or add it to your shell configuration if you want it to persist.
In PyCharm, set `DYLD_FALLBACK_LIBRARY_PATH` in **Run Configuration → Environment
variables** to the actual path printed by `brew --prefix`, followed by `/lib`
(for example, `/opt/homebrew/lib`). Do not paste `$(brew --prefix)` into the IDE
value: it is shell syntax. A terminal export does not update an already running
IDE's environment. The same applies to services that launch your application.

The checkout example preserves existing output files. Choose another output
directory, or pass `--overwrite` only when you intend to replace generated reports.

CardReport does not install native libraries or modify environment variables.
An incompatible adapter fails explicitly.

### Windows

For native Windows x64, use 64-bit Windows Python 3.12+ and install
[MSYS2](https://www.msys2.org/) with its default directory, `C:\msys64`.
In the **MSYS2 UCRT64** terminal, install Pango:

```sh
pacman -S mingw-w64-ucrt-x86_64-pango
```

Close that terminal. In **PowerShell**, open your existing uv project and run:

```powershell
$env:WEASYPRINT_DLL_DIRECTORIES = "C:\msys64\ucrt64\bin"
uv add "cardreport[weasyprint]"
uv run python -m weasyprint --info
```

Adjust the DLL directory if MSYS2 is installed elsewhere. The environment setting
applies to this PowerShell session and its child processes; configure it in your
IDE or service environment when launching the application there. For a checkout,
replace `uv add` with `uv sync --extra weasyprint --locked`.

These steps follow the [upstream Windows Python-library installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows).
CardReport imports the Python library, so a standalone WeasyPrint executable
does not supply its dependencies. Run the PDF example below to check the complete
renderer; CardReport has not yet been verified on Windows. For WSL, follow the
[Linux instructions](#linux) inside the distribution.

### Use the renderer

```python
from cardreport import Card, KPI, Report, WeasyPrintRenderer

report = Report("Summary").row(Card(KPI("Clients", 21)), height_mm=50)
pdf = report.to_pdf(renderer=WeasyPrintRenderer())
assert pdf.startswith(b"%PDF-")
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

## Language and display settings

Both engines consume report language, formatting and resolved empty text from the
validated snapshot. They emit HTML language and PDF `/Lang`. Both support customized
numeric separators/precision within their existing chart capabilities. Chromium
date axes use preformatted sampled input positions when formatting is explicit.
See [format rules and compatibility](localization.md#chart-axes-and-compatibility).

Version 0.4.0 precomputes ChartData date tick tuples even when Formatting is absent
(the labels then use ISO). SVG consumes these sampled ticks; Chromium retains its
automatic date ticks unless Formatting is supplied. Numeric tick locations can
differ between engines. Category legends use shared HTML and consume part of the
chart rectangle. See [dashboard controls](dashboards.md).
