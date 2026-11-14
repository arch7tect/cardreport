# What's new

User-visible changes to CardReport. Installation and usage start in the
[README](README.md). Version numbers come from `pyproject.toml`.

## Unreleased

## 0.9.1 — 2026-11-14

- Fix datetime display: preserve supplied offsets by default instead of forcing
  UTC. Optional `Report(timezone="Asia/Nicosia")` / template `report.timezone`
  converts display consistently across text, KPI, tables and both chart engines.
- Interpret datetimes without offsets as UTC in Python, JSON, YAML, CSV and pandas.
  Calendar dates never shift; date extraction occurs after display-zone conversion.
- Add the Jinja `datetime` filter with an optional LDML pattern.
- Always use shared date-axis labels in Chromium, including when formatting is
  omitted. Chart positions still represent the same instants. Full ISO timestamps
  can require a wider chart or a shorter `datetime_format`; overlaps still fail
  explicitly. Reserve space between date ticks and the numeric axis.
- Behavior change: select `timezone="UTC"` explicitly to retain prior UTC display.
  Canonical serialization adds `+00:00` to timestamps received without an offset.

## 0.9.0 — 2026-11-14

- Add Jinja text substitutions in template report titles/subtitles, card titles,
  Text content and KPI labels/notes. Use `{{ datasets.summary.report_date }}` with
  existing one-row datasets; dates and numbers inherit report formatting.
- Add explicit `date`, `number`, `integer`, `percent` and `currency` text filters.
  Template loading checks references and filters; binding validates final text.
  JSON, YAML, CLI and both renderers share the same behavior.
- Add a daily report example and document formatting, escaping and located errors.
- Compatibility: `cardreport.template/1` is retained, but literal Jinja delimiters
  in these six text positions now require raw escaping. Other strings, bound data
  and the direct Python model API remain literal.


## 0.8.5 — 2026-11-13

- Renderer implementers: `Renderer` is now an abstract base class. Change
  `class CustomRenderer:` to `class CustomRenderer(Renderer):` and implement both
  `render_html` and `render_pdf`. Incomplete subclasses cannot be instantiated.
  Existing custom metaclasses must be compatible with `ABCMeta`; a protocol must
  not inherit `Renderer`. Type checkers require subclassing, while existing duck-typed
  implementations still work at runtime. Method signatures and built-in exports are unchanged.
- Improve PyCharm type inference for binary render workers, adapters and template
  traversal, without suppressing inspections or changing runtime validation.
- Internal refactoring adds typed SVG payloads, separates chart drawing from label
  checks and reuses model defaults in the template binder. No template/data schema
  or rendering behavior changes are intended.

## 0.8.4 — 2026-11-10

- Fix WeasyPrint cards without a parent-supplied height collapsing around tables
  and other content. Natural-height cards now grow with their contents; no fixed
  row-height workaround is required.
- Cards in fixed-height rows and weighted columns retain their allocated space.
  Oversized cards and reports still fail layout checks; nothing is shrunk or hidden.

## 0.8.3 — 2026-11-10

- Layout failures now carry optional typed diagnostics: component path, page,
  measurement basis, available dimensions and directional overflow in millimetres.
  Both renderers preserve these details through PDF worker processes.
- Applications can expose the data-free diagnostic without forwarding chart label
  values from exception messages. Missing measurements and old errors remain valid.
- Measurements describe current layout, not a guaranteed resize. Rendering and
  strict overflow rejection are unchanged.

## 0.8.2 — 2026-11-07

### Fixed

- PDF export accepts finite positive timeouts above five minutes in Python and
  the CLI. The default remains 30 seconds; long deadlines retain process cleanup
  and use bounded internal waits to avoid platform timeout overflow.

### Documentation

- The layout guide and agent skill explain A4 space budgets, genuine label
  collisions and compact/full-width alternatives, with an executable synthetic
  example using space-grouped numbers.

- A portable CardReport skill guides agents through report composition, layout,
  rendering and verification, with an entry link near the beginning of README.
  Skill links and Python snippets participate in the documentation checks.

## 0.8.1 — 2026-11-06

### Fixed

- Chromium no longer rejects separated, rotated chart labels because their
  axis-aligned bounding boxes overlap. Real text collisions still fail and
  identify the conflicting labels.
- Chromium reserves measured space for outside bar and funnel value labels,
  allowing narrow charts to fit without hiding or shrinking text. Charts that
  remain too crowded still raise `LayoutOverflowError`.
- WeasyPrint dependency errors preserve the underlying loader error and link to
  the renderer setup guide for all platforms.
- macOS setup documents the complete Homebrew, library-path and runtime-check
  sequence, including checkout usage and PyCharm environment settings.

### Documentation

- A runnable flow dashboard combines whole card rows with a table that continues
  across pages, with guidance on A4 space and explicit page breaks.

## 0.8.0 — 2026-11-05

### Added

- WeasyPrint supports multiple bar series in grouped/stacked modes, in either
  orientation, and multiple line series with dates, gaps and optional markers.
- Funnel charts render as centered vector stages with connectors and optional
  value labels in WeasyPrint.
- Series legends reuse the measured HTML layout. Stacked values preserve signed
  accumulation; labels must fit their segments and never silently shrink.
- A complete synthetic multi-series/funnel example works with both engines.

### Changed

- Bar label checks now also reject text covering another bar, including
  single-series charts and overlapping signed-stack segments.

Public Python APIs and JSON/YAML schemas are unchanged. Automatic table flow
remains available only with Chromium.

## 0.7.1 — 2026-11-05

### Fixed

- Remove the full JSON Schema data walk that slowed loading in 0.7.0. The concrete
  decoder reads cached key/type metadata and scalar patterns from the same schema.
- Validate decoded values once during Dataset construction; retain row/column,
  value and aggregate limits, located errors, and binding validation.
- Keep full template validation and exported schema documents unchanged. No
  validation-disabling option or separate envelope schema is needed.
- Add malformed-input parity tests and a repeatable JSON/YAML loading benchmark.

## 0.7.0 — 2026-11-05

### Changed

- Use the packaged JSON Schemas to validate JSON/YAML input structure at runtime,
  removing parallel field and option rules from transport loaders.
- Share typed date, datetime and decimal lexical rules with CSV parsing. Keep
  native Python model checks, binding semantics and resource limits intact.
- Include jsonschema and referencing in the core installation. Validation stays
  offline and does not fetch input `$schema` URLs.
- Report structural failures through the existing error classes and location
  attributes without including input values. Error wording may differ from 0.6.0.
- Validate nested components and data cells through conditional schema branches,
  and reject oversized component trees before recursive schema validation.
- Clarify the shared runtime/editor contract in the API and YAML documentation.

## 0.6.0 — 2026-11-05

### Added

- Read and write report templates and named datasets as YAML through the Python
  API and CLI, using standard ruamel.yaml safe loading and dumping.
- Support YAML comments, multiline text, anchors and merges, with bounded input
  expansion. Native YAML date/datetime cells share the existing Dataset model;
  exact decimal values retain the portable typed-cell notation.
- Ship JSON Schema 2020-12 documents for template/1 and data/1, with offline
  `json_schema()` access and optional root `$schema` editor metadata.
- Add `cardreport validate` for template/data checks without rendering and
  `cardreport schema` for local schema export. Mix JSON, YAML and CSV sources.
- Add a YAML version of the original reference report, an embedding/editor guide,
  and codec, schema, CLI and installed-package verification.

## 0.5.0 — 2026-11-05

### Added

- Render JSON templates from the terminal with `python -m cardreport render` or
  the equivalent installed `cardreport` command, producing HTML or PDF.
- Load named JSON datasets and CSV files together. CSV names default to filename
  stems; `--csv-as NAME PATH` supplies an explicit name, including
  names or paths containing spaces or equals signs.
- Reuse template schemas for CSV types, with configurable encoding, delimiter and
  null tokens. Reject duplicate dataset inputs and report errors without tracebacks.
- Select Chromium or SVG/WeasyPrint and a PDF deadline. Preserve existing outputs
  by default and protect input files even when output replacement is enabled.
- Add a complete CLI guide, ready-to-run JSON/CSV examples and installed-command
  checks in both core-only and full-extra packaging verification.

## 0.4.1 — 2026-11-04

### Examples and documentation

- Add a self-contained Python example with an inline JSON template and named
  datasets, producing the same report as the direct component API.
- Show Chromium and SVG/WeasyPrint dashboard exports side by side in the README.
- Show table continuation across pages, including repeated column headings and
  card titles, with links to the Python example and pagination guide.
- Reorganize the README introduction and documentation links, and extend the
  preview generator to reproduce all five screenshots from actual PDF exports.

## 0.4.0 — 2026-11-04

### Added

- LineChart axes/marker controls and zero-baseline area fill, including compact
  trends composed with KPIs. Null gaps remain gaps; isolated values retain a dot.
- Single-series LineChart support in SVG/WeasyPrint, with full or hidden axes.
- Category-colored bars and shared left/bottom category legends in both engines.
- Independent KPI value sizing through Theme.kpi_value_size_pt.
- Matching optional settings in template/1, an operations dashboard example and
  a dashboard guide. Its snapshot values come from the supplied dashboard;
  synthetic historical trends are labelled explicitly.
- Two README previews rasterized from real PDF exports, plus a regeneration script.

### Fixed

- Distinct series colors when the theme accent matches a palette color.
- Compact chart edge markers stay visible; shared styled-line ranges include all
  input coordinates, including missing endpoints. Date ordering uses exact UTC
  datetimes instead of plotting floats.

### Compatibility

- Existing chart/KPI defaults remain unchanged. Styled date lines require strictly
  increasing UTC coordinates; zero fill and SVG lines support one series.
- Non-default KPI sizes keep values on one line and reject overflow. Default 24 pt
  retains legacy wrapping. Compact text-free charts allow 10 mm containers.
- Date tick tuples in the renderer snapshot are now populated even without
  Formatting for SVG use; Chromium's default automatic date axes are preserved.

## 0.3.1 — 2026-11-04

### Fixed

- BarChart date and aware datetime categories now use report date/datetime formats
  in both renderers. Literal strings remain unchanged; equal formatted labels do
  not merge distinct categories.
- JSON bar category fields accept date/datetime within template/1. The Spanish
  reference calendar now uses a typed date and displays its Spanish date pattern.

### Renderer implementers

- For typed bar categories, use `ChartData.labels` as category keys and
  `category_labels` as display text; an empty `category_labels` retains the
  existing string-category representation.

## 0.3.0 — 2026-11-04

### Added

- Report language tags, localized empty states and application-defined empty text.
- Report-wide number separators and decimal precision, plus custom Babel LDML
  date/datetime patterns and an optional date locale override.
- The same settings in `cardreport.template/1`; existing templates remain valid.
- A Spanish report example using the reference report's datasets.
- This changelog, with version entries used as GitHub Release notes.

### Fixed

- Custom fractional-second patterns truncate exactly without float rounding.
  Unsupported Babel fields fail validation instead of displaying a missing value.
- Numeric display is isolated from application Decimal precision and traps.

### Compatibility

- Babel and langcodes are new core dependencies. Language tags have no product
  allowlist; date locale availability and font coverage are checked separately.
- Chromium PDFs are cloned through pypdf to set `/Lang` without rasterizing content.
- ReportDocument and ChartData gain trailing fields with defaults. Templates using
  the new settings require 0.3.0; older packages reject these optional keys.

- Omitting formatting keeps existing number/date output and automatic chart axes.
  Explicit formatting also controls chart labels and axes. Date axes label up to
  six actual data positions; data coordinates and values remain unchanged.
- `Table.empty_text` now defaults to `None`, inheriting the report's empty label.
  An explicit string, including an empty string, keeps its meaning.
- Language tags do not imply font coverage or automatic translation of user text.
  Chromium remains the default; the experimental WeasyPrint subset is unchanged.

## 0.2.1 — 2026-11-04

- First PyPI publication and automated GitHub/PyPI releases from main on version
  increases. Ordinary pushes run checks without publishing a new version.
- Verified distributions, checksum manifests and recovery using the original files.
- PyPI installation documentation and GitHub/PyPI version badges.

## 0.2.0 — 2026-11-04

- JSON report templates separated from named immutable datasets.
- Typed data JSON, schema-driven single-file CSV and optional pandas adapters.
- Reference JSON template/data examples and embedding documentation.
- This version was distributed as a Git tag only, without a GitHub Release or
  PyPI package.
