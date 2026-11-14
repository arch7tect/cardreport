import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cardreport import (
    BindingError,
    DataError,
    Dataset,
    ReportTemplate,
    TemplateError,
    datasets_from_json,
    datasets_from_yaml,
    datasets_to_json,
    json_schema,
)

ROOT = Path(__file__).resolve().parents[1]


def validator(kind):
    schema = json.loads(json_schema(kind))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.mark.parametrize("kind", ["template", "data"])
def test_metaschemas_and_packaged_identity(kind):
    schema = validator(kind).schema
    assert re.fullmatch(
        rf"https://raw\.githubusercontent\.com/arch7tect/cardreport/"
        rf"v[0-9]+\.[0-9]+\.[0-9]+/src/cardreport/schemas/{kind}-1\.json",
        schema["$id"],
    )
    source = ROOT / "src/cardreport/schemas" / f"{kind}-1.json"
    assert schema == json.loads(source.read_text())
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    with pytest.raises(ValueError):
        json_schema("unknown")


@pytest.mark.parametrize("example", ["reference", "spanish", "operations"])
def test_json_yaml_fixtures_match_schemas(example):
    template = ReportTemplate.from_json(
        (ROOT / f"examples/{example}_template.json").read_bytes()
    )
    data = datasets_from_json((ROOT / f"examples/{example}_data.json").read_bytes())
    validator("template").validate(template.to_dict())
    validator("template").validate(
        ReportTemplate.from_yaml(template.to_yaml()).to_dict()
    )
    validator("data").validate(json.loads(datasets_to_json(data)))
    assert template.bind(data)


def test_normalized_yaml_dates_match_data_schema():
    data = datasets_from_yaml(
        "format: cardreport.data/1\ndatasets: {x: {columns: [d], rows: [{d: 2026-11-05}]}}"
    )
    validator("data").validate(json.loads(datasets_to_json(data)))


def objects(value):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from objects(v)
    elif isinstance(value, list):
        for v in value:
            yield from objects(v)


def test_unknown_properties_rejected_by_schema_and_parser():
    spec = json.loads((ROOT / "examples/operations_template.json").read_text())
    for obj in objects(spec):
        if not (
            "type" in obj or "blocks" in obj or "cardinality" in obj or "bind" in obj
        ):
            continue
        obj["unexpected_property"] = 1
        assert not validator("template").is_valid(spec)
        with pytest.raises(TemplateError):
            ReportTemplate.from_dict(spec)
        del obj["unexpected_property"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s.pop("report"),
        lambda s: s.update(format="cardreport.template/2"),
        lambda s: s.update(unexpected=True),
        lambda s: s["report"].update(mode="invalid"),
        lambda s: s["report"].update(formatting=None),
        lambda s: s["report"].update(
            blocks=[{"type": "row", "children": [{"type": "page_break"}]}]
        ),
        lambda s: s["report"].update(
            blocks=[
                {
                    "type": "card",
                    "content": {
                        "type": "card",
                        "content": {"type": "text", "text": "x"},
                    },
                }
            ]
        ),
        lambda s: s["report"].update(
            blocks=[
                {
                    "type": "bar",
                    "dataset": "calls",
                    "category": "result",
                    "value": "count",
                    "series": [{"field": "count", "label": "Count"}],
                }
            ]
        ),
    ],
)
def test_structural_invalid_templates(mutation):
    spec = json.loads((ROOT / "examples/cli/report.json").read_text())
    mutation(spec)
    assert not validator("template").is_valid(spec)
    with pytest.raises(TemplateError):
        ReportTemplate.from_dict(spec)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s.update(extra=1),
        lambda s: s.update(format="cardreport.data/2"),
        lambda s: s["datasets"]["summary"].update(columns=["total", "total"]),
        lambda s: s["datasets"]["summary"]["rows"][0].update(total=True),
        lambda s: s["datasets"]["summary"]["rows"][0].update(
            total={"$type": "decimal", "value": 12.5}
        ),
    ],
)
def test_structural_invalid_data(mutation):
    spec = json.loads((ROOT / "examples/cli/data.json").read_text())
    mutation(spec)
    assert not validator("data").is_valid(spec)
    with pytest.raises(DataError):
        datasets_from_json(json.dumps(spec))


def test_schema_semantic_boundary_is_explicit():
    spec = json.loads((ROOT / "examples/cli/report.json").read_text())
    spec["report"]["blocks"][0]["content"]["value"]["bind"]["field"] = "missing"
    validator("template").validate(spec)
    with pytest.raises(TemplateError):
        ReportTemplate.from_dict(spec)
    data = {
        "summary": Dataset.single({"total": 1.0}),
        "calls": Dataset.from_dicts([], columns=["result", "count"]),
    }
    template = ReportTemplate.from_json(
        (ROOT / "examples/cli/report.json").read_bytes()
    )
    validator("data").validate(json.loads(datasets_to_json(data)))
    with pytest.raises(BindingError):
        template.bind(data)


def test_all_component_variants():
    source = json.loads((ROOT / "examples/cli/report.json").read_text())
    variants = [
        {"type": "text", "text": "Title", "style": "heading"},
        {
            "type": "kpi",
            "label": "Calls",
            "value": {"bind": {"dataset": "summary", "field": "total"}},
            "note": None,
            "format": "integer",
        },
        {
            "type": "table",
            "dataset": "calls",
            "columns": [
                {"key": "result", "label": "Result", "align": "left", "width": None},
                {"key": "count", "label": "Calls", "format": "integer"},
            ],
            "empty_text": None,
        },
        {
            "type": "bar",
            "dataset": "calls",
            "category": "result",
            "value": "count",
            "value_format": {"currency": "EUR"},
            "show_labels": True,
            "orientation": "horizontal",
        },
        {
            "type": "line",
            "dataset": "calls",
            "x": "result",
            "series": [{"field": "count", "label": "Calls"}],
            "x_kind": "category",
            "axes": False,
            "markers": False,
            "fill": "zero",
            "legend": False,
        },
        {
            "type": "funnel",
            "dataset": "calls",
            "category": "result",
            "value": "count",
            "show_labels": True,
        },
        {
            "type": "row",
            "children": [
                {
                    "type": "column",
                    "children": [{"type": "text", "text": "x"}],
                    "heights": None,
                }
            ],
            "widths": None,
            "height_mm": 50,
        },
        {"type": "page_break"},
    ]
    for node in variants:
        spec = deepcopy(source)
        spec["report"]["blocks"] = [node]
        validator("template").validate(spec)
        ReportTemplate.from_dict(spec)


def test_structure_comes_from_the_packaged_schema(monkeypatch):
    from cardreport import _schema

    schema = json.loads(json_schema("template"))
    schema["$defs"]["report"]["properties"]["editor_note"] = {"type": "string"}
    original = _schema.json_schema
    monkeypatch.setattr(
        _schema,
        "json_schema",
        lambda kind: json.dumps(schema) if kind == "template" else original(kind),
    )
    _schema._validator.cache_clear()
    try:
        spec = {
            "format": "cardreport.template/1",
            "datasets": {},
            "report": {"blocks": [], "editor_note": "Design note"},
        }
        assert ReportTemplate(spec).to_dict() == spec
        spec["report"]["editor_note"] = 42
        with pytest.raises(TemplateError) as error:
            ReportTemplate(spec)
        assert error.value.template_path == "report.editor_note"
    finally:
        _schema._validator.cache_clear()


@pytest.mark.parametrize("syntax", ["json", "yaml"])
def test_structural_error_paths_and_redaction(syntax):
    from cardreport._yaml import dump_yaml

    def encode(value):
        return json.dumps(value) if syntax == "json" else dump_yaml(value, 100000)

    load_template = getattr(ReportTemplate, "from_" + syntax)
    load_data = datasets_from_json if syntax == "json" else datasets_from_yaml
    spec = {
        "format": "cardreport.template/1",
        "datasets": {},
        "report": {
            "blocks": [
                {
                    "type": "row",
                    "children": [
                        {"type": "text", "text": "x", "style": "PRIVATE_VALUE"}
                    ],
                }
            ]
        },
    }
    with pytest.raises(TemplateError) as error:
        load_template(encode(spec))
    assert error.value.template_path == "report.blocks[0].children[0].style"
    assert "PRIVATE_VALUE" not in str(error.value)
    data = {
        "format": "cardreport.data/1",
        "datasets": {
            "a.b": {
                "columns": ["c.d"],
                "rows": [{"c.d": {"$type": "date", "value": "PRIVATE_VALUE"}}],
            }
        },
    }
    with pytest.raises(DataError) as error:
        load_data(encode(data))
    assert (error.value.dataset, error.value.row, error.value.field) == (
        "a.b",
        0,
        "c.d",
    )
    assert "PRIVATE_VALUE" not in str(error.value)


@pytest.mark.parametrize(
    "kind,value",
    [
        ("decimal", "12.50\n"),
        ("date", "2026-11-05\n"),
        ("datetime", "2026-11-05T00:00:00Z\n"),
    ],
)
def test_typed_scalar_grammar_rejects_trailing_newlines(kind, value):
    data = {
        "format": "cardreport.data/1",
        "datasets": {
            "x": {"columns": ["v"], "rows": [{"v": {"$type": kind, "value": value}}]}
        },
    }
    assert not validator("data").is_valid(data)
    with pytest.raises(DataError):
        datasets_from_json(json.dumps(data))


def test_integer_settings_retain_native_type_semantics():
    spec = {
        "format": "cardreport.template/1",
        "datasets": {},
        "report": {"blocks": [], "formatting": {"number_decimals": 2.0}},
    }
    # JSON Schema integers include 2.0; the Python model requires an actual int.
    validator("template").validate(spec)
    with pytest.raises(TemplateError) as error:
        ReportTemplate(spec)
    assert error.value.template_path == "report.formatting.number_decimals"


def test_schema_metadata_never_triggers_network(monkeypatch):
    import socket
    import urllib.request

    def unexpected(*args, **kwargs):
        pytest.fail("validation attempted network access")

    monkeypatch.setattr(socket, "create_connection", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    spec = {
        "$schema": "https://invalid.example/schema",
        "format": "cardreport.template/1",
        "datasets": {},
        "report": {"blocks": []},
    }
    ReportTemplate(spec)
    data = {
        "$schema": "https://invalid.example/schema",
        "format": "cardreport.data/1",
        "datasets": {},
    }
    assert datasets_from_json(json.dumps(data)) == {}


def test_component_limits_precede_schema_recursion(monkeypatch):
    import cardreport.templates as templates

    def unexpected(*args, **kwargs):
        pytest.fail("schema validation ran before resource limits")

    monkeypatch.setattr(templates, "validate_structure", unexpected)
    for blocks in ([{"type": "text", "text": "x"}] * 501,):
        with pytest.raises(TemplateError, match="count/depth"):
            ReportTemplate(
                {
                    "format": "cardreport.template/1",
                    "datasets": {},
                    "report": {"blocks": blocks},
                }
            )
    node = {"type": "text", "text": "x"}
    for _ in range(14):
        node = {"type": "column", "children": [node]}
    with pytest.raises(TemplateError, match="count/depth"):
        ReportTemplate(
            {
                "format": "cardreport.template/1",
                "datasets": {},
                "report": {"blocks": [node]},
            }
        )


def test_deep_valid_template_does_not_expand_alternative_branches():
    import subprocess
    import sys

    # Earlier recursive oneOf alternatives revisited the same children exponentially.
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
from cardreport import ReportTemplate
node = {"type": "text", "text": "x"}
for _ in range(12):
    node = {"type": "column", "children": [node]}
ReportTemplate({"format": "cardreport.template/1", "datasets": {}, "report": {"blocks": [node]}})
""",
        ],
        check=True,
        timeout=15,
    )


def test_native_literal_options_match_transport_schema():
    from typing import get_args, get_type_hints

    from cardreport import (
        BarChart,
        DatasetSchema,
        FieldSpec,
        Formatting,
        LineChart,
        Page,
        Report,
        TableColumn,
        Text,
    )
    from cardreport.model import Format

    defs = validator("template").schema["$defs"]
    pairs = [
        (Text, "style", "textComponent", "style"),
        (TableColumn, "align", "tableColumn", "align"),
        (Page, "orientation", "page", "orientation"),
        (DatasetSchema, "cardinality", "dataset", "cardinality"),
        (FieldSpec, "type", "field", "type"),
        (Formatting, "decimal", "formatting", "decimal"),
        (Formatting, "group", "formatting", "group"),
        *[
            (BarChart, key, "bar", key)
            for key in ("orientation", "mode", "color_by", "legend_position")
        ],
        *[(LineChart, key, "line", key) for key in ("x_kind", "fill")],
    ]
    for model, field, definition, prop in pairs:
        annotation = get_type_hints(model)[field]
        annotation = getattr(annotation, "__value__", annotation)
        assert set(get_args(annotation)) == set(
            defs[definition]["properties"][prop]["enum"]
        )
    assert set(
        get_args(
            get_type_hints(Report.__init__, localns={"Formatting": Formatting})["mode"]
        )
    ) == set(defs["report"]["properties"]["mode"]["enum"])
    assert set(get_args(get_args(Format.__value__)[0])) == set(
        defs["format"]["anyOf"][0]["enum"]
    )


@pytest.mark.parametrize(
    "source",
    [
        "format: cardreport.data/1\ndatasets: {x: {columns: [v], rows: [{v: {$type: date, value: 2026-11-05}}]}}",
    ],
)
def test_yaml_native_scalars_keep_locations_on_rejection(source):
    with pytest.raises(DataError) as error:
        datasets_from_yaml(source)
    assert (error.value.dataset, error.value.row, error.value.field) == ("x", 0, "v")


def test_external_schema_missing_type_chains_remain_bounded():
    import subprocess
    import sys

    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import json
from jsonschema import Draft202012Validator
from cardreport import json_schema
node = {"text": "x"}
for _ in range(24):
    node = {"children": [node]}
spec = {"format": "cardreport.template/1", "datasets": {}, "report": {"blocks": [node]}}
errors = list(Draft202012Validator(json.loads(json_schema("template"))).iter_errors(spec))
assert errors
""",
        ],
        check=True,
        timeout=15,
    )


def test_schema_caps_match_native_limits():
    from cardreport import DataLimits

    caps = DataLimits()
    template = validator("template").schema
    data = validator("data").schema
    for schema in (template, data):
        assert schema["properties"]["datasets"]["maxProperties"] == caps.max_datasets
    fields = template["$defs"]["dataset"]["properties"]["fields"]
    dataset = data["$defs"]["dataset"]["properties"]
    assert fields["maxProperties"] == dataset["columns"]["maxItems"] == caps.max_columns
    assert dataset["rows"]["items"]["maxProperties"] == caps.max_columns
    assert dataset["rows"]["maxItems"] == caps.max_rows
    for definition in ("cell", "decimal", "date", "datetime"):
        assert data["$defs"][definition]["maxLength"] == caps.max_string_chars
    formats = template["$defs"]
    assert set(formats["numericFormat"]["anyOf"][0]["enum"]) == set(
        formats["format"]["anyOf"][0]["enum"]
    ) - {"date"}


def test_theme_colour_schema_rejects_trailing_newline():
    spec = {
        "format": "cardreport.template/1",
        "datasets": {},
        "report": {"blocks": [], "theme": {"accent": "#aabbcc\n"}},
    }
    assert not validator("template").is_valid(spec)
    with pytest.raises(TemplateError) as error:
        ReportTemplate(spec)
    assert error.value.template_path == "report.theme.accent"
