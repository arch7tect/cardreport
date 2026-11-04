"""Normalize an optional pandas DataFrame into an immutable Dataset."""

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Literal

from .._inputs import DataError
from ..data import DEFAULT_LIMITS, DataLimits, Dataset, DatasetSchema
from ..model import DependencyError

if TYPE_CHECKING:
    from pandas import DataFrame


def from_pandas(
    frame: "DataFrame",
    *,
    schema: DatasetSchema,
    index: Literal["error", "drop"] = "error",
    limits: DataLimits = DEFAULT_LIMITS,
) -> Dataset:
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise DependencyError("Install cardreport[pandas] to use from_pandas") from exc
    if not isinstance(frame, pd.DataFrame) or not isinstance(schema, DatasetSchema):
        raise DataError("expected DataFrame and DatasetSchema")
    if index not in ("error", "drop"):
        raise DataError("index must be error or drop")
    if index == "error" and (
        not isinstance(frame.index, pd.RangeIndex)
        or frame.index.start != 0
        or frame.index.stop != len(frame)
        or frame.index.step != 1
        or frame.index.name is not None
    ):
        raise DataError(
            "materialize the index as columns or explicitly use index='drop'"
        )
    columns = list(frame.columns)
    Dataset(columns, (), limits=limits)
    if len(frame) > limits.max_rows:
        raise DataError("DataFrame row limit exceeded")

    def rows() -> Iterable[Sequence[object]]:
        for i, row in enumerate(frame.itertuples(index=False, name=None)):
            converted: list[object] = []
            for field, value in zip(columns, row, strict=True):
                if value is None or value is pd.NA or value is pd.NaT:
                    converted.append(None)
                    continue
                if isinstance(value, pd.Timestamp):
                    if value.nanosecond:
                        raise DataError(
                            "timestamp has sub-microsecond precision",
                            row=i,
                            field=field,
                        )
                    value = value.to_pydatetime()
                elif isinstance(value, (np.integer, np.floating)):
                    value = value.item()
                if isinstance(value, float) and np.isnan(value):
                    value = None
                converted.append(value)
            yield converted

    dataset = Dataset(columns, rows(), limits=limits)
    schema.validate(dataset)
    return dataset
