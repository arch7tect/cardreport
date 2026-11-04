# Command-line examples

[Documentation home](../../README.md) · [Python quickstart](quickstart.md)

The primary API is Python. There is no installed `cardreport` CLI command; these
are optional runners in a repository checkout. They call the same public builder
and export methods used by applications.

## Prepare a checkout

```sh
git clone https://github.com/arch7tect/cardreport.git
cd cardreport
uv sync --extra pdf --locked
uv run --extra pdf python -m playwright install chromium
```

## Run the examples

```sh
uv run --extra pdf python examples/quickstart.py
uv run --extra pdf python examples/reference_report.py --output output/reference
uv run --extra pdf python examples/flow_report.py --output output/flow
uv run --extra pdf python examples/reference_from_template.py --data examples/reference_data_second.json --output output/template-second
```

Quickstart returns results in memory and prints their sizes; it does not save
files. The reference and flow runners each write a PDF and HTML file.

| Script | Options |
| --- | --- |
| `quickstart.py` | No options |
| `reference_report.py` | `--output PATH`, `--overwrite`, `--renderer chromium\|weasyprint` |
| `reference_from_template.py` | `--data PATH`, `--output PATH`, `--overwrite`, `--renderer chromium\|weasyprint` |
| `flow_report.py` | `--output PATH`, `--overwrite` |

The template runner defaults to `output/template` and the original data; other file runners default to `output`, and the default reference renderer is
Chromium. Existing files are preserved; add `--overwrite` only to intentionally
regenerate your own results. A runner writes PDF and HTML separately, not as one
atomic pair: if the second write fails, the first result can already exist.

## Run the reference with WeasyPrint

Complete [native setup](renderers.md#weasyprint) first, then:

```sh
uv run --extra weasyprint python examples/reference_report.py --renderer weasyprint --output output/weasyprint
```

Use separate output directories to retain both versions. Flow is unsupported by
the experimental engine. Library checks and packaging commands belong in the
[development guide](../project/development.md).

## Spanish example

```sh
uv run --all-extras python examples/spanish_report.py --output output/spanish
uv run --all-extras python examples/spanish_report.py --renderer weasyprint --output output/spanish-weasyprint
```

As with other repository runners, outputs are not overwritten unless `--overwrite`
is passed. Prefer the [Python embedding example](examples.md#spanish-reference-report)
when integrating with an application.


## Operations dashboard

```sh
uv run --all-extras python examples/operations_report.py --output output/operations
uv run --all-extras python examples/operations_report.py --renderer weasyprint --output output/operations-weasyprint
```

Accepts `--data PATH` for replacement named datasets and `--overwrite` for deliberate
regeneration. Prefer [Python embedding](dashboards.md#templates-and-the-operations-example).
