# CardReport contributor instructions

Use Python 3.12+ and uv. Write source, comments and documentation in English.
Read docs/design.md and docs/implementation-plan.md before implementing or
changing the public API. Keep README and docs/implementation-status.md aligned with tested behavior.
The design and plan preserve history; working examples are in examples/.

Read docs/backend-decision.md: v0.1 selects Plotly/Jinja2/Chromium based on the
measured P0 comparison. The owner subsequently authorized a provisional Renderer protocol and an experimental
SVG/WeasyPrint extra. Chromium remains the production default. Keep rendering
libraries behind typed public components; see docs/renderer-extension.md. No
arbitrary Plotly kwargs, user HTML, custom CSS or template plugin API in v0.1.
Prefer small concrete modules to a backend/plugin framework. No BI server,
query engine, telemetry, or network-dependent report assets.

Use uv sync --all-extras --locked for development and uv build for packaging.
PDF implementation must include selected-engine integration checks, output
inspection, font readiness, hostile-label coverage and overflow rejection. Browser
lifecycle checks apply only if the browser candidate is selected. Never silently
shrink, truncate or rasterize unsupported content. Add meaningful tests with
implementation, not tests for the existence of scaffold files.

Keep .venv, .idea, local config and generated reports ignored. Do not overwrite
existing reports by default. No publishing or remote creation without request.
