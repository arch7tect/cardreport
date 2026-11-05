# YAML and formal schemas

Status: implemented in 0.6.0; runtime schema validation added in 0.7.0. Owner: Oleg Orlov. Date: 2026-11-05.
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
Since 0.7.0, jsonschema and referencing are core dependencies. A cached standard
Draft202012Validator with an empty Registry validates the normalized transport
tree against these same resources, without remote retrieval or validator
extensions. The codecs no longer carry lists of allowed/required keys or runtime
enum rules. Scalar lexical patterns are also shared with CSV parsing. Native
model validation remains independent for direct Python callers; binding, calendar
validity, numeric safety and aggregate/custom limits remain semantic checks.

Bounded template snapshots normalize Mapping/tuple inputs before validation.
YAML data dates normalize to portable typed cells; JSON data needs no extra tree
copy. Resource guards precede recursive schema checks. Conditional component/cell
branches avoid repeatedly visiting alternatives. Errors preserve public classes
and location attributes without including the input value. Exact error wording
is not part of the compatibility contract. Tests cover resource bounds, offline
operation, schema-driven field changes, native enum agreement and scalar types.

To add a transport property, update its schema and the concrete model/builder
wiring if needed; do not add a parallel transport validation list. The native
Python API still requires its own types and validation. No generated model layer,
custom schema interpreter or framework is introduced.

CLI render and validate share source loading, schema-based CSV acquisition and
collision rules. YAML/yml suffixes select YAML independently for template/data;
other suffixes retain the previous JSON interpretation. Validate never measures
layout; schema prints local schema text. No conversion command or source registry.

Verification includes codec round trips, library scalar behavior, no global state
changes, merge/literal-key rules, malformed input, alias limits, schema structure,
CLI parity, reference output through both engines, docs and installed packages.
