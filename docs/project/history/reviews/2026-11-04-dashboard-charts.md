# Dashboard chart extension

Date: 2026-11-04. Version: 0.4.0.

## Delivered contract

One LineChart model supports full and compact presentation, with axes, markers
and none/zero fill. The existing definite Row and weighted Column allocate size;
text-free lines allow a 10mm container. Both engines keep gaps, isolated points
and negative values, with shared styled-line ranges and zero fill. SVG supports
ordinary single-series lines as well as compact ones. Unsupported multi-series
SVG charts and flow still fail explicitly.

Bar category colors use a deduplicated finite palette. One plot is paired with a
shared escaped HTML legend, left or bottom, preserving the same colors and names
in both engines. KPI value size is independent of body text. Python and template/1
options match; old defaults retain their output behavior. The original reference
fixtures remain unchanged.

## Advisory review and disposition

Two design consultations and two implementation reviews used restricted read-only
Claude tools. The final implementation review found no release blocker. Command
and rendering evidence was collected separately, not by the reviewer.

Confirmed findings fixed: compact edge-marker clipping, differing styled x ranges,
float-based chronology rejection of valid microsecond datetimes, and unlocated
palette exhaustion errors. Series colors also avoid an accent/palette collision.
Native legend layout uses a deterministic grid after a flex-wrapping prototype
exposed unnecessary label breaks. Native glyph preflight explicitly permits a
text-free SVG only for hidden axes; labelled charts still require native text.

Default 24pt KPI wrapping is intentionally retained, while non-default sizes keep
values on one line. Duplicate formatted category names are retained consistently
with the existing date-category contract; docs recommend distinguishing patterns.
Snapshot date ticks are now populated without Formatting for SVG. Chromium keeps
automatic date ticks when settings are absent. Plotting below millisecond/pixel
resolution is not guaranteed, though chronology validation is exact.

## Verification and publication

Local macOS/Python 3.12 verification includes 286 tests without skips, both engines,
Ruff, strict mypy, executable user documentation, local links, wheel/sdist metadata,
Twine and isolated installed-wheel core/full smoke. New probes cover gaps, singleton
and all-null lines, missing endpoints, small tracks, marker clipping configuration,
vector marker/swatch presence, escaped legends, overflow and template parity.
Operations and Spanish report PDFs were visually inspected. Two README images are
rasterizations of actual checked PDF pages, regenerated with a repository script.
Operations snapshot values were transcribed from the user-provided dashboard;
trends are synthetic and visibly labelled. The unavailable fifth agent name is
marked; no raw source attachment is included. Publication of these report previews
was explicitly requested by the owner.

Raw review logs, PDFs and runtime results remain ignored. Hosted publication is
verified separately after push. See [dashboard guide](../../../user/dashboards.md),
[release notes](../../../../CHANGELOG.md) and
[preview reproduction](../../development.md#readme-screenshots).

The first hosted attempt failed before checkout: GitHub reported that no hosted
runner acquired the job and noted macOS ARM capacity constraints. A retry also
remained queued and was cancelled. CI now selects the standard macOS 15 Intel
runner; all checks and publication gates are unchanged. This is an infrastructure
workaround, not evidence of a code or test failure.
An additional restricted Claude review found no blocker in the runner change;
native layout, dependency installation and installed-wheel smoke remain mandatory
hosted checks. Local ARM evidence does not imply hosted ARM coverage.
