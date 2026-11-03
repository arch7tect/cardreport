"""Experimental SVG bars, using Matplotlib for axes and text measurement."""

from __future__ import annotations

from importlib.resources import files
from io import StringIO
from typing import Any
from xml.etree import ElementTree as ET

from .model import Currency, Format, LayoutOverflowError, format_value


def render_svg(spec: dict[str, Any], width: float, height: float, path: str) -> str:
    from matplotlib import rc_context, rcdefaults, rcParams
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties
    from matplotlib.layout_engine import ConstrainedLayoutEngine
    from matplotlib.text import Text
    from matplotlib.ticker import FuncFormatter, MaxNLocator

    if width < 40 or height < 35 * 96 / 25.4 - 1:
        raise LayoutOverflowError(f"{path}: chart has insufficient allocated space")
    font = FontProperties(
        fname=str(files("cardreport").joinpath("assets", "DejaVuSans.ttf")),
        size=spec["font_size"],
    )
    fmt: Format = (
        Currency(spec["format"]) if len(spec["format"]) == 3 else spec["format"]
    )
    with rc_context():
        rcdefaults()
        rcParams.update(
            {
                "svg.fonttype": "none",
                "text.usetex": False,
                "text.parse_math": False,
                "font.size": spec["font_size"],
            }
        )
        fig = Figure(figsize=(width / 96, height / 96), dpi=96, layout="constrained")
        layout = fig.get_layout_engine()
        assert isinstance(layout, ConstrainedLayoutEngine)
        layout.set(w_pad=12 / 96, h_pad=8 / 96)
        canvas = FigureCanvasAgg(fig)
        ax = fig.subplots()
        positions = list(range(len(spec["labels"])))
        horizontal = spec["horizontal"]
        if horizontal:
            bars = ax.barh(positions, spec["values"], color=spec["color"])
            ax.set_yticks(positions, spec["labels"])
            ax.invert_yaxis()
            ax.xaxis.set_major_formatter(
                FuncFormatter(lambda v, _: format_value(v, fmt))
            )
            ax.margins(x=0.22)
        else:
            bars = ax.bar(positions, spec["values"], color=spec["color"])
            ax.set_xticks(positions, spec["labels"])
            ax.yaxis.set_major_formatter(
                FuncFormatter(lambda v, _: format_value(v, fmt))
            )
            ax.margins(y=0.22)
        if fmt == "integer":
            (ax.xaxis if horizontal else ax.yaxis).set_major_locator(
                MaxNLocator(integer=True)
            )
        labels = (
            ax.bar_label(bars, labels=spec["value_labels"], padding=4)
            if spec["show_labels"]
            else []
        )
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis="x" if horizontal else "y", alpha=0.2)
        ax.set_facecolor("none")
        fig.patch.set_alpha(0)
        # Force tick creation before applying the exact bundled font and literal text.
        canvas.draw()  # type: ignore[no-untyped-call]
        for label in fig.findobj(Text):
            label.set_fontproperties(font)
            label.set_parse_math(False)
            label.set_color(spec["text_color"])
        canvas.draw()  # type: ignore[no-untyped-call]
        renderer = canvas.get_renderer()  # type: ignore[no-untyped-call]
        area = ax.get_window_extent(renderer)
        if area.width < 40 or area.height < 40:
            raise LayoutOverflowError(
                f"{path}: labels leave insufficient plotting area"
            )
        texts: list[Text] = list(labels)
        for axis, limits in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            lo, hi = sorted(limits)
            texts.extend(
                t.label1 for t in axis.get_major_ticks() if lo <= t.get_loc() <= hi
            )
        boxes = []
        for label in texts:
            if not label.get_visible() or not label.get_text():
                continue
            b = label.get_window_extent(renderer)
            if b.x0 < 2 or b.y0 < 2 or b.x1 > width - 2 or b.y1 > height - 2:
                raise LayoutOverflowError(
                    f"{path}: chart label exceeds available space"
                )
            boxes.append(b)
        for i, a in enumerate(boxes):
            for b in boxes[i + 1 :]:
                if (
                    min(a.x1, b.x1) - max(a.x0, b.x0) > 1
                    and min(a.y1, b.y1) - max(a.y0, b.y0) > 1
                ):
                    raise LayoutOverflowError(f"{path}: chart labels overlap")
        fig.set_layout_engine("none")
        out = StringIO()
        fig.savefig(out, format="svg")
        svg = out.getvalue()
        svg = svg[svg.index("<svg") :]
        # Only style attributes are changed; literal user labels stay untouched.
        root = ET.fromstring(svg)
        namespace = "http://www.w3.org/2000/svg"
        ET.register_namespace("", namespace)
        ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
        for element in root.iter():
            if element.tag in (f"{{{namespace}}}text", f"{{{namespace}}}tspan"):
                element.set(
                    "style", element.get("style", "") + ";font-family:CardReport"
                )
        return ET.tostring(root, encoding="unicode")
