import json
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
    assert schema["$id"].endswith(f"/v0.6.0/src/cardreport/schemas/{kind}-1.json")
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
