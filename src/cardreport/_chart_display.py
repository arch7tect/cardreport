"""Small shared display rules; renderer-specific geometry stays in each engine."""

from collections.abc import Sequence
from datetime import UTC, datetime

from .document import ChartData
from .model import BarChart, Chart, LineChart, Theme, ValidationError

PALETTE = (
    "#20a6c4",
    "#4263eb",
    "#f59f00",
    "#7950f2",
    "#e8590c",
    "#2f9e44",
    "#c2255c",
    "#495057",
)


def compact(obj: Chart, data: ChartData) -> bool:
    return (
        isinstance(obj, LineChart)
        and not obj.axes
        and not (obj.legend and len(data.series) > 1)
    )


def empty(obj: Chart, data: ChartData) -> bool:
    return not data.labels or (
        isinstance(obj, LineChart)
        and not obj.axes
        and all(v is None for s in data.series for v in s.values)
    )


def category_colors(
    obj: BarChart, theme: Theme, count: int, path: str = "chart"
) -> tuple[str, ...]:
    if obj.color_by != "category":
        return ()
    colors = tuple(dict.fromkeys(c.lower() for c in (theme.accent, *PALETTE)))
    if count > len(colors):
        raise ValidationError(
            f"{path}.color_by: {count} categories exceed the {len(colors)} distinct theme colors"
        )
    return colors[:count]


def date_instants(labels: Sequence[str]) -> tuple[datetime, ...]:
    values = (datetime.fromisoformat(v) for v in labels)
    return tuple(
        v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC) for v in values
    )


def date_positions(labels: Sequence[str]) -> tuple[float, ...]:
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    return tuple((v - epoch).total_seconds() / 86400 for v in date_instants(labels))


def line_x_range(positions: Sequence[float], *, dates: bool) -> tuple[float, float]:
    if not positions:
        return (-0.5, 0.5)
    lo, hi = min(positions), max(positions)
    pad = (hi - lo) * 0.04
    if not dates or hi == lo:
        pad = max(pad, 0.5)
    return lo - pad, hi + pad


def series_colors(theme: Theme) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(c.lower() for c in (theme.accent, *PALETTE[1:], PALETTE[0]))
    )


def segments(values: Sequence[float | None]) -> list[list[int]]:
    result: list[list[int]] = []
    for i, value in enumerate(values):
        if value is None:
            continue
        if i == 0 or values[i - 1] is None:
            result.append([])
        result[-1].append(i)
    return result


def marker_sizes(values: Sequence[float | None], enabled: bool) -> list[int]:
    return [
        6
        if v is not None
        and (
            enabled
            or (
                (i == 0 or values[i - 1] is None)
                and (i == len(values) - 1 or values[i + 1] is None)
            )
        )
        else 0
        for i, v in enumerate(values)
    ]


def line_range(data: ChartData, fill: str) -> tuple[float, float]:
    values = [v for s in data.series for v in s.values if v is not None]
    if not values:
        return (-1, 1)
    if fill == "zero":
        values.append(0)
    lo, hi = min(values), max(values)
    pad = (hi - lo) * 0.08 if hi > lo else max(abs(lo) * 0.08, 1)
    return lo - pad, hi + pad


def fill_color(accent: str, background: str) -> str:
    return "#" + "".join(
        f"{round(int(accent[i : i + 2], 16) * 0.22 + int(background[i : i + 2], 16) * 0.78):02x}"
        for i in (1, 3, 5)
    )
