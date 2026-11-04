"""Render actual example PDFs and rasterize their first pages for the README."""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cardreport import WeasyPrintRenderer  # noqa: E402
from examples.operations_report import build_report as operations  # noqa: E402
from examples.spanish_report import build_report as spanish  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/images")
    parser.add_argument("--reports", type=Path, default=ROOT / "output/readme")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    rasterizer = shutil.which("pdftoppm")
    if rasterizer is None:
        raise SystemExit("Install Poppler (pdftoppm) to regenerate README previews")
    previews = (
        ("operations", operations, None),
        ("operations-weasyprint", operations, WeasyPrintRenderer()),
        ("spanish", spanish, None),
    )
    for name, _, _ in previews:
        for path in (args.output / f"{name}.png", args.reports / f"{name}.pdf"):
            if path.exists() and not args.overwrite:
                raise FileExistsError(path)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, build, renderer in previews:
        pdf = args.reports / f"{name}.pdf"
        build().write_pdf(pdf, overwrite=args.overwrite, renderer=renderer)
        with tempfile.TemporaryDirectory(prefix="cardreport-preview-") as directory:
            prefix = Path(directory) / name
            subprocess.run(
                [
                    rasterizer,
                    "-f",
                    "1",
                    "-singlefile",
                    "-scale-to",
                    "1800",
                    "-png",
                    str(pdf),
                    str(prefix),
                ],
                check=True,
            )
            (args.output / f"{name}.png").write_bytes(
                prefix.with_suffix(".png").read_bytes()
            )
        print(f"Rendered {name}: {pdf} -> {args.output / (name + '.png')}")


if __name__ == "__main__":
    main()
