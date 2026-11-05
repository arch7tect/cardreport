import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from cardreport import (
    DataError,
    DataLimits,
    Dataset,
    ReportTemplate,
    TemplateError,
    datasets_from_json,
    datasets_from_yaml,
    datasets_to_json,
    datasets_to_yaml,
)
from cardreport._yaml import load_yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("example", ["reference", "spanish", "operations"])
def test_existing_reports_roundtrip(example):
    template = ReportTemplate.from_json(
        (ROOT / f"examples/{example}_template.json").read_bytes()
    )
    data = datasets_from_json((ROOT / f"examples/{example}_data.json").read_bytes())
    restored = ReportTemplate.from_yaml(template.to_yaml())
    restored_data = datasets_from_yaml(datasets_to_yaml(data))
    assert restored.to_dict() == template.to_dict()
    assert datasets_to_json(restored_data) == datasets_to_json(data)
    assert restored.bind(restored_data).to_html() == template.bind(data).to_html()


def test_standard_yaml_scalars_and_native_dates():
    data = datasets_from_yaml("""
format: cardreport.data/1
datasets:
  values:
    columns: [word, code, day, instant, amount]
    rows:
      - word: on
        code: "00123"
        day: 2026-11-05
        instant: 2026-11-05T12:30:00+02:00
        amount: {$type: decimal, value: "1200.50"}
""")
    row = data["values"].rows[0]
    assert row[:3] == ("on", "00123", date(2026, 11, 5))
    assert row[3] == datetime.fromisoformat("2026-11-05T12:30:00+02:00")
    assert row[4] == Decimal("1200.50")
    assert json.loads(datasets_to_json(data))["datasets"]["values"]["rows"][0][
        "day"
    ] == {"$type": "date", "value": "2026-11-05"}


def test_roundtrip_strings_and_exact_types():
    values = [
        "on",
        "no",
        "00123",
        "1_000",
        "2026-11-05",
        "<<",
        "",
        "~",
        "true",
        "\nhello\nworld\n",
        "Пример",
        "\r\n",
        "\u2028",
        " leading and trailing ",
    ]
    data = {"values": Dataset.from_dicts([{"v": value} for value in values])}
    assert (
        datasets_from_yaml(datasets_to_yaml(data))["values"].rows == data["values"].rows
    )
    typed = {
        "one": Dataset.single(
            {
                "n": Decimal("0.123456789123456789"),
                "d": date(2026, 1, 1),
                "t": datetime(2026, 1, 1, tzinfo=UTC),
            }
        )
    }
    assert datasets_to_json(
        datasets_from_yaml(datasets_to_yaml(typed))
    ) == datasets_to_json(typed)


def test_aliases_merges_and_block_strings():
    template = ReportTemplate.from_yaml("""
format: cardreport.template/1
datasets: {}
report:
  blocks:
    - &first
      type: text
      text: |
        First line
        Second line
    - <<: *first
      style: heading
      text: Another heading
""")
    blocks = template.to_dict()["report"]["blocks"]
    assert blocks[0]["text"] == "First line\nSecond line\n"
    assert blocks[1] == {"type": "text", "text": "Another heading", "style": "heading"}
    assert "&first" not in template.to_yaml()


def test_literal_merge_key_and_library_unmodified():
    data = datasets_from_yaml("""
format: cardreport.data/1
datasets:
  values:
    columns: ["<<"]
    rows: [{"<<": "literal"}]
""")
    assert data["values"].rows == (("literal",),)
    assert YAML(typ="safe", pure=True).load("day: 2026-11-05")["day"] == date(
        2026, 11, 5
    )


@pytest.mark.parametrize(
    "source",
    [
        "a: 1\na: SECRET_VALUE\n",
        "a: !custom SECRET_VALUE\n",
        "!!python/object/apply:os.system [SECRET_VALUE]",
        "a: 1\n---\na: 2\n",
        "a: [SECRET_VALUE\n",
    ],
)
def test_clean_yaml_syntax_errors(source):
    with pytest.raises(TemplateError) as caught:
        ReportTemplate.from_yaml(source)
    cause = str(caught.value.__cause__)
    assert "line" in cause and "SECRET_VALUE" not in cause


@pytest.mark.parametrize(
    "source", ["&a [*a]", "&a {<<: *a}", "[" * 100 + "0" + "]" * 100]
)
def test_recursive_or_deep_graph_rejected(source):
    with pytest.raises(ValueError, match="limit"):
        load_yaml(source, 10000)


def test_exponential_aliases_rejected_before_construction():
    source = 'a0: &a0 [""]\n' + "".join(
        f"a{i}: &a{i} [*a{i - 1}, *a{i - 1}]\n" for i in range(1, 25)
    )
    with pytest.raises(ValueError, match="expanded-node limit"):
        load_yaml(source, 10000)


@pytest.mark.parametrize(
    "scalar",
    [
        "true",
        ".inf",
        ".nan",
        "!!binary aGVsbG8=",
        "!!set {x: null}",
        "2026-11-05T12:30:00",
    ],
)
def test_unsupported_data_scalars(scalar):
    with pytest.raises(DataError):
        datasets_from_yaml(
            "format: cardreport.data/1\ndatasets:\n  d:\n    columns: [v]\n    rows: [{v: "
            + scalar
            + "}]\n"
        )


def test_byte_caps_and_nonstring_keys():
    with pytest.raises(DataError, match="data YAML"):
        datasets_from_yaml(" " * 11, limits=DataLimits(max_json_bytes=10))
    with pytest.raises(TemplateError):
        ReportTemplate.from_yaml(b"\xff")
    with pytest.raises(TemplateError):
        ReportTemplate.from_yaml("true: value")
    with pytest.raises(DataError):
        datasets_to_yaml(
            {"x": Dataset.single({"a": 1})}, limits=DataLimits(max_json_bytes=10)
        )


def test_template_dates_require_quotes():
    with pytest.raises(TemplateError):
        ReportTemplate.from_yaml(
            "format: cardreport.template/1\ndatasets: {}\nreport: {blocks: [], title: 2026-11-05}"
        )


def test_optional_schema_metadata_without_network():
    spec = {
        "$schema": "https://invalid.invalid/schema",
        "format": "cardreport.template/1",
        "datasets": {},
        "report": {"blocks": []},
    }
    template = ReportTemplate.from_dict(spec)
    assert ReportTemplate.from_yaml(template.to_yaml()).to_dict() == spec
    assert (
        datasets_from_yaml(
            "$schema: https://invalid.invalid/data\nformat: cardreport.data/1\ndatasets: {}"
        )
        == {}
    )
    for invalid in (None, 1, {}):
        with pytest.raises(TemplateError):
            ReportTemplate.from_dict({**spec, "$schema": invalid})


@pytest.mark.parametrize("engine", ["chromium", "weasyprint"])
def test_yaml_reference_pdf(engine):
    import io

    from pypdf import PdfReader

    from cardreport import WeasyPrintRenderer

    if engine == "weasyprint":
        pytest.importorskip("weasyprint")
    template = ReportTemplate.from_yaml(
        (ROOT / "examples/reference_template.yaml").read_bytes()
    )
    data = datasets_from_yaml((ROOT / "examples/reference_data.yaml").read_bytes())
    renderer = WeasyPrintRenderer() if engine == "weasyprint" else None
    pdf = PdfReader(io.BytesIO(template.bind(data).to_pdf(renderer=renderer)))
    assert len(pdf.pages) == 1
    assert "Campaign progress" in pdf.pages[0].extract_text()
    assert not list(pdf.pages[0].images)


def test_invalid_explicit_scalar_does_not_expose_value():
    with pytest.raises(TemplateError) as caught:
        ReportTemplate.from_yaml("x: !!int SECRET_VALUE")
    assert str(caught.value.__cause__) == "invalid YAML scalar"


def test_large_aliased_scalars_rejected_before_template_serialization():
    source = "x: &big " + "x" * 600_000 + "\ny: [*big, *big]\n"
    with pytest.raises(TemplateError) as caught:
        ReportTemplate.from_yaml(source)
    assert "expanded-scalar limit" in str(caught.value.__cause__)


def test_maximum_typed_dataset_roundtrip():
    columns = [f"c{i}" for i in range(100)]
    data = {
        "large": Dataset.from_records(
            columns, [[Decimal("1.25")] * 100 for _ in range(1000)]
        )
    }
    encoded = datasets_to_yaml(data)
    assert len(encoded.encode()) < DataLimits().max_json_bytes
    assert datasets_to_json(datasets_from_yaml(encoded)) == datasets_to_json(data)


def test_unsupported_ordered_map_duplicate_has_clean_error():
    with pytest.raises(DataError) as caught:
        datasets_from_yaml("!!omap [{x: 1}, {x: 2}]")
    assert "invalid YAML mapping" in str(caught.value.__cause__)


def test_raw_depth_guard_runs_before_composition(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("composition must not start")

    monkeypatch.setattr(YAML, "compose", unexpected)
    with pytest.raises(ValueError, match="event/depth limit"):
        load_yaml("[" * 100 + "0" + "]" * 100, 10000)


@pytest.mark.parametrize("tag", ["", "!!int "])
def test_long_yaml_11_integer_rejected_before_construction(tag, monkeypatch):
    source = "%YAML 1.1\n---\nx: " + tag + "1" + ":0" * 200_000 + "\n"

    def unexpected(*args, **kwargs):
        raise AssertionError("construction must not start")

    monkeypatch.setattr(YAML, "load", unexpected)
    with pytest.raises(ValueError, match="numeric scalar limit"):
        load_yaml(source, 1024 * 1024)


def test_normal_yaml_11_integer_uses_library_rules():
    assert load_yaml("%YAML 1.1\n---\nx: 1:00\n", 1000) == {"x": 60}
