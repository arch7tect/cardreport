"""Daily headings from typed data, with no preassembled display strings."""

from datetime import date

from cardreport import Dataset, Report, ReportTemplate

TEMPLATE_YAML = """
format: cardreport.template/1
datasets:
  summary:
    cardinality: one
    fields:
      report_date: {type: date}
      total: {type: integer}
      rate: {type: number}
report:
  language: en
  formatting:
    date_format: dd.MM.yyyy
    group: space
  title: "Daily report for {{ datasets.summary.report_date }}"
  subtitle: "Automation: {{ datasets.summary.rate | percent }}"
  blocks:
    - type: card
      title: "Month: {{ datasets.summary.report_date | date('MMMM yyyy') }}"
      content:
        type: kpi
        label: Total calls
        value:
          bind: {dataset: summary, field: total}
        format: integer
        note: "Updated {{ datasets.summary.report_date }}"
"""


def build_report(day: date = date(2026, 11, 14), total: int = 12540) -> Report:
    template = ReportTemplate.from_yaml(TEMPLATE_YAML)
    return template.bind(
        {"summary": Dataset.single({"report_date": day, "total": total, "rate": 0.976})}
    )


def main() -> None:
    report = build_report()
    html = report.to_html()
    pdf = report.to_pdf()
    print(f"Generated {len(html)} HTML characters and {len(pdf)} PDF bytes")


if __name__ == "__main__":
    main()
