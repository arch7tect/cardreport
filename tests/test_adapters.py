from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from cardreport import DataError, DataLimits, DatasetSchema, FieldSpec
from cardreport.adapters.csv import from_csv


def test_csv_typed_null_and_leading_zero(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text(
        "id,amount,day,note\n00123,1200.50,2026-11-04,\n00456,\\N,2026-11-05,hello\n"
    )
    schema = DatasetSchema(
        {
            "id": FieldSpec("text"),
            "amount": FieldSpec("decimal", True),
            "day": FieldSpec("date"),
            "note": FieldSpec("text"),
        }
    )
    ds = from_csv(path, schema=schema, null_values=["\\N"])
    assert ds.rows[0] == ("00123", Decimal("1200.50"), date(2026, 11, 4), "")
    assert ds.rows[1][1] is None
    with pytest.raises(DataError):
        from_csv(path, schema=schema)


@pytest.mark.parametrize(
    "content",
    [
        "x,x\n1,2\n",
        "x\n1,2\n",
        "x\n1_000\n",
        "x\n 1\n",
        "x\nNaN\n",
        "x\n\n",
        "other\n1\n",
        "",
    ],
)
def test_csv_rejections(tmp_path, content):
    path = tmp_path / "input.csv"
    path.write_text(content)
    with pytest.raises(DataError):
        from_csv(path, schema=DatasetSchema({"x": FieldSpec("integer")}))


def test_csv_empty_bom_and_caps(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("x\n")
    assert from_csv(
        path, schema=DatasetSchema({"x": FieldSpec("integer")})
    ).columns == ("x",)
    with pytest.raises(DataError):
        from_csv(path, schema=DatasetSchema({"x": FieldSpec("integer")}, "one"))
    path.write_text("\ufeffx\n1\n")
    assert from_csv(
        path, schema=DatasetSchema({"x": FieldSpec("integer")}), encoding="utf-8-sig"
    ).rows == ((1,),)
    with pytest.raises(DataError):
        from_csv(path, schema=DatasetSchema({"x": FieldSpec("integer")}))
    path.write_text("x\n1\n2\n")
    with pytest.raises(DataError):
        from_csv(
            path,
            schema=DatasetSchema({"x": FieldSpec("integer")}),
            limits=DataLimits(max_rows=1),
        )
    with pytest.raises(DataError):
        from_csv(
            path,
            schema=DatasetSchema({"x": FieldSpec("integer")}),
            limits=DataLimits(max_json_bytes=2),
        )
    path.write_bytes(b"x\n\xff")
    with pytest.raises(DataError):
        from_csv(path, schema=DatasetSchema({"x": FieldSpec("text")}))


def test_pandas_normalization_and_snapshot():
    pd = pytest.importorskip("pandas")
    from cardreport.adapters.pandas import from_pandas

    df = pd.DataFrame(
        {
            "n": pd.Series([1, None], dtype="Int64"),
            "amount": [Decimal("2.30"), None],
            "at": [pd.Timestamp("2026-11-04T00:00:00Z"), pd.NaT],
        }
    )
    schema = DatasetSchema(
        {
            "n": FieldSpec("integer", True),
            "amount": FieldSpec("decimal", True),
            "at": FieldSpec("datetime", True),
        }
    )
    ds = from_pandas(df, schema=schema)
    assert ds.rows == (
        (1, Decimal("2.30"), datetime(2026, 11, 4, tzinfo=UTC)),
        (None, None, None),
    )
    df.loc[0, "n"] = 99
    assert ds.rows[0][0] == 1
    assert from_pandas(df.iloc[:0], schema=schema).columns == ("n", "amount", "at")
    indexed = df.set_index("n")
    with pytest.raises(DataError):
        from_pandas(indexed, schema=DatasetSchema({}))
    from_pandas(indexed, schema=DatasetSchema({}), index="drop")


@pytest.mark.parametrize(
    "kind",
    [
        "float_decimal",
        "naive",
        "precision",
        "duplicate",
        "bool",
        "infinity",
        "object",
        "named_index",
    ],
)
def test_pandas_rejections(kind):
    pd = pytest.importorskip("pandas")
    from cardreport.adapters.pandas import from_pandas

    schema = DatasetSchema({"x": FieldSpec("number", True)})
    options = {
        "float_decimal": pd.DataFrame({"x": [1.2]}),
        "naive": pd.DataFrame({"x": [pd.Timestamp("2026-01-01")]}),
        "precision": pd.DataFrame(
            {"x": [pd.Timestamp("2026-01-01T00:00:00.000000001Z")]}
        ),
        "duplicate": pd.DataFrame([[1, 2]], columns=["x", "x"]),
        "bool": pd.DataFrame({"x": [True]}),
        "infinity": pd.DataFrame({"x": [float("inf")]}),
        "object": pd.DataFrame({"x": [[1, 2]]}),
        "named_index": pd.DataFrame({"x": [1]}).rename_axis("row"),
    }
    if kind == "float_decimal":
        schema = DatasetSchema({"x": FieldSpec("decimal")})
    with pytest.raises(DataError):
        from_pandas(options[kind], schema=schema)


def test_pandas_nan_explicit_policy():
    pd = pytest.importorskip("pandas")
    from cardreport.adapters.pandas import from_pandas

    assert from_pandas(
        pd.DataFrame({"x": [float("nan")]}),
        schema=DatasetSchema({"x": FieldSpec("number", True)}),
    ).rows == ((None,),)


def test_missing_pandas_extra(monkeypatch):
    import sys

    from cardreport import DependencyError
    from cardreport.adapters.pandas import from_pandas

    monkeypatch.setitem(sys.modules, "pandas", None)
    with pytest.raises(DependencyError, match=r"cardreport\[pandas\]"):
        from_pandas(None, schema=DatasetSchema({}))


def test_missing_csv_column_has_location(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("account\n00123\n")
    with pytest.raises(DataError) as caught:
        from_csv(path, schema=DatasetSchema({"amount": FieldSpec("decimal")}))
    assert caught.value.field == "amount"
