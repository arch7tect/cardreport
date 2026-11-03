"""Experimental browser-free renderer, deliberately limited to dashboard reports."""

from __future__ import annotations

import importlib.util
import json
import time
from html import escape

from .document import ReportDocument
from .html import render_block, render_header, render_styles
from .model import BarChart, Chart, DependencyError, PageBreak, UnsupportedFeatureError
from .pdf import run_worker
from .validation import MAX_PAGES


class WeasyPrintRenderer:
    """Experimental: dashboard cards, text, tables and single-series bars.

    Line/funnel charts, multi-series bars and automatic flow are explicitly
    unsupported. Uses pinned WeasyPrint 70.0 private box measurements with a
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
            if not isinstance(obj, BarChart) or len(doc.charts[path].series) != 1:
                raise UnsupportedFeatureError(
                    f"{path}: WeasyPrintRenderer currently supports single-series BarChart only"
                )
            data = doc.charts[path]
            attrs = f'data-kind="BarChart" data-path="{path}"'
            if not data.labels:
                return f'<div class="empty-chart" {attrs}>No data</div>'
            charts[path] = {
                "labels": data.labels,
                "values": data.series[0].values,
                "value_labels": data.series[0].labels,
                "horizontal": obj.orientation == "horizontal",
                "show_labels": obj.show_labels,
                "font_size": doc.theme.font_size_pt,
                "color": doc.theme.accent,
                "text_color": doc.theme.text,
                "format": obj.value_format
                if isinstance(obj.value_format, str)
                else obj.value_format.code,
            }
            return f'<div class="chart" {attrs} data-chart="{path}" data-definite="{str(definite).lower()}"><!--chart:{path}--></div>'

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
            current += render_block(block, f"blocks.{i}", chart)
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
        html = f'<!doctype html><html><head><meta charset="utf-8"><title>{escape(doc.title or "Report")}</title><style>{styles}</style></head><body>{content}</body></html>'
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
