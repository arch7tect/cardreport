"""The deliberately closed Plotly adapter; no backend objects escape."""

from html import escape
from typing import Any

from ._chart_display import (
    category_colors,
    compact,
    date_positions,
    empty,
    fill_color,
    line_range,
    line_x_range,
    marker_sizes,
    segments,
    series_colors,
)
from .document import ChartData
from .formatting import Formatting
from .model import (
    BarChart,
    Chart,
    Currency,
    Funnel,
    LineChart,
    Theme,
)
from .validation import normalize_chart


def chart_spec(
    obj: Chart,
    theme: Theme,
    path: str,
    prepared: ChartData | None = None,
    formatting: Formatting | None = None,
    language: str = "en",
) -> dict[str, Any]:
    normalized = (
        prepared
        if prepared is not None
        else normalize_chart(obj, path, formatting, language)
    )
    x = [escape(label) for label in normalized.labels]
    series = normalized.series
    data = []
    for i, item in enumerate(series):
        name = escape(item.name)
        vals = list(item.values)
        color = series_colors(theme)[i]
        trace: dict[str, Any] = {
            "name": name,
            "marker": {"color": color},
            "hoverinfo": "skip",
        }
        if isinstance(obj, LineChart):
            trace.update(
                type="scatter",
                mode="lines+markers",
                x=x,
                y=vals,
                connectgaps=False,
                line={"color": color},
            )
            if not obj.axes or not obj.markers or obj.fill != "none":
                trace["cliponaxis"] = False
                trace["marker"]["size"] = marker_sizes(vals, obj.markers)
                trace["marker"]["opacity"] = 1
                trace["marker"]["line"] = {"width": 0}
                trace["line"]["width"] = 2
            if obj.fill == "zero":
                sizes = marker_sizes(vals, obj.markers)
                for indices in segments(vals):
                    data.append(
                        {
                            **trace,
                            "x": [x[j] for j in indices],
                            "y": [vals[j] for j in indices],
                            "marker": {
                                "color": color,
                                "opacity": 1,
                                "line": {"width": 0},
                                "size": [sizes[j] for j in indices],
                            },
                            "fill": "tozeroy",
                            "fillcolor": fill_color(color, theme.card_background),
                            "showlegend": False,
                        }
                    )
                continue
        elif isinstance(obj, Funnel):
            trace.update(
                type="funnel",
                y=x,
                x=vals,
                textinfo="text" if obj.show_labels else "none",
                cliponaxis=False,
                text=[escape(label) for label in item.labels],
                textposition="outside",
            )
        else:
            horizontal = obj.orientation == "horizontal"
            trace.update(
                type="bar",
                orientation="h" if horizontal else "v",
                x=vals if horizontal else x,
                y=x if horizontal else vals,
            )
            if obj.color_by == "category":
                trace["marker"]["color"] = list(category_colors(obj, theme, len(x)))
            if obj.show_labels:
                trace.update(
                    text=[escape(label) for label in item.labels],
                    textposition="outside",
                    cliponaxis=False,
                )
        data.append(trace)
    if empty(obj, normalized):
        data = []
    horizontal = isinstance(obj, Funnel) or (
        isinstance(obj, BarChart) and obj.orientation == "horizontal"
    )
    axis: dict[str, Any] = {
        "showgrid": True,
        "gridcolor": "#ececec",
        "zeroline": False,
        "automargin": True,
        "tickfont": {"size": theme.font_size_pt * 96 / 72},
    }
    category: dict[str, Any] = {
        **axis,
        "showgrid": False,
        "type": "date"
        if isinstance(obj, LineChart) and obj.x_kind == "date"
        else "category",
    }
    if category["type"] == "category":
        category.update(
            tickmode="array",
            tickvals=x,
            ticktext=[escape(label) for label in normalized.category_labels] or x,
            categoryorder="array",
            categoryarray=x,
        )
    if isinstance(obj.value_format, Currency):
        axis.update(tickformat=",.2f", tickprefix=obj.value_format.code + " ")
    elif obj.value_format == "percent":
        axis["tickformat"] = ".1%"
    elif obj.value_format == "integer":
        axis["tickformat"] = ",.0f"
    if formatting is not None:
        grouping = "," if formatting.group != "none" else ""
        if isinstance(obj.value_format, Currency):
            axis["tickformat"] = f"{grouping}.{formatting.currency_decimals}f"
        elif obj.value_format == "percent":
            axis["tickformat"] = f"{grouping}.{formatting.percent_decimals}%"
        elif obj.value_format == "integer":
            axis["tickformat"] = f"{grouping}.0f"
        else:
            axis["tickformat"] = f"{grouping}.{formatting.number_decimals}~f"
        axis["exponentformat"] = "none"
        if category["type"] == "date":
            category.update(
                tickmode="array",
                tickvals=list(normalized.tick_values),
                ticktext=[escape(t) for t in normalized.tick_labels],
            )
    category_count: int | None = (
        len(x)
        if category["type"] == "category"
        else (len(normalized.tick_values) if formatting is not None else None)
    )
    if isinstance(obj, LineChart):
        if not obj.axes or not obj.markers or obj.fill != "none":
            axis["range"] = line_range(normalized, obj.fill)
        if (
            not obj.axes or not obj.markers or obj.fill != "none"
        ) and normalized.labels:
            dates = obj.x_kind == "date"
            positions = (
                date_positions(normalized.labels)
                if dates
                else tuple(float(i) for i in range(len(x)))
            )
            limits = line_x_range(positions, dates=dates)
            category["range"] = (
                [v * 86400000 for v in limits] if dates else list(limits)
            )
        if not obj.axes:
            category.update(visible=False, automargin=False)
            axis.update(visible=False, automargin=False)
            category_count = None
    if isinstance(obj, BarChart) and not obj.category_labels:
        category.update(visible=False, automargin=False)
        category_count = None
    if horizontal:
        category["autorange"] = "reversed"
    layout = {
        "font": {
            "family": "CardReport",
            "size": theme.font_size_pt * 96 / 72,
            "color": theme.text,
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": {"l": 10, "r": 35, "t": 15, "b": 30},
        "xaxis": axis if horizontal else category,
        "yaxis": category if horizontal else axis,
        "showlegend": getattr(obj, "legend", False) and len(series) > 1,
        "legend": {"orientation": "h", "y": -0.2},
        "uniformtext": {"minsize": theme.font_size_pt * 96 / 72, "mode": "show"},
        "barmode": "stack" if getattr(obj, "mode", None) == "stacked" else "group",
    }
    if isinstance(obj, LineChart) and not obj.axes:
        layout["margin"] = {
            "l": 5,
            "r": 5,
            "t": 5,
            "b": 5 if compact(obj, normalized) else 30,
        }
    if formatting is not None:
        layout["separators"] = formatting.decimal + (
            formatting.group_character or ("." if formatting.decimal == "," else ",")
        )
    return {
        "data": data,
        "layout": layout,
        "compact": compact(obj, normalized),
        "categoryCount": category_count,
        "categoryAxis": ".y" if horizontal else ".x",
    }
