"""Measure installed-package data loading and binding using synthetic tables."""

import argparse
import gc
import hashlib
import json
import platform
from datetime import UTC, date, datetime
from decimal import Decimal
from importlib.metadata import version
from statistics import median
from time import perf_counter

from cardreport import (
    Dataset,
    ReportTemplate,
    datasets_from_json,
    datasets_from_yaml,
    datasets_to_json,
    datasets_to_yaml,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=7)
    parser.add_argument("--format", choices=("json", "yaml", "both"), default="both")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    for kind in ("numeric", "typed"):
        values = (
            [42]
            if kind == "numeric"
            else [
                Decimal("12.50"),
                date(2026, 11, 5),
                datetime(2026, 11, 5, tzinfo=UTC),
            ]
        )
        types = ["integer"] if kind == "numeric" else ["decimal", "date", "datetime"]
        columns = [f"c{i}" for i in range(100)]
        row = [values[i % len(values)] for i in range(100)]
        data = {"x": Dataset(columns, [row] * 1000)}
        template = ReportTemplate(
            {
                "format": "cardreport.template/1",
                "datasets": {
                    "x": {
                        "cardinality": "many",
                        "fields": {
                            col: {"type": types[i % len(types)]}
                            for i, col in enumerate(columns)
                        },
                    }
                },
                "report": {"blocks": []},
            }
        )
        for syntax, encode, decode in (
            ("json", datasets_to_json, datasets_from_json),
            ("yaml", datasets_to_yaml, datasets_from_yaml),
        ):
            if args.format not in (syntax, "both"):
                continue
            source = encode(data)
            load_times, bind_times = [], []
            for _ in range(args.repeat):
                gc.collect()
                start = perf_counter()
                loaded = decode(source)
                load_times.append(perf_counter() - start)
                start = perf_counter()
                template.bind(loaded)
                bind_times.append(perf_counter() - start)
                assert loaded["x"].rows == data["x"].rows
            print(
                json.dumps(
                    {
                        "version": version("cardreport"),
                        "python": platform.python_version(),
                        "platform": platform.platform(),
                        "kind": kind,
                        "format": syntax,
                        "cells": 100000,
                        "source_bytes": len(source.encode()),
                        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                        "load_seconds": load_times,
                        "bind_seconds": bind_times,
                        "median_load_seconds": median(load_times),
                        "median_load_bind_seconds": median(
                            a + b for a, b in zip(load_times, bind_times, strict=True)
                        ),
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
