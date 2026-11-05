# Architecture

[Project documentation](README.md) · [Public API](../user/api.md)

CardReport is a Python library. Applications own data access and business metrics.
The library owns typed composition, semantic validation, rendering and output
publication. It has no service, query layer, plugin registry or custom geometry IR.

## Export path

```text
Optional ReportTemplate + named Dataset snapshots
  -> bind -> Report + frozen components
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
| [cli.py](../../src/cardreport/cli.py) | Thin installed command: file inputs, explicit name resolution, public binding/export APIs |
| [_yaml.py](../../src/cardreport/_yaml.py) | Bounded standard ruamel.yaml loading/dumping |
| [schemas](../../src/cardreport/schemas/) | Structural contract shared by loaders and editors |
| [_schema.py](../../src/cardreport/_schema.py) | Offline template validation, safe errors and cached data metadata |
| [data.py](../../src/cardreport/data.py) | Immutable tables, schemas, bounded native and tagged JSON input |
| [templates.py](../../src/cardreport/templates.py) | Closed JSON grammar and binding to existing components |
| [_inputs.py](../../src/cardreport/_inputs.py) | Shared bounded parsing and located errors |
| [adapters](../../src/cardreport/adapters/) | Single CSV file and lazy optional pandas ingestion |
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
[Matplotlib SVG charts](../../src/cardreport/_svg_charts.py) use isolated default settings
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

## Separate presentation and data

Version 0.2.0 adds a layer above Report, with independent `cardreport.template/1`
and `cardreport.data/1` envelopes. Templates snapshot a bounded validated definition;
Dataset copies native rows and fixed-offset datetimes. Schemas distinguish missing,
null and empty input. Binding checks every declared contract, constructs ordinary
components and calls existing validation; no unresolved expressions reach renderers.
Semantic errors map known component paths back to template paths, preserving causes.
Static validation uses one representative row per declared field type plus explicit
binding/type checks. Real row counts, values and geometry are checked later.

`from_csv` requires a schema and uses the standard library. `from_pandas` imports its
optional dependency only on invocation. Neither source access nor normalization is
part of bind/render. No source registry, SQL execution, directory scanner, expressions
or model-to-template serializer is introduced. See the [decision](decisions/report-templates.md)
and [delivery plan](template-implementation-plan.md).


## Report display context

Version 0.3.0 adds optional immutable Formatting and a canonical language tag to
Report and its snapshot. Language parsing uses langcodes without a product allowlist.
Babel LDML formats dates with an explicitly resolved locale. All numeric display
uses report separators/precision, never global locale or localized input parsing.
Shared HTML fragments and SVG tick formatting receive the same display context.
Empty text resolves once at report level, with optional table overrides.

Date coordinates stay ISO UTC. Explicit formatting precomputes at most six sampled
input-date ticks in validation, including glyph checks; Plotly receives separate
coordinates and escaped display text. Numeric tick positions remain engine-owned.
Bars containing typed dates/datetimes use positional category keys and separate
`ChartData.category_labels`, formatted during validation. String-only charts keep
their existing representation. Both adapters consume display labels independently
of identity; equal labels never merge distinct categories. UTC-normalized duplicate
datetime values are rejected; dates and literal ISO strings remain distinct.
No settings preserves the legacy automatic line/numeric axes. Chromium writes PDF language via
pypdf because browser printing does not reliably preserve HTML lang; this does not
claim PDF/UA conformance. See [the public contract](../user/localization.md).


## Dashboard chart display (0.4.0)

LineChart retains one model for ordinary and compact presentations. A small
private display helper shares empty-state, segment, marker, date-coordinate,
y-range and category-color rules. Null gaps split filled polygons, isolated values
retain a marker, and zero fill uses a shared light color. Styling is closed and
finite; no backend options or geometry framework enter the public API.

Category legends use shared escaped HTML around a single chart plot. The same
ordered label/color mapping feeds both backends. Grid allocates the remaining plot
rectangle, and both layout engines inspect wrapper, legend items and plot bounds.
SVG supports ordinary and compact lines. Since 0.8.0 it also renders multiple
bar/line series and centered funnel stages. Series legends reuse the existing
measured HTML frame on the WeasyPrint path; Chromium retains Plotly legends. Native glyph
preflight explicitly permits no text only for hidden-axis lines; labelled charts
still require text. Plot-only compact containers have a 10mm floor; ordinary
charts retain 35 mm. The browser also checks legend item coverage.

Read [the user contract](../user/dashboards.md) for fill, chronology, palette limits,
KPI no-wrap behavior, layout weights and backend capability differences.


## Installed command line (0.5.0)

`python -m cardreport` and the `cardreport` console entry point share `cli.main`.
The command owns argument parsing and explicit file acquisition, then calls
ReportTemplate, datasets_from_json, from_csv and Report.write_html/write_pdf.
It uses the public read-only `ReportTemplate.datasets` schemas without duplicating
template parsing. It rejects duplicate source names before reading CSV rows and
retains extra-JSON-dataset behavior from bind. CSV filename stems are literal;
`--csv-as NAME PATH` supports aliases without reserving `=` inside names/paths.
Spaces and equals signs remain literal; ordinary shell/argparse argument constraints still apply. No directory discovery,
source registry, SQL layer, render changes or new template version is introduced.


## YAML and JSON Schema (0.6.0)

JSON and YAML feed the same template constructor and internal data tree codec.
Standard ruamel.yaml owns parsing, scalar resolution, merges and emission. The
small wrapper bounds composed alias graphs before construction; it does not
reimplement the YAML language. Native YAML date/datetime cells normalize to the
existing portable tagged JSON representation. Templates use the standard cached
Draft 2020-12 validator with a non-retrieving registry. Since 0.7.1, the data decoder
reads fixed key/type metadata and scalar patterns from the full data schema once.
It validates transport shape while decoding, then Dataset validates values once;
only cross-dataset totals are checked after construction. This avoids the 0.7.0
full-schema per-cell pass. Binding retains its checks for caller-supplied datasets
and stricter limits. Native model semantics stay in Python. Template component
bounds precede recursive schema checks. CLI validate and schema share the installed API. See the
[decision](decisions/yaml-and-json-schema.md) and [user contract](../user/yaml-and-schemas.md).
