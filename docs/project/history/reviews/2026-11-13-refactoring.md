# Refactoring verification — 2026-11-13

Status: implemented and verified locally; no version bump or release. Baseline:
`fa3f21cf70e3e57d54322fb450a3cd72103ef4e6`.

## Scope

- Replace the provisional Renderer Protocol with one ABC and explicit built-in
  inheritance. This changes the static extension contract; exports retain runtime
  duck typing. See [migration guidance](../../../../CHANGELOG.md#unreleased).
- Reuse Page, Theme and Formatting defaults in template binding. Extract table
  and chart construction into methods in the same module, retaining error paths.
- Share typed internal SVG payloads between producer and worker; separate line,
  bar, funnel drawing and label checks without introducing a chart framework.
- Keep public method signatures, template/data schemas, lazy dependencies, drawing
  order, overflow rules and process cleanup unchanged.

## Checks

On Apple Silicon macOS/Python 3.12 with both renderers and native dependencies:

- Ruff lint/format and strict mypy passed (47 source/example/check files).
- Full pytest run: 590 passed, zero skips. A subsequent 19-test focused run passed
  after review corrections, including one additional formatting-payload drift test.
- Documentation checker executed 52 Python blocks across 13 pages; paths and
  anchors passed. Custom renderer example uses ABC inheritance.
- Final wheel/source archives passed package checks. Core-only and all-extras
  installed-wheel smoke tests passed outside the checkout.
- Reference PDFs from both engines matched baseline text, page dimensions and
  1600-pixel rasterizations exactly. Five SVG cases matched byte for byte with
  volatile metadata timestamp and ID salt fixed: grouped bars, horizontal stacked
  bars, a multi-series line with gaps, a compact filled line and a funnel.
- The server child rendered the reference template/data with this candidate
  library for Chromium/WeasyPrint and HTML/PDF. The server lock was not changed.

Claude reviewed the scoped design and implementation in both repositories through
read-only access and found no blockers. Follow-up corrections clarified static vs
runtime inheritance, preserved explicit duck-typing tests and checked formatting
payload field drift. Optional generic frameworks and storage-layer reshuffling
were not added.

The largest functions are now shorter (`render_svg`: 309 to 106 lines; binder
`node`: 148 to 42). Overall source size increased because of explicit types and
helper signatures; this change removes duplication and separates responsibilities,
rather than claiming a net line-count reduction.

Raw review output, before/after artifacts and check logs are retained under ignored
`local/refactor-2026-11-13/`. They are not package or publication inputs.

## PyCharm inspection follow-up

PyCharm's enabled MCP server inspected all 30 Python source files through
`get_file_problems`, including warnings. Explicit binary subprocess typing, typed
callbacks, local narrowing and tuple/geometry types resolved the reported type
and overload warnings without disabling inspections. Two intentional unreachable
warnings remain around the closed-union `assert_never` guard; weak style and
spelling suggestions are not treated as typing failures.

The follow-up passed all 591 tests without skips, strict mypy on 47 files, and
the CI Ruff lint/format scope (`src tests examples scripts`). Five normalized SVG
outputs still matched the baseline byte for byte. Documentation checking verified
357 local links across 56 Markdown files. A broader Ruff scan also found existing
format/style issues in historical documents and the rendering experiment outside
the CI scope; those were left unchanged.

Claude's read-only follow-up review found no blockers. Evidence is retained in
ignored `local/ide-inspections-2026-11-13/`. No release or push was performed.
