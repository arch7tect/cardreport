# Development

[Project documentation](README.md) · [Contributor instructions](../../AGENTS.md)

Use Python 3.12+ and uv. Documents, code and comments are written in English.
If using PyCharm, select `.venv/bin/python` for the checkout; keep `.idea` local.

Hosted CI uses `macos-15` (ARM) and Python 3.12 for the complete check suite.
An Intel runner was tried during the 0.4.0 release after an ARM capacity failure.
WeasyPrint chart exports exceeded the default 30-second deadline in that hosted
run; the cause was not isolated, so Intel macOS remains unverified. CI returned
to ARM with all checks intact. Native library paths come from `brew --prefix`.

## Setup

```sh
uv sync --all-extras --locked
uv run --all-extras python -m playwright install chromium
```

Complete [WeasyPrint native setup](../user/renderers.md#weasyprint) for both-engine
checks. The library never installs native dependencies implicitly. For Chromium-only
development, use `--extra pdf` instead of `--all-extras`.

## Checks

```sh
uv run --all-extras ruff check src tests examples scripts
uv run --all-extras ruff format --check src tests examples scripts
uv run --all-extras mypy
uv run --all-extras python scripts/check_docs.py
uv run --all-extras pytest -q --junitxml=local/ci-tests.xml
uv run --all-extras python scripts/check_test_results.py local/ci-tests.xml
uv run python scripts/release.py notes
uv build --no-sources
uvx --from twine==7.0.0 twine check --strict dist/*.whl dist/*.tar.gz
uv run --all-extras python scripts/check_dist.py
```

Mypy strict mode includes source, positive/negative consumer cases, executable
examples and maintenance scripts. Expected-error annotations fail if typing becomes permissive.
`check_docs.py` validates repository Markdown paths/anchors and runs Python blocks
from README and user docs in isolated temporary output directories, one namespace
per page. It also loads and binds the published template/data JSON fixtures through
the real parsers. `uv run --extra pdf --extra weasyprint --extra pandas python scripts/check_docs.py`
is the explicit equivalent of the all-extras check. The full documentation check requires both renderers, Chromium and the
native WeasyPrint libraries and the pandas extra, even if you otherwise develop with Chromium only.
Use `uv run python scripts/check_docs.py --links-only` for an offline navigation-only check.
API signatures use `text` fences and are reference notation, not runnable
Python. Network links are inventoried separately; offline checks do not claim remote
availability. Shell setup commands are not executed by the checker.

The default runtime suite skips optional WeasyPrint cases when its Python package
is absent. Full verification requires both engines and pandas with no skips.
Apple Silicon macOS/Python 3.12 is verified locally and in GitHub Actions; no Linux/Windows rendering support is claimed. The release workflow runs the same
checks on hosted macOS/Python 3.12 and blocks publication on failures or skipped tests.
Verify both rendering success and deliberate errors, literal labels, text/vector
output, native glyph bounds, file preservation and worker cleanup. Review output
visually when rendering changes. Do not publish local source evidence or reports.

## Documentation ownership

README is the user entry point. Keep it focused on installation and a short Python
example. Put tutorials in `docs/user`, the complete public contract in `api.md`, and
implementation rationale in `docs/project`. User-visible changes belong in root
`CHANGELOG.md`, linked from README and used as release notes. Keep current facts out of dated history.
The renderer capability table has one authoritative home in user documentation.

Runnable snippets use only public imports (except clearly labelled repository
examples). Keep examples import-safe: importing a builder must not write files or
start rendering. The quickstart builder appears in both its tutorial and source;
update and validate both together. When moving documents, update relative links,
AGENTS.md. Maintainers also update their local project-profile links when present.
Preserve decision/review history.

## Packaging and publication

The wheel must include fonts, font license, templates, JavaScript and `py.typed`.
Check the wheel and source archive; neither may include `local`, `output`, `.idea`
or the original PDF. The wheel includes the data/template modules and adapters; repository JSON/CSV examples
belong in the source archive. The source archive also excludes the historical experiments.
Run examples from an isolated installed wheel outside the source tree after packaging
changes; bypass stale uv caches when rebuilding the same unreleased version.

A version bump in main requests an automated GitHub Release and, once configured,
PyPI publication. See [release operations and setup](releases.md). The setup gate makes unconfigured PyPI uploads explicit and preserves GitHub
artifacts for later publication. Keep subjects concise and do not include tool attribution.
See the [dated release verification](history/reviews/2026-11-04-renderer-refactor.md)
for the initial version's test scope.


## README screenshots

The committed [images](../images/) are page rasterizations of actual checked
PDF exports: operations_report through both Chromium and SVG/WeasyPrint, and
spanish_report and flow_report through Chromium. Single-page reports use their
first page; flow_report contributes its first two pages to show table continuation.
The operations comparison uses the same template and datasets. To reproduce all
five images, install Poppler (`brew install poppler`
on macOS), the PDF extra/browser and [WeasyPrint native libraries](../user/renderers.md#weasyprint), then:

```sh
uv run --all-extras python scripts/build_readme_previews.py
```

PDF originals go to ignored `output/readme`; PNGs go to `docs/images`. Existing
files are preserved; use `--overwrite` only to deliberately refresh these generated
artifacts. Review all five images before committing. Operations snapshot values are
from the supplied dashboard, with synthetic trends visibly labelled; no private
source attachment is included. The flow table uses generated example transactions.
