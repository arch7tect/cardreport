**Read marker:** I read design.md, backend-decision.md, the review disposition, README.md, AGENTS.md and pyproject.toml. I made no edits and ran no commands.

**Verdict: endorsed as the reviewed design-stage baseline. Backend selection waits on the comparative experiment.**

The documents are consistent with each other and reflect both reviews:

- **Initial review corrections are in the design:**
  - The nested example now uses 100 mm and [2,1], which leaves 32 mm for the KPI against its 28 mm minimum.
  - The design states which component has final say over layout.
  - It defines what can be nested inside what.
  - It covers chart-label escaping, MathJax and fixed label sizes.
  - It specifies the currency format and rounding, and loads fonts before charts are created.
- **The backend review is handled critically, not just accepted:**
  - Both routes stay open.
  - There is no backend plugin framework.
  - Custom SVG plus Python line-breaking is treated as a tradeoff that needs evidence.
  - Relying on private WeasyPrint APIs cannot count as passing.
  - The controlled font resolver fixes the problem with a blanket URL blocker.
  - The experiment uses the corrected fixture.
- **The scope matches the user's request:**
  - The chart library stays hidden, and there are no Plotly kwargs, user HTML or CSS.
  - Cards and layout are first-class.
  - The project uses uv and the MIT license.
  - The no-JS/no-browser route stays open, and the user's agreement is required before choosing.
- **The scaffold is described honestly:**
  - The README and disposition say nothing is implemented.
  - The `browser` extra holds only the candidate-A packages (Plotly and Playwright). Jinja2 is the only core dependency, which is right because both candidates need it.
  - Design §2, §6 and §8 already list Jinja2 as needed by either candidate, so they agree with this.
  - Chromium is not downloaded.

**No material contradictions or blockers.** Two small wording points, neither a blocker:

1. **Flow pagination wording (design.md:181).** §4 is meant to be renderer-neutral, but this line says flow pagination is measured in the browser. The note at lines 140–142 already limits this to candidate A, so tagging the line "(candidate A)" would only make it clearer.
2. **HTML preview for candidate B.** What the HTML preview promises for candidate B (only an approximation of the PDF) is left open on purpose. backend-decision.md:84–86 already requires settling this before implementation, so it is tracked correctly.
