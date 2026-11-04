import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from cardreport import (
    DataError,
    DataLimits,
    Dataset,
    DatasetSchema,
    FieldSpec,
    datasets_from_json,
    datasets_to_json,
)


def test_snapshot_and_transport():
    row = {
        "amount": Decimal("1200.50"),
        "day": date(2026, 11, 4),
        "time": datetime(2026, 11, 4, tzinfo=timezone(timedelta(hours=2))),
        "note": None,
    }
    ds = Dataset.single(row)
    row["amount"] = 0
    restored = datasets_from_json(
        datasets_to_json({"items": ds, "empty": Dataset(["id"], [])})
    )
    assert restored["items"] == ds
    assert str(restored["items"].rows[0][0]) == "1200.50"
    assert restored["empty"].columns == ("id",)
    assert ds.rows[0][0] == Decimal("1200.50")


@pytest.mark.parametrize(
    "value",
    [
        True,
        float("inf"),
        float("nan"),
        Decimal("NaN"),
        b"a",
        [1],
        datetime(2026, 1, 1),
        datetime(2026, 1, 1, tzinfo=timezone(timedelta(seconds=30))),
    ],
)
def test_reject_cells(value):
    with pytest.raises(DataError):
        Dataset.single({"value": value})


def test_bounded_iterator_and_missing_null():
    consumed = []

    def records():
        for i in range(100):
            consumed.append(i)
            yield [i]

    with pytest.raises(DataError):
        Dataset.from_records(["id"], records(), limits=DataLimits(max_rows=2))
    assert consumed == [0, 1, 2]
    with pytest.raises(DataError):
        Dataset.from_dicts([{"a": 1}, {"b": 2}])
    schema = DatasetSchema({"a": FieldSpec("integer", nullable=True)}, "one")
    schema.validate(Dataset.single({"a": None}))
    for ds in [
        Dataset(["a"], []),
        Dataset.single({"b": 1}),
        Dataset.single({"a": "1"}),
    ]:
        with pytest.raises(DataError):
            schema.validate(ds)
    with pytest.raises(DataError):
        Dataset.from_dicts([])
    with pytest.raises(DataError):
        Dataset(["a", "a"], [])


@pytest.mark.parametrize(
    "source",
    [
        '{"format":"cardreport.data/1","format":"x","datasets":{}}',
        '{"format":"cardreport.data/2","datasets":{}}',
        '{"format":"cardreport.data/1","datasets":{"a":{"columns":["x"],"rows":[{"x":NaN}]}}}',
        '{"format":"cardreport.data/1","datasets":{"a":{"columns":["x"],"rows":[{"x":{"$type":"decimal","value":"1_000"}}]}}}',
    ],
)
def test_bad_json(source):
    with pytest.raises(DataError):
        datasets_from_json(source)


def test_caps_and_schema_types():
    with pytest.raises(DataError):
        DataLimits(max_rows=2001)
    with pytest.raises(DataError):
        DataLimits(max_rows=True)
    with pytest.raises(DataError):
        Dataset.single({"a": "abcd"}, limits=DataLimits(max_string_chars=3))
    with pytest.raises(DataError):
        datasets_to_json(
            {"a": Dataset.single({"x": 1}), "b": Dataset.single({"x": 2})},
            limits=DataLimits(max_cells=1),
        )
    with pytest.raises(DataError):
        DatasetSchema({"x": FieldSpec("decimal")}).validate(Dataset.single({"x": 1.2}))
    DatasetSchema({"x": FieldSpec("decimal")}).validate(Dataset.single({"x": 1}))
    bad = {
        "format": "cardreport.data/1",
        "datasets": {
            "a": {
                "columns": ["x"],
                "rows": [
                    {"x": {"$type": "datetime", "value": "2026-01-01T00:00:00+00:99"}}
                ],
            }
        },
    }
    with pytest.raises(DataError):
        datasets_from_json(json.dumps(bad))


@pytest.mark.parametrize(
    "row", [{"b": 1, "a": 2}, {1, 2}, bytearray([1, 2]), iter([1, 2]), None]
)
def test_records_reject_unordered_or_nonsequence_rows(row):
    with pytest.raises(DataError):
        Dataset.from_records(["a", "b"], [row])


def test_dicts_invalid_first_row_and_columns():
    with pytest.raises(DataError):
        Dataset.from_dicts([None, {"a": 1}], columns=["a"])
    with pytest.raises(DataError):
        Dataset.from_dicts([{"a": 1, "b": 2}], columns="ab")
    with pytest.raises(DataError):
        DatasetSchema([])


@pytest.mark.parametrize(
    "value",
    [
        datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=1))),
        datetime(9999, 12, 31, 23, 59, tzinfo=timezone(timedelta(hours=-1))),
    ],
)
def test_datetime_utc_overflow(value):
    with pytest.raises(DataError):
        Dataset.single({"at": value})


def test_exact_transport_types():
    source = Dataset.single(
        {
            "n": 1.0,
            "amount": Decimal("1.00"),
            "day": date(2026, 1, 1),
            "at": datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=3))),
        }
    )
    row = datasets_from_json(datasets_to_json({"x": source}))["x"].rows[0]
    assert tuple(type(v) for v in row) == (float, Decimal, date, datetime)
    assert row[1].as_tuple() == Decimal("1.00").as_tuple()
    assert row[3].utcoffset() == timedelta(hours=3)


@pytest.mark.parametrize(
    "value",
    [
        True,
        {"$type": "unknown", "value": "1"},
        {"$type": "decimal", "value": "1", "extra": 1},
        {"$type": "datetime", "value": "2026-01-01T24:00:00Z"},
        {"$type": "datetime", "value": "2026-01-01T00:00:00+24:00"},
    ],
)
def test_transport_error_locations(value):
    raw = {
        "format": "cardreport.data/1",
        "datasets": {"items": {"columns": ["x"], "rows": [{"x": value}]}},
    }
    with pytest.raises(DataError) as caught:
        datasets_from_json(json.dumps(raw))
    assert (caught.value.dataset, caught.value.row, caught.value.field) == (
        "items",
        0,
        "x",
    )


def test_json_size_depth_encoding_bounds():
    with pytest.raises(DataError):
        datasets_from_json(
            '{"format":"cardreport.data/1","datasets":{}}',
            limits=DataLimits(max_json_bytes=20),
        )
    with pytest.raises(DataError):
        datasets_from_json("[" * 66 + "0" + "]" * 66)
    with pytest.raises(DataError):
        datasets_from_json(
            '{"format":"cardreport.data/1","datasets":{}}'.encode("utf-16")
        )


def test_invalid_tagged_date_message_does_not_echo_cell():
    value = "2026-99-31"
    raw = {
        "format": "cardreport.data/1",
        "datasets": {
            "x": {
                "columns": ["day"],
                "rows": [{"day": {"$type": "date", "value": value}}],
            }
        },
    }
    with pytest.raises(DataError) as caught:
        datasets_from_json(json.dumps(raw))
    assert value not in str(caught.value)
    assert caught.value.field == "day"


def test_names_reject_unpaired_unicode_surrogates():
    with pytest.raises(DataError):
        Dataset(["\ud800"], [])
    with pytest.raises(DataError):
        DatasetSchema({"\ud800": FieldSpec("text")})
    with pytest.raises(DataError):
        datasets_to_json({"\ud800": Dataset([], [])})
    with pytest.raises(DataError):
        datasets_from_json(
            '{"format":"cardreport.data/1","datasets":{"\\ud800":{"columns":[],"rows":[]}}}'
        )
    with pytest.raises(DataError):
        datasets_from_json(
            '{"format":"cardreport.data/1","datasets":{"x":{"columns":["\\ud800"],"rows":[]}}}'
        )
