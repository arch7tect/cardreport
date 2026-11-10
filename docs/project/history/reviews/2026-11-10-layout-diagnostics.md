# Measured layout diagnostics review

Scope: optional first-failure metadata in CardReport and its server consumer.
The implementation preserves exception strings, geometric rejection and the
existing renderer boundary. There is no resize solver or full-error collection.

Claude completed a design review and implementation review across both repositories.
Accepted findings: omit unmeasured Chromium left/top scroll directions; protect
canaries and private paths from metadata construction errors; reject huge JSON
integers before float conversion; revalidate at the server supervisor boundary;
keep report values out of the structured record. Exception pickle already preserves
its instance attributes; a regression confirms no custom serialization is needed.

The full suite exposed private SVG test paths replacing LayoutOverflowError with
ValueError. Safe optional construction fixed this, retaining all existing tests.
A focused review then identified Matplotlib NumPy scalar types being rejected by
strict transport validation. A real Bbox probe confirmed it. Internal coordinates
now convert to Python floats before construction; JSON validation stays strict.
The Bbox regression asserts serializable numeric measurements; the real funnel-label
regression asserts a nonempty diagnostic (it can hit the minimum plot-area check
before the label-bound check).

Additional accepted refinements: maximum excess across the first failed box or
chart, safe one-based page lookup, native glyph units in points, explicit SVG
viewport inset documentation and old/partial-diagnostic UI coverage. Measurements
are current-layout facts, never a promised size adjustment. Server persistence
uses existing JSON errors; no database or template-schema migration is needed.

Verification includes both actual renderers, known extents/tolerances, native glyph
unit conversion, malformed/old subprocess payloads, chart-label privacy, canaries,
and installed-wheel checks. The release pipeline reruns the full suite and
executable documentation before publishing. Server release follows official PyPI
availability and tests its exact locked dependency and both image architectures.

Local acceptance: full suite 563 passed without skips, followed by 77 focused
SVG/Chromium/diagnostic cases after the final scalar-conversion fix. Ruff, strict
mypy, executable documentation (52 Python blocks), links, Twine and installed core
and full-extra wheel smokes passed. The final focused Claude review completed
successfully with no remaining material blocker. CI verifies the exact release
commit again before publication.
