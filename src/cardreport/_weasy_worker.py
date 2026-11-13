"""Owned WeasyPrint process; imports native dependencies only inside the worker."""

from __future__ import annotations

import io
import json
import re
import sys
from base64 import b64encode
from importlib.resources import files
from typing import Any, cast

from .model import DependencyError, LayoutOverflowError, RenderError, ReportError


def main() -> None:
    try:
        from weasyprint import HTML
        from weasyprint.text.fonts import FontConfiguration
    except (ImportError, OSError) as exc:
        raise DependencyError(
            f"WeasyPrint could not load its dependencies: {exc}\n"
            "Setup: https://github.com/arch7tect/cardreport/blob/main/"
            "docs/user/renderers.md#weasyprint"
        ) from exc
    from ._svg_charts import render_svg
    from ._svg_spec import SvgSpec
    from ._weasy_boxes import inspect, page_for_path, verify_adapter

    payload = json.loads(sys.stdin.buffer.read())
    fonts = {}
    for name in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        data = files("cardreport").joinpath("assets", name).read_bytes()
        fonts["data:font/ttf;base64," + b64encode(data).decode()] = data

    class BundledFonts:
        _fail_on_errors = False  # Record denial; fail explicitly after native layout.
        blocked: bool = False

        def __call__(self, url: str) -> Any:
            from weasyprint.urls import URLFetcherResponse

            if url not in fonts:
                self.blocked = True
                raise ValueError("External resource blocked")
            return URLFetcherResponse(url, fonts[url], {"Content-Type": "font/ttf"})

    fetch = BundledFonts()

    config = FontConfiguration()
    verify_adapter(HTML, config, fetch)
    html = payload["html"]
    expected_paths = set(re.findall(r'data-path="([^"]+)"', html))
    first = HTML(string=html, url_fetcher=fetch).render(font_config=config)
    if fetch.blocked:
        raise RenderError("Unexpected external resource request")
    sizes = inspect(first, payload["pages"], expected_paths)
    if set(sizes) != set(payload["charts"]):
        raise RenderError("Measured chart set differs from the input")
    for path, spec in payload["charts"].items():
        width, height = sizes[path]
        try:
            svg = render_svg(cast(SvgSpec, spec), width, height, path)
        except LayoutOverflowError as exc:
            if exc.diagnostic is not None:
                from dataclasses import replace

                exc.diagnostic = replace(
                    exc.diagnostic, page=page_for_path(first, path)
                )
            raise
        # The measured CSS box is the SVG viewport; SVG viewBox retains its coordinates.
        svg = svg.replace(
            "<svg ", f'<svg style="width:{width}px;height:{height}px" ', 1
        )
        # Check actual Pango-drawn glyphs as well as Matplotlib measurements.
        # A standalone viewport uses the same font bytes, SVG and CSS pixel size.
        from ._pdf_checks import verify_chart_bounds

        font_css = "".join(
            f"@font-face{{font-family:CardReport;src:url({url});font-weight:{weight}}}"
            for url, weight in zip(fonts, (400, 700), strict=True)
        )
        chart_html = f"<style>{font_css}@page{{size:{width}px {height}px;margin:0}}body{{margin:0}}svg{{display:block}}</style>{svg}"
        chart_pdf = HTML(string=chart_html, url_fetcher=fetch).write_pdf(
            font_config=config
        )
        verify_chart_bounds(
            chart_pdf,
            width,
            height,
            path,
            expect_text=spec.get("axes", True),
            page=page_for_path(first, path),
        )
        html = html.replace(f"<!--chart:{path}-->", svg)
    final = HTML(string=html, url_fetcher=fetch).render(font_config=config)
    final_sizes = inspect(final, payload["pages"], expected_paths)
    if set(final_sizes) != set(sizes) or any(
        abs(a - b) > 1
        for key in sizes
        for a, b in zip(sizes[key], final_sizes[key], strict=True)
    ):
        raise RenderError("Chart geometry changed after SVG insertion")
    if fetch.blocked:
        raise RenderError("Unexpected external resource request")
    if payload["pdf"]:
        pdf_data: bytes = final.write_pdf()
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_data))
        if len(reader.pages) != payload["pages"]:
            raise RenderError("PDF page count differs from measured layout")
        from ._pdf_checks import verify_fonts

        verify_fonts(reader)
        sys.stdout.buffer.write(pdf_data)
    else:
        sys.stdout.buffer.write(html.encode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # This boundary converts native-library failures into the worker protocol.
        kind = type(exc).__name__ if isinstance(exc, ReportError) else "RenderError"
        message = (
            str(exc)
            if isinstance(exc, ReportError)
            else f"WeasyPrint renderer failed ({type(exc).__name__})"
        )
        sys.stderr.write(
            "\n"
            + json.dumps(
                {
                    "kind": kind,
                    "message": message,
                    "diagnostic": exc.diagnostic.to_dict()
                    if isinstance(exc, LayoutOverflowError) and exc.diagnostic
                    else None,
                }
            )
            + "\n"
        )
        sys.exit(1)
