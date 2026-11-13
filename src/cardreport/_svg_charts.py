"""Experimental SVG charts, using Matplotlib for axes and text measurement."""

from __future__ import annotations

from collections.abc import Sequence
from importlib.resources import files
from io import StringIO
from typing import TYPE_CHECKING, cast
from xml.etree import ElementTree as ET

from ._chart_display import segments
from ._svg_spec import SvgSpec
from .formatting import Formatting
from .layout import measured_overflow, reason_diagnostic
from .model import Currency, Format, LayoutOverflowError, format_value

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backends.backend_agg import RendererAgg
    from matplotlib.patches import Rectangle
    from matplotlib.text import Text
    from matplotlib.ticker import FuncFormatter
    from matplotlib.transforms import BboxBase


def _plot_line(ax: Axes, spec: SvgSpec, formatter: FuncFormatter) -> None:
    positions = spec["positions"]
    for item in spec["series"]:
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
    ax.set_ylim(cast(tuple[float, float], spec["y_range"]))
    ax.set_xticks(spec["ticks"], spec["tick_labels"])
    ax.yaxis.set_major_formatter(formatter)
    ax.set_xlim(cast(tuple[float, float], spec["x_range"]))
    if not spec.get("axes", True):
        ax.set_axis_off()


def _plot_funnel(ax: Axes, spec: SvgSpec, labels: list[Text]) -> None:
    from matplotlib.patches import Polygon

    item = spec["series"][0]
    values = cast(Sequence[float], item["values"])
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
    ax.barh(positions, values, left=[-v / 2 for v in values], color=item["color"])
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


def _plot_bars(
    ax: Axes,
    spec: SvgSpec,
    formatter: FuncFormatter,
    labels: list[Text],
    label_bars: list[tuple[Text, Rectangle, bool]],
    all_bars: list[Rectangle],
) -> None:
    horizontal = spec["horizontal"]
    series = spec["series"]
    stacked = spec.get("mode") == "stacked" and len(series) > 1
    positions = list(range(len(spec["labels"])))
    bases = [0.0] * len(positions)
    bar_width = 0.8 if stacked else 0.8 / len(series)
    for index, item in enumerate(series):
        locations = [
            p + (0 if stacked else -0.4 + bar_width * (index + 0.5)) for p in positions
        ]
        values = cast(Sequence[float], item["values"])
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
                for i, (bar, value) in enumerate(zip(bars, values, strict=True)):
                    center = bases[i] + value / 2
                    xy = (
                        (center, locations[i]) if horizontal else (locations[i], center)
                    )
                    label = ax.annotate(
                        item["value_labels"][i],
                        xy,
                        xytext=(0, 0) if value else ((4, 0) if horizontal else (0, 4)),
                        textcoords="offset points",
                        clip_on=False,
                        ha="center" if value or not horizontal else "left",
                        va="center" if value or horizontal else "bottom",
                    )
                    labels.append(label)
                    label_bars.append((label, bar, bool(value)))
            else:
                drawn = ax.bar_label(bars, labels=item["value_labels"], padding=4)
                labels.extend(drawn)
                label_bars.extend(
                    (label, bar, False) for label, bar in zip(drawn, bars, strict=True)
                )
        if stacked:
            # Match Plotly stack, not relative: one signed cumulative base.
            bases = [base + value for base, value in zip(bases, values, strict=True)]
    if horizontal:
        ax.set_yticks(positions, spec["labels"])
        ax.invert_yaxis()
        ax.xaxis.set_major_formatter(formatter)
        ax.margins(x=0.22)
    else:
        ax.set_xticks(positions, spec["labels"])
        ax.yaxis.set_major_formatter(formatter)
        ax.margins(y=0.22)
    if not spec.get("category_labels", True):
        (ax.yaxis if horizontal else ax.xaxis).set_visible(False)


def _overlaps(a: BboxBase, b: BboxBase) -> bool:
    return bool(
        min(a.x1, b.x1) - max(a.x0, b.x0) > 1 and min(a.y1, b.y1) - max(a.y0, b.y0) > 1
    )


def _check_labels(
    ax: Axes,
    renderer: RendererAgg,
    labels: list[Text],
    label_bars: list[tuple[Text, Rectangle, bool]],
    all_bars: list[Rectangle],
    *,
    width: float,
    height: float,
    path: str,
    axes: bool,
    small: bool,
) -> None:
    area: BboxBase = ax.get_window_extent(renderer)
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
    boxes: Sequence[BboxBase] = [
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
            if _overlaps(a, b):
                raise LayoutOverflowError(
                    f"{path}: chart labels overlap",
                    diagnostic=reason_diagnostic("label_overlap", path),
                )
    for label, owner, inside in label_bars:
        box: BboxBase = label.get_window_extent(renderer)
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
            if _overlaps(box, other):
                raise LayoutOverflowError(
                    f"{path}: value label overlaps another bar",
                    diagnostic=reason_diagnostic("label_overlap", path),
                )


def render_svg(spec: SvgSpec, width: float, height: float, path: str) -> str:
    from matplotlib import rc_context, rcdefaults, rcParams
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties
    from matplotlib.layout_engine import ConstrainedLayoutEngine
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
        Currency(spec["format"])
        if len(spec["format"]) == 3
        else cast(Format, spec["format"])
    )
    raw_formatting = spec.get("formatting")
    formatting = Formatting(**raw_formatting) if raw_formatting is not None else None

    def formatter() -> FuncFormatter:
        return FuncFormatter(lambda v, _: format_value(v, fmt, formatting))

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
        if is_line:
            _plot_line(ax, spec, formatter())
        elif is_funnel:
            _plot_funnel(ax, spec, labels)
        else:
            _plot_bars(ax, spec, formatter(), labels, label_bars, all_bars)
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
        _check_labels(
            ax,
            renderer,
            labels,
            label_bars,
            all_bars,
            width=width,
            height=height,
            path=path,
            axes=axes,
            small=small,
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
