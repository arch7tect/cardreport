# Named datasets

[Documentation home](../../README.md) · [Templates](templates.md) · [API](api.md#datasets-and-data-json)

Pass a mapping of names to immutable Dataset objects. A summary for KPI/text uses
one row; tables/charts use many rows. Python callers do not need to encode JSON.

```python
from decimal import Decimal
from cardreport import Dataset, DatasetSchema, FieldSpec, datasets_from_json, datasets_to_json

data = {
    "summary": Dataset.single({"total": 34}),
    "payments": Dataset.from_dicts([
        {"account": "00123", "amount": Decimal("1200.50")},
        {"account": "00456", "amount": None},
    ]),
}
schema = DatasetSchema({
    "account": FieldSpec("text"),
    "amount": FieldSpec("decimal", nullable=True),
})
schema.validate(data["payments"])
saved = datasets_to_json(data)
restored = datasets_from_json(saved)
assert restored == data
```

Dataset copies columns/rows. Empty input needs column metadata:
`Dataset.from_records(["account", "amount"], [])`. Missing columns/keys are errors;
None is a value and must satisfy the schema's nullable flag. Extra columns are
allowed but their cells must still be supported. Project unsupported fields before
ingestion. The library does not aggregate, sort or reconcile business values.

## Types and limits

Cells support int, finite float/Decimal, str, date, aware datetime and None.
Bool, nested objects, bytes and UUID are rejected. Naive datetimes and offsets not
aligned to whole minutes or dates outside the representable UTC range are rejected. Datetimes are copied with a fixed offset;
zone identity and fold metadata are not retained. Numbers must be within +/-10^15.

FieldSpec types are text, integer, number, decimal, date and datetime. Integer
requires int; number accepts int/float/Decimal; decimal accepts Decimal/int without
converting int or recovering float precision. Date excludes datetime. Bind does
not parse strings into dates/numbers. Missing data, an empty dataset and a null
cell are distinct. `cardinality="one"` requires exactly one row, not a first row.

DataLimits defaults: 2000 rows, 100 columns, 32 datasets, 100000 cells per bundle,
10000 characters per string, 16 MiB aggregate UTF-8 cell text and 16 MiB JSON.
Options may only reduce these caps. Existing report/chart limits can be stricter.
Excess input raises an error, never silent truncation. Iterators are consumed by
constructors before binding; no live cursor or lazy data is passed to rendering.

## Data JSON

The independent envelope is `{"format":"cardreport.data/1","datasets":{...}}`.
Each dataset contains `columns` (ordered names) and `rows` (objects whose keys
exactly match columns). An empty dataset retains columns with `rows: []`.
JSON bytes must be UTF-8 without a BOM. Only version 1 is accepted. Unknown/duplicate keys and nonfinite numbers fail.

Decimal cells use `{"$type":"decimal","value":"1200.50"}`; dates use
`{"$type":"date","value":"2026-11-04"}`; datetimes use
`{"$type":"datetime","value":"2026-11-04T09:00:00+02:00"}`.
Native strings remain strings. Numeric JSON tokens become int/float; decimal tags
preserve exact values and scale. Datetime text uses seconds, optional 1–6 fractional
digits and an explicit offset or Z. Nested cells and generic `default=str` encoding
are unsupported. The data codec does not require a template.

Dataset/codec errors are DataError. DatasetSchema.validate also raises DataError;
ReportTemplate.bind wraps data-contract failures as BindingError. Errors provide
optional dataset/row/field/template_path attributes without including cell contents.
See [API](api.md#datasets-and-data-json) for signatures and import locations.

## One CSV file

`from_csv` uses the standard library and an explicit schema. In a checkout, this
example reads the bundled [payments.csv](../../examples/payments.csv); applications
supply their own path. Use `{"payments": payments}` in a template's named data map.

```python
from examples.reference_from_template import EXAMPLES
from cardreport.adapters.csv import from_csv

payments = from_csv(EXAMPLES / "payments.csv", schema=schema, null_values=["\\N"])
assert payments == data["payments"]
```

This snippet continues the schema and imports above. Defaults are UTF-8, comma,
and no null tokens. Text keeps leading zeros and whitespace. An empty text cell
stays `""`; an empty numeric/date cell fails unless explicitly selected as a null
token and permitted by the schema. Numeric text uses ASCII digits, optional sign,
decimal point and exponent; integers allow only sign/digits. Number/decimal fields
are parsed as Decimal, with no binary-float round trip. Dates use `YYYY-MM-DD` and
datetimes the tagged-JSON grammar above. Undeclared extra columns stay text.
No trimming, header renaming or inference occurs. For a BOM, select `encoding="utf-8-sig"`.
Missing/duplicate headers, inconsistent row widths and invalid encoding fail.
The byte cap is `limits.max_json_bytes`; row, cell and text caps also apply.
A header-only file preserves its columns, but fails a cardinality-one schema.

## Optional pandas

Install the extra in your application:

```sh
uv add "cardreport[pandas]"
```

In a checkout, use `uv sync --extra pandas --locked`. Core imports and all other
data routes do not require pandas. The adapter copies a DataFrame into Dataset:

```python
import pandas as pd
from cardreport.adapters.pandas import from_pandas

frame = pd.DataFrame({
    "account": ["00123", "00456"],
    "amount": [Decimal("1200.50"), None],
})
payments = from_pandas(frame, schema=schema)
assert payments == data["payments"]
```

The default `index="error"` accepts only an unnamed default RangeIndex; select
`index="drop"` to discard another index deliberately. Use `reset_index()` yourself
to retain an index as columns. Duplicate/non-string column names and MultiIndex
columns fail. Project unsupported object columns before ingestion.
NumPy numbers become native numbers; pandas NA/NaT and floating NaN become None,
then schema nullability is checked. For nullable integers, construct the column
with `pd.Series([1, None], dtype="Int64")`; ordinary inferred float columns do not
satisfy an integer schema. Infinity is rejected. Decimal is preserved;
float-to-decimal recovery is never attempted. Datetime values need timezone offsets
and microsecond precision: nanosecond remainders are rejected rather than truncated.
A later DataFrame mutation cannot change the captured dataset.

## Caller-owned SQL results

Execute queries in your application. Pass ordered cursor rows with explicit column
names to `Dataset.from_records`; use `from_dicts` for mapping rows. For example,
this standalone snippet uses only Python's built-in sqlite3:

```python
import sqlite3

with sqlite3.connect(":memory:") as connection:
    cursor = connection.execute("select '00123' as account, 12 as calls")
    result = Dataset.from_records([column[0] for column in cursor.description], cursor)
    assert result.rows == (("00123", 12),)
```

Constructors consume bounded rows and create a snapshot; database-driver buffering
is outside their control. Named SQL execution and CSV-directory loaders are deferred.
