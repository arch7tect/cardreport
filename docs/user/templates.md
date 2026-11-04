# Report templates

[Documentation home](../../README.md) · [Datasets](datasets.md) · [API](api.md#reporttemplate)

A template defines presentation and required named datasets. Binding returns an
ordinary Report, so export methods and renderer capabilities remain unchanged.
No data fetching, formulas, loops, interpolation or SQL run during binding.

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

Use `ReportTemplate.from_json(text)` for a stored template. `to_dict()` and
`to_json()` return its validated definition; editing a returned dict cannot mutate
the template. Native data use Dataset, stored data use datasets_from_json. Template
and data versions are separate. Neither envelope contains connection credentials.

## Vocabulary and bindings

The envelope has exactly format, datasets and report. Report requires blocks (an array, possibly empty) and accepts optional
title/subtitle/mode/page/theme with the [Python API](api.md)'s defaults. Each dataset
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
value; order is explicit and series labels unique. Categories use non-null text.
Line x_kind=date uses date/datetime fields. Chart values require numeric fields;
only Line permits nullable values for gaps. Row order is preserved. Ordinary chart
options (orientation, mode, show_labels, legend, value_format) apply where supported.

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

TemplateError rejects unknown versions/keys, incompatible bindings and structural
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
1; unsupported versions fail explicitly. YAML and JSON Schema files are deferred.
