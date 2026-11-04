"""Engine-independent validation. Geometry is checked by each renderer."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from functools import lru_cache
from importlib.resources import files
from io import BytesIO
from types import MappingProxyType

from fontTools.ttLib import TTFont

from .document import ChartData, ChartSeries, ReportDocument
from .formatting import Formatting, date_locale, empty_label, language_tag
from .model import (
    KPI,
    BarChart,
    Card,
    Chart,
    Column,
    Format,
    Funnel,
    LineChart,
    Number,
    Page,
    PageBreak,
    Report,
    Row,
    Table,
    TableColumn,
    Text,
    ValidationError,
    check_format,
    format_value,
    number,
)

MAX_BLOCKS, MAX_ROWS, MAX_POINTS, MAX_DEPTH, MAX_PAGES = 500, 2000, 500, 12, 100
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


@lru_cache(maxsize=1)
def glyphs() -> frozenset[int]:
    common: set[int] | None = None
    for name in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        with TTFont(
            BytesIO(files("cardreport").joinpath("assets", name).read_bytes())
        ) as font:
            available = set(font.getBestCmap())
            common = available if common is None else common & available
    return frozenset(common or ())


def text(value: object, path: str, limit: int = 10000) -> str:
    if not isinstance(value, str) or len(value) > limit:
        raise ValidationError(f"{path}: expected text up to {limit} characters")
    if any(ord(c) not in glyphs() and c not in "\n\t\r" for c in value):
        raise ValidationError(f"{path}: text includes an unsupported font glyph")
    return value


def weights(values: Sequence[float] | None, n: int, path: str) -> list[float]:
    if values is None:
        return [1.0] * n
    if len(values) != n:
        raise ValidationError(f"{path}: weight count must match children")
    result = [number(v, path) for v in values]
    if any(v <= 0 or v > 10000 for v in result):
        raise ValidationError(f"{path}: weights must be positive and <=10000")
    return result


def formatted(
    value: object,
    fmt: Format,
    path: str,
    formatting: Formatting | None = None,
    language: str = "en",
) -> str:
    try:
        result = format_value(value, fmt, formatting, language)
    except ValidationError as exc:
        raise ValidationError(f"{path}: {exc}") from None
    return text(result, path)


def chart_labels(obj: Chart) -> list[str]:
    labels = obj.x if isinstance(obj, LineChart) else obj.labels
    result = []
    for value in labels:
        if isinstance(value, datetime):
            value = value.astimezone(UTC)
        result.append(value.isoformat() if isinstance(value, date) else value)
    return result


def validate_chart(obj: Chart, path: str) -> None:
    check_format(obj.value_format, path + ".value_format")
    if obj.value_format == "date":
        raise ValidationError(f"{path}: chart values must use a numeric format")
    if isinstance(obj, LineChart) and obj.x_kind not in ("category", "date"):
        raise ValidationError(f"{path}: invalid x_kind")
    if isinstance(obj, BarChart) and (
        obj.orientation not in ("vertical", "horizontal")
        or obj.mode not in ("grouped", "stacked")
    ):
        raise ValidationError(f"{path}: invalid bar orientation/mode")
    for option in ("show_labels", "legend"):
        if hasattr(obj, option) and not isinstance(getattr(obj, option), bool):
            raise ValidationError(f"{path}.{option}: expected boolean")
    labels = obj.x if isinstance(obj, LineChart) else obj.labels
    if len(labels) > MAX_POINTS:
        raise ValidationError(f"{path}: maximum {MAX_POINTS} chart points")
    is_date = isinstance(obj, LineChart) and obj.x_kind == "date"
    for value in labels:
        if is_date or (isinstance(obj, BarChart) and isinstance(value, date)):
            if not isinstance(value, date):
                raise ValidationError(f"{path}: date axis requires dates")
            if isinstance(value, datetime) and value.utcoffset() is None:
                raise ValidationError(f"{path}: naive datetime")
        else:
            text(value, path + ".labels", 200)
    x = chart_labels(obj)
    identities = (
        [
            (
                "datetime"
                if isinstance(v, datetime)
                else "date"
                if isinstance(v, date)
                else "text",
                label,
            )
            for v, label in zip(labels, x, strict=True)
        ]
        if isinstance(obj, BarChart)
        else [("", label) for label in x]
    )
    if len(set(identities)) != len(x):
        raise ValidationError(f"{path}: duplicate chart categories/dates")
    if not is_date and len(x) > 30:
        raise ValidationError(
            f"{path}: at most 30 categories; use a date axis for longer lines"
        )
    series: Mapping[str, Sequence[Number | None]] | None
    if isinstance(obj, Funnel):
        series = {"": obj.values}
    else:
        if (obj.values is None) == (obj.series is None):
            raise ValidationError(f"{path}: provide exactly one of values or series")
        series = {"": obj.values} if obj.values is not None else obj.series
    if not series or len(series) > 8:
        raise ValidationError(f"{path}: 1..8 series required")
    for name, values in series.items():
        text(name, path + ".series", 100)
        if len(values) != len(x):
            raise ValidationError(f"{path}: series length differs from categories")
        for v in values:
            if v is None and isinstance(obj, LineChart):
                continue
            n = number(v, path + ".values")
            if isinstance(obj, Funnel) and n < 0:
                raise ValidationError(f"{path}: funnel cannot contain negatives")


def normalize_chart(
    obj: Chart, path: str, formatting: Formatting | None = None, language: str = "en"
) -> ChartData:
    validate_chart(obj, path)
    series: Mapping[str, Sequence[Number | None]] | None
    if isinstance(obj, Funnel):
        series = {"": obj.values}
    else:
        series = {"": obj.values} if obj.values is not None else obj.series
    assert series is not None
    tick_values: tuple[str, ...] = ()
    tick_labels: tuple[str, ...] = ()
    if isinstance(obj, LineChart) and obj.x_kind == "date" and formatting is not None:
        coordinates = chart_labels(obj)
        ordered = sorted(range(len(coordinates)), key=lambda i: coordinates[i])
        count = min(6, len(ordered))
        indices = [
            ordered[round(i * (len(ordered) - 1) / max(1, count - 1))]
            for i in range(count)
        ]
        tick_values = tuple(coordinates[i] for i in indices)
        tick_labels = tuple(
            formatted(obj.x[i], "number", path + ".ticks", formatting, language)
            for i in indices
        )
    category_values = tuple(chart_labels(obj))
    category_labels: tuple[str, ...] = ()
    if isinstance(obj, BarChart) and any(isinstance(v, date) for v in obj.labels):
        category_labels = tuple(
            text(
                formatted(v, "number", path + ".labels", formatting, language),
                path + ".labels",
                200,
            )
            for v in obj.labels
        )
        # Positional category keys prevent equal display text from merging bars.
        category_values = tuple(str(i) for i in range(len(obj.labels)))
    return ChartData(
        category_values,
        tuple(
            ChartSeries(
                name,
                tuple(None if v is None else number(v, path) for v in values),
                tuple(
                    formatted(
                        v, obj.value_format, path + ".values", formatting, language
                    )
                    for v in values
                ),
            )
            for name, values in series.items()
        ),
        tick_values,
        tick_labels,
        category_labels,
    )


def validate_timeout(timeout: float) -> None:
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 0 < timeout <= 300
    ):
        raise ValidationError("timeout: expected seconds in (0, 300]")


def validate_report(report: Report) -> ReportDocument:
    report.page.dimensions()
    language = language_tag(report.language)
    formatting = report.formatting
    if formatting is not None:
        if not isinstance(formatting, Formatting):
            raise ValidationError("formatting: expected Formatting")
        if (
            formatting.date_format is not None
            or formatting.datetime_format is not None
            or formatting.locale is not None
        ):
            try:
                date_locale(formatting.locale or language)
            except ValidationError as exc:
                path = (
                    "formatting.locale" if formatting.locale is not None else "language"
                )
                raise ValidationError(
                    f"{path}: no date locale data for language"
                ) from exc
    empty = text(
        empty_label(language) if report.empty_text is None else report.empty_text,
        "empty_text",
        500,
    )
    if report.mode not in ("dashboard", "flow"):
        raise ValidationError("mode: use dashboard or flow")
    theme = report.theme
    for key in ("accent", "background", "card_background", "text"):
        if not isinstance(getattr(theme, key), str) or not re.fullmatch(
            r"#[0-9a-fA-F]{6}", getattr(theme, key)
        ):
            raise ValidationError(f"theme.{key}: expected #RRGGBB")
    for key, lo, hi in [
        ("gap_mm", 0, 20),
        ("padding_mm", 0, 20),
        ("font_size_pt", 9, 24),
        ("chart_height_mm", 35, 200),
    ]:
        if not lo <= number(getattr(theme, key), f"theme.{key}") <= hi:
            raise ValidationError(f"theme.{key}: outside {lo}..{hi}")
    text(report.title, "title", 500)
    text(report.subtitle, "subtitle", 1000)
    charts: dict[str, ChartData] = {}
    blocks = report.blocks
    seen: set[int] = set()
    count = cells = 0

    def node(
        obj: object,
        path: str,
        depth: int = 0,
        definite: bool = False,
        top: bool = False,
    ) -> None:
        nonlocal count, cells
        count += 1
        if count > MAX_BLOCKS or depth > MAX_DEPTH:
            raise ValidationError(f"{path}: report nesting/block limit exceeded")
        if id(obj) in seen:
            raise ValidationError(f"{path}: cyclic layout")
        seen.add(id(obj))
        try:
            if isinstance(obj, PageBreak):
                if not top:
                    raise ValidationError(f"{path}: PageBreak must be top-level")
            elif isinstance(obj, Card):
                if isinstance(obj.content, Card):
                    raise ValidationError(f"{path}: Card cannot directly contain Card")
                if obj.title is not None:
                    text(obj.title, path + ".title", 500)
                node(obj.content, path + ".content", depth + 1, definite)
            elif isinstance(obj, (Row, Column)):
                if not obj.children:
                    raise ValidationError(f"{path}: empty layout")
                fixed = definite
                if isinstance(obj, Row):
                    weights(obj.widths, len(obj.children), path + ".widths")
                    if obj.height_mm is not None:
                        if not 1 <= number(obj.height_mm, path + ".height_mm") <= 1000:
                            raise ValidationError(f"{path}: height outside 1..1000 mm")
                        fixed = True
                elif obj.heights is not None:
                    if not definite:
                        raise ValidationError(
                            f"{path}: weighted Column requires a definite parent height"
                        )
                    weights(obj.heights, len(obj.children), path + ".heights")
                else:
                    fixed = False
                for i, child in enumerate(obj.children):
                    node(child, f"{path}.{i}", depth + 1, fixed)
            elif isinstance(obj, Text):
                if obj.style not in ("body", "heading", "caption"):
                    raise ValidationError(f"{path}: invalid text style")
                text(obj.text, path)
            elif isinstance(obj, KPI):
                text(obj.label, path + ".label", 500)
                formatted(obj.value, obj.format, path + ".value", formatting, language)
                if obj.note is not None:
                    text(obj.note, path + ".note", 500)
            elif isinstance(obj, Table):
                if not 1 <= len(obj.columns) <= 20 or len(obj.rows) > MAX_ROWS:
                    raise ValidationError(
                        f"{path}: table limited to 20 columns and {MAX_ROWS} rows"
                    )
                cells += len(obj.columns) * len(obj.rows)
                if cells > 20000:
                    raise ValidationError(f"{path}: report exceeds 20000 table cells")
                keys: list[str] = []
                for col in obj.columns:
                    if not isinstance(col, TableColumn):
                        raise ValidationError(f"{path}: invalid column")
                    keys.append(text(col.key, path + ".key", 100))
                    text(col.label, path + ".heading", 500)
                    check_format(col.format, path + ".format")
                    if col.align not in ("left", "center", "right"):
                        raise ValidationError(f"{path}: invalid alignment")
                    if (
                        col.width is not None
                        and number(col.width, path + ".width") <= 0
                    ):
                        raise ValidationError(f"{path}: column width must be positive")
                if len(keys) != len(set(keys)):
                    raise ValidationError(f"{path}: duplicate columns")
                for i, row in enumerate(obj.rows):
                    if any(col.key not in row for col in obj.columns):
                        raise ValidationError(f"{path}.rows.{i}: missing column key")
                    for col in obj.columns:
                        formatted(
                            row[col.key],
                            col.format,
                            f"{path}.rows.{i}.{col.key}",
                            formatting,
                            language,
                        )
                text(
                    empty if obj.empty_text is None else obj.empty_text,
                    path + ".empty_text",
                    500,
                )
            elif isinstance(obj, (BarChart, LineChart, Funnel)):
                charts[path] = normalize_chart(obj, path, formatting, language)
            else:
                raise ValidationError(f"{path}: unsupported component")
        finally:
            seen.remove(id(obj))

    for i, block in enumerate(blocks):
        node(block, f"blocks.{i}", top=True)
    return ReportDocument(
        report.title,
        report.subtitle,
        report.mode,
        Page(size=report.page.dimensions(), margin_mm=report.page.margin_mm),
        report.theme,
        blocks,
        MappingProxyType(charts),
        language,
        formatting,
        empty,
    )
