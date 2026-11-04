# CardReport contributor instructions

Use Python 3.12+ and uv. Write source, comments and documentation in English.
Read docs/project/architecture.md and the relevant decision before changing the
public API. Keep README.md and docs/user/api.md aligned with implemented behavior.
README is the user entry point; tutorials/reference live in docs/user. Project
rationale lives in docs/project; dated history is not the current API contract.

Chromium is the production default. The provisional Renderer protocol also supports
an experimental SVG/WeasyPrint subset. See docs/user/renderers.md for capabilities
and docs/project/decisions/renderer-extension.md for rationale. Keep renderers behind
typed public components. No arbitrary Plotly kwargs, user HTML/CSS or template
plugins. Prefer small concrete modules to a framework; no BI server, query layer,
telemetry or network-dependent report assets.

Use uv sync --all-extras --locked for development and uv build for packaging.
Follow docs/project/development.md for checks; validate snippets and links with
uv run --all-extras python scripts/check_docs.py when changing documentation.
PDF implementation must include selected-engine integration checks, output
inspection, font readiness, hostile-label coverage and overflow rejection. Browser
lifecycle checks apply only if the browser candidate is selected. Never silently
shrink, truncate or rasterize unsupported content. Add meaningful tests with
implementation, not tests for the existence of scaffold files.

Keep .venv, .idea, local config and generated reports ignored. Do not overwrite
existing reports by default. No publishing or remote creation without request.
