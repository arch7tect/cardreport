"""Frozen export snapshot, retaining the public component tree (no geometry IR)."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from .model import Block, Page, Theme


@dataclass(frozen=True)
class ChartSeries:
    name: str
    values: tuple[float | None, ...]
    labels: tuple[str, ...]


@dataclass(frozen=True)
class ChartData:
    labels: tuple[str, ...]
    series: tuple[ChartSeries, ...]


@dataclass(frozen=True)
class ReportDocument:
    title: str
    subtitle: str
    mode: Literal["dashboard", "flow"]
    page: Page
    theme: Theme
    blocks: tuple[Block, ...]
    charts: Mapping[str, ChartData]
