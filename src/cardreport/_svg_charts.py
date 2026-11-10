"""Experimental SVG charts, using Matplotlib for axes and text measurement."""

from __future__ import annotations

from importlib.resources import files
from io import StringIO
from typing import Any
from xml.etree import ElementTree as ET

from ._chart_display import segments
from .formatting import Formatting
from .layout import measured_overflow, reason_diagnostic
from .model import Currency, Format, LayoutOverflowError, format_value


def render_svg(spec: dict[str, Any], width: float, height: float, path: str) -> str:
    from matplotlib import rc_context, rcdefaults, rcParams
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties
    from matplotlib.layout_engine import ConstrainedLayoutEngine
    from matplotlib.patches import Polygon, Rectangle
    from matplotlib.text import Text
    from matplotlib.ticker import FuncFormatter, MaxNLocator

    small = bool(spec.get("compact", False))
    is_line = spec.get("kind") == "line"
    is_funnel = spec.get("kind") == "funnel"
    axes = spec.get("axes", True)
    if width < 40 or height < (10 if small else 35) * 96 / 25.4 - 1:
        raise LayoutOverflowError(
            f"{path}: chart has insufficient allocated space",
            diagnostic=reason_diagnostic("insufficient_space", path),
        )
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
        labels: list[Text] = []
        label_bars: list[tuple[Text, Rectangle, bool]] = []
        all_bars: list[Rectangle] = []
        label: Text
        horizontal = spec["horizontal"]
        series = spec["series"]
        stacked = spec.get("mode") == "stacked" and len(series) > 1
        if is_line:
            positions = spec["positions"]
            for item in series:
                values = [float("nan") if v is None else v for v in item["values"]]
                ax.plot(positions, values, color=item["color"], linewidth=1.5)
                sizes = item["marker_sizes"]
                points = [i for i, size in enumerate(sizes) if size]
                ax.scatter(
                    [positions[i] for i in points],
                    [values[i] for i in points],
                    s=[(sizes[i] * 0.75) ** 2 for i in points],
                    color=item["color"],
                    zorder=3,
                    clip_on=False,
                    linewidths=0,
                )
                if spec["fill"] == "zero":
                    for indices in segments(item["values"]):
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
        elif is_funnel:
            item = series[0]
            values = item["values"]
            positions = list(range(len(values)))
            for i in range(len(values) - 1):
                left, right = values[i] / 2, values[i + 1] / 2
                ax.add_patch(
                    Polygon(
                        [
                            (-left, i + 0.4),
                            (left, i + 0.4),
                            (right, i + 0.6),
                            (-right, i + 0.6),
                        ],
                        facecolor=item["color"],
                        alpha=0.2,
                        edgecolor="none",
                        zorder=0,
                    )
                )
            bars = ax.barh(
                positions, values, left=[-v / 2 for v in values], color=item["color"]
            )
            ax.set_yticks(positions, spec["labels"])
            ax.invert_yaxis()
            extent = max(values) * 0.75 if max(values) else 1
            ax.set_xlim(-extent, extent)
            ax.xaxis.set_visible(False)
            ax.spines[["bottom", "left"]].set_visible(False)
            ax.tick_params(axis="y", length=0)
            if spec["show_labels"]:
                for i, value in enumerate(values):
                    labels.append(
                        ax.annotate(
                            item["value_labels"][i],
                            (value / 2, i),
                            xytext=(4, 0),
                            textcoords="offset points",
                            ha="left",
                            va="center",
                            clip_on=False,
                        )
                    )
        else:
            positions = list(range(len(spec["labels"])))
            bases = [0.0] * len(positions)
            bar_width = 0.8 if stacked else 0.8 / len(series)
            for index, item in enumerate(series):
                locations = [
                    p + (0 if stacked else -0.4 + bar_width * (index + 0.5))
                    for p in positions
                ]
                values = item["values"]
                colors = spec.get("colors") or item["color"]
                if horizontal:
                    bars = ax.barh(
                        locations, values, height=bar_width, left=bases, color=colors
                    )
                else:
                    bars = ax.bar(
                        locations, values, width=bar_width, bottom=bases, color=colors
                    )
                all_bars.extend(bars)
                if spec["show_labels"]:
                    if stacked:
                        for i, (bar, value) in enumerate(
                            zip(bars, values, strict=True)
                        ):
                            center = bases[i] + value / 2
                            xy = (
                                (center, locations[i])
                                if horizontal
                                else (locations[i], center)
                            )
                            label = ax.annotate(
                                item["value_labels"][i],
                                xy,
                                xytext=(0, 0)
                                if value
                                else ((4, 0) if horizontal else (0, 4)),
                                textcoords="offset points",
                                clip_on=False,
                                ha="center" if value or not horizontal else "left",
                                va="center" if value or horizontal else "bottom",
                            )
                            labels.append(label)
                            label_bars.append((label, bar, bool(value)))
                    else:
                        drawn = ax.bar_label(
                            bars, labels=item["value_labels"], padding=4
                        )
                        labels.extend(drawn)
                        label_bars.extend(
                            (label, bar, False)
                            for label, bar in zip(drawn, bars, strict=True)
                        )
                if stacked:
                    # Match Plotly stack, not relative: one signed cumulative base.
                    bases = [
                        base + value for base, value in zip(bases, values, strict=True)
                    ]
            if horizontal:
                ax.set_yticks(positions, spec["labels"])
                ax.invert_yaxis()
                ax.xaxis.set_major_formatter(
                    FuncFormatter(lambda v, _: format_value(v, fmt, formatting))
                )
                ax.margins(x=0.22)
            else:
                ax.set_xticks(positions, spec["labels"])
                ax.yaxis.set_major_formatter(
                    FuncFormatter(lambda v, _: format_value(v, fmt, formatting))
                )
                ax.margins(y=0.22)
            if not spec.get("category_labels", True):
                (ax.yaxis if horizontal else ax.xaxis).set_visible(False)
        if fmt == "integer":
            (ax.xaxis if horizontal else ax.yaxis).set_major_locator(
                MaxNLocator(integer=True)
            )
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_axisbelow(True)
        if not is_funnel:
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
                f"{path}: labels leave insufficient plotting area",
                diagnostic=reason_diagnostic("insufficient_space", path),
            )
        texts: list[Text] = list(labels)
        for axis, limits in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            if not axes or not axis.get_visible():
                continue
            lo, hi = sorted(limits)
            texts.extend(
                t.label1 for t in axis.get_major_ticks() if lo <= t.get_loc() <= hi
            )
        boxes = [
            label.get_window_extent(renderer)
            for label in texts
            if label.get_visible() and label.get_text()
        ]
        if any(
            b.x0 < 2 or b.y0 < 2 or b.x1 > width - 2 or b.y1 > height - 2 for b in boxes
        ):
            raise LayoutOverflowError(
                f"{path}: chart label exceeds available space",
                diagnostic=measured_overflow(
                    path,
                    (2, 2, width - 2, height - 2),
                    (
                        min(b.x0 for b in boxes),
                        height - max(b.y1 for b in boxes),
                        max(b.x1 for b in boxes),
                        height - min(b.y0 for b in boxes),
                    ),
                    box="viewport",
                    reason="label_outside",
                ),
            )
        for i, a in enumerate(boxes):
            for b in boxes[i + 1 :]:
                if (
                    min(a.x1, b.x1) - max(a.x0, b.x0) > 1
                    and min(a.y1, b.y1) - max(a.y0, b.y0) > 1
                ):
                    raise LayoutOverflowError(
                        f"{path}: chart labels overlap",
                        diagnostic=reason_diagnostic("label_overlap", path),
                    )
        for label, owner, inside in label_bars:
            box = label.get_window_extent(renderer)
            area = owner.get_window_extent(renderer)
            if inside and (
                box.x0 < area.x0 - 1
                or box.x1 > area.x1 + 1
                or box.y0 < area.y0 - 1
                or box.y1 > area.y1 + 1
            ):
                raise LayoutOverflowError(
                    f"{path}: stacked value label does not fit its segment",
                    diagnostic=reason_diagnostic("label_outside", path),
                )
            for bar in all_bars:
                if bar is owner:
                    continue
                other = bar.get_window_extent(renderer)
                if (
                    min(box.x1, other.x1) - max(box.x0, other.x0) > 1
                    and min(box.y1, other.y1) - max(box.y0, other.y0) > 1
                ):
                    raise LayoutOverflowError(
                        f"{path}: value label overlaps another bar",
                        diagnostic=reason_diagnostic("label_overlap", path),
                    )
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
