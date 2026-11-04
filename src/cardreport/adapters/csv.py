"""Read one CSV file according to an explicit dataset schema."""

import csv
import io
from collections.abc import Iterable, Sequence
from pathlib import Path

from .._inputs import DataError, parse_scalar
from ..data import DEFAULT_LIMITS, DataLimits, Dataset, DatasetSchema


def from_csv(
    path: str | Path,
    *,
    schema: DatasetSchema,
    encoding: str = "utf-8",
    delimiter: str = ",",
    null_values: Sequence[str] = (),
    limits: DataLimits = DEFAULT_LIMITS,
) -> Dataset:
    if not isinstance(schema, DatasetSchema):
        raise DataError("schema must be DatasetSchema")
    if isinstance(null_values, str) or any(not isinstance(v, str) for v in null_values):
        raise DataError("null_values must be a sequence of strings")
    try:
        with Path(path).open("rb") as source:
            payload = source.read(limits.max_json_bytes + 1)
        if len(payload) > limits.max_json_bytes:
            raise DataError("CSV byte limit exceeded")
        reader = csv.reader(
            io.StringIO(payload.decode(encoding), newline=""),
            delimiter=delimiter,
            strict=True,
        )
        header = next(reader, None)
        if header is None:
            raise DataError("CSV requires a header")
        # Check names/duplicates before reading cells, including header-only files.
        Dataset(header, (), limits=limits)
        for field in schema.fields:
            if field not in header:
                raise DataError("CSV is missing a required column", field=field)

        def rows() -> Iterable[Sequence[object]]:
            for i, raw in enumerate(reader):
                if i >= limits.max_rows:
                    raise DataError("CSV row limit exceeded", row=i)
                if len(raw) != len(header):
                    raise DataError("CSV row width does not match header", row=i)
                result: list[object] = []
                for field, text in zip(header, raw, strict=True):
                    if len(text) > limits.max_string_chars:
                        raise DataError(
                            "CSV field character limit exceeded", row=i, field=field
                        )
                    if text in null_values:
                        result.append(None)
                    else:
                        try:
                            result.append(
                                parse_scalar(text, schema.fields[field].type)
                                if field in schema.fields
                                else text
                            )
                        except (ValueError, ArithmeticError) as exc:
                            raise DataError(
                                "CSV field does not match declared type",
                                row=i,
                                field=field,
                            ) from exc
                yield result

        dataset = Dataset(header, rows(), limits=limits)
        schema.validate(dataset)
        return dataset
    except (
        OSError,
        UnicodeError,
        LookupError,
        csv.Error,
        ValueError,
        TypeError,
    ) as exc:
        raise DataError("unable to read CSV with the supplied options") from exc
