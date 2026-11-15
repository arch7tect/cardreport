# Configurable resource budgets

The caller owns resource policy. Keep default data/report budgets but allow any
positive integer, with no unlimited sentinel and no upper ceiling equal to the
default. Existing DataLimits covers transport/decoded datasets. A small immutable
ReportLimits covers table sizes, chart points/categories and page count. Report
snapshots carry that policy into both engines. ReportTemplate remembers a separate
max_bytes budget; bind receives report_limits. CLI overrides call the same APIs.

JSON Schemas describe structure, not installation-specific resource ceilings.
Fixed input/layout recursion guards, component count, supported formats, finite
values, display text bounds and Pillow protection remain independent. Sample
binding validates template structure without enforcing the default table width;
real bound data uses the selected policy. YAML expansion scales with actual source
bytes, preventing a small alias graph from borrowing a large configured budget.

This is not a streaming renderer or a guarantee of successful layout. Long tables
still need Chromium flow, while WeasyPrint needs explicit supported page layouts.
See [limits](../../user/limits.md) for the executable example and defaults.
