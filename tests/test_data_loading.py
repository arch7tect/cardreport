import json
from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest
from jsonschema import Draft202012Validator

from cardreport import (
    DataError,
    DataLimits,
    datasets_from_json,
    datasets_from_yaml,
    json_schema,
)
from cardreport._yaml import dump_yaml


def document(value=1):
    return {
        "format": "cardreport.data/1",
        "datasets": {"x": {"columns": ["v"], "rows": [{"v": value}]}},
    }


def load(spec, syntax="json", **kwargs):
    if syntax == "json":
        return datasets_from_json(json.dumps(spec), **kwargs)
    return datasets_from_yaml(dump_yaml(spec, 1000000), **kwargs)


@pytest.mark.parametrize("syntax", ["json", "yaml"])
@pytest.mark.parametrize(
    "value",
    [
        {},
        {"$type": "date"},
        {"value": "2026-11-05"},
        {"$type": "decimal", "value": "1", "extra": 1},
        *[
            {"$type": kind, "value": "1"}
            for kind in ("integer", "text", "number", "PRIVATE", None, [], {})
        ],
        *[{"$type": kind, "value": 1} for kind in ("date", "datetime", "decimal")],
        {"$type": "decimal", "value": "0" * 10000 + "1"},
        True,
        [],
        1e16,
        "a" * 10001,
    ],
)
def test_invalid_cells_match_full_schema_and_keep_locations(syntax, value):
    spec = document(value)
    assert not Draft202012Validator(json.loads(json_schema("data"))).is_valid(spec)
    with pytest.raises(DataError) as error:
        load(spec, syntax)
    assert (error.value.dataset, error.value.row, error.value.field) == ("x", 0, "v")
    assert "PRIVATE" not in str(error.value)


@pytest.mark.parametrize("syntax", ["json", "yaml"])
@pytest.mark.parametrize(
    "mutate,dataset",
    [
        (lambda s: s.update(extra=1), None),
        (lambda s: s.update(format="unknown"), None),
        (lambda s: s.update({"$schema": 1}), None),
        (lambda s: s.pop("format"), None),
        (lambda s: s.pop("datasets"), None),
        (lambda s: s.update(datasets=[]), None),
        (lambda s: s["datasets"]["x"].pop("columns"), "x"),
        (lambda s: s["datasets"]["x"].pop("rows"), "x"),
        (lambda s: s["datasets"]["x"].update(extra=1), "x"),
        (lambda s: s["datasets"]["x"].update(columns="v"), "x"),
        (lambda s: s["datasets"]["x"].update(rows={}), "x"),
    ],
)
def test_invalid_envelopes_match_full_schema(syntax, mutate, dataset):
    spec = document()
    mutate(spec)
    assert not Draft202012Validator(json.loads(json_schema("data"))).is_valid(spec)
    with pytest.raises(DataError) as error:
        load(spec, syntax)
    assert error.value.dataset == dataset
    assert error.value.row is None and error.value.field is None


@pytest.mark.parametrize("syntax", ["json", "yaml"])
def test_only_one_value_validation_per_loaded_cell(monkeypatch, syntax):
    import cardreport._schema as schemas
    import cardreport.data as module

    calls = 0
    original = module.cell

    def count(value, limits):
        nonlocal calls
        calls += 1
        return original(value, limits)

    def unexpected(*args, **kwargs):
        pytest.fail("data loader must not invoke full schema validation")

    monkeypatch.setattr(module, "cell", count)
    monkeypatch.setattr(schemas, "validate_structure", unexpected)
    monkeypatch.setattr(Draft202012Validator, "iter_errors", unexpected)
    spec = document()
    spec["datasets"]["x"]["rows"] = [
        {"v": 1},
        {"v": "text"},
        {"v": None},
        {"v": {"$type": "decimal", "value": "1.00"}},
        {"v": {"$type": "date", "value": "2026-11-05"}},
    ]
    assert len(load(spec, syntax)["x"].rows) == 5
    assert calls == 5


def test_typed_kinds_are_read_from_schema(monkeypatch):
    from cardreport import _schema

    schema = json.loads(json_schema("data"))
    schema["$defs"]["typedCell"]["properties"]["$type"]["enum"].remove("date")
    original = _schema.json_schema
    monkeypatch.setattr(
        _schema,
        "json_schema",
        lambda kind: json.dumps(schema) if kind == "data" else original(kind),
    )
    _schema._validator.cache_clear()
    _schema.data_shape.cache_clear()
    try:
        with pytest.raises(DataError) as error:
            load(document({"$type": "date", "value": "2026-11-05"}))
        assert (error.value.dataset, error.value.row, error.value.field) == (
            "x",
            0,
            "v",
        )
    finally:
        _schema._validator.cache_clear()
        _schema.data_shape.cache_clear()


@pytest.mark.parametrize("row", [[], {}, {"wrong": {"$type": "PRIVATE"}}])
def test_row_shape_is_checked_before_decoding(row):
    spec = document()
    spec["datasets"]["x"]["rows"] = [row]
    with pytest.raises(DataError) as error:
        load(spec)
    assert (error.value.dataset, error.value.row, error.value.field) == ("x", 0, None)
    assert "PRIVATE" not in str(error.value)


def test_bundle_totals_still_enforced():
    spec = document("éé")
    spec["datasets"]["y"] = deepcopy(spec["datasets"]["x"])
    for limits in (DataLimits(max_cells=1), DataLimits(max_text_bytes=6)):
        with pytest.raises(DataError) as error:
            load(spec, limits=limits)
        assert error.value.dataset == "y"


def test_lower_string_limit_applies_to_decoded_values():
    limits = DataLimits(max_string_chars=1)
    # A date is not a string cell; a decimal limit counts its coefficient digits.
    assert load(document({"$type": "date", "value": "2026-11-05"}), limits=limits)[
        "x"
    ].rows == ((date(2026, 11, 5),),)
    assert load(document({"$type": "decimal", "value": "0000001"}), limits=limits)[
        "x"
    ].rows == ((Decimal("1"),),)
    with pytest.raises(DataError):
        load(document({"$type": "decimal", "value": "12"}), limits=limits)
    with pytest.raises(DataError):
        load(document("ab"), limits=limits)


def test_fixed_metadata_assumptions_match_schema():
    from cardreport._schema import data_shape

    schema = json.loads(json_schema("data"))
    shape = data_shape()
    assert schema["properties"]["$schema"] == {"type": "string"}
    assert shape.dataset_keys == set(schema["$defs"]["dataset"]["required"])
    assert shape.cell_keys == set(schema["$defs"]["typedCell"]["required"])
    for kind in shape.cell_kinds:
        assert schema["$defs"][kind]["type"] == "string"
        assert schema["$defs"][kind]["maxLength"] == DataLimits().max_string_chars


@pytest.mark.parametrize("bad_name", ["", "PRIVATE" * 15, "\ud800"])
def test_invalid_names_do_not_leak_into_error_locations(bad_name):
    spec = document()
    spec["datasets"][bad_name] = spec["datasets"].pop("x")
    with pytest.raises(DataError) as error:
        load(spec)
    assert error.value.dataset is None
    assert "PRIVATE" not in str(error.value)
    spec = document()
    spec["datasets"]["x"]["columns"] = [bad_name]
    with pytest.raises(DataError) as error:
        load(spec)
    assert error.value.dataset == "x" and error.value.field is None


def test_root_errors_keep_safe_details():
    for spec, message in [
        ({}, "required"),
        ({"format": "unknown", "datasets": {}}, "unsupported data format"),
        (
            {
                "format": "cardreport.data/1",
                "datasets": [],
            },
            "expected an object",
        ),
    ]:
        with pytest.raises(DataError, match=message):
            load(spec)
