"""Packaged structural contracts shared by runtime loaders and editors."""

from importlib.resources import files
from typing import Literal


def json_schema(kind: Literal["template", "data"]) -> str:
    """Return the installed schema as JSON text without network access."""
    if kind not in ("template", "data"):
        raise ValueError("schema kind must be template or data")
    return files(__package__).joinpath(f"{kind}-1.json").read_text(encoding="utf-8")
