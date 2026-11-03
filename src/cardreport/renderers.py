"""Provisional renderer boundary, with Chromium as the production default."""

import time
from typing import Protocol

from .document import ReportDocument
from .model import RenderTimeoutError


class Renderer(Protocol):
    """Render a validated, frozen export snapshot.

    No registry or inheritance is needed. HTML is a preview: only PDF guarantees
    checked geometry. Each engine owns pagination, fonts and chart bounds.
    ReportDocument uses the public component tree and raw, unescaped chart data.
    Raise ReportError subclasses: LayoutOverflowError for geometry,
    UnsupportedFeatureError for unsupported inputs, DependencyError for missing
    runtime dependencies, RenderTimeoutError when the monotonic deadline expires,
    and RenderError for unexpected rendering failure. Owned processes must be
    stopped on failure. The deadline includes prior validation work.
    This extension contract is provisional while the experimental engine matures.
    """

    def render_html(self, doc: ReportDocument) -> str: ...

    def render_pdf(self, doc: ReportDocument, *, deadline: float) -> bytes: ...


class ChromiumRenderer:
    """Default offline Plotly/Chromium renderer; dependencies load only on export."""

    def render_html(self, doc: ReportDocument) -> str:
        from .html import render_html

        return render_html(doc)

    def render_pdf(self, doc: ReportDocument, *, deadline: float) -> bytes:
        from .pdf import render_pdf

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RenderTimeoutError("Export deadline expired")
        return render_pdf(doc, deadline=deadline)
