# Architecture

[Project documentation](README.md) · [Public API](../user/api.md)

CardReport is a Python library. Applications own data access and business metrics.
The library owns typed composition, semantic validation, rendering and output
publication. It has no service, query layer, plugin registry or custom geometry IR.

## Export path

```text
Report + frozen components
  -> semantic validation and chart normalization
  -> frozen ReportDocument
  -> Renderer (HTML preview or checked PDF)
  -> optional atomic file publication
```

`Report` is a mutable builder. Components copy their input sequences and table rows.
Validation checks structure, values, formats, glyph coverage and bounds on input
size. It creates a snapshot retaining the public component types and a read-only
mapping of normalized chart data. Chart coordinates are floats; value labels are
formatted from original values. Strings remain unescaped until output generation.
A snapshot contains no page coordinates. PDF deadlines start before validation.

## Modules

| Module | Responsibility |
| --- | --- |
| [model.py](../../src/cardreport/model.py) | Components, aliases, formats, errors and Report facade |
| [validation.py](../../src/cardreport/validation.py) | Independent semantic checks and normalization |
| [document.py](../../src/cardreport/document.py) | Frozen export and chart records |
| [renderers.py](../../src/cardreport/renderers.py) | Provisional Renderer Protocol and Chromium entry point |
| [html.py](../../src/cardreport/html.py) | Escaped shared fragments and Chromium HTML document |
| [charts.py](../../src/cardreport/charts.py) | Private Plotly specification adapter |
| [pdf.py](../../src/cardreport/pdf.py) | Owned worker, deadline, error transport and cleanup |
| [output.py](../../src/cardreport/output.py) | Atomic publication and no-clobber policy |
| [weasyprint.py](../../src/cardreport/weasyprint.py) | Experimental renderer and capability checks |

## Chromium

The HTML embeds fonts, Plotly (when needed), settings and the
[layout script](../../src/cardreport/assets/layout.js). The browser loads fonts,
places blocks on fixed pages, fragments top-level flow tables, draws charts and
checks page/component/chart-label bounds. Plotly DOM inspection stays within this
engine. `window.cardreport` signals ready/pages or a typed error; the
[worker](../../src/cardreport/_worker.py) waits, prints and checks page count.
Network requests are blocked. PDF export runs in an owned subprocess to avoid
caller event-loop conflicts and to stop the process tree on timeout/interruption.

## Experimental WeasyPrint

Capabilities are defined in the [user-facing table](../user/renderers.md#capabilities).
The engine reuses validated components, shared markup, themes and publication.
It owns native layout and checks; it does not reuse Chromium pagination code.

The [box adapter](../../src/cardreport/_weasy_boxes.py) isolates private WeasyPrint
70.0 geometry. Positive/negative bundled-font canaries fail closed on incompatibility.
Two document layout passes measure placeholders and verify final SVG placement.
[Matplotlib SVG bars](../../src/cardreport/_svg_charts.py) use isolated default settings
and the bundled font. A separate native SVG preflight checks actual PDF glyph bounds
with pdfplumber, because Matplotlib and native text metrics can differ.
[PDF checks](../../src/cardreport/_pdf_checks.py) recurse through form resources and
compare embedded font identity/version with bundled fonts.

The [worker](../../src/cardreport/_weasy_worker.py) allows only exact bundled font
URLs and rejects any other attempted fetch. Its version-specific fetcher flag is
also tied to the WeasyPrint pin. Native system-library setup belongs to the caller.
Unsupported features fail explicitly rather than switching engines or weakening checks.

## Maintenance boundaries

Keep the component vocabulary closed and strongly typed. A new component requires
validation, rendering support or explicit rejection, API documentation and tests.
New renderer implementations satisfy the shared semantic/error/output contract,
while owning their geometry and lifecycle. Do not add a registry or inheritance
framework merely to reuse helpers. See the [extension decision](decisions/renderer-extension.md)
for the rationale and the [development guide](development.md) for verification.
