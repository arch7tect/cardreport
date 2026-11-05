"""Small bounded JSON and scalar parsing helpers for the interchange layer."""

import json
import re
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import cast

from .model import ReportError, ValidationError


class LocatedError(Exception):
    dataset: str | None
    row: int | None
    field: str | None
    template_path: str | None

    def __init__(
        self,
        message: str,
        *,
        dataset: str | None = None,
        row: int | None = None,
        field: str | None = None,
        template_path: str | None = None,
    ) -> None:
        self.dataset, self.row, self.field = dataset, row, field
        self.template_path = template_path
        super().__init__(message)


class DataError(LocatedError, ReportError):
    """Invalid dataset, data transport or adapter input."""


class TemplateError(LocatedError, ValidationError):
    """Invalid presentation definition."""


class BindingError(LocatedError, ValidationError):
    """Data does not satisfy a template's contract."""


def mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("expected an object")
    result: dict[str, object] = {}
    for key, item in cast(Mapping[object, object], value).items():
        if not isinstance(key, str):
            raise ValueError("object keys must be strings")
        result[key] = item
    return result


def array(value: object) -> list[object]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("expected an array")
    return list(cast(list[object] | tuple[object, ...], value))


def name(value: object) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 100:
        raise ValueError("expected a nonempty name up to 100 characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("name must be valid Unicode") from exc
    return value


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise ValueError("nonfinite JSON number")


def load_json(source: str | bytes, max_bytes: int) -> object:
    if not isinstance(source, (str, bytes)):
        raise ValueError("expected JSON text or bytes")
    if len(source) > max_bytes:
        raise ValueError("JSON byte limit exceeded")
    if isinstance(source, str) and len(source.encode("utf-8")) > max_bytes:
        raise ValueError("JSON byte limit exceeded")
    if isinstance(source, bytes):
        source = source.decode("utf-8")
    result: object = json.loads(
        source, object_pairs_hook=_pairs, parse_constant=_constant
    )
    check_tree(result)
    return result


def check_tree(value: object, *, allow_dates: bool = False) -> None:
    # Iterative traversal bounds native trees too, including cycles.
    stack = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if depth > 64 or count > 500_000:
            raise ValueError("input tree depth/node limit exceeded")
        if isinstance(item, Mapping):
            stack.extend((v, depth + 1) for v in mapping(item).values())
        elif isinstance(item, (list, tuple)):
            stack.extend((v, depth + 1) for v in array(item))
        elif allow_dates and type(item) in (date, datetime):
            continue
        elif type(item) not in (str, int, float, bool, type(None)):
            raise ValueError("expected JSON-compatible input")


def plain_tree(value: object) -> object:
    """Normalize mappings after check_tree has bounded depth and rejected cycles."""
    if isinstance(value, Mapping):
        return {key: plain_tree(item) for key, item in mapping(value).items()}
    if isinstance(value, (list, tuple)):
        return [plain_tree(item) for item in array(value)]
    return value


INTEGER = re.compile(r"[+-]?[0-9]+\Z")


def parse_scalar(text: str, kind: str) -> str | int | Decimal | date:
    from ._schema import scalar_pattern

    if kind == "text":
        return text
    if kind == "integer" and INTEGER.fullmatch(text):
        return int(text)
    if kind in ("number", "decimal") and scalar_pattern("decimal").fullmatch(text):
        try:
            return Decimal(text)
        except InvalidOperation:
            pass
    if kind == "date" and scalar_pattern("date").fullmatch(text):
        return date.fromisoformat(text)
    if kind == "datetime" and scalar_pattern("datetime").fullmatch(text):
        # fromisoformat accepts out-of-range offset minutes by normalizing them.
        if text[-1] != "Z" and (int(text[-5:-3]) > 23 or int(text[-2:]) > 59):
            raise ValueError("invalid datetime offset")
        return datetime.fromisoformat(text)
    raise ValueError(f"expected {kind} in the documented lexical format")
