"""Internal JSON chart payload shared by the WeasyPrint producer and worker."""

from collections.abc import Sequence
from typing import Literal, NotRequired, TypedDict


class FormattingSpec(TypedDict):
    decimal: Literal[".", ","]
    group: Literal[",", ".", "'", "space", "none"]
    number_decimals: int
    percent_decimals: int
    currency_decimals: int
    date_format: str | None
    datetime_format: str | None
    locale: str | None


class SvgSeries(TypedDict):
    values: Sequence[float | None]
    value_labels: Sequence[str]
    color: str
    # Bars/funnels do not consume markers; minimal internal specs may omit them.
    marker_sizes: NotRequired[Sequence[float]]


class SvgSpec(TypedDict):
    labels: Sequence[str]
    series: Sequence[SvgSeries]
    horizontal: bool
    show_labels: bool
    font_size: float
    color: str
    text_color: str
    format: str
    # Missing kind retains the original bar default.
    kind: NotRequired[Literal["bar", "line", "funnel"]]
    formatting: NotRequired[FormattingSpec | None]
    compact: NotRequired[bool]
    axes: NotRequired[bool]
    mode: NotRequired[Literal["grouped", "stacked"]]
    colors: NotRequired[Sequence[str]]
    category_labels: NotRequired[bool]
    positions: NotRequired[Sequence[float]]
    fill: NotRequired[Literal["none", "zero"]]
    fill_color: NotRequired[str]
    y_range: NotRequired[Sequence[float]]
    ticks: NotRequired[Sequence[float]]
    tick_labels: NotRequired[Sequence[str]]
    x_range: NotRequired[Sequence[float]]
