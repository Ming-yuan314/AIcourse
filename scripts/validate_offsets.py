#!/usr/bin/env python3
"""Validate global offsets in a PatientPheX JSONL file."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from patientphex.common.io import JSONLReadError, read_jsonl  # noqa: E402
from patientphex.common.offsets import validate_document_spans  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 JSONL document file")
    args = parser.parse_args()

    documents = []
    try:
        documents = list(read_jsonl(args.input))
    except (JSONLReadError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    patient_mentions = sum(len(patient.mention) for document in documents for patient in document.patient)
    entities = sum(len(document.entities) for document in documents)
    issues = [issue for document in documents for issue in validate_document_spans(document)]
    total_spans = patient_mentions + entities

    print(f"Documents: {len(documents)}")
    print(f"Patient mentions: {patient_mentions}")
    print(f"Entities: {entities}")
    print(f"Valid spans: {total_spans - len(issues)}")
    print(f"Invalid spans: {len(issues)}")
    for issue in issues:
        print(f"{issue.error_code}: {issue.message}", file=sys.stderr)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())