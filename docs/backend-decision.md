# Rendering backend decision gate

> Update 2026-11-03: the owner authorized typed components, independent validation
> and a provisional renderer extension with an experimental SVG/WeasyPrint path.
> See [renderer extension](renderer-extension.md); the original decision below is historical.


Date: 2026-11-03. Status: A selected for v0.1 after a local comparative experiment and Claude review.
Owner: Oleg Orlov. Current result: [P0 findings](p0-results.md) and
[Claude checkpoint](reviews/2026-11-03-claude-p0.md). The user subsequently authorized
autonomous implementation and routine internal choices. A provides direct measured
overflow checks without a second layout engine. Final implementation verification
is tracked in [implementation status](implementation-status.md).

The sections below preserve the original decision criteria and candidate discussion;
future-tense experiment/install statements describe the pre-implementation state.
This record supersedes any unconditional choice of Chromium
in the initial draft. There will be one production renderer, not a plugin system.

## Requirement and review outcome

The user wants a small CardReport API with cards, KPIs, constrained charts, rows
and columns. Interactivity is unnecessary. The user explicitly asked to keep a
JavaScript-free and browser-free option open and consult Claude.

[Claude's comparison](reviews/2026-11-03-claude-backends.md) recommends testing
static Python-generated SVG + Jinja2 + WeasyPrint first, with Plotly + Jinja2 +
Chromium as fallback. This is advice based on document review, not tested evidence.
The maintainer has not selected a final renderer. The external API remains the
same in both candidates.

## Candidates

| Concern | A: Plotly + Chromium | B: static SVG + WeasyPrint |
| --- | --- | --- |
| Charts | Mature private chart adapter; disable interaction and force SVG traces | Matplotlib SVG or a deliberately small direct-SVG subset; no Plotly |
| Installation | Playwright plus explicitly installed Chromium/system libraries | WeasyPrint with Pango and related native libraries; Matplotlib adds dependencies |
| Report layout | Browser is sole measurement/layout authority | WeasyPrint is final PDF authority; usable geometry/overflow strategy must be proved |
| Preview | Standalone HTML needs JavaScript; test against the pinned Chromium | Static HTML has no JavaScript, but browser and PDF layout may differ |
| Hard part | Readiness, label sizing, browser lifecycle and PDF inspection | Text metrics, CSS support, overflow checks and possibly chart/line-breaking code |

The [Plotly documentation](https://plotly.com/python/static-image-export/)
confirms that current Kaleido static export needs Chrome; it is not candidate B.
[WeasyPrint installation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)
requires Pango, so browser-free does not mean system-dependency-free.
[WeasyPrint API/versioning](https://doc.courtbouillon.org/weasyprint/stable/api_reference.html)
warns that rendering may change across major releases and private APIs are not stable.
[Matplotlib fonts](https://matplotlib.org/stable/users/explain/text/fonts.html)
describes SVG text output options. Preserving text nodes alone does not prove
selectable text or font fidelity after conversion to PDF.

## Disposition of Claude's recommendations

Accepted: keep B open; no automatic backend abstraction; evaluate selectable text,
fonts, clipping, native installation and table splitting on actual output; keep
browser-specific implementation conditional. No backend implementation is included
in the project-creation task.

Qualified: Claude favors direct SVG and Python-owned geometry/line breaking. This
would create chart axes, legends, wrapping and pagination code. It is not accepted
as an architectural decision without evidence that it is simpler to maintain than
Matplotlib or the existing browser engine. A bundled font reduces metric drift but
does not prove identical layout across FreeType, Pango and a preview browser.

Rejected as a pass condition: dependence on undocumented WeasyPrint box-tree APIs
must not silently count as success. Any need for private APIs or a second text
layout engine is a recorded decision tradeoff, not a default implementation detail.
Resource loading must allow exact bundled font/image resources via a controlled
resolver; a blanket failing URL fetcher would also break those embedded assets.
No network or arbitrary filesystem loading is allowed.

Claude's sample reused the old 90 mm / [3,1] geometry. Use the corrected 100 mm /
[2,1] fixture from design.md so the KPI share exceeds its 28 mm minimum.

## Small staged experiment (future implementation work)

1. One shared fixture: A4 landscape, 3 KPI cards, weighted nested row/column,
   funnel, grouped bar, date line with a gap; long English/Cyrillic labels and
   literal markup; a deliberate overflow variant. Use synthetic data only.
2. Produce A and B versions outside src, with no common backend framework.
   First test Matplotlib SVG with text retained; test direct SVG only for the
   representative bar/funnel if that could materially simplify dependency/code cost.
3. Check selectable expected labels and numbers, no raster images, no clipping,
   pinned-font use, visual alignment, explicit overflow failure and zero external
   fetches. Compare measured text/box positions with an initial 0.5 mm tolerance.
4. If B passes dashboard checks, test a separate 120-row flow report with repeated
   headings, exactly-once row IDs and oversized-row rejection. Flow remains Slice 2,
   but this probe must reveal whether the later requirement is achievable.
5. Record installation steps, dependency footprint, code needed and failures on
   macOS and Linux. Windows support remains unspecified; confirm before claiming
   cross-platform readiness. Do not install new OS packages silently as part of
   this design-only task.

Select B only if vector/selectable text, layout, reliable overflow detection and
acceptable installation pass without disproportionate chart/layout code. Otherwise
retain A and record the concrete failing gate. If neither passes, revise the
requirements or design explicitly; do not weaken no-clipping guarantees silently.
For B, the PDF is authoritative and browser preview is approximate unless fixtures
prove parity for the supported subset. Resolve this contract before implementation.

## Dependency status

The uv scaffold initially resolved Jinja2, Plotly and Playwright for candidate A.
These are not a final runtime commitment. Candidate-A packages are now in the
optional browser extra. B dependencies will be added only for the comparative
spike or after selection; WeasyPrint/Matplotlib are not tested or installed by
this task. Chromium is not downloaded by this task.
