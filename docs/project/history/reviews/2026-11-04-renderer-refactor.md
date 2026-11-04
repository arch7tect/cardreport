# Typed components and renderer extension

Date: 2026-11-04. Initial version 0.1.0. Owner authorized implementation and public
GitHub initialization. Chromium remains the production default; WeasyPrint is an
explicit experimental subset.

## Agreement and implementation

Claude accepted the revised scope and requested a frozen snapshot, normalized chart
data, an explicit deadline/error contract and native overflow gates. Implemented:
closed recursive public types, Literal options, scalar aliases, explicit row keywords,
strict mypy and consumer typing fixtures; standalone semantic validation; frozen
ReportDocument/ChartData; provisional Renderer Protocol; unchanged default behavior.
No registry, base-class hierarchy, geometry IR or arbitrary component plugins.

WeasyPrintRenderer supports dashboards, explicit pages, cards/text/KPI/tables,
weighted layout and single-series bars. It rejects flow, line/funnel and multi-series
charts. Its pinned private box adapter has positive and negative bundled-font
canaries, checks bounds/component presence/fragmentation, and compares native layout
before and after SVG insertion. Native libraries remain caller-managed.

## Implementation review disposition

The read-only Claude implementation review completed successfully (exit 0). It
found two publication blockers and recommended several focused corrections:

- Whole-SVG font-name replacement could alter a literal label. Replaced it with XML
  text/tspan style-only updates; a literal 'DejaVu Sans' regression test passes.
- Font inspection was shallow and only checked family names. It now recursively
  traverses PDF form resources and compares font IDs 1/3/5 with the bundled faces.
  A deliberately substituted font version inside a nested form is rejected.
- Matplotlib settings are reset inside an isolated rc_context; a changed local font
  list and tick padding no longer affect output. Integer axes use integer ticks.
- SVG metrics needed a native check. An actual PDF character-boundary test detected
  an out-of-bounds horizontal label. SVG now has inward spacing and a native preflight
  using the same viewport/fonts, with pdfplumber checking actual glyph bounds.
  This uses WeasyPrint for rendering, not a second text-layout implementation.
- Overflow canaries include a must-fit case and bundled fonts. External fetch denial
  is surfaced explicitly despite the native library's unusual fatal-error hierarchy.
- Chromium now carries the original absolute deadline through to its worker.
- HTML preview's fixed 30-second experimental deadline is documented.

Raw advisory outputs remain ignored in local/reviews. Original source PDF and all
rendered artifacts remain local; neither is part of the public repository.

## Verification

Final combined checks passed: 80 tests in 51.03 seconds, strict mypy across source
and consumer fixtures (16 files), Ruff lint and formatting (21 files), and wheel/sdist
build. Both renderer examples run from isolated wheel installations outside the
source tree; core-only installation supports validation/HTML and rejects missing
PDF dependencies. Fresh installs bypassed stale same-version uv wheel caches.
Distribution assets/exclusions were checked; local data and experiments are excluded
from packages. Publication contents were reviewed separately, including the original
P0 experiment, licenses and review notes. The third-party font license is preserved
verbatim; its original whitespace is exempted through a narrowly scoped attribute.

The focused final Claude review completed successfully (exit 0), confirmed the prior
blockers resolved and found no new release blocker. Its scope was the SVG adapter,
PDF resource checks, WeasyPrint worker/box adapter and renderer tests; it did not run
tests. Optional future checks for text in PDF pattern/annotation resources remain
out of scope because the current renderer does not generate those structures.
See [final advisory review](2026-11-04-claude-refactor-final.md).

Local macOS/Python 3.12 is verified; Linux/Windows remain unverified. Both reference
PDFs have one vector/text page; layout/ticks differ and pixel parity is not claimed.
GitHub destination: https://github.com/arch7tect/cardreport (public), initial main
commit. No package-registry upload or release tag is part of this initialization.
