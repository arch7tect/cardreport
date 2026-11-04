# CardReport

[![Latest release](https://img.shields.io/github/v/release/arch7tect/cardreport)](https://github.com/arch7tect/cardreport/releases/latest)

Build static reports in Python from cards, KPIs, charts and tables. Compose a
report, then get standalone HTML or PDF bytes for your application. PDF text is
selectable and charts are vector graphics.

## Install in your project

Python 3.12+ is required. Install the verified GitHub release shown below and the PDF
browser runtime with uv (PyPI publishing is prepared and awaits initial account setup):

```sh
uv add "cardreport[pdf] @ https://github.com/arch7tect/cardreport/releases/download/v0.2.1/cardreport-0.2.1-py3-none-any.whl"
uv run python -m playwright install chromium
```

The downloaded wheel pins the library version. For HTML-only use, omit `[pdf]` and the
browser-install command. See [installation and quickstart](https://github.com/arch7tect/cardreport/blob/main/docs/user/quickstart.md)
for local checkouts, wheels and how to embed exports.

Once the package is published on PyPI, installation is simply
`uv add "cardreport[pdf]"`, followed by the same browser setup.

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
- [Templates](https://github.com/arch7tect/cardreport/blob/main/docs/user/templates.md) — JSON presentation with separate named datasets.
- [Datasets](https://github.com/arch7tect/cardreport/blob/main/docs/user/datasets.md) — native Python data and typed JSON storage.
- [User guide](https://github.com/arch7tect/cardreport/blob/main/docs/user/guide.md) — cards, layout, formatting and multiple pages.
- [API reference](https://github.com/arch7tect/cardreport/blob/main/docs/user/api.md) — signatures, defaults, constraints and errors.
- [Renderers](https://github.com/arch7tect/cardreport/blob/main/docs/user/renderers.md) — installation, supported features and extensions.
- [Examples and integration](https://github.com/arch7tect/cardreport/blob/main/docs/user/examples.md) — the original report, tables and async code.
- [Command-line examples](https://github.com/arch7tect/cardreport/blob/main/docs/user/command-line.md) — optional script runners.

Chromium is the default renderer. The experimental SVG/WeasyPrint renderer works
without JavaScript or a browser, with a smaller supported feature set. Both can
render the [original reference example](https://github.com/arch7tect/cardreport/blob/main/docs/user/examples.md#reference-report).
Local macOS/Python 3.12 is verified; Linux and Windows are not yet verified.

For architecture, decisions and contributing, see [project documentation](https://github.com/arch7tect/cardreport/blob/main/docs/project/README.md).

## License

[MIT](https://github.com/arch7tect/cardreport/blob/main/LICENSE). Bundled DejaVu fonts retain their [font license](https://github.com/arch7tect/cardreport/blob/main/src/cardreport/assets/LICENSE_DEJAVU).
Third-party rendering packages retain their own licenses.
