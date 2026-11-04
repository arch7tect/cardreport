# CardReport

Build static reports in Python from cards, KPIs, charts and tables. Compose a
report, then get standalone HTML or PDF bytes for your application. PDF text is
selectable and charts are vector graphics.

## Install in your project

Python 3.12+ is required. CardReport 0.2.0 is available from this GitHub repository,
not PyPI. With uv, add version 0.2.0 and install the PDF browser runtime:

```sh
uv add "cardreport[pdf] @ git+https://github.com/arch7tect/cardreport.git@v0.2.0"
uv run python -m playwright install chromium
```

The tag pins the library version. For HTML-only use, omit `[pdf]` and the
browser-install command. See [installation and quickstart](docs/user/quickstart.md)
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

- [Quickstart](docs/user/quickstart.md) — build from application data; return strings/bytes.
- [Templates](docs/user/templates.md) — JSON presentation with separate named datasets.
- [Datasets](docs/user/datasets.md) — native Python data and typed JSON storage.
- [User guide](docs/user/guide.md) — cards, layout, formatting and multiple pages.
- [API reference](docs/user/api.md) — signatures, defaults, constraints and errors.
- [Renderers](docs/user/renderers.md) — installation, supported features and extensions.
- [Examples and integration](docs/user/examples.md) — the original report, tables and async code.
- [Command-line examples](docs/user/command-line.md) — optional script runners.

Chromium is the default renderer. The experimental SVG/WeasyPrint renderer works
without JavaScript or a browser, with a smaller supported feature set. Both can
render the [original reference example](docs/user/examples.md#reference-report).
Local macOS/Python 3.12 is verified; Linux and Windows are not yet verified.

For architecture, decisions and contributing, see [project documentation](docs/project/README.md).

## License

[MIT](LICENSE). Bundled DejaVu fonts retain their [font license](src/cardreport/assets/LICENSE_DEJAVU).
Third-party rendering packages retain their own licenses.
