"""The README report with inline JSON presentation and named datasets."""

from cardreport import Report, ReportTemplate, datasets_from_json

TEMPLATE_JSON = """
{
  "format": "cardreport.template/1",
  "datasets": {
    "summary": {
      "cardinality": "one",
      "fields": {"total": {"type": "integer"}}
    },
    "calls": {
      "cardinality": "many",
      "fields": {
        "result": {"type": "text"},
        "count": {"type": "integer"}
      }
    }
  },
  "report": {
    "title": "Call results",
    "blocks": [
      {"type": "card", "content": {
        "type": "kpi", "label": "Total calls",
        "value": {"bind": {"dataset": "summary", "field": "total"}}
      }},
      {"type": "row", "height_mm": 70, "children": [
        {"type": "card", "content": {
          "type": "bar", "dataset": "calls",
          "category": "result", "value": "count"
        }}
      ]}
    ]
  }
}
"""

DATA_JSON = """
{
  "format": "cardreport.data/1",
  "datasets": {
    "summary": {"columns": ["total"], "rows": [{"total": 34}]},
    "calls": {
      "columns": ["result", "count"],
      "rows": [
        {"result": "Answered", "count": 24},
        {"result": "No answer", "count": 10}
      ]
    }
  }
}
"""


def build_report(data_json: str = DATA_JSON) -> Report:
    template = ReportTemplate.from_json(TEMPLATE_JSON)
    datasets = datasets_from_json(data_json)
    return template.bind(datasets)


def main() -> None:
    report = build_report()
    html = report.to_html()
    pdf = report.to_pdf()
    print(f"Generated {len(html)} HTML characters and {len(pdf)} PDF bytes")


if __name__ == "__main__":
    main()
