"""Application-owned resource budgets, independent of report presentation."""

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class ReportLimits:
    max_table_rows: int = 2000
    max_table_columns: int = 20
    max_table_cells: int = 20_000
    max_chart_points: int = 500
    max_chart_categories: int = 30
    max_pages: int = 100

    def __post_init__(self) -> None:
        for spec in fields(self):
            value = getattr(self, spec.name)
            if type(value) is not int or value < 1:
                from .model import ValidationError

                raise ValidationError(
                    f"limits.{spec.name}: expected a positive integer"
                )


DEFAULT_REPORT_LIMITS = ReportLimits()
