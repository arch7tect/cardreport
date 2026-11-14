# JSON templates and named datasets

Datetime semantics were superseded by the [timezone hotfix](timezones.md) in 0.9.1:
missing offsets mean UTC; supplied offsets are preserved for display unless the
report selects a zone. Earlier requirements below record the original design.


Status: implemented and verified in version 0.2.0. YAML/schema deferrals below
are superseded by the [0.6.0 decision](yaml-and-json-schema.md).
Date: 2026-11-04. [Review and disposition](../history/reviews/2026-11-04-template-architecture.md).
Owner: Oleg Orlov. This document records the reviewed extension contract.
The current Python API is
specified by the [API reference](../../user/api.md).

## Purpose and scope

Store report presentation independently from its data in files or a database.
Reuse one presentation with SQL results, CSV files, DataFrames or native Python
records through one binding API. The original dashboard must be the first complete
example, with the same layout and original aggregate discrepancy preserved.

Add a small layer above the existing Python API. Keep concrete components, semantic
validation, ReportDocument and renderer interfaces unchanged. Python callers may
continue composing reports directly. No conversion through JSON is required in
Python applications.

The [current architecture](../architecture.md) gives applications responsibility for
data access. V1 adds explicit conversion adapters and single-file CSV reading;
applications retain SQL execution, connection ownership, query definition,
transactions and business calculations.
No network/database work occurs during template binding or rendering. The owner
subsequently deferred named SQL execution and CSV-directory loading to later
versions; these conveniences are not required for v1.

## Boundary and data flow

```text
JSON template -> ReportTemplate (presentation + required data contract)

SQL / CSV / pandas / Python records / data JSON
                 -> named immutable Dataset snapshots

ReportTemplate.bind(datasets)
  -> existing concrete Report
  -> existing semantic validation
  -> existing ReportDocument and renderer
  -> HTML / PDF
```

Three concerns remain separate:

| Concern | Contents | Ownership |
| --- | --- | --- |
| Presentation template | Components, layout, theme, display formats, bindings, required dataset schema | Stored/versioned by the application |
| Dataset bundle | Named tables of values, including one-row summaries | Supplied per report run |
| Acquisition configuration | SQL and bound parameters, files, encoding, delimiter, connection | Application code; optional source manifest later |

A template contains no SQL, file paths, connection strings or credentials. Renderer,
PDF timeout and output path are export arguments. A dataset contains no cursor,
connection, iterator or other resource that could perform I/O later.

## Dataset contract

The engine-facing input is `Mapping[str, Dataset]`. Dataset names and column names
are nonempty, case-sensitive strings (maximum 100 characters). They are literal
keys, not dot paths or expressions. Duplicate names are errors.

Proposed shape, using the existing `Value` alias:

```text
Dataset:
    columns: tuple[str, ...]
    rows: tuple[tuple[Value, ...], ...]

Dataset.from_records(columns, records, *, limits=...) -> Dataset
Dataset.from_dicts(rows, *, columns=None, limits=...) -> Dataset
Dataset.single(values, *, limits=...) -> Dataset
```

Constructors copy/normalize inputs into immutable values and equal-width rows.
Records/iterators can be consumed by constructors and loaders, never by `bind`.
`from_dicts` infers columns from the first row if omitted; every subsequent row must
have the same key set. Empty input requires explicit `columns`. Missing keys never
become null implicitly. `single` is convenience for exactly one record.

Column names are retained for empty datasets. A zero-row dataset with the required
columns is valid for cardinality `many`; one without those columns is invalid.
Schema types belong to the template contract, not a second independent dtype
system inside Dataset. Extra columns and extra datasets are allowed for reuse;
all supplied values must still satisfy Dataset's scalar and resource constraints.
No merge API is provided in v1. Applications composing source mappings are
responsible for detecting collisions; a plain dict assignment intentionally
replaces its existing value. Future batch loaders must define collision behavior.

Cell types are the existing `Value`: int, finite float, finite Decimal, str, date,
timezone-aware datetime, or None. Bool, bytes, UUID, arrays and nested records are
not accepted as cells in v1. Callers can explicitly convert them before ingestion.
Naive datetimes and UTC offsets not divisible by one minute are rejected at
Dataset construction; v1 does not guess a timezone. Input datetime offsets are
retained in Dataset; existing rendering normalizes them to UTC. The data codec
preserves the represented instant, local date/time and numeric offset, not timezone
class/zone identity or fold metadata. It is a value round-trip, not object identity.

## Template envelope and schema

Root keys are exactly `format`, `datasets` and `report`:

```json
{
  "format": "cardreport.template/1",
  "datasets": {
    "summary": {
      "cardinality": "one",
      "fields": {
        "total_calls": {"type": "integer"},
        "period": {"type": "text"}
      }
    },
    "outcomes": {
      "cardinality": "many",
      "fields": {
        "outcome": {"type": "text"},
        "count": {"type": "integer"}
      }
    }
  },
  "report": {
    "title": "Call results",
    "subtitle": {"bind": {"dataset": "summary", "field": "period"}},
    "blocks": [
      {
        "type": "row",
        "height_mm": 50,
        "children": [
          {
            "type": "card",
            "content": {
              "type": "kpi",
              "label": "Total calls",
              "value": {"bind": {"dataset": "summary", "field": "total_calls"}},
              "format": "integer"
            }
          }
        ]
      },
      {
        "type": "row",
        "height_mm": 70,
        "children": [
          {
            "type": "card",
            "content": {
              "type": "bar",
              "dataset": "outcomes",
              "category": "outcome",
              "value": "count",
              "show_labels": true
            }
          }
        ]
      }
    ]
  }
}
```

Every field specification has required `type` and optional `nullable` (default
false). Dataset specifications require exactly `cardinality` and `fields`.
Acquisition limits are caller options, not template fields. Cardinality `one`
requires exactly
one row, `many` allows zero or more. All declared datasets/fields are required even
if unused by a particular component. Unused declarations are allowed for reuse.

| Field type | Accepted native values | CSV decoding |
| --- | --- | --- |
| `text` | str | Preserve text, including leading zeros |
| `integer` | int, excluding bool | Signed base-10 integer |
| `number` | int, float, Decimal, all finite | Decimal from numeric text |
| `decimal` | Decimal or int, retained without conversion | Decimal from numeric text |
| `date` | date, excluding datetime | ISO calendar date |
| `datetime` | timezone-aware datetime | ISO datetime with explicit offset |

Nullable fields additionally accept None. Float is not accepted for `decimal`:
precision lost upstream cannot be reconstructed. Strings are not automatically
converted by `bind`; decoding CSV and typed JSON happens before binding.
No conversion depends on display format. Current numeric limits still apply.

## Component and binding vocabulary

Keep public component field names/defaults unless listed here. Report accepts
`title`, `subtitle`, `mode`, `page`, `theme`, `blocks`. Page/Theme definitions and
constraints follow the current API; custom page dimensions are a JSON array.
Formats are `number`, `integer`, `percent`, `date`, or `{"currency":"EUR"}`.
Unknown keys, discriminators and versions are errors, including misspelled options.

| JSON `type` | Model | Data-bearing fields |
| --- | --- | --- |
| `card` | Card | `content`; title is literal text or scalar binding |
| `row` | Row | `children`; widths and height_mm are literals |
| `column` | Column | `children`; heights are literals |
| `page_break` | PageBreak | None; top-level only |
| `text` | Text | text is literal text or scalar binding |
| `kpi` | KPI | value is scalar binding; label/note are literal text or scalar binding |
| `table` | Table | dataset name; literal columns use field names as keys |
| `bar` | BarChart | dataset, category, and value or series |
| `line` | LineChart | dataset, x, and value or series |
| `funnel` | Funnel | dataset, category, value |

Report title/subtitle accept literal text or scalar binding and default to empty
strings; they, KPI label and Text.text require non-nullable `text` when bound.
Only Card.title and KPI.note accept literal null or bindings to nullable `text`;
omitting them means None. Other omitted fields take their Python defaults. A scalar binding
is exactly `{"bind":{"dataset":"summary","field":"total_calls"}}` and requires
cardinality `one`. It never selects a first row or calculates an aggregate.
KPI value accepts the existing Value-compatible field types, subject to formatting.

For Table, `dataset` replaces `rows`; `columns` are ordinary TableColumn definitions.
For a single-series chart, `value` is a field name. Multi-series Bar/Line use
`series: [{"field":"promised","label":"Promised"}, ...]`; order is explicit,
labels are unique literal strings, and exactly one of value/series is required.
Bar category fields accept non-nullable text, date or datetime (extended in 0.3.1
within template/1); Funnel categories require non-nullable text. Bar category
identity is independent of formatted display text. Line uses `x` and the existing `x_kind`:
category requires text, date requires date/datetime. Chart value fields are numeric;
only Line permits nullable values, yielding gaps. Existing chart checks reject
nonfinite values, duplicate categories/dates, excessive series/points and invalid
Funnel values. Rows are neither sorted nor grouped by binding.

Layout, formats, Table headings/empty text, series labels, chart settings and theme
are literals. Since 0.9.0, the six text-binding positions also support
[Jinja text substitutions](text-substitutions.md) from one-row datasets. Whole-text
bindings remain supported. Calculations remain outside the template.

V1 deliberately keeps KPI values, table rows and chart data outside presentation:
no inline numeric KPI values, table rows or parallel labels/values arrays. Static
numbers can live in a one-row dataset; direct Python composition remains available.
A reverse `from_report` codec is deferred: extracting reusable bindings from a
populated report cannot be inferred reliably. This narrows the earlier proposal
for a general literal-report serialization format.

## Data JSON is a separate transport

Native Python callers pass Dataset objects directly. The optional data codec has
its own envelope and can store/replay a dataset bundle without a template:

```json
{
  "format": "cardreport.data/1",
  "datasets": {
    "summary": {
      "columns": ["total_calls", "period"],
      "rows": [{"total_calls": 34, "period": "November 2026"}]
    },
    "outcomes": {
      "columns": ["outcome", "count"],
      "rows": [
        {"outcome": "Answered", "count": 24},
        {"outcome": "No answer", "count": 10}
      ]
    }
  }
}
```

Each row's key set must equal columns, including extra columns; column order comes
from `columns`. Empty datasets use `rows: []`, preserving their column names.
JSON text remains text. Use explicit typed cells for values JSON cannot represent:

```json
{
  "amount": {"$type": "decimal", "value": "1200.50"},
  "day": {"$type": "date", "value": "2026-11-04"},
  "at": {"$type": "datetime", "value": "2026-11-04T09:00:00+02:00"}
}
```

The last block illustrates cells inside a row, not another envelope. These are the
only cell objects allowed; keys/tags are closed. Native int/float/null use JSON
numbers/null; Decimal always uses its tagged string, never float. Dates/datetimes
use the tagged ISO form; datetime requires an offset. Reject nonfinite numeric
values and duplicate JSON keys at any level. Encoding never uses generic
`default=str`. Finite floating values round-trip as floats, not exact decimals.
The template later checks the decoded cells against its field types.

Use an ASCII integer grammar `[+-]?[0-9]+` for CSV integer cells and
`[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?` for CSV numeric cells
and tagged decimal strings. No whitespace, underscores, Unicode digits or
nonfinite spellings. Leading zeros are accepted for numeric fields; text fields
preserve them. Untagged JSON numbers follow JSON's own grammar. Dates use
`YYYY-MM-DD`; datetime uses `YYYY-MM-DDTHH:MM:SS`, an optional dot followed by
1–6 fractional digits, then `Z` or an offset `+HH:MM` / `-HH:MM`.
Require calendar-valid values and valid timezone offsets. No
leap-second or sub-microsecond coercion. Native numeric cells must also be finite
and satisfy the existing absolute-value bound.

JSON is canonical for interchange, but byte-canonical JSON or reproducible PDF
bytes are not promised. JSON Schema files for editor support are deferred until
the implemented grammar stabilizes; the initial parser and semantic checks define the contract.
YAML, includes and source manifests are deferred; no custom YAML tags/loaders.
Only the exact identifiers `cardreport.template/1` and `cardreport.data/1` are
accepted in their respective decoders; every other identifier fails explicitly.
Template revisions and pairing a
saved dataset bundle with a template revision are application storage concerns.

## Proposed Python interface

This is illustrative API, not runnable against the current package:

```python
from cardreport import Dataset, ReportTemplate, datasets_from_json

# Loading/validation of the template performs no source access or rendering.
template = ReportTemplate.from_json(template_text)
data = datasets_from_json(data_text)
report = template.bind(data)
pdf = report.to_pdf()

# Native data need no JSON conversion.
data = {
    "summary": Dataset.single({"total_calls": 34, "period": "November 2026"}),
    "outcomes": Dataset.from_dicts(
        [{"outcome": "Answered", "count": 24},
         {"outcome": "No answer", "count": 10}]
    ),
}
report = template.bind(data)
```

`ReportTemplate.from_dict(mapping)` also validates and copies its input;
`to_dict()`/`to_json()` return a detached representation. `datasets_to_json()` is
the inverse of the data decoder. `template.datasets` is a read-only mapping of
DatasetSchema records, useful to loaders. `bind` returns a fresh concrete Report,
checks dataset schemas and runs existing semantic validation before returning.
It does not prove geometric fit or renderer-specific capability support.

Do not add `Ref` unions to existing component fields or a parallel public hierarchy
of TemplateKPI/TemplateRow classes. Internally use a small closed parsed tree and
explicit constructors. New core APIs use typed aliases/records and narrowed object
inputs, without public Any. IDEs know Dataset/Report and schema record fields;
column names loaded at runtime are checked at runtime. Generated TypedDicts are
deferred. Direct Python composition keeps all existing IDE assistance.

## Acquisition and adapters

V1 provides bounded Dataset constructors, explicit single-file CSV decoding and
an optional pandas adapter. The owner deferred named SQL-query execution and
CSV-directory discovery to subsequent versions. There is no Query type, load_sql,
read_csv_directory, source manifest, Provider hierarchy or merge API in v1.
Core Dataset and template support require no pandas/database dependency.

SQL execution and cursor ownership remain application code. Native records can
come from DB-API cursors or other libraries; no connection enters Dataset. Proposed
usage (SELECT SQL and driver-specific parameters are application-owned):

```python
cursor = connection.cursor()
try:
    cursor.execute(SUMMARY_SQL, {"day": day})
    summary = Dataset.from_records(
        columns=[column[0] for column in cursor.description],
        records=cursor,
    )
finally:
    cursor.close()
```

The application chooses transactions/isolation and query timeouts. One connection
alone does not promise a consistent snapshot across queries. Bounded consumption
limits materialization by CardReport, not buffering by the driver or time spent
inside execute/fetch. SQLAlchemy results can similarly supply keys and rows;
no SQLAlchemy dependency or dedicated cursor adapter is required.

Use small explicit adapters: `cardreport.adapters.csv.from_csv` (stdlib) and
`cardreport.adapters.pandas.from_pandas` (optional pandas extra, lazy import).
Both require keyword-only `schema: DatasetSchema`, return Dataset and validate
that contract. `from_csv` requires it for explicit parsing; `from_pandas` requires
it for consistent early checks. Neither infers a schema. A mixed-source example:

```python
from cardreport.adapters.csv import from_csv
from cardreport.adapters.pandas import from_pandas

outcomes = from_csv("outcomes.csv", schema=template.datasets["outcomes"],
                    encoding="utf-8", delimiter=",")
# Alternatively, replace the CSV call with:
# outcomes = from_pandas(outcomes_df, schema=template.datasets["outcomes"])
data = {"summary": summary, "outcomes": outcomes}
report = template.bind(data)
```

CSV uses declared field types, not inference. Extra columns stay text. The default
encoding is UTF-8, delimiter comma, and no implicit null tokens: empty text remains
empty text and empty numeric/date cells fail. An explicit `null_values` sequence
(e.g. `["\\N"]` or `[""]`) maps exact cell strings to None, subject to nullable.
Quoted empty strings follow the same token policy. No locale guessing, thousands
separators, silent trimming, replacement decoding or automatic header renaming.
Use `utf-8-sig` explicitly for BOM input. Duplicate/missing headers and ragged rows
are errors. Preserve row order; decimal/date parsing follows the field table.

The pandas adapter checks unique flat string column names and rejects a nondefault
index unless the caller explicitly selects `index="drop"` or materializes it as
columns. It converts supported numpy scalars and pandas timestamps to native cells,
normalizes None/pd.NA/NaT/float NaN to None, and rejects infinity, naive timestamps,
nested objects and timestamp precision beyond Python datetime. Decimal is retained;
float input to a decimal field fails. No lost upstream precision is reconstructed.
Required field types and nullability are checked after normalization.

Native SQL/pandas inputs are not parsed as CSV strings or narrowed implicitly:
prepare native date values for `date` fields and aware datetimes for `datetime`.
An integral Decimal does not satisfy `integer`; callers can cast it explicitly or
use a `number` field with integer display format. This preserves the distinction
between data types and display formats. Select/project columns before ingestion
when unused columns contain unsupported values: extra columns are permitted, not
exempt from validation. Bar categories require text, including dates formatted as
ISO strings by the caller; a date-valued x axis uses LineChart with `x_kind="date"`
and remains subject to renderer capability limits.

Future batch loaders may map names to parameterized SQL queries or CSV filenames
and return the same Mapping[str, Dataset]. They must define missing-file/name
collisions, connection/cursor ownership, partial-failure behavior and bounds before
implementation. Their future specification must not add source access to bind or
render. No initial implementation depends on those convenience APIs.

## Validation, bounds and errors

1. Parse/copy template: closed keys, version, bindings, declared names, field types,
   scalar cardinality and structural limits. Statically reject numeric fields with
   date display format (KPI/Table), non-text text bindings, undeclared TableColumn
   keys, incompatible chart category/x/value types, and nullable fields in chart
   positions that cannot accept gaps. Do not invent additional coercion rules;
   other value/format semantics follow the Python API and are checked at bind.
2. Acquire/decode: check column names, row shape, allowed native cells and bounds;
   loaders with schemas also check declared types/cardinality.
3. Bind: resolve all names, check required datasets/columns/types/cardinality, build
   a concrete Report and run its semantic checks. Templates/datasets are unchanged.
4. Render: existing engine-specific capability, layout, font and deadline checks.

Use `TemplateError(ValidationError)`, `BindingError(ValidationError)` and
`DataError(ReportError)` for acquisition/codec failures. Errors carry structured
optional `dataset`, `row`, `field` and `template_path` attributes; paths use actual
JSON locations, e.g. `report.blocks[0].children[0].content.value`. Map generated
component paths back to these locations for bind-time errors. Existing renderer
errors remain unchanged in v1; retain their component path for diagnosis.
Binding checks for types, null and cardinality supply data locations directly.
For later existing ValidationError failures, keep a generated component-prefix to
JSON-path map, match the longest leading `path:` prefix and preserve the original
exception as `__cause__`. Such semantic failures are raised as BindingError.
The template_path is the mapped component path; append a suffix only if it
identifies an actual JSON key. Never invent a TableColumn index for an ambiguous
`.format`/`.key`/`.heading` failure. A table `.rows.i.key` suffix identifies the
bound dataset, row and field, not a template rows property; translate it only
when the suffix matches known row/column information. Unknown/unstructured
messages retain the original message
without an invented location. Row/field are populated only when known; graph-wide
errors need not identify a row. Row/Column child index `.i` maps to `.children[i]`,
Card `.content` maps directly, and top-level `blocks.i` maps to `report.blocks[i]`.
This deterministic correspondence also helps interpret unchanged renderer paths.
Data schema mismatches found during acquisition/decoding use DataError; the same
mismatch encountered by bind uses BindingError. Do not dump cell values, SQL
parameters or credentials in error messages.

Initial acquisition/parser caps (implementation acceptance targets, not benchmarks):
1 MiB template JSON, 16 MiB data JSON, JSON depth 64; 32 datasets, 100 columns per
dataset, 2000 rows per dataset and 100000 cells per bundle; strings at most 10000
characters with 16 MiB aggregate UTF-8 cell-text bytes per bundle. Constructors,
from_dict and native bindings enforce equivalent structural/cell bounds so they
cannot bypass the JSON limits. Single-dataset loaders enforce local caps and bind
checks the aggregate bundle. Caller-supplied limits may only reduce the default
caps; they are not serialized in the presentation template.

Reject excess input instead of truncating. Check byte limits before parsing file
payloads and row/string limits while consuming, not after an unbounded list/fetchall.
Catch parser recursion failures and check tree depth before recursive construction.
Final Report limits (including total component/table/chart bounds) still apply and
may be stricter: e.g. 500 date-chart points, 30 categorical chart labels. Reusing one
dataset in several components does not waive those output limits.

Acquisition timeout/cancellation is owned by the caller/driver. `bind` has no I/O;
PDF timeout begins in the existing export method. No end-to-end acquisition timeout
is implied. Close owned resources on failure; preserve caller-owned connections.

## Compatibility and implementation sequence

The [implementation plan](../template-implementation-plan.md) defines delivery
slices, per-slice documentation and acceptance checks.

The existing Report API, frozen components, renderer interface and file publication
behavior remain unchanged. The new formats start provisional at version 1;
compatibility changes to serialized structure normally require a new format version.
Owner exception (2026-11-04, version 0.3.0): with no external users, optional
language/formatting/empty_text fields extend template/1. Existing templates keep
their behavior; older library versions reject the new keys. Data/1 is unchanged.
No automatic migrations or code execution from documents.

Implement in small independently verified steps:

1. Dataset, DatasetSchema, immutable copies and bounded constructors; typed data
   JSON codec with precision/date round-trip tests.
2. ReportTemplate parser, complete component vocabulary, scalar/dataset bindings
   and existing semantic validation integration.
3. Original `reference_template.json` plus `reference_data.json` as the first full
   example, and a second dataset proving presentation reuse. Keep the Python
   reference example as an independent baseline.
4. Single-file CSV and optional pandas adapters. Document schema parsing and
   null/index policies; show caller-owned SQL acquisition with native records.
5. User API/quickstart/renderer-limit documentation and executable examples.

Acceptance: preserve template/data inputs across repeated binds; verify missing
vs null vs empty, bad versions/keys/duplicates/types, scalar cardinality, column
metadata on empty native/CSV/DataFrame results, resource bounds,
Decimal/date transport, literal hostile labels and overflow with larger datasets.
Test a caller-owned SQL acquisition example without production access, using
SQLite and controlled native typed-result fixtures (SQLite alone does not prove
Decimal behavior for other drivers). Test pandas optional dependency absence.

For the original report, compare bound component values/normalized chart data and
rendered PDF page geometry/text/vector properties against the Python baseline in
both engines. Do not require byte-identical PDFs or universally identical HTML.
Run strict mypy, Ruff, existing runtime tests and new contract tests. Existing
Python users must retain the same behavior and editor assistance.

Deferred: general expressions (beyond text substitution), formulas, joins, grouping/sorting, conditional visibility,
repeated layout blocks, JSONPath, arbitrary HTML/Jinja/CSS, source manifests, YAML,
named SQL execution, CSV-directory loading, provider/connector frameworks, Arrow,
async loaders, caching, JSON Schema files and generated typing.
SQL performs application-defined computation before ingestion; CSV/pandas callers
may transform data themselves. The report layer does not infer business consistency.
