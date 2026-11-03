# Initial version — 0.1.0

## Architecture update — 2026-11-04

The owner authorized the reviewed improvements and public GitHub initialization.
Current source includes typed recursive components and explicit builder keywords,
independent semantic validation, normalized chart data and a frozen export snapshot.
A provisional Renderer protocol accepts that snapshot and an absolute PDF deadline.
Chromium remains the production default; no registry or inheritance framework exists.

The optional experimental WeasyPrintRenderer reproduces the reference through the
same model without a browser or JavaScript. Supported: dashboard pages, explicit
breaks, cards/text/KPI/tables, weighted rows/columns and single-series bars.
Flow, line/funnel charts and multi-series bars explicitly raise UnsupportedFeatureError.
It uses a pinned WeasyPrint 70.0 box adapter with overflow canaries, measured SVG
placeholders and final geometry checks. Font-only fetching and actual PDF font
metadata prevent fallback to system fonts. CSS break-word avoids expensive native
minimum-width computation; long unbreakable text can be rejected instead of wrapped.
Native libraries are caller-managed; tested on local macOS only.

Strict mypy checks source and positive/negative consumer fixtures. Ruff lint and
format are separate required checks. Shared tests exercise the supported subset
across engines; Chromium-specific flow and lifecycle tests remain in place.
See [renderer extension](renderer-extension.md) and README for current contracts.

The sections below record the earlier Chromium milestone and are historical where
superseded by this update. Final refactor verification: 80 tests, strict mypy, Ruff lint/format, package build
and isolated installs passed. See [refactor review](reviews/2026-11-04-renderer-refactor.md).


Date: 2026-11-03. Local working version; no remote or publication.

## Delivered

| Stage | Result |
| --- | --- |
| P0 | Compared WeasyPrint/Matplotlib SVG and Plotly/Chromium; selected A for direct overflow checks and lower custom layout cost. Claude supported the choice. |
| P1 | Frozen public component records, copied inputs, validation/limits, formats and errors; renderer hidden. |
| P2 | Cards, KPI/text/table, custom/named pages, weighted rows/columns, offline HTML and checked PDF. |
| P3 | Bar, line and funnel; SVG/text fidelity, literal labels, bounded density, category completeness and label collision checks. |
| P4 | First example reconstructs the owner-confirmed original report with its values and layout; one-page vector PDF. |
| P5 | Automatic flow table fragmentation, repeated headings/titles, exact row accounting, oversized-row rejection and explicit page breaks. |
| P6 | Contract/integration/type/build and installed-wheel checks; platform scope is local macOS/Python 3.12 only. |

Test commands and final counts are recorded in the implementation review disposition.
Raw validation and review outputs remain under ignored local/. No checks are
claimed for Linux/Windows: the local Docker daemon was unavailable. No throughput
SLA or pixel-identical cross-browser output is claimed.

## Reference comparison

The original is one raster page (1600 x 1200 pt). The recreated file is one page
(Chromium's size quantization differs by about 0.08 pt in width), with selectable
labels and zero image XObjects. Card boundaries follow the source canvas: three
columns, then a 2-column-wide table with a KPI card, then a full-width calendar.
Values, headings, categories and the November 4 payment date are preserved.
Original 3-vs-2 promise inconsistency remains explicit.

Deliberate cosmetic differences: bundled DejaVu Sans rather than source screenshot
font; clear bold card titles; KPI labels below the value; automatically selected
numeric ticks/bar-axis padding; no Superset controls. The calendar uses correctly
formatted half-unit ticks rather than the source's rounded repeated integer labels.
These affect typography/chrome, not data or grouping. The implementation preserves
the source's 4:3 canvas instead of forcing A4. No customer identifiers are embedded.

## Small implementation decisions

- One renderer, seven small Python modules, one layout script and one template;
  no plugin/back-end architecture, service, connection pool or browser reuse.
- PDF is a synchronous public call using a private subprocess. This avoids nested
  Playwright event-loop conflicts and permits a hard deadline. psutil handles the
  owned descendant tree, including Chromium's separate process group. Native async
  API remains deferred; async callers can use asyncio.to_thread.
- pypdf is part of the PDF extra solely to reject a printed/measured page-count
  mismatch. FontTools validates bundled regular/bold glyph coverage; font licenses
  are shipped. Plotly's JavaScript is embedded once per HTML.
- Explicit custom page dimensions are used as given; a non-default orientation
  with custom dimensions is rejected. Named sizes support orientation normally.
- Leading/consecutive/trailing explicit breaks do not create blank pages. An empty
  report produces one blank page. A title cannot become an orphaned first page.
- PDF/HTML publication uses same-directory atomic link/replace. Output permissions
  remain private (0600); APFS/ext4-style hard-link support is required for default
  no-clobber writes. This is preferable to an incomplete-file fallback.
- Error output is parsed from the worker's final JSON line, tolerating preceding
  warnings. Missing browser/dependencies produce a setup hint, not a download.

## Limitations

HTML requires JavaScript for local rendering and validates layout only when opened.
The standalone HTML holds input data; it is not a sanitized export. Preview parity
is scoped to the tested Chromium. Static no-JS HTML serialization is not implemented.
No arbitrary HTML/CSS/JS, images, templates, runtime font files, user Plotly objects,
PDF/A, accessibility certification, global locale support or arbitrary scripts.
Limits and supported input formats are documented in README. Original attachment
and generated reports remain ignored; no external publication has occurred.
