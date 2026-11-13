"""Validate interchange structure against the same schemas shipped to editors."""

import json
import re
from functools import cache
from typing import Any, Literal, NamedTuple, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from referencing import Registry

from ._inputs import DataError, TemplateError
from .schemas import json_schema


@cache
def _validator(kind: Literal["template", "data"]) -> Draft202012Validator:
    # An empty registry never retrieves remote references. Input $schema is metadata.
    return Draft202012Validator(json.loads(json_schema(kind)), registry=Registry())


def validate_structure(kind: Literal["template", "data"], value: object) -> None:
    # Unknown inputs intentionally reach jsonschema for validation, not coercion.
    error = next(_validator(kind).iter_errors(cast(Any, value)), None)
    if error is None:
        return
    error = best_match([error]) or error
    path = tuple(error.absolute_path)
    # Do not echo jsonschema messages: they can include entire datasets or labels.
    message = f"invalid {kind} structure ({error.validator})"
    if kind == "template":
        location = "".join(
            f"[{part}]" if isinstance(part, int) else ("." if i else "") + part
            for i, part in enumerate(path)
        )
        raise TemplateError(message, template_path=location or None)
    dataset = path[1] if len(path) > 1 and path[0] == "datasets" else None
    row = path[3] if len(path) > 3 and path[2] == "rows" else None
    field = path[4] if len(path) > 4 and path[2] == "rows" else None
    raise DataError(message, dataset=dataset, row=row, field=field)


@cache
def scalar_pattern(kind: str) -> re.Pattern[str]:
    """Share the transport's lexical rules with the CSV scalar decoder."""
    schema = _validator("data").schema
    assert isinstance(schema, dict)
    return re.compile(schema["$defs"][kind]["pattern"])


class DataShape(NamedTuple):
    root_keys: frozenset[str]
    root_required: frozenset[str]
    format: str
    dataset_keys: frozenset[str]
    cell_keys: frozenset[str]
    cell_kinds: frozenset[str]


@cache
def data_shape() -> DataShape:
    """Read the fixed data envelope, not a general interpretation of JSON Schema."""
    schema = _validator("data").schema
    assert isinstance(schema, dict)
    dataset = schema["$defs"]["dataset"]
    cell = schema["$defs"]["typedCell"]
    assert set(dataset["required"]) == set(dataset["properties"])
    assert set(cell["required"]) == set(cell["properties"])
    return DataShape(
        frozenset(schema["properties"]),
        frozenset(schema["required"]),
        schema["properties"]["format"]["const"],
        frozenset(dataset["properties"]),
        frozenset(cell["properties"]),
        frozenset(cell["properties"]["$type"]["enum"]),
    )
