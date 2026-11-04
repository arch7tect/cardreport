# Template and dataset architecture review

Date: 2026-11-04. Scope: the [architecture proposal](../../decisions/report-templates.md),
not implementation or runtime verification. The owner requested the document and
Claude consultation. Three restricted read-only consultations completed with exit 0.

## Agreed direction

Presentation and data are separate from the first format version. A versioned JSON
template binds named, immutable Dataset snapshots into the existing concrete Report.
Python callers need no JSON round-trip. Existing components, validation and renderer
interfaces remain unchanged. Dataset retains column names for empty results; scalar
bindings require exactly one row. Tables/charts use named dataset fields.

The data JSON codec uses explicit Decimal/date/datetime tags. pandas is optional;
it is not the core data type. Single-file `from_csv(path, schema=...)` remains in
scope, as explicitly confirmed by the owner. Named SQL-query execution and loading
a CSV directory are deferred by the owner's subsequent instruction. Caller-owned
SQL results can already feed the proposed bounded Dataset constructors.

## Findings and disposition

- Kept acquisition outside bind/render. Deferring query execution preserves the
  current no-query-layer rules without changing the current implementation guide.
- Defined how bind-time errors map existing component paths to JSON/data locations;
  unknown locations remain unknown, the original exception is preserved, and
  renderer errors retain their existing paths.
- Clarified that v1 has no merge API. Collision handling when combining application
  dictionaries belongs to the caller, not an unimplemented library service.
- Enumerated static schema/binding checks and retained current Python formatting
  semantics for other cases.
- Distinguished omitted defaults from nullable text: only Card.title and KPI.note
  accept nullable text; Report title/subtitle default to non-null empty strings.
- Made format identifiers exact and closed. Deferred JSON Schema files until the
  implemented grammar stabilizes; acquisition limits are caller options.
- Specified finite values and lexical number/date rules. Datetime offsets must be
  whole minutes so native Dataset values fit the transport grammar. The codec
  preserves value/offset, not timezone object identity or fold metadata.
- Both single-file CSV and pandas adapters require an explicit keyword-only schema.
  Decimal fields accept int without conversion; unsupported extra columns remain
  subject to validation and can be projected out by the caller.

Template to_dict/to_json remain for storing its validated representation. A reverse
codec from populated Report is deferred. This does not introduce inline table/chart
business data into the presentation format.

The final focused review reported no remaining blocking findings and readiness to
guide implementation. The review also confirmed that the original reference report
is expressible, including its custom page, nested layout and intentionally preserved
3-versus-2 discrepancy. Raw advisory responses remain in ignored local storage.

## Verification of the document

Local Markdown links/anchors pass. All three JSON blocks parse; the sample template
and data agree on names, columns and cardinalities. All three proposed Python
snippets parse as Python syntax. They are illustrative new APIs and were not run.
No feature implementation, runtime test claim, commit or publication is part of
this design-only task. Implementation acceptance checks are specified in the proposal.
