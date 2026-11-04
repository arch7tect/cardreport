# Implementation review disposition

Date: 2026-11-03. Local v0.1.0. Three implementation-stage Claude consultations
completed successfully (exit 0): P0 selection, full code review, final focused
review. Reviews were advisory/read-only; no reviewer ran tests or edited files.

Sources: [P0 checkpoint](2026-11-03-claude-p0.md),
[code review](2026-11-03-claude-implementation.md),
[final review](2026-11-03-claude-working-final.md).

## Findings and actions

- Selected A based on the concrete overflow experiment; no claim that B cannot
  render reports. Original source mapped to the public API before final selection.
- Disabled funnel axis clipping, checked plot area/category counts and cross-group
  label collisions. Literal-markup/Cyrillic and vector PDF tests exercise output.
- Worker uses exact page-size viewport, CSS page geometry and printed/measured
  page-count verification. Fractional custom-size and title-break checks pass.
- Hard deadline cleanup now covers all exits, not only TimeoutExpired. An owned
  descendant snapshot handles detached Chromium; group/direct-worker kill handles
  process-exit and PermissionError races. Tests reach real Chromium on timeout and
  interruption and assert descendants are gone. A separate simulated group-permission
  race verifies direct-PID fallback.
- All Playwright timeouts are disabled in favor of the parent deadline; no implicit
  browser downloads. Worker error parsing tolerates warnings before final JSON.
- Input container/type validation, negative-zero normalization, regular/bold glyph
  intersection and custom-size orientation errors are explicit.
- Retained private 0600 files and atomic hard-link no-clobber publication; documented
  filesystem limitation rather than adding a partially written output fallback.
- Required installed/editable package is documented; no sys.path propagation hack.

The final reviewer found no blockers, with a small macOS kill-order/PermissionError
race recommended for correction. That correction was applied and regression-tested.
The reviewer noted conservative rotated-label bounding boxes and the narrow window
for a descendant created after the cleanup snapshot; those are recorded limitations,
not a reason to add a service/pool. Routine tested cleanup leaves no owned live
processes. The interrupt test was strengthened after the review to reach Chromium.

## Verification

- `uv run --extra pdf pytest -q`: final suite includes model, output, flow, fidelity
  and process-cleanup tests; the final command result is retained locally.
- `uv run mypy src/cardreport`: passed.
- `uv run ruff format --check src tests examples`: passed.
- `uv build`: wheel and source distribution; fonts/templates/scripts/license present,
  experiments/local evidence/generated output absent.
- Isolated wheel environment: reference example PDF/HTML generated successfully;
  core-only installation creates HTML and gives a clear PDF dependency error.
- Reference PDF: 1 page, all specified aggregate content, selectable text, no image
  XObjects. Original/generated renders visually inspected. Flow example: 5 pages.
- Linux was not exercised because the local Docker daemon was unavailable.

No remote, commit, tag or publication was created. This is a tested local working
version, not a cross-platform release or promise of pixel-identical source styling.
