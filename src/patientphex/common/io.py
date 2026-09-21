"""Strict UTF-8 JSONL reader and atomic writer for PatientPheX documents."""
from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from .schema import Document, SchemaError


class JSONLReadError(ValueError):
    """A JSON or schema error annotated with source path and line number."""

    def __init__(self, path: Path, line_number: int, message: str) -> None:
        self.path = path
        self.line_number = line_number
        super().__init__(f"{path}: line {line_number}: {message}")


def _is_official_download(path: Path) -> bool:
    """Return whether ``path`` is inside the immutable official download tree."""
    resolved = path.resolve(strict=False)
    parts = resolved.parts
    for index in range(len(parts) - 1):
        if parts[index] == "downloads" and parts[index + 1] == "PatientData":
            return True
    return False


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


def write_jsonl(path: str | Path, documents: Iterable[Document]) -> None:
    """Atomically write documents as UTF-8 JSONL in the given iteration order.

    The immutable official download directory is deliberately rejected as a
    destination.  A temporary file is fsynced in the destination directory and
    replaced into place only after every document has serialized successfully.
    """
    destination = Path(path)
    if _is_official_download(destination):
        raise ValueError(f"refusing to write inside immutable downloads/PatientData: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            for document in documents:
                json.dump(document.to_dict(), handle, ensure_ascii=False, separators=(",", ":"))
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


__all__ = ["JSONLReadError", "load_jsonl", "read_jsonl", "write_jsonl"]
