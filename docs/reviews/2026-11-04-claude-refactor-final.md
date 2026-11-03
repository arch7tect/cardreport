# Final focused Claude review

Date: 2026-11-04. Read-only advisory review; runner exit 0.

**Verdict: the prior blockers are resolved in the code I read, and I found nothing in these changes that blocks the initial public release.** This was a read-only review of the five files you named. I ran no tests, so everything about tests passing comes from your report.

**Prior blockers**

1. **Font rename changed literal labels: resolved.** `_svg_charts.py:119-129` parses the SVG and only appends `;font-family:CardReport` to the `style` attribute of `text` and `tspan` elements. Label text is never touched, and ElementTree escapes it again on output. That also covers the label-substitution risk in `html.replace("<!--chart:…-->")` at `_weasy_worker.py:77`: an escaped `<` can't produce a fake marker. `test_svg_font_rewrite_preserves_text_and_ignores_local_rc` checks that the literal `'DejaVu Sans'` label survives.
2. **Inherited rc settings: resolved.** `rcdefaults()` runs inside `rc_context()` (`_svg_charts.py:31-40`). It resets to Matplotlib's built-in defaults, not the user's matplotlibrc, and the user's settings come back on exit. The same test overrides `font.sans-serif` and `xtick.major.pad` and gets identical text elements.
3. **Shallow font verification: resolved.** `resource_scopes` walks form XObject resources recursively and guards against cycles. `font_identity` compares name IDs 1, 3 and 5 as a set and ignores platform, so the subsetter dropping Mac names doesn't cause false failures. A font with no `/FontFile2` is rejected, which also rejects Type3 and CFF fonts. The nested-form test with a version-99 font exercises the substitution path. If a label has a glyph DejaVu lacks, Pango falls back to a system font and the final `verify_fonts` rejects the output, so it fails closed.
4. **Native glyph metrics vs Agg: resolved.** The preflight at `_weasy_worker.py:66-76` renders the same SVG, font bytes and viewport size alone and checks pdfplumber character boxes. pdfminer ignores clip paths, so glyphs clipped by the SVG viewport still get reported. That's the right test. There's still only one text layout engine. The end-to-end `test_weasy_pdf_chart_character_bounds` covers both orientations.
5. **Blocked external fetches: acceptable.** The `blocked` flag stays set once tripped. It's checked after the first render and again after the final render, so fetches during the canary and the chart preflight are covered too. The pin to version 70.0 is checked in `verify_adapter` before any rendering, which keeps the reliance on WeasyPrint's private `_fail_on_errors` attribute bounded. `test_weasy_blocks_resource_fetches` checks the explicit error.
6. **Canaries: resolved.** They now use the bundled font through the same fetcher (the data URL matches a `fonts` key exactly), and a positive must-fit case comes before the two must-reject cases.
7. **Integer tick locator:** correct, and only applied to the `integer` format.

**New blockers:** none found.

**Optional follow-ups (not blockers)**
- `resource_scopes` doesn't walk `/Pattern` resources, Type3 `/Resources` or annotation appearance streams. Type3 is already rejected, and the current output has no text in patterns or annotations. This only matters if the output gets more complex.
- If the standalone preflight ever produces two pages from float rounding, the error says "native SVG text was lost", which is misleading. It still fails closed.
- An unsupported glyph comes back as a generic `RenderError("Unexpected font identity or version")`. A message that points to glyph coverage would help users.
- `test_weasy_canary_fail_closed` matches `"canary"`, which both canary errors contain. It doesn't tell apart "rejected a fitting canary" from "failed its canary".
- The rc-independence test compares whole attributes but doesn't assert that `font-family:CardReport` appears in the style.
- The chart-text check runs on the standalone render, not on each chart inside the final document. Final placement is only checked through `inspect` box geometry plus the end-to-end test. That's consistent with the design.
