"""Data-free measurements of a failed layout check, not a resizing prediction."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, fields
from typing import Literal, get_args

LayoutReason = Literal[
    "content_overflow",
    "page_overflow",
    "label_outside",
    "label_overlap",
    "insufficient_space",
    "fragmented",
    "page_limit",
    "missing_content",
    "layout_overflow",
]
LayoutBox = Literal["content", "padding", "border", "viewport"]
_PATH = re.compile(
    r"(?:report|pages\.[0-9]+|blocks\.[0-9]+(?:\.(?:[0-9]+|content|frame|legend))*)\Z"
)


@dataclass(frozen=True)
class LayoutDiagnostic:
    """First failed check; dimensions describe only the current rendered layout."""

    reason: LayoutReason
    path: str
    page: int | None = None
    box: LayoutBox | None = None
    available_width_mm: float | None = None
    available_height_mm: float | None = None
    overflow_left_mm: float | None = None
    overflow_top_mm: float | None = None
    overflow_right_mm: float | None = None
    overflow_bottom_mm: float | None = None

    def __post_init__(self) -> None:
        if self.reason not in get_args(LayoutReason):
            raise ValueError("Invalid layout reason")
        if (
            not isinstance(self.path, str)
            or len(self.path) > 512
            or not _PATH.fullmatch(self.path)
        ):
            raise ValueError("Invalid layout path")
        if self.page is not None and (
            type(self.page) is not int or not 1 <= self.page <= 10000
        ):
            raise ValueError("Invalid layout page")
        if self.box is not None and self.box not in get_args(LayoutBox):
            raise ValueError("Invalid layout box")
        for field in fields(self):
            if field.name.endswith("_mm"):
                value = getattr(self, field.name)
                if value is not None and (
                    type(value) not in (int, float)
                    or not 0 <= value <= 1e9
                    or not math.isfinite(value)
                ):
                    raise ValueError("Invalid layout measurement")
                if value is not None and self.box is None:
                    raise ValueError("Layout measurements require a box")

    def to_dict(self) -> dict[str, object]:
        """Return only the closed, data-free transport fields."""
        return {key: value for key, value in asdict(self).items() if value is not None}

    @classmethod
    def from_dict(cls, value: object) -> LayoutDiagnostic:
        """Validate an untrusted JSON record; raise ValueError on invalid fields."""
        if not isinstance(value, dict) or set(value) - {f.name for f in fields(cls)}:
            raise ValueError("Invalid layout diagnostic")
        try:
            return cls(**value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid layout diagnostic") from exc


def decode_diagnostic(value: object) -> LayoutDiagnostic | None:
    """Optional metadata must never replace the original rendering failure."""
    try:
        return LayoutDiagnostic.from_dict(value)
    except ValueError:
        return None


def measured_overflow(
    path: str,
    area: tuple[float, float, float, float],
    extent: tuple[float, float, float, float],
    *,
    box: LayoutBox,
    page: int | None = None,
    reason: LayoutReason = "content_overflow",
    mm_per_unit: float = 25.4 / 96,
) -> LayoutDiagnostic | None:
    try:
        left, top, right, bottom = map(float, area)
        x0, y0, x1, y1 = map(float, extent)
        if not all(math.isfinite(v) for v in (*area, *extent, mm_per_unit)):
            return None
        return LayoutDiagnostic(
            reason,
            path,
            page,
            box,
            max(0, right - left) * mm_per_unit,
            max(0, bottom - top) * mm_per_unit,
            max(0, left - x0) * mm_per_unit,
            max(0, top - y0) * mm_per_unit,
            max(0, x1 - right) * mm_per_unit,
            max(0, y1 - bottom) * mm_per_unit,
        )
    except (ValueError, OverflowError):
        return None


def reason_diagnostic(reason: LayoutReason, path: str) -> LayoutDiagnostic | None:
    return decode_diagnostic({"reason": reason, "path": path})
