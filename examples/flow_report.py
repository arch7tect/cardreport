"""Multi-page table with repeated headings and intact rows."""

import argparse
from pathlib import Path

from cardreport import Card, Currency, Report, Table, TableColumn


def build_report() -> Report:
    return Report("Account summary", mode="flow").add(
        Card(
            Table(
                columns=[
                    TableColumn("id", "Record", width=1),
                    TableColumn("description", "Description", width=3),
                    TableColumn(
                        "amount", "Amount", format=Currency("EUR"), align="right"
                    ),
                ],
                rows=[
                    {
                        "id": f"ROW-{i:03d}",
                        "description": "Example transaction. Пример записи.",
                        "amount": i * 1.25,
                    }
                    for i in range(120)
                ],
            ),
            title="Transactions",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    report = build_report()
    report.write_pdf(args.output / "flow_report.pdf", overwrite=args.overwrite)
    report.write_html(args.output / "flow_report.html", overwrite=args.overwrite)
    print(args.output / "flow_report.pdf")


if __name__ == "__main__":
    main()
