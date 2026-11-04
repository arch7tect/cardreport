# CardReport implementation plan

> Update 2026-11-03: the owner authorized typed components, independent validation
> and a provisional renderer extension with an experimental SVG/WeasyPrint path.
> See [renderer extension](../decisions/renderer-extension.md); the original decision below is historical.


Date: 2026-11-03. Owner: Oleg Orlov.
Status: implementation executed through P6 for local macOS v0.1.
See [implementation status](implementation-status.md) for evidence and limitations.
The staged plan below is retained as design history, not pending authorization.
Owner clarification: the original Superset report must be the first usage example.

## Scope and starting point

Deliver a small Python library with Card, KPI, Text, constrained charts and tables,
Row/Column layout, standalone HTML and PDF. The public API hides the rendering
libraries. Ship one production renderer. No BI server, visual editor, raw
HTML/CSS/Plotly escape hatch or backend plugin framework.

The existing repository contains a uv src-layout scaffold, MIT license, README,
proposed design and successful design reviews. It has no reporting implementation,
renderer tests, remote or commits. Package installation/import/build were checked.
The owner opened the project in PyCharm and subsequently authorized end-to-end
implementation, routine decisions and Claude reviews with minimal interruption.

Contracts: [design](design.md), [backend decision gate](../decisions/backend-selection.md),
[design review disposition](reviews/2026-11-03-disposition.md). The gate takes
precedence over browser-specific details in the initial design. This plan refines
the design's large Slice 1 into smaller milestones; it does not expand the scope.

## Dependency sequence and deliverables

| Stage | Depends on | Reviewable output | Completion condition |
| --- | --- | --- | --- |
| P0: rendering experiment | Scaffold | Same fixtures through A and B; evidence and recommendation | Renderer recommended, or documented contract conflict for owner resolution |
| P1: selected contract and data model | P0 decision | Updated design, typed components, validation/formatting | Model contract checks pass; no engine objects in public API |
| P2: cards and page layout | P1 | Small KPI/text/table dashboard in HTML/PDF | Geometry, fonts, text and overflow checks pass |
| P3: supported charts | P2 + reference-to-API mapping | Bar/line/funnel with uniform theme | SVG/selectable-text, label-density and literal-text checks pass |
| P4: dashboard delivery | P3 | Installable dashboard milestone and real examples | Packaged offline outputs and failure handling verified |
| P5: flow reports | P4 | Multi-page reports and table continuations | Exactly-once rows, breaks, headings and overflow verified |
| P6: version readiness | P5 | Release candidate documentation and installed-wheel checks | Declared platform matrix passes; version ready, not published |

P4 is the first usable dashboard milestone, deliberately smaller than the complete
v0.1 scope. P6 includes flow mode. Browser reuse, extra themes, native async API,
new chart types and a CLI are deferred until a concrete use case justifies them.
The mandatory first usage example is the original Superset report that started
this project: `examples/reference_report.py`. It must use only CardReport's public
API and be the first example in README. A synthetic lookalike does not satisfy
this deliverable. No calendar estimates until P0 reveals the cost of layout and
platform setup.

## P0 — compare rendering paths before writing the library

Keep experiment code in `experiments/rendering/`, separate from `src/cardreport`.
Explicitly exclude `experiments/` from the source distribution as well as the
wheel when adding experiment files; verify archive contents, not just imports.
Use a small experiment-local uv project/lockfile for candidate dependencies and a
README with exact reproduction commands. Share only synthetic input/expected
results, not a general backend abstraction. Outputs and detailed observations go
under ignored `local/rendering-comparison/<run-id>/` with a manifest of input,
font, package and output hashes plus environment versions. Link a concise
sanitized result in `docs/project/decisions/backend-selection.md`; preserve raw evidence unchanged.

### P0.1 — define fixtures and checks

Locate the original PDF through a confirmed user-provided attachment/path or the
shared conversation's accessible attachment; do not assume a similarly named local
file is the original. Preserve its bytes and record provenance/hash in ignored
local evidence. Inspect pages and inventory KPI, charts, tables, captions, exact
values, order and relative layout. Create `docs/project/history/reference-report.md` with a sanitized
inventory, source identity and a checklist for visual comparison. Map every
reference element to planned components/options: chart type/orientation/labels,
KPI format/note, table columns/formats and card nesting. Record unsupported elements
and resolve the minimal addition or agreed adaptation with the owner before the
final P0 renderer decision. Add reference-specific compositions to the comparison
fixtures when the generic set does not cover them. Any private data
stays ignored; use approved reproducible data in a distributable example, and
record any sanitization explicitly. Do not publish the source attachment by default.
If the attachment is unavailable, record the missing input and request it when
implementation starts. Synthetic probes may proceed, but the reference example
and P4 cannot be declared complete until the source is verified or the owner
explicitly changes the reference requirement. A renderer recommendation based only
on synthetic fixtures is provisional, not the final reference-compatible choice.
Generic P1/P2 work may proceed under that recorded qualification. At the P3 entry
gate require the source-to-API mapping: if the original arrived after P1, reassess
and amend affected P0/P1/P2 decisions before P3 begins. If it remains unavailable,
pause P3 or obtain an explicit owner scope change; do not assume reference coverage.

Select one redistributable Latin/Cyrillic font, record its license/notice and use
the same bytes throughout. Fixtures use explicit page dimensions and expected
content; no confidential production reports. Build these small documents:

1. Dashboard: A4 landscape, 10 mm margins, three KPI cards, nested [2,1] Row and
   [2,1] Column in a 100 mm row, funnel and grouped bar, plus a small table.
2. Separate chart/text page: category and date line with gaps, negative/zero
   values, long Cyrillic and Latin text, unbreakable token, empty data and literal
   markup including closing-script syntax. Do not cram this into fixture 1.
3. Failure variants: too-small weighted KPI, excessive labels, text/row exceeding
   the printable page and missing font/resource.
4. Flow probe: 120 identified rows, wrapped cells, repeated headings and a separate
   over-tall-row case. This is feasibility evidence, not production pagination.

Use a permissively licensed test runner/PDF inspection tool. Inspect expected text
and page counts, vector paths and recursive PDF resources (including image objects
inside form XObjects); absence of raster images alone does not prove charts exist.
Check representative chart marks, literal labels, embedded font and no clipping
visually as well. Record expected marks/labels independently of the implementation.

### P0.2 — attempt B, then construct the A baseline

B: Python-generated SVG + Jinja2 + WeasyPrint, no JavaScript or browser at render
time. Start with Matplotlib SVG retaining text nodes; test a small direct-SVG bar
or funnel only if it resolves a concrete dependency/fidelity problem. Do not build
an axis/tick/layout framework during the experiment. Verify font handling,
selectable text and all allowed SVG features after PDF conversion. Check final
WeasyPrint output for collisions/clipping of text positioned by Matplotlib; apply
the same 0.5 mm position tolerance, which never permits overlap or lost glyphs.

A: private Plotly + Jinja2 + Playwright/Chromium, explicit SVG traces, disabled
interaction, deterministic chart/font readiness. Reproduce the same valid fixtures
and failure variants. This is a comparison artifact, not a second library backend.
Kaleido/Plotly static export is not a browser-free alternative.

For B, investigate supported CSS, trustworthy overflow detection and text wrapping
without relying on private box trees. If reliable detection requires private APIs
or a custom line-breaking engine, record this as an architectural cost/blocker;
do not silently add it. For A, test measured fit and label density rather than
assuming Plotly's default behavior meets no-clipping guarantees.

Exercise both candidates against the flow probe, including an oversized row.
If B fails earlier, record the early failure and stop unnecessary B work; still
verify the fallback A against the selection checks. Do not automatically select
A merely because B failed. If A fails a hard gate, likewise record it and stop unnecessary A work. If neither
passes, finish P0 with a documented contract conflict; P1 remains blocked pending
resolution rather than a forced backend choice.

### P0.3 — decide from evidence

Record for each candidate: setup commands/dependencies, font license, output size,
render duration (observed, not an SLA), implementation effort, fidelity failures,
external-resource behavior and maintainability risks. Test on available macOS and
Linux environments (an already available local container runtime may supply
Linux evidence); unavailable platform checks remain visibly pending. Never
create cloud infrastructure or fabricate a Linux result. Windows is unclaimed
unless requested; lack of an answer does not block local experimentation.

Hard gates: expected content/marks present, selectable text, vector charts, no
unintended external fetches, reliable explicit overflow failure, feasible flow
contract, and no silent reduction in font size/data. Geometry uses an initial
0.5 mm tolerance for expected box positions, not exact PDF byte equality.
A tolerance never excuses clipping, missing glyphs or lost rows.

Prefer B if it meets the contracts with acceptable setup and less total maintenance
work. If it requires substantial custom geometry/text code, compare that explicitly
against A; browser-free is a benefit, not an absolute requirement. Present a concrete
recommendation and updated backend decision. Resolve any change to user-visible
contracts (preview parity, platform requirements, supported layout) with the owner
before dependent work. Ordinary internal choices that preserve those contracts do
not require an extra approval loop once implementation is authorized.

Exit: either one candidate recommended/selected with evidence, failures preserved
and user-visible tradeoffs resolved, or an explicit no-go record naming the
contract conflict and the required owner decision. A no-go closes the experiment
but does not authorize P1. Platform checks still pending block claims
for those platforms, not all single-platform implementation. Document one source
of truth for layout and the precise HTML-preview guarantee before P1.

## P1 — freeze the selected contract and implement the model

Update design sections 4–7 to describe the selected renderer, removing conflicting
candidate-specific promises. Keep discarded experiment evidence for traceability.
Replace the experimental dependency setup with the chosen runtime/optional extra
contract; update uv lock, installation docs and contributor instructions together.
Define minimum supported Python/engine versions and tested platform scope.

Implement Report/Page/Theme, Row/Column/Card, KPI/Text, chart input records,
Table/TableColumn, formats and ReportError subclasses as small concrete modules.
Add a dev group with pytest, mypy and pypdf; use pdfplumber for PDF text positions
when geometry checks require it. Retain versioned tool commands in the README.
Add the proposed builders and public imports, immutable component records,
defensive copying, export snapshots and block paths in errors. Define numeric,
Decimal, None, date/time, shape and containment semantics from the design.

Choose finite documented caps for nesting, blocks/pages, rows/cells, series/points
and input text in this stage using P0 evidence. State units and test boundary and
one-over-boundary cases. These caps are input limits, not claims of a memory
sandbox. No production renderer is needed to verify model behavior.

Checks: meaningful invalid nesting/weights and minimum allocations; mutable-input
isolation; currency/percent rounding; malformed/missing keys; UTC/naive-time rules;
empty data and line gaps; cycles/limits. The exact design example is a contract
fixture and must build through public API. Unsupported flow mode fails explicitly.

When reference mapping is pending, the generic model baseline remains provisional
until the P3 entry gate; record any revision instead of implying API completeness.

Exit: model tests and type checks pass; no renderer objects or arbitrary engine
kwargs leak through public imports. Canonical formats and limits are documented.

## P2 — first vertical slice: cards, layout and PDF

Implement the selected renderer only. Build the minimal end-to-end path from
Report to HTML and PDF for KPI, Text and a small unsplit Table; include Card,
weighted Row/Column, page margins, title, fonts and theme. Implement engine-specific
measurement inside the private renderer, not two independent layout engines.

Implement no-clobber output publication, dependency errors, timeouts and cleanup
now, alongside the first PDF path. Define a bounded failure mechanism for the
selected engine: B may need an owned worker process to enforce the deadline; A
must cover launch, layout and printing rather than only navigation timeout. Make
resource loading allowlisted for bundled assets and block network/arbitrary files.
Reuse P0 results where they are checked and understandable, not wholesale spike code.

Checks: expected PDF geometry/text/page count, nested minimum-height rejection,
wrap/overflow behavior, all fonts loaded, matching packaged font bytes, zero
unintended fetches, missing assets, timeout and existing-output preservation. Test
normal return and failure cleanup. Export two different reports to detect stale state.

Exit: an installed-library example creates an accurate card dashboard and refuses
overflow; HTML-preview guarantees match the chosen contract. No chart stubs are
presented as functioning features. Private renderer may be incomplete for charts.

## P3 — implement the closed chart vocabulary

Add BarChart (grouped/stacked, both orientations), LineChart (category/date, gaps)
and Funnel (caller stage order). Apply named theme styles and a small public option
set. Use bounded label/legend layout and literal-text handling. Axis labels and
data labels are distinct: optional value labels may be off, required categories
may not silently disappear. Reject unsupported density at a documented boundary. P3 may tighten P1 input
limits when measured label density requires it; update documentation and boundary
tests together before the dashboard milestone.

Checks: empty and all-zero data; negative bars/lines; multi-series; funnel increases
and negative-value rejection; Decimal conversion; date normalization; line gaps;
hostile labels as literal text; long Cyrillic; label collisions; vector marks and
selectable labels. For A explicitly reject WebGL and unsafe label markup; for B
verify SVG text/clip/use features and no unintended path-outlined text.

Assemble `examples/reference_report.py` as the first full public-API example,
using the source inventory from P0. Include the original KPI/card/chart/table
composition and values (or explicitly approved sanitized equivalents). Keep chart
backend imports out of the example. Preserve inconsistent source metrics rather
than silently correcting them; flag discrepancies in the example documentation.

Exit: all three public chart types render and fail predictably through the same
API. The full synthetic campaign example passes content and visual review. The
reference example is assembled from the mapped source; final reference
acceptance belongs to P4. No
chart-library imports are needed in user examples.

## P4 — dashboard milestone

Complete multi-page explicit dashboard composition and all public write methods.
Check source/wheel packaging includes templates, scripts (A only), font bytes and
third-party notices. Make the original report the first documented runnable example:
`uv run python examples/reference_report.py`. It produces
`output/reference_report.html` and `output/reference_report.pdf`; input values live
in a small explicit data structure/file with provenance and any sanitization
explained. The default command must run without backend-library knowledge and
must preserve an existing output unless overwrite is explicitly requested.
Secondary examples cover a small report, nested layout, empty input and a handled
overflow error. README becomes executable usage plus
installation/troubleshooting for the selected path; label flow as unavailable.

Checks: inspect wheel and sdist contents (including experiment/local-artifact
exclusion), clean-wheel install and execution without the source tree, rendering with
network access disabled, generated HTML preview, correct explicit page counts,
no browser/native install at import time, absent optional dependency message,
failed export leaves original output intact, and repeated export resource cleanup.
Run the dashboard suite on each declared supported platform; report untested ones.

Reference acceptance: compare against the verified original PDF for page count,
all expected KPI values and table rows, chart stages/categories/order, card grouping,
relative widths/heights, titles, units and readable labels. Inspect the original
and generated pages side by side; record any visible differences and their causes.
Use the shared 0.5 mm geometry tolerance for measured boxes where practical; font
substitution or cosmetic differences require an explicit recorded disposition,
not a false claim of pixel identity. Check selectable text, vector chart marks,
no clipping and working offline HTML. As a final regression check, confirm no source element remains outside the
closed API after the early P0/P3 mapping. If a missed gap is discovered, reopen
the affected contract and renderer decision before marking the example complete; never substitute an unrelated chart silently.

Exit: the first usage example passes its reference comparison, and a user can
install locally with uv, run an example and obtain a dependable
PDF using only the documented CardReport API. Dashboard milestone may be delivered
without claiming complete v0.1. Public API changes after this point require migration
notes; do not rename components casually in subsequent slices.

## P5 — multi-page flow reports

Implement the tested pagination strategy from P0 with the selected layout authority.
Enable flow mode, PageBreak and top-level Table/Card(Table) fragmentation. Repeat
column headings and card titles, keep rows whole and ordinary cards/rows indivisible.
Nested tables remain indivisible. Handle leading/trailing breaks and empty content
explicitly; agree exact empty-report behavior in the contract before coding it.

Checks: 120-row fixture with IDs appearing exactly once, headings on each fragment,
wrapped cell heights, oversized row, tall indivisible nested card, page-boundary
cases, title-only fragments, explicit breaks and absence of blank pages. Include
font/width variations to invalidate fixed row-count assumptions. Cross-check the
saved PDF rather than only intermediate layout metadata.

Exit: both dashboard and flow suites pass; flow usage is documented. No production
pagination code is carried for the unselected renderer.

## P6 — readiness, not publication

Run the combined contract, integration and packaging suite on the declared Python
and platform matrix. Add automation only for available/authorized repository CI;
no hosted repository creation is implied. Verify installed wheel offline behavior,
licenses, notices, imports and documented setup. Record observed performance and
limits without speculative promises. Provide a concise release-candidate checklist
and known limitations. Version consistently after API scope is complete.

Exit: reproducible checks and examples pass; docs describe actual behavior. Remote
creation, release tagging, upload and publication remain separate explicit tasks.
PyPI name availability must be checked before publication, not assumed from the
local project name. No post-v0.1 renderer reuse/async/theme work is bundled here.

## Review, change control and evidence

Each stage leaves a short completion record with implemented scope, exact commands,
results and unresolved limits. Preserve synthetic fixtures and sanitized summaries
in the project; generated outputs stay ignored. Critical backend findings must also
be routed to CodexHome through its wiki lifecycle. If the experiment becomes durable
textual research, use the CodexHome research bundle and evidence gate before commit.
Do not turn local logs into published evidence or delete unique comparison outputs.

Implementation was subsequently authorized; preserve stage verification and avoid
unrelated refactoring.
If a gate fails, narrow the fix to the cause and rerun affected checks; do not expand
scope or weaken content/overflow requirements. Experimental alternatives remain
outside the shipped package. Preserve a working milestone when replacing renderer
internals; compare against its acceptance fixtures before switching.

Open inputs: the original Superset PDF/source data are required for the P3
reference-to-API gate, first usage example and P4 acceptance, not for starting
synthetic P0 probes or provisional generic P1/P2 work. Windows
support and throughput goals are unspecified. A local macOS start is sufficient
for P0; Linux results are needed before claiming Linux support. Missing reference
data must stay visible as a deliverable dependency, never be replaced by invented
values without owner agreement. These unknowns do not block writing/reviewing this
plan.
