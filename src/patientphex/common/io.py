"""Strict UTF-8 JSONL reader for PatientPheX documents."""
from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .schema import Document, SchemaError


class JSONLReadError(ValueError):
    """A JSON or schema error annotated with source path and line number."""

    def __init__(self, path: Path, line_number: int, message: str) -> None:
        self.path = path
        self.line_number = line_number
        super().__init__(f"{path}: line {line_number}: {message}")


def read_jsonl(path: str | Path) -> Iterator[Document]:
    """Yield validated documents from a UTF-8 JSONL file in source order."""
    source = Path(path)
    with source.open("r", encoding="utf-8", newline="") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                raise JSONLReadError(source, line_number, "blank lines are not allowed")
            try:
                value: Any = json.loads(raw_line)
            except json.JSONDecodeError as error:
                raise JSONLReadError(source, line_number, f"invalid JSON: {error.msg}") from error
            try:
                yield Document.from_dict(value)
            except SchemaError as error:
                raise JSONLReadError(source, line_number, str(error)) from error


def load_jsonl(path: str | Path) -> list[Document]:
    """Read all validated documents into a list."""
    return list(read_jsonl(path))


__all__ = ["JSONLReadError", "load_jsonl", "read_jsonl"]