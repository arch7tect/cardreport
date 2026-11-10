import io

import pytest
from pypdf import PdfReader

from cardreport import (
    BarChart,
    Card,
    Column,
    LayoutOverflowError,
    LineChart,
    Report,
    Row,
    Table,
    TableColumn,
    Text,
    WeasyPrintRenderer,
)


def table(count=9):
    return Table(
        [TableColumn("label", "Item"), TableColumn("value", "Value")],
        [{"label": f"Record-{i:02}", "value": 100 + i} for i in range(count)],
    )


def render(report):
    pytest.importorskip("weasyprint")
    reader = PdfReader(io.BytesIO(report.to_pdf(renderer=WeasyPrintRenderer())))
    assert len(reader.pages) == 1
    assert not reader.pages[0].images
    return reader.pages[0].extract_text()


@pytest.mark.parametrize("title", [None, "Results", "A title that wraps " * 5])
@pytest.mark.parametrize("container", ["top", "row", "column"])
def test_natural_table_card_keeps_all_rows_and_following_content(title, container):
    card = Card(table(), title=title)
    block = (
        card
        if container == "top"
        else Row(card)
        if container == "row"
        else Column(card)
    )
    output = render(Report().add(block).add(Text("Following block")))
    for i in range(9):
        assert f"Record-{i:02}" in output
        assert str(100 + i) in output
    assert output.index("Record-08") < output.index("Following block")


def test_natural_nested_cards_and_mixed_auto_row():
    report = Report().add(
        Card(
            Column(
                Text("Introduction"),
                Row(Card(table(5), title="Table"), Card(Text("Short"), title="Note")),
                Text("Conclusion"),
            ),
            title="Outer card",
        )
    )
    output = render(report)
    for label in ("Outer card", "Introduction", "Record-04", "Short", "Conclusion"):
        assert label in output


def test_natural_chart_card_uses_default_chart_height():
    output = render(
        Report()
        .add(
            Card(
                BarChart(["Alpha", "Beta"], series={"One": [1, 2], "Two": [3, 4]}),
                title="Chart",
            )
        )
        .add(Text("After chart"))
    )
    assert all(
        label in "".join(output.split())
        for label in ("Alpha", "Beta", "One", "Two", "Afterchart")
    )


def test_fixed_weighted_cards_still_fit():
    output = render(
        Report().row(
            Column(
                Card(table(3), title="First"),
                Card(table(3), title="Second"),
                heights=[1, 1],
            ),
            height_mm=150,
        )
    )
    assert output.count("Record-02") == 2


@pytest.mark.parametrize("kind", ["fixed_row", "weighted_column", "page"])
def test_true_overflow_still_fails_and_preserves_output(kind, tmp_path):
    pytest.importorskip("weasyprint")
    card = Card(table(40 if kind == "page" else 9), title="Too much")
    report = Report()
    if kind == "fixed_row":
        report.row(card, height_mm=25)
    elif kind == "weighted_column":
        report.row(Column(card, Card(Text("Other")), heights=[1, 1]), height_mm=60)
    else:
        report.add(card)
    target = tmp_path / "kept.pdf"
    target.write_bytes(b"keep")
    with pytest.raises(LayoutOverflowError):
        report.write_pdf(target, renderer=WeasyPrintRenderer(), overwrite=True)
    assert target.read_bytes() == b"keep"


def test_natural_card_with_mixed_column_contents():
    output = render(
        Report().add(
            Card(
                Column(
                    Text("Paragraph " * 40),
                    table(3),
                    LineChart(["Start", "Finish"], [2, 4]),
                ),
                title="Mixed content",
            )
        )
    )
    assert "Record-02" in output and "Finish" in output


def test_auto_row_stretches_unequal_table_cards():
    output = render(
        Report()
        .row(
            Card(table(2), title="Short table"),
            Card(table(8), title="Long table"),
        )
        .add(Text("After both"))
    )
    assert "Record-07" in output and "After both" in output
    assert output.count("Record-01") == 2


def test_natural_card_can_contain_fixed_row():
    output = render(
        Report()
        .add(
            Card(
                Row(Card(table(4), title="Fixed inner"), height_mm=70),
                title="Natural outer",
            )
        )
        .add(Text("Following"))
    )
    assert all(
        label in output
        for label in ("Fixed inner", "Natural outer", "Record-03", "Following")
    )


def test_unweighted_column_resets_fixed_parent_for_cards():
    output = render(
        Report().row(
            Column(Card(table(4), title="Natural child"), Card(Text("Tail"))),
            height_mm=120,
        )
    )
    assert "Record-03" in output and "Tail" in "".join(output.split())


def test_natural_card_keeps_actual_pdf_text_below_table():
    pytest.importorskip("weasyprint")
    import pdfplumber

    report = Report().add(Card(table(), title="Results")).add(Text("Following"))
    with pdfplumber.open(
        io.BytesIO(report.to_pdf(renderer=WeasyPrintRenderer()))
    ) as doc:
        words = doc.pages[0].extract_words()
        last = next(word for word in words if word["text"] == "Record-08")
        following = next(word for word in words if word["text"] == "Following")
        assert following["top"] > last["bottom"]
