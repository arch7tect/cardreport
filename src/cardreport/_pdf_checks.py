"""Inspect all PDF resource scopes, including nested SVG form resources."""

from collections.abc import Iterator
from importlib.resources import files
from io import BytesIO
from typing import Any

from fontTools.ttLib import TTFont
from pypdf import PdfReader

from .model import LayoutOverflowError, RenderError


def resource_scopes(resources: Any, seen: set[int] | None = None) -> Iterator[Any]:
    seen = set() if seen is None else seen
    resources = resources.get_object()
    if id(resources) in seen:
        return
    seen.add(id(resources))
    yield resources
    if "/XObject" in resources:
        for ref in resources["/XObject"].get_object().values():
            obj = ref.get_object()
            if "/Resources" in obj:
                yield from resource_scopes(obj["/Resources"], seen)


def font_identity(data: bytes) -> frozenset[tuple[int, str]]:
    with TTFont(BytesIO(data)) as font:
        return frozenset(
            (n.nameID, n.toUnicode())
            for n in font["name"].names
            if n.nameID in (1, 3, 5)
        )


def verify_fonts(reader: PdfReader) -> None:
    expected = {
        font_identity(files("cardreport").joinpath("assets", name).read_bytes())
        for name in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
    }
    for page in reader.pages:
        for resources in resource_scopes(page["/Resources"]):
            if "/Font" not in resources:
                continue
            for ref in resources["/Font"].get_object().values():
                font = ref.get_object()
                descendants = (
                    font["/DescendantFonts"] if "/DescendantFonts" in font else [font]
                )
                for descendant in descendants:
                    descriptor = descendant.get_object().get("/FontDescriptor")
                    if (
                        descriptor is None
                        or "/FontFile2" not in descriptor.get_object()
                    ):
                        raise RenderError("Expected embedded bundled font")
                    embedded = descriptor.get_object()["/FontFile2"].get_data()
                    if font_identity(embedded) not in expected:
                        raise RenderError("Unexpected font identity or version")


def verify_chart_bounds(
    data: bytes,
    width_px: float,
    height_px: float,
    path: str,
    *,
    expect_text: bool = True,
) -> None:
    """Validate glyph bounds in the native SVG render, in PDF points."""
    import pdfplumber

    with pdfplumber.open(BytesIO(data)) as pdf:
        if len(pdf.pages) != 1 or (expect_text and not pdf.pages[0].chars):
            raise RenderError(f"{path}: native SVG text was lost")
        width, height = width_px * 0.75, height_px * 0.75
        for char in pdf.pages[0].chars:
            if (
                char["x0"] < 0
                or char["top"] < 0
                or char["x1"] > width
                or char["bottom"] > height
            ):
                raise LayoutOverflowError(
                    f"{path}: native chart label exceeds available space"
                )
