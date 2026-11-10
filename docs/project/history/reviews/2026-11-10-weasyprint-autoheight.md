# WeasyPrint natural card height

The owner authorized a library fix, Claude review, tests/docs and a patch release.

A synthetic standalone Card(Table) reproduced the failure before the fix. In
WeasyPrint 70, the adapter's `minmax(0,1fr)` auto-height card content track could
collapse to zero while the table retained its own height. The parent card then
failed the existing overflow check despite sufficient page space.

Cards now expose the existing inherited definite-height context in shared markup.
WeasyPrint lays out natural-height cards as blocks, retaining the title/content
gap. Cards constrained by rows or weighted columns keep the grid layout. The
unweighted Column reset and fixed Row propagation follow the same rules as chart
sizing and validation. Chromium does not style this card attribute. No public
API, schema, dependency, overflow tolerance or resource-fetch policy changes.

The restricted Claude design review endorsed this approach over changing every
grid track's minimum, which could alter fixed-height chart sizing. Regression
coverage includes titled/untitled/wrapping titles, natural rows/columns, unequal
cards, mixed/nested content, a natural card around a fixed row, unweighted columns
inside a fixed row, chart legends and actual PDF text placement. Too-small rows,
weighted columns and overfull pages still fail and preserve existing output files.

A private five-page report was also rendered with its original template and data,
without the fixed-height workaround. All five pages were visually inspected and
all table cell values were found in their expected pages. Private inputs and
outputs are not included in the repository; regressions use synthetic fixtures.

The implementation review found no blockers. Its documentation finding was
confirmed: a natural KPI card now renders, so the old explicit-height warning was
removed and the executable renderer example now uses a natural card. Two initial
test assertions were adjusted for PDF text extraction kerning ("T wo"/"T ail");
the rendered content and geometry were correct. Runtime behavior was not changed
to accommodate those assertions.

Local acceptance: all 587 tests passed without skips, including 20 new regression
cases. Ruff/format, strict mypy, 355 local links, 52 executable Python documentation
blocks, bundled fixtures/CLI examples, wheel/sdist metadata and installed core/full
wheel smoke checks passed. Native WeasyPrint setup used the documented Homebrew
library path. The release workflow must repeat these checks before publication.
