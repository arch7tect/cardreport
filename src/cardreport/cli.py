"""Render and validate JSON/YAML templates with named datasets."""

import argparse
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Literal

from . import (
    DataError,
    Dataset,
    ReportError,
    ReportTemplate,
    WeasyPrintRenderer,
    datasets_from_json,
    datasets_from_yaml,
    json_schema,
)
from ._inputs import LocatedError
from .adapters.csv import from_csv
from .data import DEFAULT_LIMITS
from .templates import MAX_TEMPLATE_BYTES


class _Arguments(argparse.Namespace):
    command: str
    kind: Literal["template", "data"]
    template: Path
    data: Path | None
    csv: list[Path]
    csv_as: list[list[str]]
    csv_encoding: str
    csv_delimiter: str
    csv_null: list[str]
    output: Path
    overwrite: bool
    renderer: str
    timeout: float


def _timeout(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected seconds in (0, 300]") from exc
    if not 0 < seconds <= 300:
        raise argparse.ArgumentTypeError("expected seconds in (0, 300]")
    return seconds


def _delimiter(value: str) -> str:
    if len(value) != 1:
        raise argparse.ArgumentTypeError("expected one delimiter character")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cardreport", description=__doc__, allow_abbrev=False
    )
    parser.add_argument("--version", action="version", version=version("cardreport"))
    commands = parser.add_subparsers(dest="command", required=True)
    render = commands.add_parser(
        "render", help="render to HTML or PDF", allow_abbrev=False
    )
    _input_arguments(render)
    validate = commands.add_parser(
        "validate",
        help="validate template and optional data; no layout check",
        allow_abbrev=False,
    )
    _input_arguments(validate)
    schema = commands.add_parser(
        "schema", help="print an installed JSON Schema", allow_abbrev=False
    )
    schema.add_argument("kind", choices=("template", "data"))
    render.add_argument(
        "--output", type=Path, required=True, help="destination .html or .pdf"
    )
    render.add_argument(
        "--renderer", choices=("chromium", "weasyprint"), default="chromium"
    )
    render.add_argument(
        "--timeout",
        type=_timeout,
        default=30,
        help="PDF export seconds in (0, 300] (default: 30)",
    )
    render.add_argument(
        "--overwrite", action="store_true", help="replace an existing output file"
    )
    return parser


def _input_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--template", type=Path, required=True, help="template JSON or YAML file"
    )
    parser.add_argument(
        "--data", type=Path, help="cardreport.data/1 JSON or YAML bundle"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        action="append",
        default=[],
        metavar="PATH",
        help="CSV file; dataset name is its filename without the last suffix (repeatable)",
    )
    parser.add_argument(
        "--csv-as",
        nargs=2,
        action="append",
        default=[],
        metavar=("NAME", "PATH"),
        help="CSV file with an explicit dataset name (repeatable)",
    )
    parser.add_argument(
        "--csv-encoding", default="utf-8", help="all CSV files (default: utf-8)"
    )
    parser.add_argument(
        "--csv-delimiter",
        type=_delimiter,
        default=",",
        help="all CSV files (default: comma)",
    )
    parser.add_argument(
        "--csv-null",
        action="append",
        default=[],
        metavar="TOKEN",
        help="CSV null token (repeatable; none by default)",
    )


def _read(path: Path, limit: int) -> bytes:
    with path.open("rb") as source:
        payload = source.read(limit + 1)
    if len(payload) > limit:
        raise DataError(f"{path}: input byte limit exceeded ({limit})")
    return payload


def _csv_inputs(args: _Arguments) -> list[tuple[str, Path]]:
    return [(path.stem, path) for path in args.csv] + [
        (name, Path(path)) for name, path in args.csv_as
    ]


def _load_inputs(args: _Arguments) -> tuple[ReportTemplate, dict[str, Dataset]]:
    csv_inputs = _csv_inputs(args)
    read_template = (
        ReportTemplate.from_yaml
        if args.template.suffix.lower() in (".yaml", ".yml")
        else ReportTemplate.from_json
    )
    template = read_template(_read(args.template, MAX_TEMPLATE_BYTES))
    sources: dict[str, Path] = {}
    for name, path in csv_inputs:
        if name not in template.datasets:
            raise ValueError(
                f"{path}: dataset {name!r} is not declared by the template; "
                "use --csv-as NAME PATH to choose its name"
            )
        if name in sources:
            raise ValueError(
                f"duplicate CSV dataset {name!r}: {sources[name]} and {path}"
            )
        sources[name] = path
    datasets: dict[str, Dataset] = (
        (
            datasets_from_yaml
            if args.data.suffix.lower() in (".yaml", ".yml")
            else datasets_from_json
        )(_read(args.data, DEFAULT_LIMITS.max_json_bytes))
        if args.data is not None
        else {}
    )
    for name in sources:
        if name in datasets:
            raise ValueError(f"dataset {name!r} supplied by both --data and CSV")
    for name, path in sources.items():
        try:
            datasets[name] = from_csv(
                path,
                schema=template.datasets[name],
                encoding=args.csv_encoding,
                delimiter=args.csv_delimiter,
                null_values=args.csv_null,
            )
        except DataError as exc:
            raise DataError(
                f"{path}: {exc}",
                dataset=name,
                row=exc.row,
                field=exc.field,
                template_path=exc.template_path,
            ) from exc.__cause__
    return template, datasets


def _render(args: _Arguments) -> Path:
    suffix = args.output.suffix.lower()
    if suffix not in (".html", ".pdf"):
        raise ValueError("--output must end in .html or .pdf")
    csv_inputs = _csv_inputs(args)
    inputs = [args.template, *(path for _, path in csv_inputs)]
    if args.data is not None:
        inputs.append(args.data)
    for source in inputs:
        if args.output.resolve() == source.resolve() or (
            args.output.exists() and source.exists() and args.output.samefile(source)
        ):
            raise ValueError(f"output must not replace an input file: {source}")
    if not args.overwrite and (args.output.exists() or args.output.is_symlink()):
        raise FileExistsError(
            f"{args.output}: output exists; use --overwrite to replace it"
        )
    template, datasets = _load_inputs(args)
    report = template.bind(datasets)
    renderer = WeasyPrintRenderer() if args.renderer == "weasyprint" else None
    if suffix == ".pdf":
        return report.write_pdf(
            args.output,
            overwrite=args.overwrite,
            renderer=renderer,
            timeout=args.timeout,
        )
    return report.write_html(args.output, overwrite=args.overwrite, renderer=renderer)


def _error_message(exc: Exception) -> str:
    message = str(exc)
    context: list[str] = []
    if isinstance(exc, LocatedError):
        if exc.dataset is not None:
            context.append(f"dataset {exc.dataset!r}")
        if exc.row is not None:
            context.append(f"data row {exc.row + 1}")
        if exc.field is not None:
            context.append(f"field {exc.field!r}")
        if exc.template_path is not None:
            context.append(f"template {exc.template_path}")
    if context:
        message += " (" + ", ".join(context) + ")"
    if exc.__cause__ is not None:
        cause = str(exc.__cause__)
        if cause and cause not in message:
            message += ": " + cause
    return message


def main(argv: list[str] | None = None) -> int:
    """Command entry point; return an exit status after parsing arguments."""
    args = _Arguments()
    _parser().parse_args(argv, namespace=args)
    try:
        if args.command == "schema":
            print(json_schema(args.kind), end="")
            return 0
        if args.command == "validate":
            template, datasets = _load_inputs(args)
            if args.data is not None or args.csv or args.csv_as:
                template.bind(datasets)
                print("Template and data valid; layout has not been checked")
            else:
                print("Template valid; data and layout have not been checked")
            return 0
        path = _render(args)
    except (ReportError, OSError, ValueError) as exc:
        print(f"cardreport: error: {_error_message(exc)}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("cardreport: interrupted", file=sys.stderr)
        return 130
    print(path)
    return 0
