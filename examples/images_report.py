"""Embedded logo and image blocks, with equivalent Python and JSON/YAML models."""

import argparse
from pathlib import Path

from cardreport import (
    KPI,
    Card,
    Image,
    Report,
    ReportTemplate,
    Row,
    Text,
    WeasyPrintRenderer,
)

LOGO = Path(__file__).parent / "assets" / "company-logo.png"


def build_report() -> Report:
    return (
        Report(
            "Monthly account statement",
            subtitle="November 2026 · Static image example",
            logo=Image.from_file(LOGO, alt="ACME"),
            logo_position="right",
        )
        .add(
            Row(
                Card(KPI("Transactions", 128, format="integer")),
                Card(KPI("Total", 12540, format="number")),
                height_mm=35,
            )
        )
        .add(
            Card(
                Row(
                    Image.from_bytes(LOGO.read_bytes(), width_mm=45, alt="ACME"),
                    Text(
                        "Account statement prepared by ACME.\nThe logo is embedded; no network access is required."
                    ),
                    widths=[1, 2],
                    height_mm=30,
                ),
                title="Company details",
            )
        )
    )


def build_template() -> ReportTemplate:
    return ReportTemplate.from_dict(
        {
            "format": "cardreport.template/1",
            "datasets": {},
            "assets": {"company": Image.from_file(LOGO).to_asset()},
            "report": {
                "title": "Monthly account statement",
                "subtitle": "November 2026 · Template image example",
                "logo": {"asset": "company", "alt": "ACME"},
                "logo_position": "right",
                "blocks": [
                    {
                        "type": "card",
                        "title": "Company details",
                        "content": {
                            "type": "row",
                            "height_mm": 30,
                            "widths": [1, 2],
                            "children": [
                                {
                                    "type": "image",
                                    "asset": "company",
                                    "width_mm": 45,
                                    "alt": "ACME",
                                },
                                {
                                    "type": "text",
                                    "text": "The same resource can be used in the header and in a card.",
                                },
                            ],
                        },
                    }
                ],
            },
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output/images"))
    parser.add_argument(
        "--renderer", choices=("chromium", "weasyprint"), default="chromium"
    )
    parser.add_argument("--template", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = build_template().bind({}) if args.template else build_report()
    renderer = WeasyPrintRenderer() if args.renderer == "weasyprint" else None
    report.write_html(args.output / "report.html", renderer=renderer)
    report.write_pdf(args.output / "report.pdf", renderer=renderer)


if __name__ == "__main__":
    main()
