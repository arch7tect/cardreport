**Read marker:** in `docs/design.md`, line 28 starts with `o network at rendering time`. The leading "N" is missing.

**Evidence basis:** I only read `docs/design.md` and `README.md`. I ran no commands and didn't check `pyproject.toml`, the lockfile or installed packages. Anything I say below about WeasyPrint, Matplotlib or Chromium comes from what I know, not from a local test. Items marked **[fixture]** need to be checked against real output.

## Correction to the current framing

- Plotly can't be used in a browser-free route. Static export (SVG or PDF) goes through Kaleido, and current Kaleido drives Chrome. Plotly's HTML needs plotly.js running in a browser. So B means **no Plotly**, not "Plotly with a different exporter."
- About half of the design exists only because of the browser: the readiness protocol, async Plotly promises, the browser lifecycle, the asyncio-in-a-running-loop rules, the network sandbox, and Plotly label-markup escaping. B removes that work but adds other work, covered below.

## Comparison

| Concern | A: Plotly + Jinja2 + Playwright/Chromium | B: Python SVG + Jinja2 + WeasyPrint |
|---|---|---|
| Install / native deps | Pip wheels, plus a separate browser download of roughly 100+ MB. Linux needs system libraries (`install-deps`). Docker and CI are heavier. | WeasyPrint needs Pango, HarfBuzz and fontconfig from the OS. That's easy on Linux, needs Homebrew on macOS, and has historically been painful on Windows. Direct SVG has no native deps. Matplotlib has binary wheels but pulls in numpy. |
| Vector marks / selectable text | Inline SVG `<text>` printed by Chromium is normally vector text **[fixture]**. | WeasyPrint has its own SVG renderer that handles inline SVG. Text support for `text-anchor`, `tspan` and baselines may be partial **[fixture]**. Matplotlib's default `svg.fonttype='path'` turns text into outlines, so it isn't selectable. `'none'` keeps `<text>`, but Matplotlib places text using its own metrics, and its output uses `<use>`, `clip-path` and `style="font: …"`, which WeasyPrint may handle imperfectly **[fixture]**. |
| Offline HTML preview | About 3–4 MB of inlined plotly.js. JS must run, and fit is only validated when the file is opened. | Truly static: inline SVG, CSS and base64 fonts. It opens anywhere. But the preview browser and WeasyPrint are different engines, so text wrapping can differ. |
| Nested Row/Column | The browser does flex/grid well, and JS measurement is authoritative. | WeasyPrint's flexbox is partial and its grid support is recent and limited **[fixture]**. Don't depend on either: let Python compute every page, card and chart box in mm, then emit fixed-size, absolutely positioned boxes. Both engines handle that consistently. |
| Tables / pagination | Chromium repeats `thead`. The design already needs a JS measurement pass. | Paged media is WeasyPrint's strength: repeated `thead`, `break-inside`, `@page`. The catch is detecting an over-tall row or an overflow. That needs either Python pre-measurement or inspecting WeasyPrint's laid-out box tree, which is a semi-private API **[fixture]**. |
| Font consistency | One engine handles measuring, rendering and preview, assuming the preview runs in Chromium. | Up to three text engines: Python measurement (fontTools or Matplotlib's FreeType), Pango, and the preview browser. Fix this with one bundled font registered everywhere, plus a cmap check in Python that rejects unsupported glyphs at validation time. That check is deterministic and stronger than A's. Pango versions vary by OS, which can change shaping slightly **[fixture]**. |
| Chart vocabulary | Comes free, but needs a trace allowlist, WebGL prevention and markup escaping. | You write grouped/stacked bar, line (category and date axes, gaps), funnel, legend and value labels yourself. My estimate is about 1k LOC. Date ticks and "nice" axis ticks are the hardest parts. Hostile labels reduce to XML escaping. Funnel isn't native in Matplotlib either. |
| Maintenance | Plotly majors, the monthly Playwright/Chromium cadence, the JS readiness code, browser security settings. | WeasyPrint majors and CSS gaps, Pango drift across platforms, your own chart and text-measurement code. A smaller attack surface: no JS, and a custom `url_fetcher` can deny all fetches. |
| Single source of layout truth | The browser is the truth for both outputs, but only if the preview executes the same JS. | Python is the truth for geometry. WeasyPrint is the truth for glyph rendering only if Python also does line breaking (emitting explicit lines). Then preview, PDF and overflow checks all agree, within a tolerance. |

All the libraries involved (Pango is LGPL, linked dynamically) are compatible with an MIT project. One side note, not a recommendation: if Python owns all geometry and line breaking, WeasyPrint becomes mainly a painter. A direct PDF writer such as ReportLab could then replace it without Pango. I'd leave that out unless B fails only on installation.

## Recommendation

Use **B as the provisional first backend**: a small direct SVG subset (not Matplotlib), Python-owned layout and line breaking, Jinja2, and WeasyPrint. Gate it with the spike below. If the gate fails on text fidelity or overflow reliability, fall back to A. Ship **one** production renderer. No backend interface and no plugin seam beyond the private modules the design already lists.

Why B: it fits the stated priorities (static output, no JS or browser, simple to use and maintain). The chart vocabulary is closed and small. And Python-computed geometry gives deterministic overflow errors, with no async readiness machinery.

**Assumptions:**
- Users are Python developers.
- Target platforms are unknown. Whether Windows is a requirement matters a lot for B. **Please confirm.**
- There is no throughput requirement.
- Latin/Cyrillic text only.

## Minimal comparative spike (time-boxed, roughly 2–3 days, throwaway, not in `src/`)

**One synthetic fixture:**
- A4 landscape.
- A row of 3 KPI cards.
- A second row with weights `[2,1]` and height 90 mm: a funnel card, plus a Column with heights `[3,1]` holding a grouped bar card and a KPI card.
- A line chart with a date axis and a gap.
- A long Cyrillic label, a long unbreakable token, and the literal hostile label `</script><b>&amp;`.
- A flow-mode `Card(Table)` with about 120 rows and wrapped cells.
- A deliberately overflowing variant.

**Variants:**
1. **B-direct:** hand-written SVG and Python layout through WeasyPrint.
2. **B-mpl (half a day, bar chart only):** Matplotlib with `fonttype='none'` through WeasyPrint, to decide whether Matplotlib is worth its weight.
3. **A-baseline:** the same page through Plotly and Playwright, as the reference.

**Checks (run automatically where possible):**
- Clean-venv install steps and size on macOS and Linux (and Windows, if it's a target).
- No image XObjects in the PDF.
- Only the bundled font is embedded.
- Every label is extractable, including Cyrillic and the hostile literal.
- Text positions extracted from the PDF match the Python-computed boxes within about 0.5 mm.
- Python line breaks match WeasyPrint's output (no extra wraps).
- The overflow variant raises before any file is written.
- Table headings and the card title repeat across pages, each row appears exactly once, and an oversized row is rejected.
- Zero fetches (the `url_fetcher` raises).
- Side-by-side visual review of preview and PDF.

**Decision gate:** choose B only if all of these pass:
- SVG text renders as selectable vector text in the bundled font.
- Geometry stays within tolerance.
- Overflow detection is reliable without private WeasyPrint APIs, or with one narrowly wrapped API.
- Installation is acceptable on the confirmed platforms.

Otherwise choose A and record the specific failure.

## Suggested wording changes (not applied)

- **design §1:** replace "The user selected Python + Plotly + Jinja2 + Playwright" with: "Renderer not yet chosen; the preferred direction is static SVG + WeasyPrint with no JS or browser, decided by the gate in §9. Plotly/Chromium is the fallback."
- **§2:** keep "multiple rendering backends" as a non-goal and add "one production renderer."
- **§4:** replace "converts mm to CSS px … for chart measurement" with "Python layout computes all boxes in mm and is the single source of geometry and line breaking." Replace "browser-measured pagination pass" with "Python pagination pass, verified against the rendered PDF."
- **§5:** change `charts.py` to "private SVG chart generation." Make the pipeline backend-neutral, and move the Plotly/JS readiness text into a "fallback A" note.
- **§6–7:** make the dependency, browser-lifecycle and sandbox text conditional on the gate. For B, add OS packages and a no-op `url_fetcher`.
- **§9:** add the spike, the gate criteria and WeasyPrint references.
- **Line 28:** fix the typo ("o network" → "No network").
- **README "Direction":** replace "Hide Plotly, Jinja2 and Playwright" and "PDF through Chromium" with "hide rendering libraries" and "renderer decided by a documented spike."
- **AGENTS.md:** apply the same neutral wording.
- **Dependencies:** leave the `pyproject` dependency changes until the gate decides.
