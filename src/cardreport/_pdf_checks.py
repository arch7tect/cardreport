"""Inspect all PDF resource scopes, including nested SVG form resources."""

from collections.abc import Iterator
from importlib.resources import files
from io import BytesIO
from typing import Any, NamedTuple

from fontTools.ttLib import TTFont
from pypdf import PdfReader

from .layout import measured_overflow
from .model import LayoutOverflowError, RenderError


class _FontName(NamedTuple):
    name_id: int
    value: str


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
            _FontName(n.nameID, n.toUnicode())
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
    page: int | None = None,
) -> None:
    """Validate glyph bounds in the native SVG render, in PDF points."""
    import pdfplumber

    with pdfplumber.open(BytesIO(data)) as pdf:
        if len(pdf.pages) != 1 or (expect_text and not pdf.pages[0].chars):
            raise RenderError(f"{path}: native SVG text was lost")
        width, height = width_px * 0.75, height_px * 0.75
        chars = pdf.pages[0].chars
        if any(
            char["x0"] < 0
            or char["top"] < 0
            or char["x1"] > width
            or char["bottom"] > height
            for char in chars
        ):
            raise LayoutOverflowError(
                f"{path}: native chart label exceeds available space",
                diagnostic=measured_overflow(
                    path,
                    (0, 0, width, height),
                    (
                        min(c["x0"] for c in chars),
                        min(c["top"] for c in chars),
                        max(c["x1"] for c in chars),
                        max(c["bottom"] for c in chars),
                    ),
                    box="viewport",
                    reason="label_outside",
                    page=page,
                    mm_per_unit=25.4 / 72,
                ),
            )
