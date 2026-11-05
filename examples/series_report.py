"""Grouped/stacked series, dated lines and a funnel using synthetic data."""

import argparse
from datetime import date
from pathlib import Path

from cardreport import (
    BarChart,
    Card,
    Funnel,
    LineChart,
    Page,
    Report,
    WeasyPrintRenderer,
)


def build_report() -> Report:
    channels = ["Voice", "Chat", "Email"]
    return (
        Report(
            "Channels and conversion",
            subtitle="Synthetic example data",
            page=Page(size=(300, 240)),
        )
        .row(
            Card(
                BarChart(
                    channels,
                    series={"Previous": [120, 85, 65], "Current": [145, 110, 80]},
                    show_labels=True,
                    value_format="integer",
                ),
                title="Sessions by channel",
            ),
            Card(
                BarChart(
                    channels,
                    series={"Resolved": [100, 75, 50], "Escalated": [45, 35, 30]},
                    mode="stacked",
                    orientation="horizontal",
                    show_labels=True,
                    value_format="integer",
                ),
                title="Session outcomes",
            ),
            height_mm=90,
        )
        .row(
            Card(
                LineChart(
                    [date(2026, 11, day) for day in range(1, 6)],
                    series={
                        "Voice": [90, 110, None, 130, 145],
                        "Chat": [65, 75, 85, 95, 110],
                    },
                    x_kind="date",
                    value_format="integer",
                ),
                title="Daily activity",
            ),
            Card(
                Funnel(
                    ["Contacted", "Qualified", "Converted"],
                    [335, 210, 125],
                    value_format="integer",
                ),
                title="Conversion stages",
            ),
            height_mm=90,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output/series_report.pdf"))
    parser.add_argument(
        "--renderer", choices=["chromium", "weasyprint"], default="weasyprint"
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    renderer = WeasyPrintRenderer() if args.renderer == "weasyprint" else None
    build_report().write_pdf(args.output, renderer=renderer, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
