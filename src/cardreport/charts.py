"""The deliberately closed Plotly adapter; no backend objects escape."""

from html import escape
from typing import Any

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
from .validation import PALETTE, normalize_chart


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
        color = theme.accent if i == 0 else PALETTE[i]
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
            if obj.show_labels:
                trace.update(
                    text=[escape(label) for label in item.labels],
                    textposition="outside",
                    cliponaxis=False,
                )
        data.append(trace)
    if not x:
        data = []
    horizontal = isinstance(obj, Funnel) or (
        isinstance(obj, BarChart) and obj.orientation == "horizontal"
    )
    axis = {
        "showgrid": True,
        "gridcolor": "#ececec",
        "zeroline": False,
        "automargin": True,
        "tickfont": {"size": theme.font_size_pt * 96 / 72},
    }
    category = {
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
    if formatting is not None:
        layout["separators"] = formatting.decimal + (
            formatting.group_character or ("." if formatting.decimal == "," else ",")
        )
    return {
        "data": data,
        "layout": layout,
        "categoryCount": len(x)
        if category["type"] == "category"
        else (len(normalized.tick_values) if formatting is not None else None),
        "categoryAxis": ".y" if horizontal else ".x",
    }
