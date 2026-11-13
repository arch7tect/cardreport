"""Versioned presentation definitions bound to existing concrete components."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import UTC, date, datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Literal, NamedTuple, cast

from ._inputs import (
    BindingError,
    DataError,
    TemplateError,
    array,
    check_tree,
    load_json,
    mapping,
    plain_tree,
)
from ._schema import validate_structure
from .data import (
    DEFAULT_LIMITS,
    DataLimits,
    Dataset,
    DatasetSchema,
    FieldSpec,
    FieldType,
    validate_bundle,
)
from .formatting import Formatting
from .model import (
    KPI,
    BarChart,
    Block,
    Card,
    CardContent,
    Column,
    Component,
    Currency,
    Format,
    Funnel,
    LineChart,
    Number,
    Page,
    PageBreak,
    Report,
    Row,
    Table,
    TableColumn,
    Text,
    Theme,
    ValidationError,
    Value,
    check_format,
    number,
)

MAX_TEMPLATE_BYTES = 1024 * 1024


def numeric(value: object) -> float:
    return number(value, "setting")


def weights(value: object) -> list[float] | None:
    return None if value is None else [numeric(v) for v in array(value)]


def fmt(value: object) -> Format:
    if isinstance(value, dict):
        obj = mapping(value)
        result: Format = Currency(cast(str, obj["currency"]))
    else:
        result = cast(Format, value)
    check_format(result, "format")
    return result


def schemas(value: object) -> Mapping[str, DatasetSchema]:
    raw = mapping(value)
    result: dict[str, DatasetSchema] = {}
    for dataset, value in raw.items():
        obj = mapping(value)
        fields: dict[str, FieldSpec] = {}
        for field, spec in mapping(obj["fields"]).items():
            raw_field = mapping(spec)
            fields[field] = FieldSpec(
                cast(FieldType, raw_field["type"]),
                cast(bool, raw_field.get("nullable", False)),
            )
        result[dataset] = DatasetSchema(
            fields, cast(Literal["one", "many"], obj["cardinality"])
        )
    return MappingProxyType(result)


class _ComponentVisit(NamedTuple):
    node: object
    path: str
    depth: int


def _component_limits(report: object) -> None:
    # Bound traversal before the recursive schema validator runs.
    blocks = report.get("blocks") if isinstance(report, dict) else None
    if not isinstance(blocks, list):
        return
    stack: list[_ComponentVisit] = [
        _ComponentVisit(block, f"report.blocks[{i}]", 0)
        for i, block in enumerate(blocks)
    ]
    count = 0
    while stack:
        node, path, depth = stack.pop()
        count += 1
        if count > 500 or depth > 12:
            raise TemplateError(
                "template component count/depth limit exceeded", template_path=path
            )
        if not isinstance(node, dict):
            continue
        if node.get("type") == "card" and "content" in node:
            stack.append(_ComponentVisit(node["content"], path + ".content", depth + 1))
        elif node.get("type") in ("row", "column"):
            children = node.get("children")
            if isinstance(children, list):
                stack.extend(
                    _ComponentVisit(child, f"{path}.children[{i}]", depth + 1)
                    for i, child in enumerate(children)
                )


class _Builder:
    def __init__(
        self, contracts: Mapping[str, DatasetSchema], data: Mapping[str, Dataset] | None
    ) -> None:
        self.contracts, self.data = contracts, data
        self.paths: dict[str, str] = {}
        self.table_sources: dict[str, str] = {}
        self.location = "report"

    def field(self, dataset: str, field: str) -> FieldSpec:
        if dataset not in self.contracts or field not in self.contracts[dataset].fields:
            raise ValueError("binding names an undeclared dataset or field")
        return self.contracts[dataset].fields[field]

    def values(self, dataset: str, field: str) -> list[Value]:
        spec = self.field(dataset, field)
        if self.data is not None:
            ds = self.data[dataset]
            i = ds.columns.index(field)
            return [row[i] for row in ds.rows]
        samples: dict[str, Value] = {
            "text": "Example",
            "integer": 1,
            "number": 1,
            "decimal": Decimal("1"),
            "date": date(2026, 1, 1),
            "datetime": datetime(2026, 1, 1, tzinfo=UTC),
        }
        return [samples[spec.type]]

    def scalar(
        self,
        value: object,
        *,
        text: bool = False,
        optional: bool = False,
        format: Format = "number",
    ) -> Value:
        if text and (isinstance(value, str) or (optional and value is None)):
            return value
        obj = mapping(value)
        ref = mapping(obj["bind"])
        dataset, field = cast(str, ref["dataset"]), cast(str, ref["field"])
        spec = self.field(dataset, field)
        if self.contracts[dataset].cardinality != "one":
            raise ValueError("scalar binding requires cardinality one")
        if text and (spec.type != "text" or (spec.nullable and not optional)):
            raise ValueError("text binding has incompatible type/nullability")
        self.format_type(spec, format)
        return self.values(dataset, field)[0]

    @staticmethod
    def format_type(spec: FieldSpec, format: Format) -> None:
        if format == "date" and spec.type in ("integer", "number", "decimal"):
            raise ValueError("numeric fields cannot use date display format")

    def text(self, value: object, *, optional: bool = False) -> str | None:
        return cast(str | None, self.scalar(value, text=True, optional=optional))

    def children(self, value: object, path: str, generated: str) -> list[Component]:
        children: list[Component] = []
        for i, child in enumerate(array(value)):
            block = self.node(child, f"{path}.children[{i}]", f"{generated}.{i}")
            children.append(cast(Component, block))
        return children

    def node(self, value: object, path: str, generated: str) -> Block:
        self.location = path
        self.paths[generated] = path
        obj = mapping(value)
        kind = obj.get("type")
        if kind == "page_break":
            return PageBreak()
        if kind == "card":
            title = self.text(obj.get("title"), optional=True)
            content = self.node(
                obj["content"], path + ".content", generated + ".content"
            )
            return Card(cast(CardContent, content), title=title)
        if kind in ("row", "column"):
            children = self.children(obj["children"], path, generated)
            self.location = path
            if kind == "row":
                height = obj.get("height_mm")
                return Row(
                    *children,
                    widths=weights(obj.get("widths")),
                    height_mm=None if height is None else numeric(height),
                )
            return Column(*children, heights=weights(obj.get("heights")))
        if kind == "text":
            return Text(
                cast(str, self.text(obj["text"])),
                cast(Literal["body", "heading", "caption"], obj.get("style", "body")),
            )
        if kind == "kpi":
            format = fmt(obj.get("format", "number"))
            return KPI(
                cast(str, self.text(obj["label"])),
                self.scalar(obj["value"], format=format),
                format,
                self.text(obj.get("note"), optional=True),
            )
        if kind == "table":
            return self.table(obj, generated)
        if kind in ("bar", "line", "funnel"):
            return self.chart(obj, kind)
        raise ValueError("unknown component type")

    def table(self, obj: Mapping[str, object], generated: str) -> Table:
        dataset = cast(str, obj["dataset"])
        if dataset not in self.contracts:
            raise ValueError("table names an undeclared dataset")
        columns: list[TableColumn] = []
        for raw in array(obj["columns"]):
            col = mapping(raw)
            key = cast(str, col["key"])
            format = fmt(col.get("format", "number"))
            self.format_type(self.field(dataset, key), format)
            width = col.get("width")
            columns.append(
                TableColumn(
                    key,
                    cast(str, col["label"]),
                    format,
                    cast(Literal["left", "center", "right"], col.get("align", "left")),
                    None if width is None else numeric(width),
                )
            )
        values = {col.key: self.values(dataset, col.key) for col in columns}
        rows = [
            {col.key: values[col.key][i] for col in columns}
            for i in range(len(next(iter(values.values()), [])))
        ]
        self.table_sources[generated] = dataset
        return Table(
            columns,
            rows,
            None if obj.get("empty_text") is None else cast(str, obj["empty_text"]),
        )

    def chart(
        self, obj: Mapping[str, object], kind: str
    ) -> BarChart | LineChart | Funnel:
        axis = "x" if kind == "line" else "category"
        dataset, axis_field = cast(str, obj["dataset"]), cast(str, obj[axis])
        axis_spec = self.field(dataset, axis_field)
        x_kind: Literal["category", "date"] = cast(
            Literal["category", "date"], obj.get("x_kind", "category")
        )
        allowed = (
            ("text", "date", "datetime")
            if kind == "bar"
            else ("date", "datetime")
            if kind == "line" and x_kind == "date"
            else ("text",)
        )
        if axis_spec.type not in allowed or axis_spec.nullable:
            raise ValueError("incompatible category/x field")
        specs = (
            [{"field": obj["value"], "label": ""}]
            if "value" in obj
            else array(obj["series"])
        )
        series: dict[str, list[Number | None]] = {}
        for raw in specs:
            spec = mapping(raw)
            field, label = cast(str, spec["field"]), cast(str, spec["label"])
            field_spec = self.field(dataset, field)
            if field_spec.type not in ("integer", "number", "decimal") or (
                field_spec.nullable and kind != "line"
            ):
                raise ValueError("incompatible chart value field")
            if label in series:
                raise ValueError("duplicate chart series labels")
            series[label] = cast(list[Number | None], self.values(dataset, field))
        x = self.values(dataset, axis_field)
        format = fmt(obj.get("value_format", "number"))
        if kind == "line":
            return LineChart(
                cast(list[str | date | datetime], x),
                values=next(iter(series.values())) if "value" in obj else None,
                series=series if "series" in obj else None,
                x_kind=x_kind,
                axes=cast(bool, obj.get("axes", True)),
                markers=cast(bool, obj.get("markers", True)),
                fill=cast(Literal["none", "zero"], obj.get("fill", "none")),
                legend=cast(bool, obj.get("legend", True)),
                value_format=format,
            )
        numbers = cast(dict[str, list[Number]], series)
        if kind == "bar":
            return BarChart(
                cast(list[str | date | datetime], x),
                values=next(iter(numbers.values())) if "value" in obj else None,
                series=numbers if "series" in obj else None,
                orientation=cast(
                    Literal["vertical", "horizontal"],
                    obj.get("orientation", "vertical"),
                ),
                mode=cast(Literal["grouped", "stacked"], obj.get("mode", "grouped")),
                color_by=cast(
                    Literal["series", "category"], obj.get("color_by", "series")
                ),
                legend_position=cast(
                    Literal["bottom", "left"], obj.get("legend_position", "bottom")
                ),
                category_labels=cast(bool, obj.get("category_labels", True)),
                show_labels=cast(bool, obj.get("show_labels", False)),
                legend=cast(bool, obj.get("legend", True)),
                value_format=format,
            )
        return Funnel(
            cast(list[str], x),
            next(iter(numbers.values())),
            show_labels=cast(bool, obj.get("show_labels", True)),
            value_format=format,
        )

    def build(self, value: object) -> Report:
        obj = mapping(value)
        page = mapping(obj.get("page", {}))
        size = page.get("size", Page.size)
        page_size: Literal["A4", "A3", "Letter"] | tuple[float, float]
        if isinstance(size, (list, tuple)):
            dimensions = array(size)
            page_size = (numeric(dimensions[0]), numeric(dimensions[1]))
        else:
            page_size = cast(Literal["A4", "A3", "Letter"], size)
        theme = mapping(obj.get("theme", {}))
        formatting = None
        if "formatting" in obj:
            self.location = "report.formatting"
            raw = mapping(obj["formatting"])

            formatting = Formatting(
                decimal=cast(Literal[".", ","], raw.get("decimal", Formatting.decimal)),
                group=cast(
                    Literal[",", ".", "'", "space", "none"],
                    raw.get("group", Formatting.group),
                ),
                number_decimals=cast(
                    int, raw.get("number_decimals", Formatting.number_decimals)
                ),
                percent_decimals=cast(
                    int, raw.get("percent_decimals", Formatting.percent_decimals)
                ),
                currency_decimals=cast(
                    int, raw.get("currency_decimals", Formatting.currency_decimals)
                ),
                date_format=cast(
                    str | None, raw.get("date_format", Formatting.date_format)
                ),
                datetime_format=cast(
                    str | None, raw.get("datetime_format", Formatting.datetime_format)
                ),
                locale=cast(str | None, raw.get("locale", Formatting.locale)),
            )
        self.location = "report.language"
        language = cast(str, obj.get("language", "en"))
        self.location = "report.empty_text"
        empty_text = (
            None if obj.get("empty_text") is None else cast(str, obj["empty_text"])
        )
        self.location = "report"
        report = Report(
            cast(str, self.text(obj.get("title", ""))),
            subtitle=cast(str, self.text(obj.get("subtitle", ""))),
            language=language,
            formatting=formatting,
            empty_text=empty_text,
            mode=cast(Literal["dashboard", "flow"], obj.get("mode", "dashboard")),
            page=Page(
                page_size,
                cast(
                    Literal["portrait", "landscape"],
                    page.get("orientation", Page.orientation),
                ),
                numeric(page.get("margin_mm", Page.margin_mm)),
            ),
            theme=Theme(
                accent=cast(str, theme.get("accent", Theme.accent)),
                background=cast(str, theme.get("background", Theme.background)),
                card_background=cast(
                    str, theme.get("card_background", Theme.card_background)
                ),
                text=cast(str, theme.get("text", Theme.text)),
                gap_mm=numeric(theme.get("gap_mm", Theme.gap_mm)),
                padding_mm=numeric(theme.get("padding_mm", Theme.padding_mm)),
                font_size_pt=numeric(theme.get("font_size_pt", Theme.font_size_pt)),
                chart_height_mm=numeric(
                    theme.get("chart_height_mm", Theme.chart_height_mm)
                ),
                kpi_value_size_pt=numeric(
                    theme.get("kpi_value_size_pt", Theme.kpi_value_size_pt)
                ),
            ),
        )
        for i, block in enumerate(array(obj["blocks"])):
            report.add(self.node(block, f"report.blocks[{i}]", f"blocks.{i}"))
        report.validate()
        return report

    def location_for(
        self, error: Exception
    ) -> tuple[str | None, str | None, int | None, str | None]:
        prefix = str(error).split(": ", 1)[0]
        if prefix in (
            "title",
            "subtitle",
            "mode",
            "language",
            "formatting",
            "empty_text",
        ) or prefix.startswith(("theme.", "page.", "formatting.")):
            return "report." + prefix, None, None, None
        candidates = [
            p for p in self.paths if prefix == p or prefix.startswith(p + ".")
        ]
        if not candidates:
            return None, None, None, None
        generated = max(candidates, key=len)
        path = self.paths[generated]
        dataset = self.table_sources.get(generated)
        suffix = prefix[len(generated) :]
        if suffix in (".value", ".label", ".note", ".title", ".text"):
            path += suffix
        if dataset and suffix.startswith(".rows."):
            parts = suffix.split(".", 3)
            if (
                len(parts) == 4
                and parts[2].isdigit()
                and parts[3] in self.contracts[dataset].fields
            ):
                return path, dataset, int(parts[2]), parts[3]
        return path, dataset, None, None


@dataclass(frozen=True, init=False, eq=False)
class ReportTemplate:
    _encoded: str = dataclass_field(repr=False)
    datasets: Mapping[str, DatasetSchema]

    def __init__(self, spec: Mapping[str, object]) -> None:
        error_builder: _Builder | None = None
        try:
            check_tree(spec)
            encoded = json.dumps(
                plain_tree(spec),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            if len(encoded.encode("utf-8")) > MAX_TEMPLATE_BYTES:
                raise ValueError("template byte limit exceeded")
            root = mapping(load_json(encoded, MAX_TEMPLATE_BYTES))
            _component_limits(root.get("report"))
            validate_structure("template", root)
            contracts = schemas(root["datasets"])
            builder = _Builder(contracts, None)
            error_builder = builder
            builder.build(root["report"])
        except TemplateError:
            raise
        except (
            ValueError,
            TypeError,
            RecursionError,
            UnicodeError,
            DataError,
            ValidationError,
        ) as exc:
            raise TemplateError(
                "invalid template: " + str(exc),
                template_path=(
                    error_builder.location_for(exc)[0]
                    if isinstance(exc, ValidationError)
                    else error_builder.location
                )
                if error_builder
                else None,
            ) from exc
        object.__setattr__(self, "_encoded", encoded)
        object.__setattr__(self, "datasets", contracts)

    @classmethod
    def from_dict(cls, spec: Mapping[str, object]) -> "ReportTemplate":
        return cls(spec)

    @classmethod
    def from_json(cls, source: str | bytes) -> "ReportTemplate":
        try:
            return cls(mapping(load_json(source, MAX_TEMPLATE_BYTES)))
        except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
            raise TemplateError("invalid template JSON") from exc

    @classmethod
    def from_yaml(cls, source: str | bytes) -> "ReportTemplate":
        from ._yaml import load_yaml

        try:
            return cls(mapping(load_yaml(source, MAX_TEMPLATE_BYTES)))
        except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
            raise TemplateError("invalid template YAML") from exc

    def to_yaml(self) -> str:
        from ._yaml import dump_yaml

        try:
            return dump_yaml(self.to_dict(), MAX_TEMPLATE_BYTES)
        except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
            raise TemplateError("unable to serialize template YAML") from exc

    def to_dict(self) -> dict[str, object]:
        return mapping(load_json(self._encoded, MAX_TEMPLATE_BYTES))

    def to_json(self) -> str:
        return self._encoded

    def bind(
        self, data: Mapping[str, Dataset], *, limits: DataLimits = DEFAULT_LIMITS
    ) -> Report:
        try:
            validate_bundle(data, limits)
        except DataError as exc:
            raise BindingError(
                str(exc), dataset=exc.dataset, row=exc.row, field=exc.field
            ) from exc
        for dataset, schema in self.datasets.items():
            if dataset not in data:
                raise BindingError("missing required dataset", dataset=dataset)
            try:
                schema.validate(data[dataset])
            except DataError as exc:
                raise BindingError(
                    str(exc), dataset=dataset, row=exc.row, field=exc.field
                ) from exc
        builder = _Builder(self.datasets, data)
        try:
            return builder.build(self.to_dict()["report"])
        except (ValueError, TypeError, ValidationError) as exc:
            path, error_dataset, row, field = builder.location_for(exc)
            raise BindingError(
                str(exc),
                dataset=error_dataset,
                row=row,
                field=field,
                template_path=path,
            ) from exc
