"""Immutable named-table inputs, schemas and lossless scalar JSON transport."""

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from typing import Literal, cast

from ._inputs import (
    DataError,
    array,
    check_tree,
    load_json,
    mapping,
    name,
    parse_scalar,
)
from ._schema import validate_structure
from .model import ValidationError, Value, number

type FieldType = Literal["text", "integer", "number", "decimal", "date", "datetime"]


@dataclass(frozen=True)
class DataLimits:
    max_rows: int = 2000
    max_columns: int = 100
    max_datasets: int = 32
    max_cells: int = 100000
    max_string_chars: int = 10000
    max_text_bytes: int = 16 * 1024 * 1024
    max_json_bytes: int = 16 * 1024 * 1024

    def __post_init__(self) -> None:
        caps = (2000, 100, 32, 100000, 10000, 16 * 1024 * 1024, 16 * 1024 * 1024)
        for key, cap in zip(self.__dataclass_fields__, caps, strict=True):
            value = getattr(self, key)
            if type(value) is not int or not 1 <= value <= cap:
                raise DataError(f"limits.{key}: expected integer in 1..{cap}")


DEFAULT_LIMITS = DataLimits()


def cell(value: object, limits: DataLimits = DEFAULT_LIMITS) -> Value:
    if value is None:
        return None
    if type(value) is str:
        if len(value) > limits.max_string_chars:
            raise DataError("cell text limit exceeded")
        try:
            value.encode("utf-8")
        except UnicodeError as exc:
            raise DataError("cell text must be valid Unicode") from exc
        return value
    if type(value) in (int, float, Decimal):
        assert isinstance(value, (int, float, Decimal))
        if isinstance(value, Decimal):
            if (
                not value.is_finite()
                or len(value.as_tuple().digits) > limits.max_string_chars
            ):
                raise DataError("invalid or excessive decimal coefficient")
        try:
            number(value, "cell")
        except ValidationError as exc:
            raise DataError("cell must be finite and within +/-1e15") from exc
        return value
    if type(value) is datetime:
        try:
            offset = value.utcoffset()
            if offset is None or offset.total_seconds() % 60:
                raise DataError("datetime requires a whole-minute UTC offset")
            # Snapshot a potentially stateful timezone before checking UTC range.
            result = value.replace(tzinfo=timezone(offset))
            result.astimezone(UTC)
            return result
        except (ValueError, TypeError, OverflowError) as exc:
            raise DataError("invalid datetime offset or UTC range") from exc
    if type(value) is date:
        return value
    raise DataError("unsupported cell type")


@dataclass(frozen=True, init=False)
class Dataset:
    columns: tuple[str, ...]
    rows: tuple[tuple[Value, ...], ...] = field(repr=False)

    def __init__(
        self,
        columns: Sequence[str],
        rows: Iterable[Sequence[object]],
        *,
        limits: DataLimits = DEFAULT_LIMITS,
    ) -> None:
        try:
            if (
                not isinstance(columns, Sequence)
                or isinstance(columns, (str, bytes, bytearray))
                or len(columns) > limits.max_columns
            ):
                raise ValueError("invalid column sequence or column limit exceeded")
            cols = tuple(name(c) for c in columns)
            if len(set(cols)) != len(cols):
                raise ValueError("duplicate column names")
        except (ValueError, TypeError) as exc:
            raise DataError(str(exc)) from exc
        result: list[tuple[Value, ...]] = []
        text_bytes = 0
        for i, row in enumerate(rows):
            if i >= limits.max_rows or (i + 1) * len(cols) > limits.max_cells:
                raise DataError("dataset row/cell limit exceeded", row=i)
            if (
                not isinstance(row, Sequence)
                or isinstance(row, (str, bytes, bytearray))
                or len(row) != len(cols)
            ):
                raise DataError("row width does not match columns", row=i)
            converted: list[Value] = []
            for col, value in zip(cols, row, strict=True):
                try:
                    v = cell(value, limits)
                except DataError as exc:
                    raise DataError(str(exc), row=i, field=col) from exc
                if isinstance(v, str):
                    text_bytes += len(v.encode("utf-8"))
                if text_bytes > limits.max_text_bytes:
                    raise DataError(
                        "dataset text byte limit exceeded", row=i, field=col
                    )
                converted.append(v)
            result.append(tuple(converted))
        object.__setattr__(self, "columns", cols)
        object.__setattr__(self, "rows", tuple(result))

    @classmethod
    def from_records(
        cls,
        columns: Sequence[str],
        records: Iterable[Sequence[object]],
        *,
        limits: DataLimits = DEFAULT_LIMITS,
    ) -> "Dataset":
        return cls(columns, records, limits=limits)

    @classmethod
    def from_dicts(
        cls,
        rows: Iterable[Mapping[str, object]],
        *,
        columns: Sequence[str] | None = None,
        limits: DataLimits = DEFAULT_LIMITS,
    ) -> "Dataset":
        iterator = iter(rows)
        sentinel = object()
        first = next(iterator, sentinel)
        if first is sentinel:
            if columns is None:
                raise DataError("empty records require explicit columns")
            return cls(columns, (), limits=limits)
        if not isinstance(first, Mapping):
            raise DataError("expected row mappings")
        cols = cls(
            tuple(first) if columns is None else columns, (), limits=limits
        ).columns

        def records() -> Iterable[Sequence[object]]:
            from itertools import chain

            for i, row in enumerate(chain((first,), iterator)):
                if not isinstance(row, Mapping) or set(row) != set(cols):
                    raise DataError("row keys do not match columns", row=i)
                yield tuple(row[key] for key in cols)

        return cls(cols, records(), limits=limits)

    @classmethod
    def single(
        cls, values: Mapping[str, object], *, limits: DataLimits = DEFAULT_LIMITS
    ) -> "Dataset":
        return cls.from_dicts((values,), limits=limits)


@dataclass(frozen=True)
class FieldSpec:
    type: FieldType
    nullable: bool = False

    def __post_init__(self) -> None:
        if self.type not in (
            "text",
            "integer",
            "number",
            "decimal",
            "date",
            "datetime",
        ):
            raise DataError("unknown field type")
        if type(self.nullable) is not bool:
            raise DataError("nullable must be boolean")

    def accepts(self, value: Value) -> bool:
        if value is None:
            return self.nullable
        accepted = {
            "text": (str,),
            "integer": (int,),
            "number": (int, float, Decimal),
            "decimal": (int, Decimal),
            "date": (date,),
            "datetime": (datetime,),
        }
        return type(value) in accepted[self.type]


@dataclass(frozen=True, eq=False)
class DatasetSchema:
    fields: Mapping[str, FieldSpec]
    cardinality: Literal["one", "many"] = "many"

    def __post_init__(self) -> None:
        if not isinstance(self.fields, Mapping):
            raise DataError("schema fields must be a mapping")
        if self.cardinality not in ("one", "many"):
            raise DataError("cardinality must be one or many")
        if len(self.fields) > DEFAULT_LIMITS.max_columns:
            raise DataError("schema column limit exceeded")
        for key, spec in self.fields.items():
            try:
                name(key)
            except ValueError as exc:
                raise DataError(str(exc)) from exc
            if not isinstance(spec, FieldSpec):
                raise DataError("schema fields require FieldSpec")
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))

    def validate(self, dataset: Dataset) -> None:
        if not isinstance(dataset, Dataset):
            raise DataError("expected Dataset")
        if self.cardinality == "one" and len(dataset.rows) != 1:
            raise DataError("dataset requires exactly one row")
        for key, spec in self.fields.items():
            if key not in dataset.columns:
                raise DataError("missing required column", field=key)
            index = dataset.columns.index(key)
            for i, row in enumerate(dataset.rows):
                if not spec.accepts(row[index]):
                    raise DataError(
                        f"expected {spec.type}, nullable={spec.nullable}",
                        row=i,
                        field=key,
                    )


def validate_bundle(
    data: Mapping[str, Dataset], limits: DataLimits = DEFAULT_LIMITS
) -> None:
    if not isinstance(data, Mapping):
        raise DataError("expected a mapping of named datasets")
    if len(data) > limits.max_datasets:
        raise DataError("dataset count limit exceeded")
    cells = text_bytes = 0
    for key, ds in data.items():
        try:
            name(key)
        except ValueError as exc:
            raise DataError(str(exc)) from exc
        if not isinstance(ds, Dataset):
            raise DataError("expected Dataset", dataset=key)
        if len(ds.rows) > limits.max_rows or len(ds.columns) > limits.max_columns:
            raise DataError("dataset row/column limit exceeded", dataset=key)
        cells += len(ds.rows) * len(ds.columns)
        for i, row in enumerate(ds.rows):
            for col, value in zip(ds.columns, row, strict=True):
                try:
                    cell(value, limits)
                except DataError as exc:
                    raise DataError(str(exc), dataset=key, row=i, field=col) from exc
                if isinstance(value, str):
                    text_bytes += len(value.encode("utf-8"))
        if cells > limits.max_cells or text_bytes > limits.max_text_bytes:
            raise DataError("bundle cell/text limit exceeded", dataset=key)


def _decode(value: object) -> Value:
    if isinstance(value, dict):
        obj = mapping(value)
        kind, text = obj["$type"], obj["value"]
        try:
            parsed = parse_scalar(cast(str, text), cast(str, kind))
        except ValueError as exc:
            raise ValueError("invalid typed cell lexical format") from exc
        return cell(parsed)
    return cell(value)


def _transport_dates(value: object) -> object:
    if isinstance(value, dict):
        return {k: _transport_dates(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_transport_dates(v) for v in value]
    if type(value) in (date, datetime):
        return _encode(cast(date, value))
    return value


def _bundle_from_tree(tree: object, limits: DataLimits) -> dict[str, Dataset]:
    validate_structure("data", tree)
    root = mapping(tree)
    raw = mapping(root["datasets"])
    if len(raw) > limits.max_datasets:
        raise ValueError("dataset count limit exceeded")
    result: dict[str, Dataset] = {}
    for key, value in raw.items():

        def rows(raw_rows: object) -> Iterable[Mapping[str, object]]:
            for i, row in enumerate(array(raw_rows)):
                try:
                    raw_row = mapping(row)
                except ValueError as exc:
                    raise DataError(str(exc), row=i) from exc
                decoded: dict[str, object] = {}
                for col, v in raw_row.items():
                    try:
                        decoded[col] = _decode(v)
                    except (ValueError, TypeError, DataError) as exc:
                        raise DataError(str(exc), row=i, field=col) from exc
                yield decoded

        try:
            ds = mapping(value)
            columns = tuple(name(c) for c in array(ds["columns"]))
            result[key] = Dataset.from_dicts(
                rows(ds["rows"]), columns=columns, limits=limits
            )
        except DataError as exc:
            raise DataError(
                str(exc), dataset=key, row=exc.row, field=exc.field
            ) from exc
        except (ValueError, TypeError) as exc:
            raise DataError(str(exc), dataset=key) from exc
    validate_bundle(result, limits)
    return result


def datasets_from_json(
    source: str | bytes, *, limits: DataLimits = DEFAULT_LIMITS
) -> dict[str, Dataset]:
    try:
        return _bundle_from_tree(load_json(source, limits.max_json_bytes), limits)
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise DataError("invalid data JSON") from exc


def datasets_from_yaml(
    source: str | bytes, *, limits: DataLimits = DEFAULT_LIMITS
) -> dict[str, Dataset]:
    from ._yaml import load_yaml

    try:
        tree = load_yaml(source, limits.max_json_bytes)
        check_tree(tree, allow_dates=True)
        return _bundle_from_tree(_transport_dates(tree), limits)
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise DataError("invalid data YAML") from exc


def _encode(value: Value) -> object:
    if isinstance(value, datetime):
        return {"$type": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"$type": "date", "value": value.isoformat()}
    if isinstance(value, Decimal):
        return {"$type": "decimal", "value": str(value)}
    return value


def _bundle_to_tree(
    data: Mapping[str, Dataset], limits: DataLimits
) -> dict[str, object]:
    validate_bundle(data, limits)
    return {
        "format": "cardreport.data/1",
        "datasets": {
            key: {
                "columns": list(ds.columns),
                "rows": [
                    {col: _encode(v) for col, v in zip(ds.columns, row, strict=True)}
                    for row in ds.rows
                ],
            }
            for key, ds in data.items()
        },
    }


def datasets_to_json(
    data: Mapping[str, Dataset], *, limits: DataLimits = DEFAULT_LIMITS
) -> str:
    result = json.dumps(
        _bundle_to_tree(data, limits), ensure_ascii=False, allow_nan=False
    )
    if len(result.encode("utf-8")) > limits.max_json_bytes:
        raise DataError("data JSON byte limit exceeded")
    return result


def datasets_to_yaml(
    data: Mapping[str, Dataset], *, limits: DataLimits = DEFAULT_LIMITS
) -> str:
    from ._yaml import dump_yaml

    try:
        return dump_yaml(_bundle_to_tree(data, limits), limits.max_json_bytes)
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise DataError("unable to serialize data YAML") from exc
