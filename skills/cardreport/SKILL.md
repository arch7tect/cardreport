---
name: cardreport
description: Build, render and troubleshoot CardReport reports using Python components or JSON/YAML templates with named datasets. Use when creating or updating reports with this library, including layout, pagination and PDF verification.
---

# Build reports with CardReport

Use this workflow for reports built with the library. Contributor instructions
for changing CardReport itself live in [AGENTS.md](../../AGENTS.md).
Read the references relevant to the current task; the API reference defines the
contract, and this file guides the work.

## Match the environment and documentation

Check `python -m cardreport --version` using the application's interpreter
(`uv run python -m cardreport --version` in a uv project). Read documentation for
that installed version before choosing APIs or renderer features.

Links below resolve in a repository checkout. If reading a standalone copy, use
repository-root paths (drop the leading `../../`) under
`https://github.com/arch7tect/cardreport/tree/vX.Y.Z`, replacing `X.Y.Z` with the
installed version. Documentation on `main` may describe unreleased changes. If
this file disagrees with documentation for the installed tag, follow that tag. This file can be read directly or connected as a skill by a
compatible client; installing the Python package does not register it with agents.

Start with the [Python quickstart](../../docs/user/quickstart.md) and check the
[renderer capabilities and setup](../../docs/user/renderers.md#capabilities).
Chromium is the default; WeasyPrint is an experimental alternative with different
limits and native dependencies. Keep the user's renderer choice explicit. Install
needed dependencies within the task's authorization; report a missing dependency
instead of silently switching engines or claiming an unrendered PDF is verified.

## Choose the representation and prepare data

- Use Python components when composing a report in application code. Start from
  the [Python examples](../../README.md#use-from-python) and consult the
  [API reference](../../docs/user/api.md) for exact signatures and limits.
- Use a JSON/YAML template when presentation should be stored separately from
  named datasets. Follow [templates](../../docs/user/templates.md),
  [datasets](../../docs/user/datasets.md) and
  [YAML and schemas](../../docs/user/yaml-and-schemas.md). Use the installed
  schema through `python -m cardreport schema template` or `schema data` rather
  than inventing fields. A data file uses the CardReport envelope, not arbitrary
  business JSON.
- For file-based work without a Python runner, use the
  [CLI](../../docs/user/command-line.md). CSV names default to filename stems;
  explicit aliases and column types follow the template's dataset declarations.

Aggregation and business consistency belong to the calling application. Verify
row counts, totals, units, null handling and date meanings before binding data.
Percent formats take fractions, so 0.976 represents 97.6%. Keep source values
separate from display formatting; consult
[language and display formats](../../docs/user/localization.md) for localized
numbers and typed dates. Mark synthetic/example data as such in the report.

## Choose layout before filling pages

Read [layout and pagination](../../docs/user/guide.md#control-the-layout).
Use `dashboard` for explicitly arranged pages. Use Chromium `flow` when whole
rows/cards should move to the next page automatically or tables span pages.
A splittable table must be a top-level `Table` or `Card(Table(...))`; tables nested
inside `Row` or `Column` do not split. Use `report.add(Card(Table(...)))`, not
`report.row(...)`, with no fixed row height; in a template, use a top-level card
block. Keep deliberate `new_page()` calls for
intentional section breaks; adding breaks is not a fix for a chart that cannot
fit in its own allocated box.

Page geometry and row heights are in millimeters; font sizes are in points.
Widths/heights in Row/Column are relative weights after gaps; Column `heights`
need a definite parent height. A row's `height_mm`
includes its card titles and padding, not just the chart. Subtract page margins,
report heading and gaps before assigning rows. A whole row taller than an empty
page cannot be fixed by flow. Start with the
[flow dashboard](../../examples/flow_dashboard.py) for a mixed multi-page report,
or the [reference report](../../docs/user/examples.md#reference-report) for an
explicit dashboard. Adapt the example rather than assuming its dimensions fit
new labels and data.

## Render and resolve concrete failures

For Python components, call `report.validate()`. For templates, bind the actual
datasets and then validate the resulting report, or use CLI `validate` with
`--data`/`--csv`. These check structural and binding errors. This does not measure rendered geometry. Creating Chromium
HTML also does not prove it fits: layout checks execute in the browser. Export a
PDF with the intended renderer to exercise its layout checks before delivery.

On `LayoutOverflowError`, use the component path and conflicting label types/text
when available. Consult [errors](../../docs/user/api.md#errors), then change the
relevant width, height, page size or grouping and render again. Long category
labels often need more width, not more height. `show_labels=False` affects value
labels; it does not remove category ticks or legends. Since CardReport 0.8.1, Chromium adjusts outside-value margins and checks rotated
labels, but genuinely cramped charts still fail. Do not patch internal JavaScript or relax validation to force a report
through. If fitting requires fewer details or changed labels, make that choice
explicit and preserve access to the original information.

Keep source templates/datasets intact. Write to a separate output path; use
`overwrite=True` or CLI `--overwrite` only for intentional replacement of generated
outputs. If failures persist after targeted changes, preserve the exact error and
a minimal reproduction instead of repeatedly adding page breaks or dropping data.

## Verify and deliver

Inspect the actual final PDF, especially dense charts, legends and page boundaries.
Check page count, readable labels, repeated table headings, all expected records,
and consistency between KPIs and underlying totals. Successful export detects
layout violations, not business errors or every visual-quality issue. Do not
claim visual inspection if no PDF viewer or page-rendering tool was available.

Deliver the requested output plus reusable code or template/data files when part
of the task. State the renderer, library version and any material verification
limits or deliberate content changes. For future edits, retain the inputs and
working layout rather than only the rendered PDF.
