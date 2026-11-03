"""The original Superset report, expressed only with CardReport's public API."""

import argparse
from pathlib import Path

from cardreport import (
    KPI,
    BarChart,
    Card,
    ChromiumRenderer,
    Column,
    Page,
    Renderer,
    Report,
    Row,
    Table,
    TableColumn,
    Theme,
    WeasyPrintRenderer,
)


def build_report() -> Report:
    # Preserve the source's 4:3 canvas and aggregate discrepancy (table 3 vs KPI 2).
    report = Report(
        page=Page(size=(564.444, 423.333), margin_mm=5.644),
        theme=Theme(font_size_pt=14, gap_mm=5.644, padding_mm=6.3, chart_height_mm=95),
    )
    report.row(
        Card(
            Column(
                KPI("Clients", 21),
                Row(
                    KPI("Call attempted", 21, note="100.0%"),
                    KPI("Not yet called", 0, note="0.0%"),
                ),
            ),
            title="Campaign progress",
        ),
        Card(
            BarChart(
                labels=[
                    "1. Call attempted",
                    "2. Human answered",
                    "3. Identity confirmed",
                    "4. Promised to pay",
                ],
                values=[21, 5, 5, 2],
                orientation="horizontal",
                show_labels=True,
            ),
            title="Contact funnel",
        ),
        Card(
            BarChart(
                labels=[
                    "1. All attempts",
                    "2. No answer / busy / voicemail",
                    "3. Human answer",
                    "4. Technical error",
                ],
                values=[34, 10, 24, 0],
                orientation="horizontal",
                show_labels=True,
            ),
            title="Call attempt results",
        ),
        height_mm=112.889,
    )
    report.row(
        Card(
            Table(
                columns=[
                    TableColumn("outcome", "Outcome", width=3),
                    TableColumn("clients", "Clients", align="center"),
                    TableColumn("rate", "%", format="percent", align="center"),
                ],
                rows=[
                    {"outcome": "Promised to pay", "clients": 3, "rate": 0.6},
                    {"outcome": "Refused", "clients": 2, "rate": 0.4},
                ],
            ),
            title="Conversation outcomes",
        ),
        Card(
            Column(
                KPI("2 of 5 identified clients", 0.4, format="percent"),
                Row(KPI("Promises", 2), KPI("Promised amount", 0)),
            ),
            title="Promise rate (PTP rate)",
        ),
        widths=[2.03125, 1],
        height_mm=112.889,
    )
    report.row(
        Card(
            BarChart(labels=["2026-11-04"], values=[2], show_labels=True),
            title="Promised payments calendar",
        ),
        height_mm=141.111,
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--renderer", choices=["chromium", "weasyprint"], default="chromium"
    )
    args = parser.parse_args()
    report = build_report()
    renderer: Renderer = (
        WeasyPrintRenderer() if args.renderer == "weasyprint" else ChromiumRenderer()
    )
    report.write_pdf(
        args.output / "reference_report.pdf",
        overwrite=args.overwrite,
        renderer=renderer,
    )
    report.write_html(
        args.output / "reference_report.html",
        overwrite=args.overwrite,
        renderer=renderer,
    )
    print(args.output / "reference_report.pdf")


if __name__ == "__main__":
    main()
