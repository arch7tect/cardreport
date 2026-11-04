# Template and dataset implementation plan

Status: completed for version 0.2.0. Date: 2026-11-04.
Based on the [reviewed architecture](decisions/report-templates.md) and its
[review disposition](history/reviews/2026-11-04-template-architecture.md).
The architecture defines contracts; this plan defines delivery order and checks.

## Goal and scope

Deliver `JSON template + named datasets -> Report -> HTML/PDF` above the existing
Python API, with separate data JSON, single-file `from_csv` and optional
`from_pandas`. The original report is the first complete example. Existing Python
composition and both renderer interfaces remain compatible.

Deferred: named SQL execution, loading a CSV directory, YAML, JSON Schema files,
expressions, transforms, provider frameworks, Arrow and template code generation.
SQL execution remains caller-owned; native rows are accepted by Dataset constructors.

The change is additive: no migration of existing reports or stored files is needed.
Keep the direct Python builders usable as a fallback. Reverting the extension must
not rewrite or delete stored templates/datasets; incompatible format versions fail
explicitly. No unresolved product decision blocks the first slice.

## Execution rules

- Preserve the existing uncommitted design/review documents. At execution start,
  fetch refs, inspect the worktree and establish a current test baseline; the last
  recorded runtime baseline is 80 passing tests, not a result of this planning task.
- Implement the six slices below in order. Keep small modules and explicit
  constructors; no public Any or unresolved bindings inside existing components.
- Each slice includes its API documentation, meaningful tests and runnable examples.
  Document only behavior delivered by that slice. Keep design proposals out of
  the current user API reference until implemented.
- Run focused checks during a slice; run the shared suite after integration changes.
  Review/fix failures before proceeding. Use Claude checkpoints after slices 2 and 6;
  a contract change discovered earlier also needs a focused design review.
- Record completion and check evidence here as work progresses. Implementation and GitHub publication were subsequently authorized by the owner.

## 1. Native datasets, schema and data JSON

**Deliver:** immutable Dataset and DatasetSchema, bounded `from_records`,
`from_dicts` and `single`, typed errors/limit options, `datasets_from_json` and
`datasets_to_json`. Keep column metadata for empty input. Apply the same cell and
bundle constraints through native and JSON entry points. Preserve Decimal and
aware datetime values using the reviewed tagged transport.

**Verify:** input mutation isolation, row/column shape, missing versus null versus
empty, bool/nonfinite/unsupported cells, minute-aligned datetime offsets, exact
Decimal/date transport, bad tags/versions/duplicate keys and boundary-sized input.
Prove bounded iterator consumption and rejection rather than truncation. Strict
consumer typing cases must cover new public types and reject invalid usage.

**Documentation:** add Dataset/schema/error/codec sections to
[API reference](../user/api.md); create `docs/user/datasets.md` for named datasets,
cardinality, native types, null handling and the data JSON envelope. Add a small
executable native-data/JSON round-trip example, with no renderer dependency.

**Done when:** a dataset bundle can be built, stored, restored and checked without
pandas, a database driver or a renderer. No template implementation is required yet.

## 2. Template parsing and binding

**Deliver:** ReportTemplate from_dict/from_json and detached to_dict/to_json;
read-only dataset schemas; closed component grammar; scalar/text bindings;
Table/chart field mappings; `bind -> Report`. Implement the shortest vertical path
(KPI in Card/Row) first, then the remaining containers, tables and all chart types.
Incomplete intermediate branches must reject unsupported forms explicitly.

Binding checks declared names, types/cardinality and formats, constructs the
existing components and invokes current semantic validation. Include longest-known
component-path mapping, optional data locations and preserved exception causes.
Keep rendering errors and renderer contracts unchanged.

**Verify:** all component discriminators/options, malformed and unknown keys,
missing bindings, nullable text rules, one-row scalar cardinality, table/chart
ordering and series mapping, Line gaps/date axes, resource bounds and error paths.
Bind two different datasets to the same template and verify no cross-run mutation.
Exercise explicit pages, Chromium flow, empty datasets and renderer-specific
unsupported features. Binding/template loading must perform no source I/O.

**Documentation:** create `docs/user/templates.md` with a small complete template,
separate data, native-Python binding, text/scalar/row bindings and error examples.
Extend the API reference with ReportTemplate and its errors. Explain clearly that
successful binding does not guarantee geometric fit. Link both new guides from
README and the project/user documentation navigation when their examples work.

**Done when:** both JSON and native-data routes produce ordinary Reports for the
full reviewed vocabulary; existing Python behavior remains intact. Obtain a focused
Claude review of public types, parsing, binding and error contracts; fix findings.

## 3. Original report and reusable examples

**Deliver:** `examples/reference_template.json`, `reference_data.json` and a typed,
import-safe Python example that loads them, binds data and returns HTML/PDF. Retain
[reference_report.py](../../examples/reference_report.py) as an independent baseline.
Add a second dataset using the same template to demonstrate real reuse.

Preserve the custom canvas, all cards/layout, chart order, values and the original
3-versus-2 discrepancy. Dynamic phrases come from one-row datasets. Keep the
original source PDF and generated reports private/ignored.

**Verify:** compare component values/normalized chart data with the Python baseline;
render the original through Chromium and WeasyPrint, checking pages, expected text,
vector output and visual layout. Render the second dataset and test an oversized
variant that must fail rather than shrink. Do not compare PDF bytes as equivalence.

**Documentation:** update [examples](../user/examples.md) so the original report is
still the first complete example, with Python-composition and template/data routes.
Extend [quickstart](../user/quickstart.md) with a short embedding route returning
`str`/`bytes`; keep the direct Python route. Any example runner belongs only in
[command-line examples](../user/command-line.md).

**Done when:** the same presentation works with two datasets and the original
reference passes both supported renderer paths.

## 4. Single-file CSV adapter

**Deliver:** `cardreport.adapters.csv.from_csv(path, *, schema, ...)` using stdlib,
with explicit types, delimiter/encoding/null policy and bounded reading. No directory
scan or automatic schema inference. Reuse existing scalar/schema validation.

**Verify:** typed decimal/date values, leading-zero text identifiers, empty strings
versus explicit null tokens, header-only files, duplicate/missing headers, ragged
rows, invalid encoding, BOM option, malformed numbers/dates and excess data.
Ensure owned file resources close on success/failure and no output is silently cut.

**Documentation:** add the exact from_csv signature/defaults to API and a single-file
CSV example to the datasets guide. Show constructing the named mapping explicitly
and binding it. Include a small distributable CSV fixture; update executable docs
checks so the example runs in their isolated temporary working directory.

**Done when:** a CSV-backed dataset can replace a native one without changing its
template, preserving types and the documented null policy.

## 5. Optional pandas adapter

**Deliver:** `cardreport.adapters.pandas.from_pandas(frame, *, schema, ...)`, an
optional dependency extra and lazy import boundary. Copy into Dataset; no DataFrame
or pandas dependency leaks into bind/render or the core public types.

**Verify:** ordinary/empty frames, column metadata, duplicate/non-string columns,
nondefault index and explicit drop behavior, nullable values, numpy scalars,
Decimal, dates, timezone offsets and sub-microsecond rejection. Verify that later
DataFrame mutation cannot alter a captured Dataset. Test core import/use without
pandas installed and a clear missing-extra error for adapter use.

**Documentation:** add API and datasets-guide examples for installation, index and
null handling, Decimal preservation and selecting supported columns. Add an explicit
pandas-extra docs-check command; the full check must execute these examples, while
the core-only installation check proves optionality. Include one caller-owned SQL
result example through Dataset.from_records, without adding query execution APIs.

**Done when:** existing pandas users can supply datasets with explicit normalization,
and core-only users retain their dependency footprint and behavior.

## 6. Documentation, packaging and acceptance

**Deliver:** reconcile documentation around the final implemented API, package new
modules/typing markers and update the current architecture from proposed to actual
behavior. Retain dated design/review history and record deviations with reasons.

| Document | Final responsibility |
| --- | --- |
| README | Short entry; Python first; links to template and dataset guides |
| Quickstart | Complete embedding example with data, binding and returned output |
| API reference | All public signatures/defaults/types/errors and import locations |
| `docs/user/templates.md` | Template format, vocabulary, bindings and versions |
| `docs/user/datasets.md` | Data contract/JSON, from_csv, optional pandas and native SQL results |
| Examples | Original report first; native/JSON/CSV/pandas entry routes |
| Renderer guide | Same capability limits also apply to template-produced Reports |
| Command-line guide | Secondary example runners; no invented installed CLI |
| Project architecture/development | Actual modules, optional dependencies and check commands |

Extend [check_docs.py](../../scripts/check_docs.py) to validate published JSON
fixtures with the real codecs/parser and run new Python snippets. Exercise JSON
examples as data, not just syntactically valid text. Keep snippets self-contained
or explicitly sequential, resolve fixture paths from the checkout and write only
to temporary directories. Do not execute design pseudocode as user documentation.

**Verify:** Ruff lint/format, strict mypy including consumers/examples, complete
runtime/contract suite with both renderers, all executable user docs, local links
and anchors, and new external links. Run uv build and fresh isolated wheel checks
for core-only, Chromium/WeasyPrint and pandas-extra installations as relevant.
Check fonts/assets/py.typed, new modules, source-distribution examples and exclusion
of private sources/outputs. No new cross-platform claim without that platform's test.

Obtain a final Claude review of implementation and user documentation, resolve
confirmed findings and record review limits. Update CodexHome project routing and
the existing architecture draft. Publication/versioning is a separate execution
step under the user's then-current authorization; no PyPI release is assumed.

**Done when:** the feature works from an installed package, examples/docs agree with
it, legacy Python reports still pass, and no required review/check remains open.

## Progress

- [x] 1. Native datasets, schema and data JSON
- [x] 2. Template parsing and binding
- [x] 3. Original report and reusable examples
- [x] 4. Single-file CSV adapter
- [x] 5. Optional pandas adapter
- [x] 6. Documentation, packaging and acceptance


## Implementation evidence

- Initial upstream baseline: 80 tests passed; main matched origin before changes.
- Slices 1/2: immutable native/data JSON input and full template vocabulary delivered;
  core Claude review completed successfully. Confirmed shape, diagnostic-location,
  datetime-boundary and Mapping serialization findings were fixed with regressions.
- Slice 3: template-produced original model equals the independent Python baseline.
  Both renderers pass original/second-data PDF checks and reject oversized tables;
  Chromium template flow preserves all rows across pages. Both reference PDFs were
  visually inspected from fresh installed wheels.
- Slices 4/5: CSV schema/null/encoding and pandas index/scalar/precision checks pass.
  A fresh core-only wheel environment successfully binds/renders HTML and loads CSV
  without pandas/NumPy/Playwright/WeasyPrint; missing pandas gives DependencyError.
  A fresh full-extra wheel environment renders both engines and normalizes pandas.
- Slice 6: strict mypy (27 files), Ruff, executable documentation (36 Python blocks),
  published JSON fixture binding and local Markdown links pass. Wheel/source archive
  contents were inspected. Final advisory review completed; its Unicode-name finding is fixed. Final acceptance passed: 155 tests, 36 documentation blocks, strict mypy and Ruff.

See the [dated implementation review](history/reviews/2026-11-04-template-implementation.md) for final counts and publication verification.
