"""The original reference report using separate presentation and data files."""

import argparse
from pathlib import Path

from cardreport import Report, ReportTemplate, WeasyPrintRenderer, datasets_from_json

EXAMPLES = Path(__file__).resolve().parent


def build_report(data_path: Path | None = None) -> Report:
    template = ReportTemplate.from_json(
        (EXAMPLES / "reference_template.json").read_bytes()
    )
    data = datasets_from_json(
        (data_path or EXAMPLES / "reference_data.json").read_bytes()
    )
    return template.bind(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--output", type=Path, default=Path("output/template"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--renderer", choices=["chromium", "weasyprint"], default="chromium"
    )
    args = parser.parse_args()
    report = build_report(args.data)
    renderer = WeasyPrintRenderer() if args.renderer == "weasyprint" else None
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


if __name__ == "__main__":
    main()
