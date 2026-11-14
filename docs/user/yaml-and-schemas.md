# YAML and JSON Schema

[Documentation home](../../README.md) · [Templates](templates.md) · [Datasets](datasets.md) · [CLI](command-line.md)

Templates and named datasets can both be read and written as JSON or YAML. They
use the same `cardreport.template/1` and `cardreport.data/1` envelopes, binding API
and renderers. YAML support is included in the core installation.

## Use YAML from Python

```python
from cardreport import ReportTemplate, datasets_from_yaml, datasets_to_yaml

template = ReportTemplate.from_yaml("""
format: cardreport.template/1
datasets:
  summary:
    cardinality: one
    fields:
      total: {type: integer}
report:
  title: Call results
  blocks:
    - type: row
      height_mm: 50
      children:
        - type: card
          content:
            type: kpi
            label: Total calls
            value: {bind: {dataset: summary, field: total}}
""")
data = datasets_from_yaml("""
format: cardreport.data/1
datasets:
  summary:
    columns: [total]
    rows: [{total: 34}]
""")
report = template.bind(data)
html = report.to_html()
pdf = report.to_pdf()

# Value-preserving serialization; source comments/styles are not retained.
assert ReportTemplate.from_yaml(template.to_yaml()).to_dict() == template.to_dict()
assert datasets_from_yaml(datasets_to_yaml(data))["summary"].rows == ((34,),)
```

The loaders accept `str` or UTF-8 `bytes`; read files with `Path(...).read_bytes()`.
The dump methods return text. JSON and YAML loaders share the same data decoder;
applications can bind a YAML template to JSON, CSV or native Dataset inputs.

The complete original report is available as
[reference_template.yaml](../../examples/reference_template.yaml) and
[reference_data.yaml](../../examples/reference_data.yaml), alongside its JSON version.

## Standard YAML behavior

CardReport uses unmodified `ruamel.yaml` safe loading/dumping with the pure Python
implementation. It does not install custom resolvers, constructors or tags.
The default is YAML 1.2; an explicit YAML version directive follows the library's
rules. Prefer the default and quote text that another YAML version could interpret
differently. Comments, block/flow notation, multiline strings, anchors and shallow
`<<` merges work normally. Explicit fields override merged fields; earlier sources
in a merge sequence win. Duplicate explicit mapping keys fail. Quote a literal
`"<<"` key so it is not a merge directive. Anchors must occur on actual document
fields; the closed envelopes have no separate definitions section.

| YAML value | Loaded value / advice |
| --- | --- |
| `on`, `no` | Strings under the default YAML 1.2 rules |
| `true`, `false` | Booleans for presentation options; boolean dataset cells are unsupported |
| `00123` | Integer; use `"00123"` for an identifier |
| `2026-11-05` | Native date in dataset cells; quote it for a string or template label |
| `2026-11-05T12:30:00+02:00` | Timezone-aware datetime in dataset cells |
| `12.30` | Floating-point number; use a typed decimal cell for exact precision |
| `null`, `~`, an empty value | Null, distinct from `""` |

The existing explicit typed-cell notation works in both syntaxes. Its `value`
is a string, including for dates:

```yaml
amount: {$type: decimal, value: "1200.50"}
day: {$type: date, value: "2026-11-05"}
instant: {$type: datetime, value: "2026-11-05T12:30:00+02:00"}
```

Native dates/datetimes in YAML data become ordinary Python dataset values and
serialize back as portable `$type` cells. A naive datetime fails as it does in
Python. Templates contain presentation strings/bindings, so unquoted dates in
text positions fail validation. No schema-driven scalar guessing takes place.
YAML sets, binary values, non-string keys and other values outside the report
contract are rejected. Unsafe object tags are never constructed.

Each input contains one document. Existing byte, depth and dataset limits apply;
a streaming event guard bounds parsing, then a traversal of the library's
composed node graph bounds expanded nodes and scalar text, including aliases/merges,
before standard object construction. Cycles/excessive expansion
fail. Integer scalar tokens longer than 4300 characters are rejected before
conversion, including YAML 1.1 base-60 integers. Errors include available line/column information without dumping source
lines. Serialization produces ordinary YAML with library-selected quoting; it
preserves values, not original comments, anchors, whitespace or ordering style.
Emitted YAML targets YAML 1.2 readers; a YAML 1.1 reader can interpret plain
`on`/`no` differently.
A YAML serialization that exceeds the byte cap fails even if the JSON version fit.

## Formal schemas and editors

Two [JSON Schema 2020-12](https://json-schema.org/draft/2020-12) documents describe
structure, component choices, supported properties and typed data cells:

- [Template schema](../../src/cardreport/schemas/template-1.json)
- [Data schema](../../src/cardreport/schemas/data-1.json)

They are included in the wheel and source archive. Retrieve the installed version
without accessing the network:

```python
import json
from cardreport import json_schema

template_schema = json.loads(json_schema("template"))
data_schema = json.loads(json_schema("data"))
assert template_schema["properties"]["format"]["const"] == "cardreport.template/1"
```

Or export it for your editor:

```sh
python -m cardreport schema template > template.schema.json
python -m cardreport schema data > data.schema.json
```

In PyCharm/JetBrains, register the exported file in **JSON Schema Mappings** and
associate your report files. In VS Code, use JSON/YAML extension schema mappings;
the YAML extension also supports a `# yaml-language-server: $schema=...` comment.
Mapping to a local exported schema works offline. Editor feature coverage depends
on the installed editor/extension version.

Both envelopes accept an optional string `$schema` at the root. It is editor
metadata: CardReport never fetches its URL. Templates retain it when serialized;
data snapshots retain only datasets. Older CardReport versions reject this new
key, but existing documents without it remain unchanged. For example:

```json
{
  "$schema": "https://raw.githubusercontent.com/arch7tect/cardreport/v0.9.0/src/cardreport/schemas/template-1.json",
  "format": "cardreport.template/1",
  "datasets": {},
  "report": {"blocks": [{"type": "text", "text": "Hello"}]}
}
```

The schema IDs identify the release introducing that schema revision. Use a
versioned URL or the installed schema instead of a moving main-branch URL.

## What validation checks

Templates use standard `jsonschema` validation against the packaged template
schema. Since 0.7.1, data loading uses a concrete decoder: it reads allowed keys,
required keys and typed-cell kinds once from the data schema, and shares its
scalar patterns. It checks the envelope and typed-cell spelling while decoding;
`Dataset` checks the resulting values once. There is no full-schema walk over
every data cell. The full data schema remains available for editors and external
validators. The schema files themselves are unchanged from 0.7.0.

Both paths work offline; input `$schema` never selects a different validator.
Byte, nesting and expansion guards remain. No flag to disable validation is needed.

Native Python models and binding additionally check references, types,
cardinality, row keys versus columns, calendar validity, resource totals and
component relationships. JSON Schema treats `1.0` as an integer, whereas some
Python API settings require an actual integer; the runtime remains authoritative.
Schema validity does not guarantee layout fit or renderer support. Native Python
construction keeps its own validation; it does not require a JSON round trip.
Structural failures raise `TemplateError` or `DataError`, with a template path
or dataset/row/field when available. Messages identify the failed constraint
without echoing report contents; exact message wording is not a stable API.

For external validation of YAML data with native dates/datetimes, normalize it
through `datasets_from_yaml` then `datasets_to_json` first. Generic JSON Schema
validators work on JSON values and cannot validate Python date objects directly.
Outputs from `datasets_to_yaml` already use the portable typed-cell representation.

```sh
python -m cardreport validate --template report.yaml
python -m cardreport validate --template report.yaml --data datasets.yaml
```

Template-only validation checks the definition and declared bindings. Supplying
data also checks binding with actual values. Neither form launches a renderer;
rendering performs geometry and selected-engine checks. See [CLI options](command-line.md).


## Dynamic text

Quote YAML display strings containing Jinja, especially strings starting with `{{`:
`title: "Daily report for {{ datasets.summary.report_date }}"`.
JSON and YAML use the same [text substitution contract](templates.md#text-substitutions).
JSON Schema describes the string/binding shape; `ReportTemplate` checks expressions,
references and filters. Typed dates come from declared date fields, not guessing
whether a text cell looks like a date.
