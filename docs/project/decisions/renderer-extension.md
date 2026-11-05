# Renderer extension

Status: implemented initial version, 2026-11-04. Supersedes the original restriction
against a second engine. The owner authorized implementation and a public GitHub
initial repository. Claude accepted the scoped plan; the response is retained locally.

Chromium remains the production default. The public Renderer protocol is provisional;
SVG/WeasyPrint is experimental, with explicit unsupported-feature errors. No registry,
entry points, renderer base hierarchy or component plugins are introduced.

Exports validate the public component tree and create a frozen ReportDocument,
including normalized chart coordinates and labels formatted from original values.
This is a data snapshot, not a geometry model. The renderer receives the snapshot
and a monotonic deadline for PDF work. Validation counts against that deadline.
The same model, validation, formats, fonts and output publication serve both engines.
Each engine owns chart drawing, pagination and geometric checks. HTML is a preview;
PDF must complete checks before returning. Chromium HTML checks geometry on opening;
experimental static HTML does not promise browser/WeasyPrint layout parity.

The WeasyPrint prototype first proves strict overflow detection, then reproduces
the reference report. Its exact-version private box-tree adapter is isolated and
must pass overflow canaries; no independent text layout engine is introduced.
Features that cannot meet the output contract are rejected rather than silently
accepted. The original source PDF and local report evidence are never published.

Implementation checkpoints: public typing and lint; validation/snapshot/renderer
boundary; browser-free reference prototype; contract and packaging checks; Claude
implementation review; privacy-reviewed initial commit and public GitHub push.

## Implemented experimental subset

The initial prototype supported single-series bars. Version 0.4.0 added lines;
0.8.0 adds up to eight series for grouped/stacked bars and lines, plus Funnel.
Dashboard/explicit pages, cards, text, KPI, unsplit tables and weighted Row/Column
layouts remain supported. Automatic flow still raises UnsupportedFeatureError.

The existing SVG adapter loops over normalized series; no chart framework or
public API/schema changes are needed. Multi-series legends reuse the measured
HTML category-legend frame only on the WeasyPrint path. Chromium remains unchanged.
Bars use signed cumulative bases for stack parity. Nonzero stacked value labels
are centered and must fit their segment; zero labels follow the cumulative
position. All value labels must not cover other bars, including overlapping
signed-stack segments. Text collision/viewport checks,
actual PDF glyph bounds and font identity checks remain mandatory.
Funnel uses centered stage bars and connector polygons, with a hidden value axis
matching the Chromium probe. Empty/zero/increasing stages keep input semantics.
Native CSS owns layout; no separate geometry engine was added.

WeasyPrint 70.0 private boxes are accessed only in `_weasy_boxes.py`. Canaries check
vertical and horizontal overflow. The adapter checks principal element bounds,
component presence, fragmentation and page count. SVG is generated at measured
placeholder dimensions and final dimensions must agree. Matplotlib uses the exact
bundled font for bounds. Native SVG preflight checks actual PDF glyph bounds with
pdfplumber to catch font-metric differences. Embedded PDF font family, identity and
version must match the bundled faces, including resources nested in PDF forms. External
URL fetching is denied except for the exact bundled font data URLs.

CSS uses break-word for this engine to avoid expensive native intrinsic-width
calculation with anywhere wrapping. Long unbreakable text may be rejected rather
than wrapped. The package does not claim equivalent native layout or pixel parity.

The Chromium Python/JavaScript boundary uses `data-kind` for components,
`data-path` for diagnostic tree locations, `data-definite` for chart sizing and
chart container IDs to index `settings.charts`. Each chart specification carries
`categoryCount` and `categoryAxis` for completeness checks. `window.cardreport`
reports either `ready/pages` or `error/kind/message`; the worker waits for one and
verifies printed page count. Plotly DOM-dependent checks remain within that engine.

Native API references: [WeasyPrint API](https://doc.courtbouillon.org/weasyprint/stable/api_reference.html)
and the installed pinned source. Private box access is not an upstream stable API.
