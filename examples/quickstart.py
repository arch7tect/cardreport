"""Build a report from application data and return output in memory."""

from collections.abc import Mapping

from cardreport import KPI, BarChart, Card, Report


def build_report(counts: Mapping[str, int]) -> Report:
    report = Report("Call results")
    report.add(Card(KPI("Total", sum(counts.values()))))
    report.row(
        Card(
            BarChart(labels=list(counts), values=list(counts.values())),
            title="Results",
        ),
        height_mm=70,
    )
    return report


def main() -> None:
    report = build_report({"Answered": 24, "No answer": 10})
    html = report.to_html()
    pdf = report.to_pdf()
    print(f"Generated {len(html)} HTML characters and {len(pdf)} PDF bytes")


if __name__ == "__main__":
    main()
