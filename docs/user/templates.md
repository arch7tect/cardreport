# Report templates

[Documentation home](../../README.md) · [Datasets](datasets.md) · [API](api.md#reporttemplate)

A template defines presentation and required named datasets. Binding returns an
ordinary Report, so export methods and renderer capabilities remain unchanged.
Display text supports Jinja field substitutions and formatting filters.
No data fetching, formulas, loops or SQL run during binding.

## Embed a template

```python
from cardreport import Dataset, ReportTemplate

spec = {
    "format": "cardreport.template/1",
    "datasets": {
        "summary": {
            "cardinality": "one",
            "fields": {"total": {"type": "integer"}},
        },
    },
    "report": {
        "title": "Call results",
        "blocks": [{
            "type": "row", "height_mm": 50,
            "children": [{"type": "card", "content": {
                "type": "kpi", "label": "Total calls",
                "value": {"bind": {"dataset": "summary", "field": "total"}},
            }}],
        }],
    },
}
template = ReportTemplate.from_dict(spec)
report = template.bind({"summary": Dataset.single({"total": 34})})
html = report.to_html()
pdf = report.to_pdf()

# The same definition with another input creates a fresh report.
next_report = template.bind({"summary": Dataset.single({"total": 57})})
```

Use `ReportTemplate.from_json(text)` or `ReportTemplate.from_yaml(text)` for a stored template. `to_dict()` and
`to_json()`/`to_yaml()` return its validated definition; editing a returned dict cannot mutate
the template. Native data use Dataset, stored data use datasets_from_json. Template
and data versions are separate. Neither envelope contains connection credentials.

The [README alternative](../../README.md#2-json-template-and-named-datasets) and
[quickstart_template.py](../../examples/quickstart_template.py) show a complete
KPI/bar report with inline JSON for both the template and named datasets, using
only the installed public API. No separate JSON files are needed for that example.

## Vocabulary and bindings

The envelope requires format, datasets and report, and accepts optional string `$schema` editor metadata. Report requires blocks (an array, possibly empty) and accepts optional
title/subtitle/mode/page/theme/language/formatting/empty_text with the [Python API](api.md)'s defaults. Each dataset
has fields and cardinality one/many. Fields require type and optionally nullable
(default false); all declared datasets and fields are required at bind, even when
unused. Extra data columns/datasets remain permitted within data bounds.

| type | Content/data mapping |
| --- | --- |
| card | content; optional title |
| row / column | children and ordinary width/height options |
| page_break | Top-level break |
| text | text and optional style |
| kpi | label, bound value, optional format/note |
| table | dataset; ordinary TableColumn definitions in columns |
| bar / funnel | dataset, category field, value field |
| line | dataset, x field, value field and x_kind |

Bar/Line accept `series: [{"field":"count","label":"Calls"}, ...]` instead of
value; order is explicit and series labels unique. Bar categories accept non-null
text, date or datetime fields; Funnel categories require non-null text. Typed bar
categories use report date/datetime patterns without changing their order or
merging matching display labels. Text categories remain literal.
Line x_kind=date uses date/datetime fields. Chart values require numeric fields;
only Line permits nullable values for gaps. Row order is preserved. Ordinary chart
options (orientation, mode, show_labels, legend, value_format) apply where supported.
Line also accepts axes/markers booleans and fill=`"none"` or `"zero"`. Bar accepts
color_by=`"series"` or `"category"`, legend_position=`"bottom"` or `"left"`, and
category_labels. Theme accepts kpi_value_size_pt. Defaults preserve old templates;
all constraints match the [Python API](api.md) and [dashboard guide](dashboards.md).

Scalar bindings are `{"bind":{"dataset":"summary","field":"total"}}` and
require one row. They can also provide full text: report title/subtitle, Text.text,
KPI label/note and Card title. Only Card title/KPI note accept nullable text; other
text positions require non-nullable text. Constants for those text fields are
allowed. KPI values, table rows and chart data always come from datasets.

Page, Theme, layout weights, display formats, table headings/empty text and chart
settings are literal presentation. Currency is `{"currency":"EUR"}`. There is no
automatic calculation of totals or dynamic strings: supply complete phrases as
text data. Static numbers can be placed in a one-row dataset. Direct Python report
composition remains available for applications that do not need templates.

## Validation and errors

The packaged JSON Schema defines the transport structure and is used during
loading. TemplateError rejects unknown versions/keys, incompatible bindings and structural
settings. BindingError reports missing/type/cardinality/data errors, then wraps
existing semantic validation failures. Both derive from ValidationError. Error
locations may identify a dataset, zero-based row, field or template_path; unknown locations are
not invented. Existing render errors retain their ordinary component paths.

Binding succeeds before any layout measurement. PDF export can still reject
content that does not fit or a renderer's unsupported feature. A larger dataset
may overflow a fixed dashboard row even when its schema is correct. Flow and the
experimental renderer retain their [documented limits](renderers.md#capabilities).

Template JSON is limited to 1 MiB and nesting depth 64; the constructed component
tree also obeys the existing depth/count limits. The format is provisional, version
1; unsupported versions fail explicitly. YAML read/write and formal JSON Schema files are available; see [YAML and schemas](yaml-and-schemas.md).

## Display settings

The optional report fields `language`, `formatting` and `empty_text` are supported
in `cardreport.template/1` starting with CardReport 0.3.0. The format identifier is
unchanged by the owner's pre-adoption compatibility decision; older packages reject
these new keys. Existing templates retain their behavior. Data remains `cardreport.data/1`.

```python
localized_spec = template.to_dict()
localized_spec["report"]["language"] = "es-MX"
localized_spec["report"]["formatting"] = {
    "decimal": ",", "group": ".", "number_decimals": 2,
    "date_format": "d 'de' MMMM 'de' yyyy",
}
localized = ReportTemplate.from_dict(localized_spec)
assert localized.bind({"summary": Dataset.single({"total": 34})}).language == "es-MX"
```

`formatting` is an object with the [Formatting fields](api.md#language-and-formatting).
Omitting it means legacy axes; `{}` means explicit defaults. JSON `null` is not a
formatting object. `date_format`, `datetime_format` and `locale` may be omitted or
null. Report/table `empty_text` may be omitted/null to inherit, or a literal string.
These options are static presentation settings, not data bindings. Serialization
preserves the missing-vs-explicit distinction. No dataset/CSV parsing changes occur.

See [spanish_template.json](../../examples/spanish_template.json) and
[spanish_data.json](../../examples/spanish_data.json) for the complete example.


## Text substitutions

Use ordinary strings with Jinja expressions in `report.title`, `report.subtitle`,
`Card.title`, `Text.text`, `KPI.label` and `KPI.note`. The same syntax works in JSON,
YAML and `ReportTemplate.from_dict`. Quote YAML strings containing expressions.
See the complete [daily report example](../../examples/daily_report.py).

```python
from datetime import date
from cardreport import Dataset, ReportTemplate

daily_template = ReportTemplate.from_yaml("""
format: cardreport.template/1
datasets:
  summary:
    cardinality: one
    fields:
      report_date: {type: date}
      total: {type: integer}
report:
  formatting:
    date_format: dd.MM.yyyy
    group: space
  title: "Daily report for {{ datasets.summary.report_date }}"
  subtitle: "Month: {{ datasets.summary.report_date | date('MMMM yyyy') }}"
  blocks:
    - type: text
      text: "Total calls: {{ datasets.summary.total | integer }}"
""")
daily_report = daily_template.bind({
    "summary": Dataset.single({"report_date": date(2026, 11, 14), "total": 12540}),
})
assert daily_report.title == "Daily report for 14.11.2026"
assert daily_report.subtitle == "Month: November 2026"
```

Only declared fields of `cardinality: one` datasets are available, under
`datasets`. Dot lookup reads keys, including keys named `items` or `keys`.
Use brackets for other names: `{{ datasets["daily summary"]["report date"] }}`.

| Expression | Display |
| --- | --- |
| `{{ datasets.summary.report_date }}` | Typed date using report `date_format` |
| `{{ datasets.summary.report_date \| date }}` | Date-only display; default report format |
| `{{ datasets.summary.report_date \| date('d MMMM yyyy') }}` | Explicit LDML date pattern |
| `{{ datasets.summary.total }}` or `\| number` | Report number precision and grouping |
| `{{ datasets.summary.total \| integer }}` | Rounded integer with report grouping |
| `{{ datasets.summary.rate \| percent }}` | Fraction multiplied by 100, with percent precision |
| `{{ datasets.summary.amount \| currency('EUR') }}` | Currency code and report currency precision |

Typed datetimes use `datetime_format` by default; `date` selects the date only.
Datetimes are normalized to UTC before formatting, including explicit filters.
The date filter's optional pattern is a constant LDML string and supports date
fields only (no time fields). Report `formatting.locale` or `language` selects
month names. Strings stay literal, including strings resembling dates. Nullable
values display an em dash (`—`); an absent field is an error. Numeric grouping also
applies to integer years and IDs: declare these as text when grouping is unwanted.
Trailing zeros follow the existing numeric formatter, not fixed-width formatting.

Formatting filters return final text, so an explicit filter takes precedence over
default formatting. One filter per field expression is supported; filters accept
only the constant positional arguments listed above. Jinja loops, conditions,
arithmetic, function/method calls, attribute traversal on values, includes and
other filters are not supported. This is text substitution, not a calculation layer.

Unknown references, syntax and filter/type errors fail while loading the template
with a `TemplateError` and `template_path`. Binding checks actual values and final
text using the existing model limits; failures are `BindingError`. Sample values
do not determine whether a dynamic heading fits its character limit. PDF geometry
checks still happen during rendering. No new length limit or configuration is added.

Substitution runs once at bind. Strings coming from data or existing whole-value
`{bind: ...}` objects are never interpreted as templates. Serialization preserves
the original source expressions. Output remains plain text, escaped by the HTML
renderer. Table column labels, series labels, empty messages and technical strings
stay literal. Direct Python model strings such as `Text("{{ example }}")` also
stay literal.

**Compatibility in 0.9.0:** `cardreport.template/1` is retained, but existing literal
Jinja delimiters in these six text positions now have meaning. Escape literal text
with `{% raw %}{{ example }}{% endraw %}` or `{{ '{{' }}`. Jinja comments and whitespace
control use their normal syntax; Jinja normalizes CRLF to LF in parsed strings.
Ordinary strings without delimiters are unchanged, including trailing newlines.
