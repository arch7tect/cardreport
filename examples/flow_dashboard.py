"""Dashboard rows move whole; the top-level table continues across pages."""

import argparse
from pathlib import Path

from cardreport import KPI, BarChart, Card, Report, Table, TableColumn


def build_report() -> Report:
    report = Report("Weekly operations", mode="flow")
    report.row(Card(KPI("Requests", 120)), Card(KPI("Resolved", 108)), height_mm=40)
    report.row(
        Card(
            BarChart(["Mon", "Tue", "Wed", "Thu", "Fri"], [18, 24, 30, 26, 22]),
            title="Daily requests",
        ),
        Card(BarChart(["Resolved", "Pending"], [108, 12]), title="Outcomes"),
        height_mm=85,
    )
    report.add(
        Card(
            Table(
                [TableColumn("id", "Request"), TableColumn("status", "Status")],
                [
                    {
                        "id": f"REQ-{i:03d}",
                        "status": "Resolved" if i <= 108 else "Pending",
                    }
                    for i in range(1, 121)
                ],
            ),
            title="Request details",
        )
    )
    report.row(Card(KPI("Resolution rate", 0.9, format="percent")), height_mm=45)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    report = build_report()
    report.write_pdf(args.output / "flow_dashboard.pdf", overwrite=args.overwrite)
    report.write_html(args.output / "flow_dashboard.html", overwrite=args.overwrite)
    print(args.output / "flow_dashboard.pdf")


if __name__ == "__main__":
    main()
