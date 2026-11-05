# YAML and formal schemas

Status: implemented in 0.6.0; runtime template schema validation added in 0.7.0; fast data decoding in 0.7.1. Owner: Oleg Orlov. Date: 2026-11-05.
This extends the [template decision](report-templates.md) and supersedes its YAML
and JSON Schema deferrals. [User contract](../../user/yaml-and-schemas.md).

The owner requested full template/data YAML API and CLI support with an unmodified
library and a small adapter. The final design uses core ruamel.yaml safe load/dump,
with its standard scalar rules, merges and quoting. It supersedes an advisory
proposal to customize resolvers or implement a node-to-value converter. Native
YAML dates/datetimes are supported in dataset cells; template strings and typed-cell
string values must be quoted where necessary. No YAML language implementation,
constructor patches, resolver mutation or general source/plugin framework is added.

The wrapper streams standard parse events to bound depth and event count, then
uses the public compose API to bound expanded nodes and scalar text before
standard load constructs values/merges. This walk applies resource limits only; it does not implement YAML resolution,
duplicate detection, merge precedence or construction.
The subsequent report validators retain their own limits. Safe parser errors are
summarized with location rather than source snippets. Fresh YAML instances isolate
calls. YAML emission uses the library's normal safe dumper on normalized trees.

Data JSON/YAML share internal tree codecs; the public native interface remains
Dataset. Template YAML uses the existing constructor. Both /1 identifiers remain,
with optional inert root $schema metadata. Existing files remain compatible;
older package versions reject the new metadata key. Data serialization drops
transport metadata, while template snapshots preserve their complete envelope.

Two handwritten schemas use JSON Schema 2020-12 and local $defs. They are shipped
as package resources and exposed by json_schema and the schema CLI command. IDs
point to the immutable release introducing a schema revision; unchanged schemas
may retain that ID in later package releases. Schema changes require a new ID.
Jsonschema and referencing are core dependencies. Templates use a cached standard
Draft202012Validator with an empty Registry, without remote retrieval or validator
extensions. Full data-schema traversal introduced in 0.7.0 caused a substantial
load-time regression, so 0.7.1 restores concrete decoding.

The decoder reads six fixed metadata fields once from the existing data schema:
root allowed/required keys, format constant, dataset keys, typed-cell keys and
permitted typed-cell kinds. An immutable cached record holds the sets. There is
no reference traversal, conditional interpreter or second schema. Required dataset
and typed-cell keys must equal their property sets. Scalar patterns remain shared
with CSV. Numeric/text limits come from the existing DataLimits; drift tests tie
schema caps to those limits. Typed-cell spelling retains the global transport cap;
caller limits apply to decoded string values and decimal coefficient digits.

Data loading checks the envelope and row keys, decodes typed cells with fixed
redacted errors, and constructs Dataset. Only Dataset calls cell validation.
The loader then checks cross-dataset cell/text totals without revalidating values.
Public bundle validation stays unchanged for stricter binding limits and native
callers. Native models and binding retain value, calendar, type and cardinality
checks. A one-way differential invalid-input corpus checks the decoder against the schema.

Splitting envelope/content with $defs/$ref/allOf was considered and rejected:
it adds another validator entry point while typed-cell checks still belong in
the fast decoder. Fixed-path metadata extraction is small; if future schema
composition makes it require interpretation, prefer explicit constants plus drift
tests over a general schema framework. Small duplication is acceptable when it
is the only reasonable performance option, per the owner.

Byte/tree/component guards precede validation. YAML dates still normalize to
portable typed cells. Errors retain public classes and available locations,
without echoing input values; the first failure may differ from 0.7.0's schema
error selection. No trusted-input switch, model framework or code generation.
The unchanged schema resources retain their immutable v0.7.0 revision IDs.

CLI render and validate share source loading, schema-based CSV acquisition and
collision rules. YAML/yml suffixes select YAML independently for template/data;
other suffixes retain the previous JSON interpretation. Validate never measures
layout; schema prints local schema text. No conversion command or source registry.

Verification includes codec round trips, library scalar behavior, no global state
changes, merge/literal-key rules, malformed input, alias limits, schema structure,
CLI parity, reference output through both engines, docs and installed packages.
