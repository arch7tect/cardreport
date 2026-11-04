# CardReport design review (advisory only)

**Read marker:** `docs/project/history/design.md` §4 "Layout contract" includes the passage *"Dashboard mode: each explicit page is a fixed printable rectangle. Rows cannot fragment."*

I read `docs/project/history/design.md`, `README.md`, `pyproject.toml` and `AGENTS.md`, plus `src/cardreport/__init__.py` (a one-line docstring) and `py.typed`. I made no edits and ran no commands.

## Verdict

**I endorse it as the baseline, but four corrections should go into the design before Slice 1 starts.** The overall direction is coherent and can be built: a closed component set, Plotly hidden behind the API, dashboard mode first with flow mode in Slice 2, overflow treated as an error, and explicit browser readiness instead of sleeps. The gaps are wording and contract gaps, not architectural ones.

## Fix before Slice 1

### 1. The §3 example breaks the §4 minimum-size rule
- **Problem:** In the example, the `Row` has `height_mm=90` and contains a `Column` with `heights=[3, 1]`. After the 4 mm gap, 86 mm is left, so the KPI card gets 21.5 mm. §4 sets a 28 mm KPI card minimum. The design's own main example would fail.
- **Second problem:** §4 says a parent "may not violate component minimums" but doesn't say what happens when weights would. It also gives a 60 mm *default* chart height but no chart *minimum*.
- **Fix:**
  - Change the example, for example to `heights=[2, 1]` with `height_mm=100`, or lower the KPI minimum.
  - Add to §4: "Weighted allocation never redistributes. If a share falls below a component minimum, raise `LayoutOverflowError` with the path, the required size and the allocated size. Where everything involved has a fixed minimum, check this in Python before the browser runs."
  - State the chart body minimum in the default theme.
  - Say whether `height_mm` and the minimums include the card border.

### 2. It isn't clear whether Python or the browser does the layout (§4, §5)
- **Problem:** §5 gives `layout.py` "block allocation", but natural table and text heights and wrapping (§4) can only be measured in the browser. Two layout engines would drift apart.
- **Fix:** Add one sentence to §5: "The browser (CSS flex/grid plus the readiness script) is the only layout engine. `layout.py` only does static validation (the grammar, weighted-Column rules, fixed minimums, limits) and produces page and container metadata. All measured fit decisions happen in the browser."

### 3. There are no rules for what can contain what (§3 Components, §4)
- **Problem:** The design doesn't say:
  - whether a bare `KPI`, chart or `Table` can sit directly in a `Row`, `Column` or the report (the example always wraps them in `Card`);
  - whether `Card(Row(...))` is allowed (§3 only says "optionally a Column");
  - whether a `Column` can contain a `Row`.

  Also, §4 says "optional block/row height", but only `Row` has `height_mm`.
- **Fix:** Add a short list of allowed nesting. My suggestion:
  - Top-level: `Row`, `Card`, `Text`, plus `PageBreak` in flow mode.
  - `Row` and `Column` children: `Card`, `Column`, `Row`, `Text`.
  - `Card` content: one leaf component, or one `Row` or `Column`.
  - Say whether a `Column` without weights is top-aligned or stretched when its parent gives it a definite height.
  - Remove the word "block" from §4, or add `height_mm` to `Card`.

### 4. Chart text conflicts with the "never silently" rules (§4, §7)
Plotly's defaults break the design's own promises in four places:
- **Wrapping:** §4 says "Labels/cells wrap", but Plotly doesn't wrap tick, legend or funnel labels on its own. Wrapping needs `<br>` markup, and §7 says labels must be shown literally. **Fix:** Either say chart labels don't wrap in v0.1 (use automargin with a bounded margin, and fail if it's exceeded), or say the adapter escapes the text first and then inserts its own measured breaks.
- **Shrinking text:** Text inside bar and funnel segments is scaled down to fit by default, and `uniformtext.mode="hide"` hides it. Both break "never silently shrink or hide". **Fix:** Require a fixed text size (`uniformtext` with mode `show` at the theme size) or outside placement, plus an overlap check in the browser.
- **Hidden category labels:** Automatic ticks can skip category labels when they're crowded. **Fix:** Require explicit category tick values, and treat a skipped or overlapping label as a density failure.
- **Escaping and math:** §7 should name exactly what the adapter does:
  - escape `&`, `<` and `>` as entities in every Plotly text field (names, labels, hover is irrelevant, titles);
  - set `typesetMath: false`, with no MathJax;
  - add `$x$`, `&amp;` and `<br>` to the hostile-label fixtures (§8);
  - have the HTML-safe JSON encoder also escape `<!--`, U+2028 and U+2029, not only `</script`.

## Important but small

- **HTML vs PDF contract (§5):** Say the PDF is the authoritative output, and the HTML preview is only guaranteed to fit in Chromium-based browsers. Say one stylesheet is used for both screen and print, with `@page` only for print, so preview and PDF lay out the same. Say that printing the HTML from a browser is not supported.
- **Fonts and Plotly (§5 rendering order):** Plotly measures text when `newPlot` runs. So say: wait for every bundled font face to load *before the first* `newPlot`, and pass the bundled font family into the Plotly layout. The final `document.fonts.ready` check stays as a second check.
- **Currency format (§3 Formats):** "Currency with explicit currency code", but `format=` is a plain string, so there's nowhere to put the code. Define it, for example `format=Currency("USD")` or a `currency=` parameter. Also state the fixed separators and rounding mode.
- **Flow mode in Slice 1 (§3, §8):** Say that `mode="flow"` raises a clear "not implemented" error until Slice 2. Also note that in dashboard mode a long details table fails rather than paginating. That may limit how closely Slice 1 can match the Superset report.
- **PDF inspection tooling (§8):** The raster-object and text-extraction checks need a PDF parser. Plan a dev dependency group in Slice 1 for the test runner and parser; `pyproject.toml` has none yet. That's fine for a scaffold.
- **README honesty (per `AGENTS.md`):**
  - `README.md` links to `docs/reviews/`, which doesn't exist. §1 and §8 also refer to a recorded review. Add the folder or remove the references.
  - §2 has a typo: "o network" should be "no network".

## Optional simplifications

- Use one page-break concept: allow `report.new_page()` in both modes and drop the separate `PageBreak` block.
- Move `PdfRenderer` out of §6 into Slice 3 only, so §6 describes just `write_pdf`.
- §8 mentions the local IDE environment and project registration, and §1 has a private conversation share link. Consider removing both from a design doc that may be published later.
- Consider a "fill remaining page height" option for dashboard rows later. For now, computing `height_mm` by hand is acceptable.
- Plotly's embedded JavaScript adds several MB to each HTML file. Mention it in the README; no design change needed.

## Already sound — no change needed

- The weighted-Column-in-automatic-Row rule is a validation error.
- Flow pagination is staged after dashboard mode, with exactly-once row checks.
- Raster-free output is an acceptance gate (SVG traces only, no Kaleido or screenshots).
- PDF input loads in memory with network access denied.
- Output publishing refuses to overwrite and is atomic.
- The deadline and error types are defined.
- The sync wrapper fails clearly inside an active event loop.
- Dependencies are kept separate: `[pdf]` is optional and Chromium is installed explicitly.
