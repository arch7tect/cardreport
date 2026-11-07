import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

import pytest
from pypdf import PdfReader

from cardreport import Dataset, ReportTemplate, datasets_to_json
from cardreport.cli import main
from examples.quickstart_template import DATA_JSON, TEMPLATE_JSON


@pytest.fixture
def files(tmp_path):
    (tmp_path / "report.json").write_text(TEMPLATE_JSON)
    (tmp_path / "data.json").write_text(DATA_JSON)
    (tmp_path / "summary.csv").write_text("total\n34\n")
    (tmp_path / "calls.csv").write_text("result,count\nAnswered,24\nNo answer,10\n")
    return tmp_path


def arguments(files, *options, output="out.html"):
    return [
        "render",
        "--template",
        str(files / "report.json"),
        *options,
        "--output",
        str(files / output),
    ]


@pytest.mark.parametrize("entry", ["module", "console"])
def test_installed_entry_points(files, entry):
    command = (
        [sys.executable, "-m", "cardreport"]
        if entry == "module"
        else [str(Path(sys.executable).with_name("cardreport"))]
    )
    result = subprocess.run(
        command + arguments(files, "--data", str(files / "data.json")),
        capture_output=True,
        text=True,
        cwd=files,
    )
    assert result.returncode == 0, result.stderr
    assert "Total calls" in (files / "out.html").read_text()
    assert result.stdout.strip() == str(files / "out.html")
    result = subprocess.run(
        command + ["--version"], capture_output=True, text=True, cwd=files
    )
    assert result.returncode == 0 and result.stdout.strip() == version("cardreport")


def test_csv_and_overwrite(files, capsys):
    args = arguments(
        files, "--csv", str(files / "summary.csv"), "--csv", str(files / "calls.csv")
    )
    assert main(args) == 0
    original = (files / "out.html").read_bytes()
    assert b"Answered" in original and b"34" in original
    (files / "summary.csv").write_text("total\n99\n")
    assert main(args) == 1
    assert "--overwrite" in capsys.readouterr().err
    assert (files / "out.html").read_bytes() == original
    assert main(args + ["--overwrite"]) == 0
    assert b"99" in (files / "out.html").read_bytes()


def test_json_csv_merge_alias_and_extra_json(files):
    (files / "base.json").write_text(
        datasets_to_json(
            {
                "summary": Dataset.single({"total": 45}),
                "unused": Dataset.single({"x": 1}),
            }
        )
    )
    assert (
        main(
            arguments(
                files,
                "--data",
                str(files / "base.json"),
                "--csv-as",
                "calls",
                str(files / "calls.csv"),
            )
        )
        == 0
    )
    assert "45" in (files / "out.html").read_text()


@pytest.mark.parametrize("alias", [False, True])
def test_equal_sign_and_spaces_are_literal(files, alias):
    name = "call = results"
    template = json.loads(TEMPLATE_JSON)
    template["datasets"][name] = template["datasets"].pop("calls")
    template["report"]["blocks"][1]["children"][0]["content"]["dataset"] = name
    (files / "report.json").write_text(json.dumps(template))
    path = files / ("export = November.csv" if alias else name + ".csv")
    path.write_bytes((files / "calls.csv").read_bytes())
    option = ["--csv-as", name, str(path)] if alias else ["--csv", str(path)]
    assert main(arguments(files, "--csv", str(files / "summary.csv"), *option)) == 0


@pytest.mark.parametrize(
    "options, message",
    [
        (
            ["--csv", "summary.csv", "--csv-as", "summary", "absent.csv"],
            "duplicate CSV dataset",
        ),
        (["--data", "data.json", "--csv", "summary.csv"], "both --data and CSV"),
        (["--csv", "Summary.csv"], "not declared"),
        (["--csv", "summary.csv"], "missing required dataset"),
        (["--data", "absent.json"], "absent.json"),
    ],
)
def test_data_errors(files, options, message, monkeypatch, capsys):
    monkeypatch.chdir(files)
    assert main(arguments(files, *options)) == 1
    error = capsys.readouterr().err
    assert message in error
    if message == "missing required dataset":
        assert "dataset 'calls'" in error
    assert not (files / "out.html").exists()


@pytest.mark.parametrize("content", ["total\nnot-a-number\n", "wrong\n1\n", "total\n"])
def test_csv_error_context(files, content, capsys):
    (files / "summary.csv").write_text(content)
    assert (
        main(
            arguments(
                files,
                "--csv",
                str(files / "summary.csv"),
                "--csv",
                str(files / "calls.csv"),
            )
        )
        == 1
    )
    error = capsys.readouterr().err
    assert (
        "dataset 'summary'" in error
        and "summary.csv" in error
        and "Traceback" not in error
    )
    if content != "total\n":
        assert "field 'total'" in error
    if "not-a-number" in content:
        assert "data row 1" in error


def test_csv_conversion_options(files, monkeypatch):
    template = json.loads(TEMPLATE_JSON)
    template["datasets"]["typed"] = {
        "cardinality": "one",
        "fields": {
            "code": {"type": "text"},
            "amount": {"type": "decimal"},
            "day": {"type": "date"},
            "gap": {"type": "integer", "nullable": True},
        },
    }
    (files / "report.json").write_text(json.dumps(template))
    (files / "typed.csv").write_text(
        "code;amount;day;gap\n00123;2.30;2026-11-05;NULL\n", encoding="utf-8-sig"
    )
    original = ReportTemplate.bind
    captured = {}

    def bind(self, data, **kwargs):
        captured.update(data)
        return original(self, data, **kwargs)

    monkeypatch.setattr(ReportTemplate, "bind", bind)
    assert (
        main(
            arguments(
                files,
                "--data",
                str(files / "data.json"),
                "--csv",
                str(files / "typed.csv"),
                "--csv-delimiter",
                ";",
                "--csv-encoding",
                "utf-8-sig",
                "--csv-null",
                "NULL",
            )
        )
        == 0
    )
    assert captured["typed"].rows == (
        ("00123", Decimal("2.30"), date(2026, 11, 5), None),
    )


@pytest.mark.parametrize(
    "options",
    [
        ["--timeout", "nan"],
        ["--timeout", "0"],
        ["--timeout", "1e400"],
        ["--timeout", "inf"],
        ["--csv-delimiter", "::"],
        ["--renderer", "other"],
    ],
)
def test_argument_errors(files, options):
    with pytest.raises(SystemExit) as exc:
        main(arguments(files, *options))
    assert exc.value.code == 2
    assert not (files / "out.html").exists()


def test_bad_suffix_and_malformed_template(files, capsys):
    assert main(arguments(files, output="out.txt")) == 1
    assert ".html or .pdf" in capsys.readouterr().err
    (files / "report.json").write_text("{")
    assert main(arguments(files)) == 1
    assert "template JSON" in capsys.readouterr().err


@pytest.mark.parametrize("kind", ["same", "symlink", "hardlink"])
def test_input_is_never_overwritten(files, kind, capsys):
    source = files / "summary.html"
    source.write_text("total\n34\n")
    output = source if kind == "same" else files / "out.html"
    if kind == "symlink":
        output.symlink_to(source)
    elif kind == "hardlink":
        output.hardlink_to(source)
    assert (
        main(
            arguments(
                files,
                "--csv-as",
                "summary",
                str(source),
                "--overwrite",
                output=output.name,
            )
        )
        == 1
    )
    assert "input file" in capsys.readouterr().err
    assert source.read_text() == "total\n34\n"


@pytest.mark.parametrize("renderer", ["chromium", "weasyprint"])
def test_pdf_engines(files, renderer):
    if renderer == "weasyprint":
        pytest.importorskip("weasyprint")
    examples = Path(__file__).resolve().parents[1] / "examples"
    (files / "report.json").write_bytes(
        (examples / "reference_template.json").read_bytes()
    )
    (files / "data.json").write_bytes((examples / "reference_data.json").read_bytes())
    assert (
        main(
            arguments(
                files,
                "--data",
                str(files / "data.json"),
                "--renderer",
                renderer,
                "--timeout",
                "7200",
                output="out.pdf",
            )
        )
        == 0
    )
    pdf = PdfReader(files / "out.pdf")
    assert len(pdf.pages) == 1
    text = pdf.pages[0].extract_text()
    assert "Campaign progress" in text and "34" in text and "Contact funnel" in text
    assert not list(pdf.pages[0].images)


def test_static_template_needs_no_data(files):
    (files / "report.json").write_text(
        json.dumps(
            {
                "format": "cardreport.template/1",
                "datasets": {},
                "report": {"blocks": [{"type": "text", "text": "Static report"}]},
            }
        )
    )
    assert main(arguments(files)) == 0
    assert "Static report" in (files / "out.html").read_text()


def test_failed_render_preserves_output(files, monkeypatch, capsys):
    from cardreport import RenderTimeoutError, Report

    output = files / "out.pdf"
    output.write_bytes(b"original")

    def fail(self, **kwargs):
        assert kwargs["timeout"] == 0.1
        raise RenderTimeoutError("test deadline")

    monkeypatch.setattr(Report, "to_pdf", fail)
    assert (
        main(
            arguments(
                files,
                "--data",
                str(files / "data.json"),
                "--timeout",
                "0.1",
                "--overwrite",
                output="out.pdf",
            )
        )
        == 1
    )
    assert "test deadline" in capsys.readouterr().err
    assert output.read_bytes() == b"original"


def test_bounded_template_read(files, capsys):
    from cardreport.templates import MAX_TEMPLATE_BYTES

    (files / "report.json").write_bytes(b" " * (MAX_TEMPLATE_BYTES + 1))
    assert main(arguments(files)) == 1
    assert "byte limit" in capsys.readouterr().err


@pytest.mark.parametrize("option", ["--out", "--over", "--csv-d"])
def test_options_are_not_abbreviated(files, option):
    with pytest.raises(SystemExit) as exc:
        main(arguments(files, option, *([] if option == "--over" else ["x"])))
    assert exc.value.code == 2


def test_missing_csv_explains_cause(files, capsys):
    assert (
        main(arguments(files, "--csv-as", "summary", str(files / "missing.csv"))) == 1
    )
    error = capsys.readouterr().err
    assert "No such file" in error and "missing.csv" in error
    assert "dataset 'summary'" in error and "Traceback" not in error


def test_unknown_csv_encoding_explains_cause(files, capsys):
    assert (
        main(
            arguments(
                files,
                "--csv",
                str(files / "summary.csv"),
                "--csv-encoding",
                "not-an-encoding",
            )
        )
        == 1
    )
    error = capsys.readouterr().err
    assert "unknown encoding" in error and "not-an-encoding" in error


def test_top_level_options_are_not_abbreviated():
    with pytest.raises(SystemExit) as exc:
        main(["--vers"])
    assert exc.value.code == 2


def test_yaml_cli_and_validation(files, capsys):
    template = ReportTemplate.from_json((files / "report.json").read_bytes())
    (files / "report.yml").write_text(template.to_yaml())
    from cardreport import datasets_from_json, datasets_to_yaml

    (files / "data.yaml").write_text(
        datasets_to_yaml(datasets_from_json((files / "data.json").read_bytes()))
    )
    assert main(["validate", "--template", str(files / "report.yml")]) == 0
    assert "data and layout have not" in capsys.readouterr().out
    assert (
        main(
            [
                "validate",
                "--template",
                str(files / "report.yml"),
                "--data",
                str(files / "data.yaml"),
            ]
        )
        == 0
    )
    assert "Template and data valid" in capsys.readouterr().out
    assert (
        main(
            [
                "render",
                "--template",
                str(files / "report.yml"),
                "--data",
                str(files / "data.yaml"),
                "--output",
                str(files / "yaml.html"),
            ]
        )
        == 0
    )
    assert "Total calls" in (files / "yaml.html").read_text()
    assert (
        main(
            [
                "validate",
                "--template",
                str(files / "report.yml"),
                "--csv",
                str(files / "summary.csv"),
                "--csv",
                str(files / "calls.csv"),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "validate",
                "--template",
                str(files / "report.yml"),
                "--csv",
                str(files / "summary.csv"),
            ]
        )
        == 1
    )
    assert "missing required dataset" in capsys.readouterr().err


@pytest.mark.parametrize("kind", ["template", "data"])
def test_schema_command(kind, capsys):
    assert main(["schema", kind]) == 0
    output = capsys.readouterr()
    assert (
        json.loads(output.out)["$schema"]
        == "https://json-schema.org/draft/2020-12/schema"
    )
    assert not output.err


def test_validate_does_not_render(files, monkeypatch):
    from cardreport import Report

    def fail(*args, **kwargs):
        raise AssertionError("validation must not render")

    monkeypatch.setattr(Report, "to_html", fail)
    monkeypatch.setattr(Report, "to_pdf", fail)
    assert (
        main(
            [
                "validate",
                "--template",
                str(files / "report.json"),
                "--data",
                str(files / "data.json"),
            ]
        )
        == 0
    )


def test_timeout_above_five_minutes_reaches_export(files, monkeypatch):
    from cardreport import Report

    observed = []

    def export(self, **kwargs):
        observed.append(kwargs["timeout"])
        return b"%PDF-test"

    monkeypatch.setattr(Report, "to_pdf", export)
    assert (
        main(
            arguments(
                files,
                "--data",
                str(files / "data.json"),
                "--timeout",
                "3600",
                output="out.pdf",
            )
        )
        == 0
    )
    assert observed == [3600]
