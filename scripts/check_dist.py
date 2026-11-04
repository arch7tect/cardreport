"""Check packaged metadata/assets and run installed-wheel smoke tests outside source."""

import argparse
import email
import importlib.util
import io
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {
    "py.typed",
    "data.py",
    "formatting.py",
    "templates.py",
    "adapters/csv.py",
    "adapters/pandas.py",
    "assets/DejaVuSans.ttf",
    "assets/DejaVuSans-Bold.ttf",
    "assets/LICENSE_DEJAVU",
    "assets/report.html",
    "assets/layout.js",
    "assets/style.css.j2",
}


def check_archives(directory: Path) -> Path:
    version = str(
        tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    )
    wheel = directory / f"cardreport-{version}-py3-none-any.whl"
    source = directory / f"cardreport-{version}.tar.gz"
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        assert {"cardreport/" + name for name in ASSETS} <= names
        metadata = email.message_from_bytes(
            archive.read(f"cardreport-{version}.dist-info/METADATA")
        )
        assert metadata["Name"] == "cardreport" and metadata["Version"] == version
        assert any(name.endswith("/LICENSE") for name in names)
        assert {"pdf", "weasyprint", "pandas"} == set(
            metadata.get_all("Provides-Extra", [])
        )
    with tarfile.open(source) as archive:
        entries = archive.getmembers()
        assert all(entry.isfile() or entry.isdir() for entry in entries)
        source_names = {entry.name for entry in entries}
        prefix = f"cardreport-{version}/"
        assert {prefix + "src/cardreport/" + name for name in ASSETS} <= source_names
        assert {
            prefix + "examples/" + name
            for name in [
                "reference_template.json",
                "reference_data.json",
                "reference_data_second.json",
                "payments.csv",
                "spanish_template.json",
                "spanish_data.json",
                "spanish_report.py",
            ]
        } <= source_names
        metadata_file = archive.extractfile(prefix + "PKG-INFO")
        assert metadata_file is not None
        with metadata_file:
            metadata = email.message_from_bytes(metadata_file.read())
        assert metadata["Version"] == version
        assert prefix + "CHANGELOG.md" in source_names
    for name in names | source_names:
        assert not {"local", "output", ".idea", ".env", ".venv", "experiments"} & set(
            Path(name).parts
        ), name
        assert not name.endswith(".pdf"), name
    return wheel


def installed_smoke(full: bool) -> None:
    import cardreport
    from cardreport import (
        DatasetSchema,
        DependencyError,
        ReportTemplate,
        datasets_from_json,
    )
    from cardreport.adapters.csv import from_csv
    from cardreport.adapters.pandas import from_pandas

    assert cardreport.__file__ is not None and "site-packages" in cardreport.__file__
    examples = ROOT / "examples"
    template = ReportTemplate.from_json(
        (examples / "reference_template.json").read_bytes()
    )
    report = template.bind(
        datasets_from_json((examples / "reference_data.json").read_bytes())
    )
    assert "<html" in report.to_html()
    spanish = ReportTemplate.from_json(
        (examples / "spanish_template.json").read_bytes()
    ).bind(datasets_from_json((examples / "spanish_data.json").read_bytes()))
    assert "4 de noviembre de 2026" in spanish.to_html()
    assert (
        from_csv(examples / "payments.csv", schema=DatasetSchema({})).rows[0][0]
        == "00123"
    )
    if not full:
        for name in ("pandas", "numpy", "playwright", "weasyprint"):
            assert importlib.util.find_spec(name) is None
        try:
            from_pandas(None, schema=DatasetSchema({}))  # type: ignore[arg-type]
        except DependencyError:
            pass
        else:
            raise AssertionError("missing pandas extra must fail clearly")
    else:
        import pandas as pd
        from pypdf import PdfReader

        from cardreport import ChromiumRenderer, WeasyPrintRenderer

        assert from_pandas(pd.DataFrame({"x": [1]}), schema=DatasetSchema({})).rows == (
            (1,),
        )
        for renderer in (ChromiumRenderer(), WeasyPrintRenderer()):
            pdf = PdfReader(io.BytesIO(report.to_pdf(renderer=renderer)))
            assert len(pdf.pages) == 1 and not list(pdf.pages[0].images)
            assert "Campaign progress" in pdf.pages[0].extract_text()
            localized = PdfReader(io.BytesIO(spanish.to_pdf(renderer=renderer)))
            assert "4 de noviembre de 2026" in localized.pages[0].extract_text()
            assert str(localized.root_object["/Lang"]) == "es-MX"
    print("Installed wheel smoke passed:", "all extras" if full else "core only")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--smoke", choices=["core", "full"])
    args = parser.parse_args()
    if args.smoke:
        installed_smoke(args.smoke == "full")
        return
    wheel = check_archives(args.dist.resolve())
    for extra in ("core", "full"):
        with tempfile.TemporaryDirectory(prefix="cardreport-wheel-") as directory:
            python = str(Path(directory) / "venv/bin/python")
            subprocess.run(
                [
                    "uv",
                    "venv",
                    str(Path(directory) / "venv"),
                    "--python",
                    sys.executable,
                ],
                check=True,
            )
            spec = str(wheel) + ("[pdf,weasyprint,pandas]" if extra == "full" else "")
            subprocess.run(
                ["uv", "pip", "install", "--python", python, spec], check=True
            )
            subprocess.run(
                [python, "-I", str(Path(__file__).resolve()), "--smoke", extra],
                cwd=directory,
                check=True,
            )


if __name__ == "__main__":
    main()
