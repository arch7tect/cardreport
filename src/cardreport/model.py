"""Public, renderer-independent report components."""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal, Self

if TYPE_CHECKING:
    from .renderers import Renderer
import math
import re


class ReportError(Exception):
    """Base class for report failures."""


class ValidationError(ReportError):
    pass


class LayoutOverflowError(ReportError):
    pass


class UnsupportedFeatureError(ReportError):
    pass


class DependencyError(ReportError):
    pass


class RenderError(ReportError):
    pass


class RenderTimeoutError(RenderError):
    pass


@dataclass(frozen=True)
class Currency:
    code: str


type Number = int | float | Decimal
type Value = Number | str | date | datetime | None
type Format = Literal["number", "integer", "percent", "date"] | Currency
type CardContent = Text | KPI | Table | BarChart | LineChart | Funnel | Row | Column
type Component = CardContent | Card
type Block = Component | PageBreak
type Chart = BarChart | LineChart | Funnel


@dataclass(frozen=True)
class Page:
    size: Literal["A4", "A3", "Letter"] | tuple[float, float] = "A4"
    orientation: Literal["portrait", "landscape"] = "portrait"
    margin_mm: float = 10

    def dimensions(self) -> tuple[float, float]:
        if isinstance(self.size, str):
            sizes = {
                "A4": (210.0, 297.0),
                "A3": (297.0, 420.0),
                "Letter": (215.9, 279.4),
            }
            if self.size not in sizes:
                raise ValidationError(
                    "page.size: use A4, A3, Letter or (width_mm, height_mm)"
                )
            w, h = sizes[self.size]
        else:
            if not isinstance(self.size, (tuple, list)) or len(self.size) != 2:
                raise ValidationError("page.size: expected two dimensions")
            w, h = self.size
            if self.orientation != "portrait":
                raise ValidationError(
                    "page.orientation applies only to named sizes; pass custom width/height explicitly"
                )
        for v in (w, h):
            number(v, "page.size")
            if not 40 <= v <= 1000:
                raise ValidationError("page.size: each dimension must be 40..1000 mm")
        if self.orientation not in ("portrait", "landscape"):
            raise ValidationError("page.orientation: invalid orientation")
        if isinstance(self.size, str) and self.orientation == "landscape":
            w, h = h, w
        number(self.margin_mm, "page.margin_mm")
        if self.margin_mm < 0 or 2 * self.margin_mm >= min(w, h):
            raise ValidationError("page.margin_mm: no usable page area")
        return float(w), float(h)


@dataclass(frozen=True)
class Theme:
    accent: str = "#20a6c4"
    background: str = "#f5f5f5"
    card_background: str = "#ffffff"
    text: str = "#222222"
    gap_mm: float = 4
    padding_mm: float = 4
    font_size_pt: float = 10
    chart_height_mm: float = 60

    @classmethod
    def light(cls) -> Theme:
        return cls()


@dataclass(frozen=True)
class Text:
    text: str
    style: Literal["body", "heading", "caption"] = "body"


@dataclass(frozen=True)
class KPI:
    label: str
    value: Value
    format: Format = "number"
    note: str | None = None


@dataclass(frozen=True)
class Card:
    content: CardContent
    title: str | None = None


@dataclass(frozen=True, init=False)
class Row:
    children: tuple[Component, ...]
    widths: tuple[float, ...] | None
    height_mm: float | None

    def __init__(
        self,
        *children: Component,
        widths: Sequence[float] | None = None,
        height_mm: float | None = None,
    ) -> None:
        object.__setattr__(self, "children", tuple(children))
        object.__setattr__(
            self, "widths", None if widths is None else sequence(widths, "widths")
        )
        object.__setattr__(self, "height_mm", height_mm)


@dataclass(frozen=True, init=False)
class Column:
    children: tuple[Component, ...]
    heights: tuple[float, ...] | None

    def __init__(
        self, *children: Component, heights: Sequence[float] | None = None
    ) -> None:
        object.__setattr__(self, "children", tuple(children))
        object.__setattr__(
            self, "heights", None if heights is None else sequence(heights, "heights")
        )


@dataclass(frozen=True)
class TableColumn:
    key: str
    label: str
    format: Format = "number"
    align: Literal["left", "center", "right"] = "left"
    width: float | None = None


@dataclass(frozen=True)
class Table:
    columns: Sequence[TableColumn]
    rows: Sequence[Mapping[str, Value]]
    empty_text: str = "No data"

    def __post_init__(self) -> None:
        object.__setattr__(self, "columns", sequence(self.columns, "table.columns"))
        rows = sequence(self.rows, "table.rows")
        if any(not isinstance(r, Mapping) for r in rows):
            raise ValidationError("table.rows: expected mappings")
        object.__setattr__(self, "rows", tuple(MappingProxyType(dict(r)) for r in rows))


@dataclass(frozen=True)
class BarChart:
    labels: Sequence[str]
    values: Sequence[Number] | None = None
    series: Mapping[str, Sequence[Number]] | None = None
    orientation: Literal["vertical", "horizontal"] = "vertical"
    mode: Literal["grouped", "stacked"] = "grouped"
    show_labels: bool = False
    legend: bool = True
    value_format: Format = "number"

    def __post_init__(self) -> None:
        freeze_chart(self, "labels")


@dataclass(frozen=True)
class LineChart:
    x: Sequence[str | date | datetime]
    values: Sequence[Number | None] | None = None
    series: Mapping[str, Sequence[Number | None]] | None = None
    x_kind: Literal["category", "date"] = "category"
    legend: bool = True
    value_format: Format = "number"

    def __post_init__(self) -> None:
        freeze_chart(self, "x")


@dataclass(frozen=True)
class Funnel:
    labels: Sequence[str]
    values: Sequence[Number]
    show_labels: bool = True
    value_format: Format = "number"

    def __post_init__(self) -> None:
        object.__setattr__(self, "labels", sequence(self.labels, "labels"))
        object.__setattr__(self, "values", sequence(self.values, "values"))


@dataclass(frozen=True)
class PageBreak:
    pass


def sequence[T](value: Sequence[T], path: str) -> tuple[T, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError(f"{path}: expected a sequence, not scalar text")
    return tuple(value)


def freeze_chart(obj: BarChart | LineChart, labels: str) -> None:
    object.__setattr__(obj, labels, sequence(getattr(obj, labels), labels))
    if obj.values is not None:
        object.__setattr__(obj, "values", sequence(obj.values, "values"))
    if obj.series is not None:
        if not isinstance(obj.series, Mapping):
            raise ValidationError("series: expected a mapping")
        object.__setattr__(
            obj,
            "series",
            MappingProxyType({k: sequence(v, "series") for k, v in obj.series.items()}),
        )


def number(v: object, path: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float, Decimal)):
        raise ValidationError(f"{path}: expected a finite number")
    try:
        f = float(v)
    except (OverflowError, ValueError):
        raise ValidationError(f"{path}: expected a finite number") from None
    if not math.isfinite(f) or abs(f) > 1e15:
        raise ValidationError(f"{path}: number must be finite and within +/-1e15")
    return f


def check_format(fmt: object, path: str) -> None:
    if isinstance(fmt, Currency):
        if not isinstance(fmt.code, str) or not re.fullmatch(r"[A-Z]{3}", fmt.code):
            raise ValidationError(
                f"{path}: currency requires a three-letter uppercase code"
            )
    elif fmt not in ("number", "integer", "percent", "date"):
        raise ValidationError(f"{path}: unsupported format")


def format_value(v: object, fmt: Format = "number") -> str:
    check_format(fmt, "format")
    if v is None:
        return "—"
    if isinstance(v, str):
        return v
    if isinstance(v, datetime):
        if v.utcoffset() is None:
            raise ValidationError("value: naive datetime is unsupported")
        normalized = v.astimezone(UTC)
        return (
            normalized.date().isoformat() if fmt == "date" else normalized.isoformat()
        )
    if isinstance(v, date):
        return v.isoformat()
    number(v, "value")
    if fmt == "date":
        raise ValidationError("value: date format requires a date")
    n = Decimal(str(v))
    digits = 2
    if fmt == "integer":
        digits = 0
    if fmt == "percent":
        n *= 100
        digits = 1
    try:
        n = n.quantize(Decimal(10) ** -digits, rounding=ROUND_HALF_EVEN)
    except InvalidOperation:
        raise ValidationError("value: cannot format number") from None
    if not n:
        n = abs(n)
    result = f"{n:,.{digits}f}"
    if fmt == "number":
        result = result.rstrip("0").rstrip(".") if "." in result else result
    if fmt == "percent":
        result += "%"
    if isinstance(fmt, Currency):
        result = fmt.code + " " + result
    return result


class Report:
    def __init__(
        self,
        title: str = "",
        *,
        subtitle: str = "",
        mode: Literal["dashboard", "flow"] = "dashboard",
        page: Page | None = None,
        theme: Theme | None = None,
    ) -> None:
        self.title, self.subtitle, self.mode = title, subtitle, mode
        self.page, self.theme = (
            page if page is not None else Page(),
            theme if theme is not None else Theme(),
        )
        if not isinstance(self.page, Page) or not isinstance(self.theme, Theme):
            raise ValidationError("page and theme must be Page and Theme objects")
        self._blocks: list[Block] = []

    def add(self, block: Block) -> Self:
        self._blocks.append(block)
        return self

    @property
    def blocks(self) -> tuple[Block, ...]:
        return tuple(self._blocks)

    def validate(self) -> None:
        from .validation import validate_report

        validate_report(self)

    def row(
        self,
        *children: Component,
        widths: Sequence[float] | None = None,
        height_mm: float | None = None,
    ) -> Self:
        return self.add(Row(*children, widths=widths, height_mm=height_mm))

    def new_page(self) -> Self:
        return self.add(PageBreak())

    def to_html(self, *, renderer: Renderer | None = None) -> str:
        from .renderers import ChromiumRenderer
        from .validation import validate_report

        doc = validate_report(self)
        return (renderer if renderer is not None else ChromiumRenderer()).render_html(
            doc
        )

    def write_html(
        self,
        path: str | Path,
        *,
        overwrite: bool = False,
        renderer: Renderer | None = None,
    ) -> Path:
        from .output import publish

        return publish(path, self.to_html(renderer=renderer).encode("utf-8"), overwrite)

    def to_pdf(self, *, timeout: float = 30, renderer: Renderer | None = None) -> bytes:
        from .renderers import ChromiumRenderer
        from .validation import validate_report, validate_timeout

        validate_timeout(timeout)
        deadline = time.monotonic() + timeout
        doc = validate_report(self)
        if time.monotonic() >= deadline:
            raise RenderTimeoutError("Report validation exceeded export deadline")
        return (renderer if renderer is not None else ChromiumRenderer()).render_pdf(
            doc, deadline=deadline
        )

    def write_pdf(
        self,
        path: str | Path,
        *,
        overwrite: bool = False,
        timeout: float = 30,
        renderer: Renderer | None = None,
    ) -> Path:
        from .output import publish

        return publish(path, self.to_pdf(timeout=timeout, renderer=renderer), overwrite)
