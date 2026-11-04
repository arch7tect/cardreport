I found no blocker in the core design, but there are four fixes to make before a local 0.1. They are about labels that get clipped without failing the check, renderer processes that can be left running, and blank or title-only pages. I only read the code for this review. I ran nothing, so the Chromium-specific items below need a short test to confirm.

## Fix before 0.1

1. **Funnel value labels can be silently clipped.** `charts.py:87-95` (in `chart_spec`) sets `textposition="outside"` on funnels but leaves Plotly's `cliponaxis` at its default of `True`. Bar charts set it to `False` (lines 104-109); funnels don't. The bounds check at `layout.js:87-91` uses `getBoundingClientRect`, which ignores clip paths, so a label cut off by the plot area still passes. The PDF keeps the clipped text, so text-extraction tests won't catch it either.
   - Trigger: `Funnel(["A","B"], [1000000, 5], value_format=Currency("USD"))`. The widest bar fills the axis and its value label runs past the plot area.
   - Fix: set `cliponaxis=False` on funnels too.

2. **Labels from different groups are never checked against each other.** `layout.js:92-97` checks overlaps only within each selector group (x-axis ticks against x-axis ticks, legend against legend, and so on). A legend can overlap the x-axis labels, and value labels can cover tick labels.
   - Triggers: a multi-series `LineChart` in a short card, where the legend is placed below the plot (`y=-0.2`); or a horizontal `BarChart` with negative values and `show_labels`.
   - Fix: put all the selectors into one list and compare every pair.

3. **The renderer process can be left behind, and the kill path is untested.**
   - `pdf.py:44-54` only kills the worker on `TimeoutExpired`. On Ctrl-C or any other exception it is left running. Because it starts in its own session (`start_new_session=True`), Ctrl-C doesn't reach it. `_worker.py:31-34` waits with `timeout=0`, which means forever, so a stuck worker never exits. Fix: wrap the call in `try/finally` and kill the process group if `process.poll() is None`.
   - `os.killpg` raises `ProcessLookupError` if the worker exits right at the deadline. That error escapes as something other than `ReportError`. Catch it.
   - Playwright starts Chromium detached, so it is not in the worker's process group and `killpg` doesn't kill it. It probably exits when the driver's pipe closes, but nothing verifies that.
   - `test_safe_output_and_timeout` uses `timeout=0.01`. That most likely expires during HTML preparation (`render_html` always imports plotly), so `pdf.py:36` raises before any worker starts. Add a test with a deadline of about 1–2 s, which hits mid-launch, and assert that no worker or Chromium processes remain.

4. **Nothing checks that the PDF page count matches the layout's page count, so blank or title-only pages can slip through.**
   - The worker never compares `state.pages` with the number of pages in the PDF. With a fractional custom size such as `Page(size=(100.3, 150.7))`, rounding can make a `.page` slightly taller than the PDF page, which could add a blank page. Fix: count the pages in the worker's output and raise `RenderError` on a mismatch, and add a test with an odd custom size.
   - `layout.js:47`: the title header makes the page non-empty, so `Report("T").new_page().add(...)` produces a page holding only the title. Fix: treat a title-only page as empty when handling a page break.

## Should fix (cheap, fails clearly)

5. **Bold text can fall back to a system font.** `html.py:51-55` (`glyphs`) checks characters against the regular font only. Card titles, table headers, headings and `h1` use the bold font, and DejaVu Sans Bold covers fewer characters. A character missing from it would make Chromium use a system font without any error. Fix: allow only characters present in both fonts.

6. **Wrong input types are mishandled at construction.**
   - `freeze_chart` and `Funnel.__post_init__` (`model.py:201`, `model.py:210-219`) turn a string into a tuple of characters. `BarChart("Revenue", [..])` silently becomes seven one-letter categories, and with a single value it fails later with a misleading length error. Fix: reject `str`, `bytes` and mappings where a sequence is expected.
   - Several bad inputs raise `TypeError` or `AttributeError` instead of `ValidationError`: a non-mapping row in `Table` (`dict(r)`), a non-mapping `series` (`.items()`), a non-iterable series value, and `Currency(123)` (`re.fullmatch` at `model.py:236`).

7. **Error reporting from the worker is fragile.** `pdf.py:56-65` parses the whole of stderr as JSON. Any Node, Playwright or Python warning printed before the JSON turns a `DependencyError` into "PDF worker failed unexpectedly". If the JSON isn't a dict with `kind`, you get a `KeyError`. Fix: parse only the last line of stderr and use `.get`.

8. **Playwright's own timeouts can override the user's deadline.** Playwright has a default 30 s navigation timeout, so `set_content` (`_worker.py:30`) can fail as a generic `RenderError` even when the user allowed up to 300 s. Fix: call `context.set_default_timeout(0)`; the parent already enforces the real deadline.

9. **File writes (`output.py`, `publish`):**
   - `mkstemp` creates files with mode 0600, and `link`/`replace` keep that mode. Reports end up readable only by their owner. Fix: `fchmod` to `0o666 & ~umask`.
   - `os.link` fails on filesystems without hard links (exFAT, some network or container mounts). The resulting `OSError` is not `FileExistsError`, so writing without `overwrite` breaks entirely there. Either fall back to `open(target, "xb")` or document the limitation.
   - Otherwise the atomic replace and the no-clobber behaviour are correct.

10. **Orientation is ignored for custom sizes.** `Page.dimensions` (`model.py:72`) ignores `orientation` when `size` is a tuple, so `Page(size=(210, 297), orientation="landscape")` renders portrait. Swap the dimensions or reject the combination.

11. **Negative zero.** `format_value(-0.001)` returns `"-0"`, and percents can show `"-0.0%"`. Normalise the value after rounding.

12. **The worker only finds an installed package.** It starts with `-m cardreport._worker` (`pdf.py:38`), which works only if `cardreport` can be imported without the parent's `sys.path` changes. A script that adds `src/` to its path will get the generic worker error. Pass the package's parent directory in `PYTHONPATH`, or document that the package must be installed.

## Checked and fine

- **Network:** fonts and Plotly are inlined, every request is routed to abort, the request audit only allows `data:`, `blob:` and `about:`, `safe_json` escapes `<`, `>` and `&`, and labels are escaped once before Plotly sees them.
- **Flow table splitting:** each row is moved exactly once, an empty fragment is removed before the page break, the card title and table header repeat on each page, and a row that can't fit on an empty page fails.
- **Overflow checks:** they run after fonts load and after two animation frames.
- **Frozen inputs:** components store defensive copies, table rows are wrapped read-only, and cycles and depth are limited.
- **Packaging:** assets live inside the package and aren't gitignored, so hatch will include them; `local/` and `output/` are excluded from the sdist.
- **Reference docs:** `docs/project/history/reference-report.md` matches the example, including the deliberate 3-versus-2 discrepancy.
