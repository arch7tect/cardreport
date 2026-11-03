"""The only adapter to WeasyPrint private boxes. Pinned and guarded by canaries."""

from __future__ import annotations

from base64 import b64encode
from collections.abc import Iterator
from importlib.resources import files
from typing import Any

from .model import DependencyError, LayoutOverflowError

VERSION = "70.0"
TOLERANCE = 1.0  # CSS px; rounding only, never a text-fit heuristic.


def walk(box: Any) -> Iterator[Any]:
    yield box
    for child in getattr(box, "children", ()):
        yield from walk(child)


def bounds(box: Any) -> tuple[float, float, float, float]:
    x, y = float(box.position_x), float(box.position_y)
    return x, y, x + float(box.margin_width()), y + float(box.margin_height())


def inspect(
    document: Any, expected_pages: int, expected_paths: set[str] | None = None
) -> dict[str, tuple[float, float]]:
    """Check page/content bounds and fragmentation, return chart content sizes."""
    if len(document.pages) != expected_pages:
        raise LayoutOverflowError("report: dashboard content produced unexpected pages")
    charts: dict[str, tuple[float, float]] = {}
    locations: dict[str, set[int]] = {}
    try:
        for page_number, page in enumerate(document.pages):
            root = page._page_box
            for box in walk(root):
                element = box.element
                if element is None:
                    continue
                path = element.get("data-path")
                # Inline text/line boxes repeat their element; inspect the principal box.
                if not path or type(box).__name__ in ("TextBox", "LineBox"):
                    continue
                locations.setdefault(path, set()).add(page_number)
                x, y = float(box.content_box_x()), float(box.content_box_y())
                right, bottom = x + float(box.width), y + float(box.height)
                if element.get("data-chart"):
                    charts[path] = float(box.width), float(box.height)
                for child in walk(box):
                    if child is box:
                        continue
                    left, top, r, b = bounds(child)
                    if (
                        r > right + TOLERANCE
                        or b > bottom + TOLERANCE
                        or left < x - TOLERANCE
                        or top < y - TOLERANCE
                    ):
                        raise LayoutOverflowError(
                            f"{path}: content exceeds allocated width/height"
                        )
        if expected_paths is not None and set(locations) != expected_paths:
            raise LayoutOverflowError("report: components missing from measured layout")
        if any(len(pages) > 1 for pages in locations.values()):
            raise LayoutOverflowError(
                "report: indivisible dashboard block was fragmented"
            )
    except (AttributeError, TypeError, ValueError) as exc:
        raise DependencyError(
            "WeasyPrint box adapter is incompatible with this runtime"
        ) from exc
    return charts


def verify_adapter(html_class: Any, font_config: Any, fetcher: Any) -> None:
    """A native text-overflow canary must be rejected before trusting private boxes."""
    import weasyprint

    if weasyprint.__version__ != VERSION:
        raise DependencyError(f"WeasyPrintRenderer requires WeasyPrint {VERSION}")
    font = b64encode(
        files("cardreport").joinpath("assets", "DejaVuSans.ttf").read_bytes()
    ).decode()
    css = f"@font-face{{font-family:Canary;src:url(data:font/ttf;base64,{font})}}@page{{size:200px 200px;margin:0}}body{{margin:0;font:12px Canary}}"
    good = html_class(
        string=f'<style>{css}</style><div data-path="canary" style="width:150px;height:50px">Fits</div>',
        url_fetcher=fetcher,
    ).render(font_config=font_config)
    try:
        inspect(good, 1)
    except LayoutOverflowError as exc:
        raise DependencyError("WeasyPrint detector rejected a fitting canary") from exc
    for style, text in (
        ("width:25px;height:8px", "word " * 30),
        ("width:10px;height:80px;white-space:nowrap", "unbreakableword"),
    ):
        html = (
            f'<style>{css}</style><div data-path="canary" style="{style}">{text}</div>'
        )
        doc = html_class(string=html, url_fetcher=fetcher).render(
            font_config=font_config
        )
        try:
            inspect(doc, 1)
        except LayoutOverflowError:
            continue
        raise DependencyError("WeasyPrint overflow detector failed its canary")
