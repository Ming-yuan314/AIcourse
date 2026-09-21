#!/usr/bin/env python3
"""Validate PatientPheX sources, write work copies, and create article folds."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from patientphex.common.io import load_jsonl
from patientphex.common.preparation import (
    build_manifest,
    create_article_folds,
    prepare_dataset,
)


def _is_official_download(path: Path) -> bool:
    parts = path.resolve(strict=False).parts
    return any(parts[index : index + 2] == ("downloads", "PatientData") for index in range(len(parts) - 1))


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", required=True, type=Path)
    parser.add_argument("--a-list", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260915)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if _is_official_download(args.output_dir):
            raise ValueError("refusing to write outputs inside immutable downloads/PatientData")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        train_output = args.output_dir / "documents.jsonl"
        a_output = args.output_dir / "a-documents.jsonl"
        train_summary = prepare_dataset(args.train, train_output)
        a_summary = prepare_dataset(args.a_list, a_output)
        train_documents = load_jsonl(train_output)
        folds = create_article_folds(train_documents, n_folds=args.folds, seed=args.seed)
        _write_json_atomic(
            args.output_dir / "folds.json",
            folds.to_dict(source_sha256=train_summary.input_sha256),
        )
        manifest = build_manifest(
            train_summary,
            a_summary,
            folds=folds,
            hpo_version="v2026-06-23",
            git_commit=_git_commit(),
        )
        _write_json_atomic(args.output_dir / "manifest.json", manifest)
    except Exception as error:  # noqa: BLE001 - CLI must return a useful non-zero status.
        print(f"prepare_data: error: {error}", file=sys.stderr)
        return 1

    print(
        f"Train documents: {train_summary.documents}; "
        f"patients: {train_summary.patients}; "
        f"patient mentions: {train_summary.patient_mentions}; "
        f"entities: {train_summary.entities}; "
        f"associations: {train_summary.associations}"
    )
    print(
        f"A-list documents: {a_summary.documents}; "
        f"patients: {a_summary.patients}; "
        f"patient mentions: {a_summary.patient_mentions}; "
        f"entities: {a_summary.entities}; "
        f"associations: {a_summary.associations}"
    )
    print(f"Wrote processed data and {folds.n_folds} article folds to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
