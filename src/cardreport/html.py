"""Shared escaped HTML fragments and the Chromium document adapter."""

from __future__ import annotations

import json
from base64 import b64encode
from collections.abc import Callable
from html import escape
from importlib.resources import files

from jinja2 import Environment

from ._chart_display import category_colors, compact, empty
from .document import ChartData, ReportDocument
from .formatting import Formatting
from .model import (
    KPI,
    BarChart,
    Block,
    Card,
    Chart,
    Column,
    Funnel,
    LineChart,
    PageBreak,
    Row,
    Table,
    Text,
    Theme,
    format_value,
)
from .validation import MAX_PAGES, weights


def safe_json(value: object) -> str:
    return (
        json.dumps(value, ensure_ascii=True, allow_nan=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def render_block(
    obj: Block,
    path: str,
    chart: Callable[[Chart, str, bool], str],
    definite: bool = False,
    formatting: Formatting | None = None,
    language: str = "en",
    empty_text: str = "No data",
    timezone: str | None = None,
) -> str:
    """Emit validated content. Chart markup and page placement belong to the engine."""
    kind = type(obj).__name__
    attrs = f'data-kind="{kind}" data-path="{path}"'
    if isinstance(obj, PageBreak):
        return '<div data-kind="PageBreak"></div>'
    if isinstance(obj, Card):
        head = (
            ""
            if obj.title is None
            else f'<div class="card-title">{escape(obj.title)}</div>'
        )
        minimum = " kpi-card" if isinstance(obj.content, KPI) else ""
        return f'<div class="card{minimum}" data-has-title="{str(obj.title is not None).lower()}" data-definite="{str(definite).lower()}" {attrs}>{head}<div class="card-content">{render_block(obj.content, path + ".content", chart, definite, formatting, language, empty_text, timezone)}</div></div>'
    if isinstance(obj, (Row, Column)):
        fixed = definite
        style = ""
        if isinstance(obj, Row):
            vals = weights(obj.widths, len(obj.children), path + ".widths")
            style = (
                "grid-template-columns:"
                + " ".join(f"minmax(0,{v}fr)" for v in vals)
                + ";"
            )
            if obj.height_mm is not None:
                style += f"height:{float(obj.height_mm)}mm;"
                fixed = True
        elif obj.heights is not None:
            vals = weights(obj.heights, len(obj.children), path + ".heights")
            style = (
                "display:grid;grid-template-rows:"
                + " ".join(f"minmax(0,{v}fr)" for v in vals)
                + ";height:100%;"
            )
        else:
            fixed = False
        kids = "".join(
            render_block(
                c,
                f"{path}.{i}",
                chart,
                fixed,
                formatting,
                language,
                empty_text,
                timezone,
            )
            for i, c in enumerate(obj.children)
        )
        return f'<div class="{kind.lower()}" {attrs} style="{style}">{kids}</div>'
    if isinstance(obj, Text):
        return f'<div class="text {obj.style}" {attrs}>{escape(obj.text)}</div>'
    if isinstance(obj, KPI):
        note = (
            ""
            if obj.note is None
            else f'<div class="kpi-note">{escape(obj.note)}</div>'
        )
        return f'<div class="kpi" {attrs}><div class="kpi-value">{escape(format_value(obj.value, obj.format, formatting, language, timezone))}</div><div>{escape(obj.label)}</div>{note}</div>'
    if isinstance(obj, Table):
        heads = "".join(
            f'<th style="text-align:{c.align}">{escape(c.label)}</th>'
            for c in obj.columns
        )
        colweights = [float(c.width or 1) for c in obj.columns]
        cols = "".join(
            f'<col style="width:{v / sum(colweights) * 100}%">' for v in colweights
        )
        rows = [
            "<tr>"
            + "".join(
                f'<td style="text-align:{c.align}">{escape(format_value(row[c.key], c.format, formatting, language, timezone))}</td>'
                for c in obj.columns
            )
            + "</tr>"
            for row in obj.rows
        ]
        if not rows:
            rows = [
                f'<tr><td colspan="{len(obj.columns)}">{escape(empty_text if obj.empty_text is None else obj.empty_text)}</td></tr>'
            ]
        return f"<table {attrs}><colgroup>{cols}</colgroup><thead><tr>{heads}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    if isinstance(obj, (BarChart, LineChart, Funnel)):
        return chart(obj, path, definite)
    from typing import assert_never

    assert_never(obj)


def empty_chart(obj: Chart, data: ChartData, path: str, message: str) -> str:
    small = " compact-chart" if compact(obj, data) else ""
    return f'<div class="empty-chart{small}" data-kind="{type(obj).__name__}" data-path="{path}">{escape(message)}</div>'


def chart_frame(
    obj: Chart, data: ChartData, theme: Theme, path: str, definite: bool, plot: str
) -> str:
    if not isinstance(obj, BarChart) or obj.color_by != "category" or not obj.legend:
        return plot
    labels = data.category_labels or data.labels
    colors = category_colors(obj, theme, len(labels))
    return legend_frame(labels, colors, obj.legend_position, path, definite, plot)


def legend_frame(
    labels: tuple[str, ...],
    colors: tuple[str, ...],
    position: str,
    path: str,
    definite: bool,
    plot: str,
) -> str:
    items = "".join(
        f'<div class="legend-item" data-path="{path}.legend.{i}"><span class="legend-swatch" style="background:{color}"></span><span>{escape(label)}</span></div>'
        for i, (label, color) in enumerate(zip(labels, colors, strict=True))
    )
    columns = 1 if position == "left" else min(3, len(labels))
    legend = f'<div class="category-legend" data-path="{path}.legend" style="grid-template-columns:repeat({columns},minmax(0,1fr))">{items}</div>'
    return f'<div class="chart-frame legend-{position}" data-path="{path}.frame" data-definite="{str(definite).lower()}" data-legend-count="{len(labels)}">{legend}{plot}</div>'


def render_header(report: ReportDocument) -> str:
    return (
        f"<header><h1>{escape(report.title)}</h1><div>{escape(report.subtitle)}</div></header>"
        if report.title or report.subtitle
        else ""
    )


def render_styles(report: ReportDocument) -> str:
    asset = files("cardreport").joinpath("assets")
    w, h = report.page.dimensions()
    return (
        Environment(autoescape=True)
        .from_string(asset.joinpath("style.css.j2").read_text())
        .render(
            width=w,
            height=h,
            margin=report.page.margin_mm,
            theme=report.theme,
            regular=b64encode(asset.joinpath("DejaVuSans.ttf").read_bytes()).decode(),
            bold=b64encode(asset.joinpath("DejaVuSans-Bold.ttf").read_bytes()).decode(),
        )
    )


def render_html(report: ReportDocument) -> str:
    from .charts import chart_spec

    charts: dict[str, object] = {}

    def chart(obj: Chart, path: str, definite: bool) -> str:
        ident = "chart" + str(len(charts))
        spec = chart_spec(
            obj, report.theme, path, report.charts[path], report.formatting
        )
        charts[ident] = spec
        attrs = f'data-kind="{type(obj).__name__}" data-path="{path}"'
        data = report.charts[path]
        if empty(obj, data):
            return empty_chart(obj, data, path, report.empty_text)
        small = " compact-chart" if compact(obj, data) else ""
        plot = f'<div class="chart{small}" {attrs} id="{ident}" data-definite="{str(definite).lower()}"></div>'
        return chart_frame(obj, data, report.theme, path, definite, plot)

    content = "".join(
        render_block(
            n,
            f"blocks.{i}",
            chart,
            formatting=report.formatting,
            language=report.language,
            empty_text=report.empty_text,
            timezone=report.timezone,
        )
        for i, n in enumerate(report.blocks)
    )
    from plotly.offline import get_plotlyjs

    asset = files("cardreport").joinpath("assets")
    return (
        Environment(autoescape=True)
        .from_string(asset.joinpath("report.html").read_text())
        .render(
            style=render_styles(report),
            content=content,
            header=render_header(report),
            plotly=get_plotlyjs() if charts else "",
            settings=safe_json(
                {"mode": report.mode, "charts": charts, "pageLimit": MAX_PAGES}
            ),
            script=asset.joinpath("layout.js").read_text(),
            language=report.language,
            title=report.title or "Report",
        )
    )
