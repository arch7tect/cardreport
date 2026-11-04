"""Versioned presentation definitions bound to existing concrete components."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import UTC, date, datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Literal, cast

from ._inputs import (
    BindingError,
    DataError,
    TemplateError,
    array,
    check_tree,
    keys,
    load_json,
    mapping,
    name,
    plain_tree,
)
from .data import (
    DEFAULT_LIMITS,
    DataLimits,
    Dataset,
    DatasetSchema,
    FieldSpec,
    FieldType,
    validate_bundle,
)
from .model import (
    KPI,
    BarChart,
    Block,
    Card,
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


def string(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("expected text")
    return value


def boolean(value: object) -> bool:
    if type(value) is not bool:
        raise ValueError("expected boolean")
    return value


def numeric(value: object) -> float:
    return number(value, "setting")


def weights(value: object) -> list[float] | None:
    return None if value is None else [numeric(v) for v in array(value)]


def choice[T: str](value: object, options: tuple[T, ...]) -> T:
    if value not in options:
        raise ValueError("invalid option")
    return value


def fmt(value: object) -> Format:
    if isinstance(value, dict):
        obj = mapping(value)
        keys(obj, {"currency"}, set())
        result: Format = Currency(string(obj["currency"]))
    else:
        result = cast(Format, choice(value, ("number", "integer", "percent", "date")))
    check_format(result, "format")
    return result


def schemas(value: object) -> Mapping[str, DatasetSchema]:
    raw = mapping(value)
    if len(raw) > DEFAULT_LIMITS.max_datasets:
        raise ValueError("dataset schema count exceeded")
    result: dict[str, DatasetSchema] = {}
    for dataset, value in raw.items():
        name(dataset)
        obj = mapping(value)
        keys(obj, {"cardinality", "fields"}, set())
        fields: dict[str, FieldSpec] = {}
        for field, spec in mapping(obj["fields"]).items():
            raw_field = mapping(spec)
            keys(raw_field, {"type"}, {"nullable"})
            fields[name(field)] = FieldSpec(
                cast(FieldType, string(raw_field["type"])),
                boolean(raw_field.get("nullable", False)),
            )
        result[dataset] = DatasetSchema(
            fields, choice(obj["cardinality"], ("one", "many"))
        )
    return MappingProxyType(result)


class _Builder:
    def __init__(
        self, contracts: Mapping[str, DatasetSchema], data: Mapping[str, Dataset] | None
    ) -> None:
        self.contracts, self.data = contracts, data
        self.paths: dict[str, str] = {}
        self.table_sources: dict[str, str] = {}
        self.count = 0
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
        keys(obj, {"bind"}, set())
        ref = mapping(obj["bind"])
        keys(ref, {"dataset", "field"}, set())
        dataset, field = name(ref["dataset"]), name(ref["field"])
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

    def children(
        self, value: object, path: str, generated: str, depth: int
    ) -> list[Component]:
        children: list[Component] = []
        for i, child in enumerate(array(value)):
            block = self.node(
                child, f"{path}.children[{i}]", f"{generated}.{i}", depth + 1
            )
            if isinstance(block, PageBreak):
                raise ValueError("PageBreak must be top-level")
            children.append(block)
        return children

    def node(self, value: object, path: str, generated: str, depth: int = 0) -> Block:
        self.location = path
        self.paths[generated] = path
        self.count += 1
        if self.count > 500 or depth > 12:
            raise ValueError("template component count/depth limit exceeded")
        obj = mapping(value)
        kind = obj.get("type")
        if kind == "page_break":
            keys(obj, {"type"}, set())
            return PageBreak()
        if kind == "card":
            keys(obj, {"type", "content"}, {"title"})
            title = self.text(obj.get("title"), optional=True)
            content = self.node(
                obj["content"], path + ".content", generated + ".content", depth + 1
            )
            if isinstance(content, (Card, PageBreak)):
                raise ValueError("invalid direct card content")
            return Card(content, title=title)
        if kind in ("row", "column"):
            keys(
                obj,
                {"type", "children"},
                {"widths", "height_mm"} if kind == "row" else {"heights"},
            )
            children = self.children(obj["children"], path, generated, depth)
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
            keys(obj, {"type", "text"}, {"style"})
            return Text(
                cast(str, self.text(obj["text"])),
                choice(obj.get("style", "body"), ("body", "heading", "caption")),
            )
        if kind == "kpi":
            keys(obj, {"type", "label", "value"}, {"format", "note"})
            format = fmt(obj.get("format", "number"))
            return KPI(
                cast(str, self.text(obj["label"])),
                self.scalar(obj["value"], format=format),
                format,
                self.text(obj.get("note"), optional=True),
            )
        if kind == "table":
            keys(obj, {"type", "dataset", "columns"}, {"empty_text"})
            dataset = name(obj["dataset"])
            if dataset not in self.contracts:
                raise ValueError("table names an undeclared dataset")
            columns: list[TableColumn] = []
            for raw in array(obj["columns"]):
                col = mapping(raw)
                keys(col, {"key", "label"}, {"format", "align", "width"})
                key = name(col["key"])
                format = fmt(col.get("format", "number"))
                self.format_type(self.field(dataset, key), format)
                width = col.get("width")
                columns.append(
                    TableColumn(
                        key,
                        string(col["label"]),
                        format,
                        choice(col.get("align", "left"), ("left", "center", "right")),
                        None if width is None else numeric(width),
                    )
                )
            values = {col.key: self.values(dataset, col.key) for col in columns}
            rows = [
                {col.key: values[col.key][i] for col in columns}
                for i in range(len(next(iter(values.values()), [])))
            ]
            self.table_sources[generated] = dataset
            return Table(columns, rows, string(obj.get("empty_text", "No data")))
        if kind in ("bar", "line", "funnel"):
            axis = "x" if kind == "line" else "category"
            options = {"value_format", "value"}
            if kind != "funnel":
                options |= {"series", "legend"}
            if kind != "line":
                options |= {"show_labels"}
            if kind == "bar":
                options |= {"orientation", "mode"}
            if kind == "line":
                options |= {"x_kind"}
            keys(obj, {"type", "dataset", axis}, options)
            dataset, axis_field = name(obj["dataset"]), name(obj[axis])
            axis_spec = self.field(dataset, axis_field)
            x_kind: Literal["category", "date"] = choice(
                obj.get("x_kind", "category"), ("category", "date")
            )
            allowed = (
                ("date", "datetime")
                if kind == "line" and x_kind == "date"
                else ("text",)
            )
            if axis_spec.type not in allowed or axis_spec.nullable:
                raise ValueError("incompatible category/x field")
            if ("value" in obj) == ("series" in obj):
                raise ValueError("chart requires exactly one of value or series")
            specs = (
                [{"field": obj["value"], "label": ""}]
                if "value" in obj
                else array(obj["series"])
            )
            if not 1 <= len(specs) <= 8:
                raise ValueError("chart requires 1..8 series")
            series: dict[str, list[Number | None]] = {}
            for raw in specs:
                spec = mapping(raw)
                keys(spec, {"field", "label"}, set())
                field, label = name(spec["field"]), string(spec["label"])
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
            if format == "date":
                raise ValueError("charts require numeric display format")
            if kind == "line":
                return LineChart(
                    cast(list[str | date | datetime], x),
                    values=next(iter(series.values())) if "value" in obj else None,
                    series=series if "series" in obj else None,
                    x_kind=x_kind,
                    legend=boolean(obj.get("legend", True)),
                    value_format=format,
                )
            numbers = cast(dict[str, list[Number]], series)
            if kind == "bar":
                return BarChart(
                    cast(list[str], x),
                    values=next(iter(numbers.values())) if "value" in obj else None,
                    series=numbers if "series" in obj else None,
                    orientation=choice(
                        obj.get("orientation", "vertical"), ("vertical", "horizontal")
                    ),
                    mode=choice(obj.get("mode", "grouped"), ("grouped", "stacked")),
                    show_labels=boolean(obj.get("show_labels", False)),
                    legend=boolean(obj.get("legend", True)),
                    value_format=format,
                )
            return Funnel(
                cast(list[str], x),
                next(iter(numbers.values())),
                show_labels=boolean(obj.get("show_labels", True)),
                value_format=format,
            )
        raise ValueError("unknown component type")

    def build(self, value: object) -> Report:
        obj = mapping(value)
        keys(obj, {"blocks"}, {"title", "subtitle", "mode", "page", "theme"})
        page = mapping(obj.get("page", {}))
        keys(page, set(), {"size", "orientation", "margin_mm"})
        size = page.get("size", "A4")
        page_size: Literal["A4", "A3", "Letter"] | tuple[float, float]
        if isinstance(size, (list, tuple)):
            dimensions = array(size)
            if len(dimensions) != 2:
                raise ValueError("page needs two dimensions")
            page_size = (numeric(dimensions[0]), numeric(dimensions[1]))
        else:
            page_size = cast(
                Literal["A4", "A3", "Letter"], choice(size, ("A4", "A3", "Letter"))
            )
        theme = mapping(obj.get("theme", {}))
        keys(
            theme,
            set(),
            {
                "accent",
                "background",
                "card_background",
                "text",
                "gap_mm",
                "padding_mm",
                "font_size_pt",
                "chart_height_mm",
            },
        )
        report = Report(
            cast(str, self.text(obj.get("title", ""))),
            subtitle=cast(str, self.text(obj.get("subtitle", ""))),
            mode=choice(obj.get("mode", "dashboard"), ("dashboard", "flow")),
            page=Page(
                page_size,
                choice(page.get("orientation", "portrait"), ("portrait", "landscape")),
                numeric(page.get("margin_mm", 10)),
            ),
            theme=Theme(
                accent=string(theme.get("accent", "#20a6c4")),
                background=string(theme.get("background", "#f5f5f5")),
                card_background=string(theme.get("card_background", "#ffffff")),
                text=string(theme.get("text", "#222222")),
                gap_mm=numeric(theme.get("gap_mm", 4)),
                padding_mm=numeric(theme.get("padding_mm", 4)),
                font_size_pt=numeric(theme.get("font_size_pt", 10)),
                chart_height_mm=numeric(theme.get("chart_height_mm", 60)),
            ),
        )
        for i, raw in enumerate(array(obj["blocks"])):
            report.add(self.node(raw, f"report.blocks[{i}]", f"blocks.{i}"))
        report.validate()
        return report

    def location_for(
        self, error: Exception
    ) -> tuple[str | None, str | None, int | None, str | None]:
        prefix = str(error).split(": ", 1)[0]
        if prefix in ("title", "subtitle", "mode") or prefix.startswith(
            ("theme.", "page.")
        ):
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
        builder: _Builder | None = None
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
            keys(root, {"format", "datasets", "report"}, set())
            if root["format"] != "cardreport.template/1":
                raise ValueError("unsupported template format")
            contracts = schemas(root["datasets"])
            builder = _Builder(contracts, None)
            builder.build(root["report"])
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
                    builder.location_for(exc)[0]
                    if isinstance(exc, ValidationError)
                    else builder.location
                )
                if builder
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
