# Command line

[Documentation home](../../README.md) · [Python quickstart](quickstart.md)

The Python API remains the primary integration interface. The installed CLI is
useful for developing reports from a JSON or YAML template and named datasets without
writing a Python runner. `python -m cardreport` and `cardreport` are equivalent;
in a uv project, prefix either command with `uv run`.

## Install and render

```sh
uv add cardreport
python -m cardreport --help
python -m cardreport render --help
python -m cardreport render --template report.json --data data.json --output report.html
```

Default Chromium HTML generation needs only the core package. PDF output needs
`uv add "cardreport[pdf]"` and `python -m playwright install chromium`. For the
experimental engine, install `cardreport[weasyprint]` and follow its
[native setup and supported features](renderers.md#weasyprint). There is no
automatic engine fallback.

## Complete CSV example

The following files produce the same report as [Use from Python](../../README.md#use-from-python).
Save them together, or use the ready-made [example directory](../../examples/cli/).

`report.json` contains the presentation and the required data types:

```json
{
  "format": "cardreport.template/1",
  "datasets": {
    "summary": {
      "cardinality": "one",
      "fields": {"total": {"type": "integer"}}
    },
    "calls": {
      "cardinality": "many",
      "fields": {
        "result": {"type": "text"},
        "count": {"type": "integer"}
      }
    }
  },
  "report": {
    "title": "Call results",
    "blocks": [
      {"type": "card", "content": {
        "type": "kpi", "label": "Total calls",
        "value": {"bind": {"dataset": "summary", "field": "total"}}
      }},
      {"type": "row", "height_mm": 70, "children": [
        {"type": "card", "content": {
          "type": "bar", "dataset": "calls",
          "category": "result", "value": "count"
        }}
      ]}
    ]
  }
}
```

`summary.csv`:

```csv
total
34
```

`calls.csv`:

```csv
result,count
Answered,24
No answer,10
```

Run from that directory:

```sh
python -m cardreport render --template report.json --csv summary.csv --csv calls.csv --output report.html
python -m cardreport render --template report.json --csv summary.csv --csv calls.csv --output report.pdf
```

Dataset names are the filenames without the last suffix: `data/calls.csv` becomes
`calls`. Names are case-sensitive and are not normalized. To use a differently
named export, pass a name and path as two separate arguments:

```sh
python -m cardreport render --template report.json --csv summary.csv --csv-as calls exports/november.csv --output report.pdf
```

`--csv` and `--csv-as` are repeatable and may be combined. Both treat `=` literally;
there is no `NAME=PATH` syntax. Quote arguments containing spaces, for example
`--csv-as "calls = answered" "exports/November calls.csv"` when that dataset is
declared in the template. For a name starting with `-`, use a matching filename
and `--csv ./-name.csv`; argparse treats leading-hyphen alias arguments as options.
Use JSON datasets for names that cannot be expressed as command arguments or
filenames. Option names must be spelled in full. Paths are relative to the current working directory,
not the template directory. Directories are not scanned.

## JSON and CSV together

`--data` accepts one JSON or YAML [cardreport.data/1 bundle](datasets.md#data-json),
including tagged decimal/date/datetime values. A matching [data.json](../../examples/cli/data.json)
is provided for the example above. JSON and CSV may supply different datasets:

```sh
python -m cardreport render --template report.json --data summary-only.json --csv calls.csv --output report.html
```

The example [summary-only.json](../../examples/cli/summary-only.json) supplies `summary` only; it must not also supply `calls`.
A name supplied twice, including once in JSON and once in CSV, is an error;
argument order never silently overrides data. CSV names must be declared in the
template because its schemas supply their column types. Extra datasets in JSON
remain allowed, as in the Python API. Missing required datasets and invalid rows
fail validation. A template with no datasets needs neither `--data` nor CSV options.

## YAML, validation and schema export

The ready-made [example directory](../../examples/cli/) also contains `report.yaml`,
`data.yaml` and `summary-only.yaml`. Each input is selected independently:
`.yaml`/`.yml` (case-insensitive) uses YAML; all other suffixes keep the JSON behavior.
Quote string dates, leading-zero identifiers and typed-cell string values as
explained in [YAML and schemas](yaml-and-schemas.md).

```sh
python -m cardreport render --template report.yaml --data data.yaml --output report.html
python -m cardreport render --template report.yaml --data summary-only.yaml --csv calls.csv --output report.pdf
python -m cardreport validate --template report.yaml
python -m cardreport validate --template report.yaml --data data.json
python -m cardreport schema template
python -m cardreport schema data
```

`validate` accepts the same source/CSV options as render and takes no output,
renderer or timeout. Without sources it checks the template definition and
bindings against declared fields; with sources it also binds actual datasets.
Its success message states what was checked. It never starts a browser or measures
layout. The `schema` command prints the installed JSON Schema to stdout; redirect
it to a local file to configure your editor. Both commands work in a core-only
installation. Neither command downloads schemas or dependencies.

From a repository checkout, the complete reference works directly with both engines:

```sh
python -m cardreport render --template examples/reference_template.yaml --data examples/reference_data.yaml --output output/reference-yaml.pdf
python -m cardreport render --template examples/reference_template.yaml --data examples/reference_data.yaml --renderer weasyprint --output output/reference-yaml-weasyprint.pdf
```

## Options and errors

| Option | Behavior |
| --- | --- |
| `--template PATH` | Required JSON/YAML presentation file (`cardreport.template/1`) |
| `--data PATH` | Optional named dataset JSON/YAML bundle (`cardreport.data/1`) |
| `--csv PATH` | CSV with dataset name inferred from its filename; repeatable |
| `--csv-as NAME PATH` | CSV with an explicit dataset name; repeatable |
| `--csv-encoding NAME` | All CSV files; default `utf-8`, use `utf-8-sig` for a BOM |
| `--csv-delimiter CHAR` | One character for all CSV files; default comma |
| `--csv-null TOKEN` | Repeatable null token for all CSV files; none by default |
| `--output PATH` | Required `.html` or `.pdf` destination; suffix selects format |
| `--renderer chromium\|weasyprint` | Default `chromium`, applies to HTML and PDF |
| `--timeout SECONDS` | PDF export deadline in `(0, 300]`, default 30; unused for HTML |
| `--overwrite` | Allow replacing an output; input files remain protected |

CSV uses the existing [CSV conversion rules](datasets.md#one-csv-file): schema-based
conversion, no type guessing or trimming, ISO input dates and preserved text codes.
Empty strings are not null by default. To recognize both an empty cell and `\N`:

```sh
python -m cardreport render --template report.json --csv summary.csv --csv calls.csv --csv-null '' --csv-null '\N' --output report.html
```

Nullable fields are still required for null values. An invalid CSV row reports its
dataset and file, plus available field/row details. Data rows are numbered from 1
(excluding the header); template errors include available component paths. Existing input-size, row and
cell limits apply. All inputs are loaded and bound before rendering; failed exports
do not publish partial files. Parent output directories are created automatically.
An existing output is preserved unless `--overwrite` is supplied. An input path,
including a symlink or hard-link alias, cannot be used as output even with that flag.

Success prints the output path to stdout. Expected failures print an error to
stderr without a traceback. Exit codes: `0` success, `1` input/render/write failure,
`2` invalid command arguments, `130` interruption. `python -m cardreport --version`
prints the installed package version. The CLI never executes SQL or downloads
rendering dependencies.

## Repository example runners

The following scripts are additional examples in a repository checkout, not
requirements for the installed CLI. They call the public builder/export APIs.

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
