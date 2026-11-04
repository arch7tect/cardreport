"""Experimental SVG charts, using Matplotlib for axes and text measurement."""

from __future__ import annotations

from importlib.resources import files
from io import StringIO
from typing import Any
from xml.etree import ElementTree as ET

from ._chart_display import segments
from .formatting import Formatting
from .model import Currency, Format, LayoutOverflowError, format_value


def render_svg(spec: dict[str, Any], width: float, height: float, path: str) -> str:
    from matplotlib import rc_context, rcdefaults, rcParams
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties
    from matplotlib.layout_engine import ConstrainedLayoutEngine
    from matplotlib.text import Text
    from matplotlib.ticker import FuncFormatter, MaxNLocator

    small = bool(spec.get("compact", False))
    is_line = spec.get("kind") == "line"
    axes = spec.get("axes", True)
    if width < 40 or height < (10 if small else 35) * 96 / 25.4 - 1:
        raise LayoutOverflowError(f"{path}: chart has insufficient allocated space")
    font = FontProperties(
        fname=str(files("cardreport").joinpath("assets", "DejaVuSans.ttf")),
        size=spec["font_size"],
    )
    fmt: Format = (
        Currency(spec["format"]) if len(spec["format"]) == 3 else spec["format"]
    )
    formatting = (
        Formatting(**spec["formatting"]) if spec.get("formatting") is not None else None
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
        layout.set(w_pad=(3 if small else 12) / 96, h_pad=(3 if small else 8) / 96)
        canvas = FigureCanvasAgg(fig)
        ax = fig.subplots()
        labels = []
        horizontal = spec["horizontal"]
        if is_line:
            positions = spec["positions"]
            values = [float("nan") if v is None else v for v in spec["values"]]
            ax.plot(positions, values, color=spec["color"], linewidth=1.5)
            sizes = spec["marker_sizes"]
            points = [i for i, size in enumerate(sizes) if size]
            ax.scatter(
                [positions[i] for i in points],
                [values[i] for i in points],
                s=[(sizes[i] * 0.75) ** 2 for i in points],
                color=spec["color"],
                zorder=3,
                clip_on=False,
                linewidths=0,
            )
            if spec["fill"] == "zero":
                for indices in segments(spec["values"]):
                    if len(indices) < 2:
                        continue
                    ax.fill_between(
                        [positions[i] for i in indices],
                        [values[i] for i in indices],
                        0,
                        color=spec["fill_color"],
                        zorder=1,
                    )
            ax.set_ylim(spec["y_range"])
            ax.set_xticks(spec["ticks"], spec["tick_labels"])
            ax.yaxis.set_major_formatter(
                FuncFormatter(lambda v, _: format_value(v, fmt, formatting))
            )
            ax.set_xlim(spec["x_range"])
            if not axes:
                ax.set_axis_off()
        else:
            positions = list(range(len(spec["labels"])))
            colors = spec.get("colors") or spec["color"]
            if horizontal:
                bars = ax.barh(positions, spec["values"], color=colors)
                ax.set_yticks(positions, spec["labels"])
                ax.invert_yaxis()
                ax.xaxis.set_major_formatter(
                    FuncFormatter(lambda v, _: format_value(v, fmt, formatting))
                )
                ax.margins(x=0.22)
            else:
                bars = ax.bar(positions, spec["values"], color=colors)
                ax.set_xticks(positions, spec["labels"])
                ax.yaxis.set_major_formatter(
                    FuncFormatter(lambda v, _: format_value(v, fmt, formatting))
                )
                ax.margins(y=0.22)
            if not spec.get("category_labels", True):
                (ax.yaxis if horizontal else ax.xaxis).set_visible(False)
            labels = (
                ax.bar_label(bars, labels=spec["value_labels"], padding=4)
                if spec["show_labels"]
                else []
            )
        if fmt == "integer":
            (ax.xaxis if horizontal else ax.yaxis).set_major_locator(
                MaxNLocator(integer=True)
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
        if area.width < 40 or area.height < (20 if small else 40):
            raise LayoutOverflowError(
                f"{path}: labels leave insufficient plotting area"
            )
        texts: list[Text] = list(labels)
        for axis, limits in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            if not axes or not axis.get_visible():
                continue
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
