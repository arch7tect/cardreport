import io
from pathlib import Path

import pytest
from pypdf import PdfReader

from cardreport import ChromiumRenderer, WeasyPrintRenderer
from cardreport.validation import validate_report
from examples.reference_from_template import build_report as from_template
from examples.reference_report import build_report as from_python


def test_reference_model_equivalence():
    assert validate_report(from_template()) == validate_report(from_python())


@pytest.mark.parametrize("renderer", [ChromiumRenderer, WeasyPrintRenderer])
def test_reference_pdf_and_reuse(renderer):
    if renderer is WeasyPrintRenderer:
        pytest.importorskip("weasyprint")
    first = PdfReader(io.BytesIO(from_template().to_pdf(renderer=renderer())))
    second = PdfReader(
        io.BytesIO(
            from_template(
                Path(__file__).parents[1] / "examples/reference_data_second.json"
            ).to_pdf(renderer=renderer())
        )
    )
    assert len(first.pages) == len(second.pages) == 1
    assert abs(float(first.pages[0].mediabox.width) - 1600) < 0.3
    for phrase in ["Campaign progress", "40.0%", "34", "21"]:
        assert phrase in first.pages[0].extract_text()
    for phrase in ["68", "42", "4 of 10"]:
        assert phrase in second.pages[0].extract_text()
    assert not list(first.pages[0].images)


@pytest.mark.parametrize("renderer", [ChromiumRenderer, WeasyPrintRenderer])
def test_reference_overflow_is_rejected(renderer):
    from cardreport import (
        Dataset,
        LayoutOverflowError,
        ReportTemplate,
        datasets_from_json,
    )
    from examples.reference_from_template import EXAMPLES

    if renderer is WeasyPrintRenderer:
        pytest.importorskip("weasyprint")
    template = ReportTemplate.from_json(
        (EXAMPLES / "reference_template.json").read_bytes()
    )
    data = datasets_from_json((EXAMPLES / "reference_data.json").read_bytes())
    original = data["outcomes"]
    data["outcomes"] = Dataset(original.columns, original.rows * 30)
    report = template.bind(data)
    with pytest.raises(LayoutOverflowError):
        report.to_pdf(renderer=renderer())


def test_template_flow_and_empty_chart():
    from cardreport import Dataset, ReportTemplate, UnsupportedFeatureError

    template = ReportTemplate(
        {
            "format": "cardreport.template/1",
            "datasets": {
                "rows": {
                    "cardinality": "many",
                    "fields": {"label": {"type": "text"}, "value": {"type": "integer"}},
                }
            },
            "report": {
                "mode": "flow",
                "blocks": [
                    {
                        "type": "table",
                        "dataset": "rows",
                        "columns": [
                            {"key": "label", "label": "Item"},
                            {"key": "value", "label": "Value"},
                        ],
                    },
                    {"type": "page_break"},
                    {
                        "type": "bar",
                        "dataset": "rows",
                        "category": "label",
                        "value": "value",
                    },
                ],
            },
        }
    )
    empty = template.bind({"rows": Dataset(["label", "value"], [])})
    pdf = PdfReader(io.BytesIO(empty.to_pdf()))
    assert len(pdf.pages) == 2
    assert "No data" in pdf.pages[0].extract_text()
    spec = template.to_dict()
    spec["report"]["blocks"] = spec["report"]["blocks"][:1]
    flow = ReportTemplate(spec).bind(
        {
            "rows": Dataset.from_dicts(
                [{"label": f"Entry-{i:03d}", "value": i} for i in range(120)]
            )
        }
    )
    pages = PdfReader(io.BytesIO(flow.to_pdf())).pages
    assert len(pages) > 1
    text = "\n".join(page.extract_text() for page in pages)
    for i in range(120):
        assert text.count(f"Entry-{i:03d}") == 1
    with pytest.raises(UnsupportedFeatureError):
        flow.to_html(renderer=WeasyPrintRenderer())
