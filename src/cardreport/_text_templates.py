"""Jinja text substitution over declared single-row datasets."""

from collections.abc import Mapping
from dataclasses import replace
from datetime import date
from typing import cast

from jinja2 import Environment, StrictUndefined, Undefined, nodes

from .data import Dataset, DatasetSchema, FieldSpec
from .formatting import Formatting
from .model import Currency, Format, check_format, format_value


class _TextEnvironment(Environment):
    def getitem(self, obj: object, argument: object) -> object:
        if isinstance(obj, Mapping) and isinstance(argument, str) and argument in obj:
            return obj[argument]
        return self.undefined(name=str(argument))

    def getattr(self, obj: object, attribute: str) -> object:
        # Dataset keys such as "items" must never resolve to Python attributes.
        return self.getitem(obj, attribute)


class TextTemplates:
    def __init__(
        self,
        contracts: Mapping[str, DatasetSchema],
        data: Mapping[str, Dataset] | None,
        formatting: Formatting | None,
        language: str,
    ) -> None:
        self.contracts = contracts
        self.formatting = formatting
        self.language = language
        self.data = data
        self.context = (
            {
                name: dict(zip(data[name].columns, data[name].rows[0], strict=True))
                for name, contract in contracts.items()
                if contract.cardinality == "one"
            }
            if data is not None
            else {}
        )
        self.env = _TextEnvironment(
            autoescape=False,
            undefined=StrictUndefined,
            finalize=self.format,
            keep_trailing_newline=True,
        )
        self.env.globals.clear()
        self.env.tests.clear()
        self.env.filters.clear()
        self.env.filters.update(
            date=self.date,
            number=self.format,
            integer=lambda value: self.format(value, "integer"),
            percent=lambda value: self.format(value, "percent"),
            currency=lambda value, code: self.format(value, Currency(code)),
        )

    def format(self, value: object, fmt: Format = "number") -> str:
        if isinstance(value, Undefined):
            return str(value)  # Preserve StrictUndefined's missing-field diagnostic.
        return format_value(value, fmt, self.formatting, self.language)

    def date(self, value: object, pattern: str | None = None) -> str:
        formatting = self.formatting
        if pattern is not None:
            formatting = replace(formatting or Formatting(), date_format=pattern)
        return format_value(value, "date", formatting, self.language)

    def _reference(self, node: nodes.Expr) -> FieldSpec:
        parts: list[str] = []
        while isinstance(node, (nodes.Getattr, nodes.Getitem)):
            if isinstance(node, nodes.Getattr):
                parts.append(node.attr)
            elif isinstance(node.arg, nodes.Const) and isinstance(node.arg.value, str):
                parts.append(node.arg.value)
            else:
                raise ValueError("dataset and field keys must be constant strings")
            node = node.node
        if (
            not isinstance(node, nodes.Name)
            or node.name != "datasets"
            or len(parts) != 2
        ):
            raise ValueError("expected datasets.<dataset>.<field>")
        field, dataset = parts
        contract = self.contracts.get(dataset)
        if contract is None or field not in contract.fields:
            raise ValueError(f"undeclared dataset or field: {dataset}.{field}")
        if contract.cardinality != "one":
            raise ValueError("text substitution requires cardinality one")
        return contract.fields[field]

    def _expression(self, node: nodes.Expr) -> str:
        if isinstance(node, nodes.Const) and isinstance(node.value, str):
            return node.value
        if not isinstance(node, nodes.Filter):
            self._reference(node)
            return ""
        if (
            node.name not in self.env.filters
            or node.node is None
            or node.kwargs
            or node.dyn_args is not None
            or node.dyn_kwargs is not None
            or any(
                not isinstance(arg, nodes.Const) or not isinstance(arg.value, str)
                for arg in node.args
            )
        ):
            raise ValueError("unsupported text filter or arguments")
        spec = self._reference(node.node)
        args = [cast(str, cast(nodes.Const, arg).value) for arg in node.args]
        if node.name == "date":
            if spec.type not in ("date", "datetime") or len(args) > 1:
                raise ValueError(
                    "date filter requires a date/datetime and optional pattern"
                )
            self.date(date(2026, 1, 1), args[0] if args else None)
        else:
            if spec.type not in ("integer", "number", "decimal"):
                raise ValueError("numeric filter requires a numeric field")
            if len(args) != (1 if node.name == "currency" else 0):
                raise ValueError(
                    "currency requires a code; other numeric filters take no arguments"
                )
            fmt: Format = (
                Currency(args[0])
                if node.name == "currency"
                else cast(Format, node.name)
            )
            check_format(fmt, "text filter")
        return ""

    def render(self, source: str) -> str:
        if not any(marker in source for marker in ("{{", "{%", "{#")):
            return source
        tree = self.env.parse(source)
        literals: list[str] = []
        for statement in tree.body:
            if not isinstance(statement, nodes.Output):
                raise ValueError(
                    "only text, field substitutions and formatting filters are supported"
                )
            for node in statement.nodes:
                literals.append(
                    node.data
                    if isinstance(node, nodes.TemplateData)
                    else self._expression(node)
                )
        # Samples cannot predict the length or glyphs of the actual bound values.
        if self.data is None:
            return "".join(literals)
        return self.env.from_string(tree).render(datasets=self.context)
