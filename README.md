# CardReport

[![Latest release](https://img.shields.io/github/v/release/arch7tect/cardreport)](https://github.com/arch7tect/cardreport/releases/latest)
[![PyPI version](https://img.shields.io/pypi/v/cardreport?cacheSeconds=300)](https://pypi.org/project/cardreport/)

[What’s new](https://github.com/arch7tect/cardreport/blob/main/CHANGELOG.md)

Build static reports in Python from cards, KPIs, charts and tables. Compose a
report, then get standalone HTML or PDF bytes for your application. PDF text is
selectable and charts are vector graphics.

Chromium is the default renderer. The experimental SVG/WeasyPrint renderer works
without JavaScript or a browser, with a smaller supported feature set. Both can
render the [original reference example](https://github.com/arch7tect/cardreport/blob/main/docs/user/examples.md#reference-report).

## Reports in practice

These are images of PDFs produced by the library, not design mockups.

**Operations dashboard** — large KPIs, compact line charts and a color-coded
ranking. Snapshot values come from an operations dashboard screenshot; trends are explicitly
synthetic demonstration data. [Python, template and datasets](https://github.com/arch7tect/cardreport/blob/main/docs/user/dashboards.md).

The same template and datasets, rendered by both engines. Open either image for a full-size view.

| Chromium | SVG/WeasyPrint |
| --- | --- |
| [![Operations dashboard rendered by Chromium](https://github.com/arch7tect/cardreport/blob/main/docs/images/operations.png?raw=true)](https://github.com/arch7tect/cardreport/blob/main/docs/images/operations.png) | [![Operations dashboard rendered by SVG/WeasyPrint](https://github.com/arch7tect/cardreport/blob/main/docs/images/operations-weasyprint.png?raw=true)](https://github.com/arch7tect/cardreport/blob/main/docs/images/operations-weasyprint.png) |

**Spanish campaign report** — the reference report with localized dates/numbers,
tables and charts. [Example and provenance](https://github.com/arch7tect/cardreport/blob/main/docs/user/examples.md#spanish-reference-report).

![Spanish campaign report rendered by CardReport](https://github.com/arch7tect/cardreport/blob/main/docs/images/spanish.png?raw=true)

**Table across pages** — a 120-row demonstration report using `mode="flow"`.
Chromium moves complete rows to the next page and repeats the column headings
and card title. The first two pages show the continuation from `ROW-027` to
`ROW-028`. [Python example](https://github.com/arch7tect/cardreport/blob/main/examples/flow_report.py)
· [Embedding and pagination](https://github.com/arch7tect/cardreport/blob/main/docs/user/examples.md#long-table).

| Page 1 | Page 2 — continued |
| --- | --- |
| [![Long table, page 1 ending at ROW-027](https://github.com/arch7tect/cardreport/blob/main/docs/images/flow-page-1.png?raw=true)](https://github.com/arch7tect/cardreport/blob/main/docs/images/flow-page-1.png) | [![Long table, page 2 starting at ROW-028 with repeated headings](https://github.com/arch7tect/cardreport/blob/main/docs/images/flow-page-2.png?raw=true)](https://github.com/arch7tect/cardreport/blob/main/docs/images/flow-page-2.png) |

## Install in your project

Python 3.12+ is required. Install from PyPI with uv, then install the PDF browser runtime:

```sh
uv add "cardreport[pdf]"
uv run python -m playwright install chromium
```

Keep your application’s uv.lock to pin the installed version. For HTML-only use, omit `[pdf]` and the
browser-install command. See [installation and quickstart](https://github.com/arch7tect/cardreport/blob/main/docs/user/quickstart.md)
for local checkouts, wheels and how to embed exports.

## Use from Python

```python
from cardreport import BarChart, Card, KPI, Report

report = Report("Call results")
report.add(Card(KPI("Total calls", 34)))
report.row(
    Card(BarChart(labels=["Answered", "No answer"], values=[24, 10])),
    height_mm=70,
)

html: str = report.to_html()
pdf: bytes = report.to_pdf()
```

Return `pdf` from your application, put it in storage, or use
`report.write_pdf("report.pdf")` to save a file. Existing files are preserved by
default. Reports reject content that does not fit rather than silently shrinking it.

## Documentation

- [Quickstart](https://github.com/arch7tect/cardreport/blob/main/docs/user/quickstart.md) — build from application data; return strings/bytes.
- [KPI dashboards](https://github.com/arch7tect/cardreport/blob/main/docs/user/dashboards.md) — compact charts, category legends and larger KPI values.
- [Templates](https://github.com/arch7tect/cardreport/blob/main/docs/user/templates.md) — JSON presentation with separate named datasets.
- [Datasets](https://github.com/arch7tect/cardreport/blob/main/docs/user/datasets.md) — native Python data and typed JSON storage.
- [User guide](https://github.com/arch7tect/cardreport/blob/main/docs/user/guide.md) — cards, layout, formatting and multiple pages.
- [Language and display formats](https://github.com/arch7tect/cardreport/blob/main/docs/user/localization.md) — report language tags, custom dates, number precision and the Spanish example.
- [API reference](https://github.com/arch7tect/cardreport/blob/main/docs/user/api.md) — signatures, defaults, constraints and errors.
- [Renderers](https://github.com/arch7tect/cardreport/blob/main/docs/user/renderers.md) — installation, supported features and extensions.
- [Examples and integration](https://github.com/arch7tect/cardreport/blob/main/docs/user/examples.md) — the original report, tables and async code.
- [Command-line examples](https://github.com/arch7tect/cardreport/blob/main/docs/user/command-line.md) — optional script runners.

For architecture, decisions and contributing, see [project documentation](https://github.com/arch7tect/cardreport/blob/main/docs/project/README.md).

## License

[MIT](https://github.com/arch7tect/cardreport/blob/main/LICENSE). Bundled DejaVu fonts retain their [font license](https://github.com/arch7tect/cardreport/blob/main/src/cardreport/assets/LICENSE_DEJAVU).
Third-party rendering packages retain their own licenses.
