"""Validated PatientPheX preparation and deterministic article folds."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .io import load_jsonl, write_jsonl
from .offsets import SpanIssue, validate_document_spans
from .schema import Document


class PreparationError(ValueError):
    """Raised when a source file cannot become a validated work copy."""


@dataclass(frozen=True, slots=True)
class PreparationSummary:
    input_path: str
    output_path: str
    input_sha256: str
    output_sha256: str
    documents: int
    patients: int
    patient_mentions: int
    entities: int
    associations: int
    invalid_spans: int = 0

    @property
    def document_count(self) -> int:
        return self.documents

    @property
    def patient_count(self) -> int:
        return self.patients

    @property
    def patient_mention_count(self) -> int:
        return self.patient_mentions

    @property
    def entity_count(self) -> int:
        return self.entities

    @property
    def association_count(self) -> int:
        return self.associations


@dataclass(frozen=True, slots=True)
class FoldAssignment:
    seed: int
    n_folds: int
    assignments: dict[str, int]
    fold_statistics: tuple[dict[str, int], ...]

    def to_dict(self, *, source_sha256: str | None = None) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema_version": 1,
            "seed": self.seed,
            "n_folds": self.n_folds,
            "assignments": dict(self.assignments),
            "fold_statistics": [dict(item) for item in self.fold_statistics],
        }
        if source_sha256 is not None:
            value["source_sha256"] = source_sha256
        return value


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_documents(documents: Sequence[Document], source: Path) -> tuple[SpanIssue, ...]:
    seen: set[str] = set()
    issues: list[SpanIssue] = []
    for index, document in enumerate(documents):
        if not document.pmc_id.strip():
            raise PreparationError(f"{source}: document[{index}] has an empty pmc_id")
        if document.pmc_id in seen:
            raise PreparationError(f"{source}: duplicate pmc_id {document.pmc_id!r}")
        seen.add(document.pmc_id)
        issues.extend(validate_document_spans(document))
    return tuple(issues)


def _counts(documents: Sequence[Document]) -> tuple[int, int, int, int, int]:
    return (
        len(documents),
        sum(len(document.patient) for document in documents),
        sum(len(patient.mention) for document in documents for patient in document.patient),
        sum(len(document.entities) for document in documents),
        sum(len(document.association) for document in documents),
    )


def prepare_dataset(input_path: str | Path, output_path: str | Path) -> PreparationSummary:
    """Validate a JSONL source, write an exact atomic work copy, and recheck it."""
    source = Path(input_path)
    destination = Path(output_path)
    documents = load_jsonl(source)
    issues = _check_documents(documents, source)
    if issues:
        first = issues[0]
        raise PreparationError(
            f"{source}: invalid span(s)={len(issues)}; first {first.item_path}: "
            f"{first.error_code}: {first.message}"
        )

    input_sha256 = _sha256(source)
    write_jsonl(destination, documents)
    reloaded = load_jsonl(destination)
    expected = [document.to_dict() for document in documents]
    actual = [document.to_dict() for document in reloaded]
    if actual != expected:
        raise PreparationError(f"{destination}: output objects differ from input objects")
    document_count, patient_count, mention_count, entity_count, association_count = _counts(documents)
    return PreparationSummary(
        input_path=str(source),
        output_path=str(destination),
        input_sha256=input_sha256,
        output_sha256=_sha256(destination),
        documents=document_count,
        patients=patient_count,
        patient_mentions=mention_count,
        entities=entity_count,
        associations=association_count,
        invalid_spans=0,
    )


def create_article_folds(
    documents: Sequence[Document],
    n_folds: int = 5,
    seed: int = 20260915,
) -> FoldAssignment:
    """Assign each article exactly once using a stable hash of seed and pmc_id."""
    if isinstance(n_folds, bool) or not isinstance(n_folds, int) or n_folds <= 0:
        raise ValueError("n_folds must be a positive integer")
    seen: set[str] = set()
    keyed: list[tuple[str, str, Document]] = []
    for document in documents:
        if not document.pmc_id.strip():
            raise ValueError("pmc_id must not be empty")
        if document.pmc_id in seen:
            raise ValueError(f"duplicate pmc_id {document.pmc_id!r}")
        seen.add(document.pmc_id)
        key = hashlib.sha256(f"{seed}:{document.pmc_id}".encode("utf-8")).hexdigest()
        keyed.append((key, document.pmc_id, document))
    keyed.sort(key=lambda item: (item[0], item[1]))
    assignments = {pmc_id: index % n_folds for index, (_key, pmc_id, _document) in enumerate(keyed)}
    statistics: list[dict[str, int]] = []
    for fold in range(n_folds):
        members = [document for _key, pmc_id, document in keyed if assignments[pmc_id] == fold]
        statistics.append(
            {
                "fold": fold,
                "documents": len(members),
                "patients": sum(len(document.patient) for document in members),
                "entities": sum(len(document.entities) for document in members),
            }
        )
    return FoldAssignment(
        seed=seed,
        n_folds=n_folds,
        assignments=assignments,
        fold_statistics=tuple(statistics),
    )


def build_manifest(
    train_summary: PreparationSummary,
    a_summary: PreparationSummary,
    *,
    folds: FoldAssignment,
    hpo_version: str = "v2026-06-23",
    git_commit: str | None = None,
) -> dict[str, Any]:
    """Build a portable, deterministic manifest for the prepared artifacts."""
    return {
        "schema_version": 1,
        "sources": {
            "train": {
                "filename": Path(train_summary.input_path).name,
                "sha256": train_summary.input_sha256,
            },
            "a_list": {
                "filename": Path(a_summary.input_path).name,
                "sha256": a_summary.input_sha256,
            },
        },
        "outputs": {
            "train": {
                "filename": Path(train_summary.output_path).name,
                "sha256": train_summary.output_sha256,
            },
            "a_list": {
                "filename": Path(a_summary.output_path).name,
                "sha256": a_summary.output_sha256,
            },
        },
        "hpo": {"version": hpo_version, "filename": "hp-2026-06-23.obo"},
        "counts": {
            "train": {
                "documents": train_summary.documents,
                "patients": train_summary.patients,
                "patient_mentions": train_summary.patient_mentions,
                "entities": train_summary.entities,
                "associations": train_summary.associations,
                "invalid_spans": train_summary.invalid_spans,
            },
            "a_list": {
                "documents": a_summary.documents,
                "patients": a_summary.patients,
                "patient_mentions": a_summary.patient_mentions,
                "entities": a_summary.entities,
                "associations": a_summary.associations,
                "invalid_spans": a_summary.invalid_spans,
            },
        },
        "folds": {"seed": folds.seed, "n_folds": folds.n_folds},
        "git_commit": git_commit,
    }


__all__ = [
    "FoldAssignment",
    "PreparationError",
    "PreparationSummary",
    "build_manifest",
    "create_article_folds",
    "prepare_dataset",
]
