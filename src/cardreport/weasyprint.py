"""Experimental browser-free renderer, deliberately limited to dashboard reports."""

from __future__ import annotations

import importlib.util
import json
import time
from dataclasses import asdict
from html import escape

from ._chart_display import (
    category_colors,
    compact,
    date_positions,
    empty,
    fill_color,
    line_range,
    line_x_range,
    marker_sizes,
    series_colors,
)
from .document import ReportDocument
from .html import (
    chart_frame,
    empty_chart,
    legend_frame,
    render_block,
    render_header,
    render_styles,
)
from .model import (
    BarChart,
    Chart,
    DependencyError,
    Funnel,
    LineChart,
    PageBreak,
    UnsupportedFeatureError,
)
from .pdf import run_worker
from .validation import MAX_PAGES


class WeasyPrintRenderer:
    """Experimental: dashboard cards, text, tables, bars, lines and funnels.

    Automatic flow is explicitly unsupported. Uses pinned WeasyPrint 70.0 private box measurements with a
    fail-closed canary. Native libraries must be installed by the caller.
    Static HTML is a preview; its layout in other browsers is not guaranteed.
    """

    def render_html(self, doc: ReportDocument) -> str:
        return self._render(doc, time.monotonic() + 30, pdf=False).decode("utf-8")

    def render_pdf(self, doc: ReportDocument, *, deadline: float) -> bytes:
        return self._render(doc, deadline, pdf=True)

    def _render(self, doc: ReportDocument, deadline: float, *, pdf: bool) -> bytes:
        if doc.mode != "dashboard":
            raise UnsupportedFeatureError(
                "WeasyPrintRenderer: flow mode is not yet supported"
            )
        charts: dict[str, object] = {}

        def chart(obj: Chart, path: str, definite: bool) -> str:
            data = doc.charts[path]
            attrs = f'data-kind="{type(obj).__name__}" data-path="{path}"'
            if empty(obj, data):
                return empty_chart(obj, data, path, doc.empty_text)
            payload: dict[str, object] = {
                "kind": "line"
                if isinstance(obj, LineChart)
                else "funnel"
                if isinstance(obj, Funnel)
                else "bar",
                "compact": compact(obj, data),
                "labels": data.category_labels or data.labels,
                "formatting": asdict(doc.formatting)
                if doc.formatting is not None
                else None,
                "series": [
                    {
                        "values": item.values,
                        "value_labels": item.labels,
                        "color": series_colors(doc.theme)[i],
                        "marker_sizes": marker_sizes(item.values, obj.markers)
                        if isinstance(obj, LineChart)
                        else [],
                    }
                    for i, item in enumerate(data.series)
                ],
                "horizontal": isinstance(obj, Funnel)
                or (isinstance(obj, BarChart) and obj.orientation == "horizontal"),
                "show_labels": isinstance(obj, (BarChart, Funnel)) and obj.show_labels,
                "font_size": doc.theme.font_size_pt,
                "color": doc.theme.accent,
                "text_color": doc.theme.text,
                "format": obj.value_format
                if isinstance(obj.value_format, str)
                else obj.value_format.code,
            }
            if isinstance(obj, LineChart):
                positions = (
                    date_positions(data.labels)
                    if obj.x_kind == "date"
                    else tuple(float(i) for i in range(len(data.labels)))
                )
                payload.update(
                    x_range=line_x_range(positions, dates=obj.x_kind == "date"),
                    axes=obj.axes,
                    fill=obj.fill,
                    y_range=line_range(data, obj.fill),
                    fill_color=fill_color(doc.theme.accent, doc.theme.card_background),
                    positions=date_positions(data.labels)
                    if obj.x_kind == "date"
                    else tuple(range(len(data.labels))),
                    ticks=date_positions(data.tick_values)
                    if obj.x_kind == "date"
                    else tuple(range(len(data.labels))),
                    tick_labels=data.tick_labels
                    if obj.x_kind == "date"
                    else data.labels,
                )
            elif isinstance(obj, BarChart):
                payload.update(
                    mode=obj.mode,
                    category_labels=obj.category_labels,
                    colors=category_colors(obj, doc.theme, len(data.labels)),
                )
            charts[path] = payload
            small = " compact-chart" if compact(obj, data) else ""
            plot = f'<div class="chart{small}" {attrs} data-chart="{path}" data-definite="{str(definite).lower()}"><!--chart:{path}--></div>'
            if (
                isinstance(obj, (BarChart, LineChart))
                and obj.legend
                and len(data.series) > 1
            ):
                return legend_frame(
                    tuple(item.name for item in data.series),
                    series_colors(doc.theme)[: len(data.series)],
                    "bottom",
                    path,
                    definite,
                    plot,
                )
            return chart_frame(obj, data, doc.theme, path, definite, plot)

        segments: list[str] = []
        current = render_header(doc)
        has_content = False
        pending_break = False
        for i, block in enumerate(doc.blocks):
            if isinstance(block, PageBreak):
                pending_break = has_content
                continue
            if pending_break:
                segments.append(current)
                current = ""
                has_content = False
                pending_break = False
            current += render_block(
                block,
                f"blocks.{i}",
                chart,
                formatting=doc.formatting,
                language=doc.language,
                empty_text=doc.empty_text,
            )
            has_content = True
        segments.append(current)
        if len(segments) > MAX_PAGES:
            from .model import LayoutOverflowError

            raise LayoutOverflowError("report: page limit exceeded")
        content = "".join(
            f'<section class="page"><div class="page-body" data-path="pages.{i}">{s}</div></section>'
            for i, s in enumerate(segments)
        )
        # Native paged media owns layout; no browser script is included.
        styles = (
            render_styles(doc)
            + f"""
.page-body{{display:block}} .page-body>*+*{{margin-top:{doc.theme.gap_mm}mm}}
.page,.row,.card,table,tr{{break-inside:avoid}}
.card{{display:grid;grid-template-columns:minmax(0,1fr);grid-template-rows:minmax(0,1fr)}}
.text,.card-title,td,th{{overflow-wrap:break-word}}
.card[data-has-title=true]{{grid-template-rows:auto minmax(0,1fr)}}
.chart svg{{display:block}} .page{{break-before:auto}}
"""
        )
        html = f'<!doctype html><html lang="{escape(doc.language, quote=True)}"><head><meta charset="utf-8"><title>{escape(doc.title or "Report")}</title><style>{styles}</style></head><body>{content}</body></html>'
        payload = json.dumps(
            {"html": html, "charts": charts, "pages": len(segments), "pdf": pdf}
        ).encode()
        if any(
            importlib.util.find_spec(name) is None
            for name in ("weasyprint", "matplotlib", "psutil", "pypdf", "pdfplumber")
        ):
            raise DependencyError(
                "Install cardreport[weasyprint] and the WeasyPrint native libraries"
            )
        return run_worker(
            "cardreport._weasy_worker", payload, [], deadline=deadline, pdf=pdf
        )
