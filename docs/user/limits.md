# Resource limits and long reports

[Documentation home](../../README.md) · [API](api.md#limits) · [Images](images.md)

Resource budgets belong to the application running CardReport. Defaults remain
small enough for ordinary reports; every configurable value is a positive integer
that can be increased or decreased. There is no `None`, zero or unlimited mode.
A larger budget permits more work; it does not guarantee that it fits in memory,
finishes before the timeout, or fits on a page.

## Python

`DataLimits` controls dataset loading, serialization and binding. `ReportLimits`
controls rendered table rows/columns/cells, chart points/categories and output pages.
Use both when a template binds a large dataset. Direct Python reports need only
`ReportLimits`.

```python
from cardreport import DataLimits, Dataset, ReportLimits, ReportTemplate

data_limits = DataLimits(max_rows=20_000, max_cells=200_000)
report_limits = ReportLimits(max_table_rows=20_000, max_table_cells=200_000,
                             max_pages=500)
template = ReportTemplate({
    "format": "cardreport.template/1",
    "datasets": {"transactions": {"cardinality": "many", "fields": {
        "id": {"type": "integer"}, "amount": {"type": "number"}}}},
    "report": {"title": "Transactions", "mode": "flow", "blocks": [{
        "type": "card", "content": {"type": "table", "dataset": "transactions",
        "columns": [{"key": "id", "label": "ID"},
                    {"key": "amount", "label": "Amount", "format": "number"}]}}]},
})
data = {"transactions": Dataset(["id", "amount"], [(i, i / 100) for i in range(2500)],
                                 limits=data_limits)}
report = template.bind(data, limits=data_limits, report_limits=report_limits)
report.validate()
# report.write_pdf("transactions.pdf", timeout=180)
```

Pass the same `data_limits` to `datasets_from_json`, `datasets_from_yaml`,
`datasets_to_json`, `datasets_to_yaml`, `from_csv` or `from_pandas` when using them.
JSON/YAML byte limits include encoded values and keys. CSV shares `max_json_bytes`
for its file size. `max_text_bytes` counts decoded string cells across the bundle.
Python's CSV parser also has its standard process-wide field-size limit; changing
that parser setting is the application's responsibility if exceptionally large
individual CSV fields are needed.

## Defaults

| Policy | Field | Default |
| --- | --- | --- |
| DataLimits | max_rows / max_columns | 2000 / 100 per dataset |
| DataLimits | max_datasets / max_cells | 32 / 100000 across a bundle |
| DataLimits | max_string_chars | 10000 per cell |
| DataLimits | max_text_bytes / max_json_bytes | 16777216 / 16777216 |
| ReportLimits | max_table_rows / max_table_columns | 2000 / 20 per table |
| ReportLimits | max_table_cells | 20000 across the report |
| ReportLimits | max_chart_points / max_chart_categories | 500 / 30 per chart |
| ReportLimits | max_pages | 100 |

`ReportTemplate(spec, max_bytes=...)` and `from_dict`, `from_json`, `from_yaml`
accept a template byte budget (default 1048576). The template remembers it for
round trips. `to_yaml()` checks the emitted YAML too, which can be larger than
compact JSON. Embedded image assets count toward this budget.

## Command line

Both `render` and `validate` accept repeatable `--data-limit NAME=INTEGER` and
`--report-limit NAME=INTEGER`, using the field names above. Use
`--template-max-bytes INTEGER` for larger templates. For example, add
`--data-limit max_rows=20000 --report-limit max_table_rows=20000
--report-limit max_table_cells=200000 --report-limit max_pages=500`
to your existing render command. Other fields keep their defaults.

## What does not change

Component depth/count, input nesting depth, type checks, finite numbers, supported
glyphs, chart-series count and text-display lengths remain structural/format rules.
JSON node allowances grow with the selected byte budget; YAML traversal is bounded
by actual source bytes as well as its configured input budget. YAML expanded
aliases and scalars remain bounded. Pillow retains its standard decompression
protection independently of these budgets. Budgets are never read from template
or dataset documents, and editor schemas describe structure rather than runtime
resource policy.

Use Chromium `mode="flow"` and top-level `Table` or `Card(Table)` for long lists.
WeasyPrint still requires explicit pages and does not split flow tables. Increasing
row limits cannot make a single unsplittable table fit on a physical page. A fixed
height can still fail geometry checks. Increase the export timeout separately
when needed; the caller or hosting service owns process/container memory limits.
