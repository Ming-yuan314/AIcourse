from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from patientphex.common.io import load_jsonl, write_jsonl
from patientphex.common.preparation import (
    PreparationError,
    build_manifest,
    create_article_folds,
    prepare_dataset,
)
from patientphex.common.schema import Document, Entity, Patient, PatientMention, Section


def _document(pmc_id: str = "1", *, valid: bool = True) -> Document:
    section = Section(section_type="CASE", type="text", offset=10, text="患者 α")
    mention_offset = 10 if valid else 100
    mention = PatientMention(text="患者", offset=mention_offset, length=2)
    entity = Entity(
        identifier="HP:0000001",
        type="Phenotype",
        offset=10,
        length=2,
        text="患者",
        note=None,
    )
    return Document(
        pmc_id=pmc_id,
        pmid=None,
        patient=(Patient(patient_id="P1", mention=(mention,)),),
        full_text=(section,),
        entities=(entity,),
        association=(),
    )


def _write_input(path: Path, documents: list[Document]) -> None:
    path.write_text(
        "".join(json.dumps(document.to_dict(), ensure_ascii=False) + "\n" for document in documents),
        encoding="utf-8",
    )


def test_write_jsonl_round_trips_utf8_and_preserves_order(tmp_path: Path) -> None:
    documents = [_document("二"), _document("一")]
    output = tmp_path / "documents.jsonl"

    write_jsonl(output, documents)

    assert load_jsonl(output) == documents
    assert output.read_text(encoding="utf-8").endswith("\n")
    assert "患者" in output.read_text(encoding="utf-8")
    assert "\\u" not in output.read_text(encoding="utf-8")
    assert list(tmp_path.glob(".*.tmp")) == []


def test_prepare_dataset_reloads_exact_objects_and_counts(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    output = tmp_path / "processed.jsonl"
    documents = [_document("1"), _document("2")]
    _write_input(source, documents)

    summary = prepare_dataset(source, output)

    assert load_jsonl(output) == documents
    assert summary.documents == 2
    assert summary.patients == 2
    assert summary.patient_mentions == 2
    assert summary.entities == 2
    assert summary.associations == 0
    assert summary.invalid_spans == 0
    assert summary.input_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert summary.output_sha256 == hashlib.sha256(output.read_bytes()).hexdigest()


def test_duplicate_pmc_ids_are_rejected_without_output(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    output = tmp_path / "processed.jsonl"
    _write_input(source, [_document("same"), _document("same")])

    with pytest.raises(PreparationError, match="duplicate pmc_id"):
        prepare_dataset(source, output)
    assert not output.exists()


def test_invalid_offset_blocks_output(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    output = tmp_path / "processed.jsonl"
    _write_input(source, [_document("bad", valid=False)])

    with pytest.raises(PreparationError, match="bad"):
        prepare_dataset(source, output)
    assert not output.exists()


def test_article_folds_cover_eighty_documents_in_five_equal_sets() -> None:
    documents = [_document(str(index)) for index in range(80)]

    first = create_article_folds(documents, n_folds=5, seed=20260915)
    second = create_article_folds(documents, n_folds=5, seed=20260915)
    different = create_article_folds(documents, n_folds=5, seed=20260916)

    assert first == second
    assert first.assignments != different.assignments
    assert set(first.assignments) == {str(index) for index in range(80)}
    assert sorted(first.assignments.values()) == [fold for fold in range(5) for _ in range(16)]
    for fold in range(5):
        members = {pmc for pmc, assigned in first.assignments.items() if assigned == fold}
        assert len(members) == 16
    assert set(first.assignments) == set().union(
        *(set(pmc for pmc, fold in first.assignments.items() if fold == index) for index in range(5))
    )


def test_fold_assignment_serializes_statistics() -> None:
    folds = create_article_folds([_document(str(index)) for index in range(5)], n_folds=5)

    payload = folds.to_dict()

    assert payload["schema_version"] == 1
    assert payload["n_folds"] == 5
    assert len(payload["assignments"]) == 5
    assert [item["documents"] for item in payload["fold_statistics"]] == [1] * 5


def test_manifest_contains_source_output_hashes_counts_and_hpo_version(tmp_path: Path) -> None:
    train_source = tmp_path / "PatientPheX-train.jsonl"
    train_output = tmp_path / "documents.jsonl"
    a_source = tmp_path / "PatientPheX-A.jsonl"
    a_output = tmp_path / "a-documents.jsonl"
    train_docs = [_document("train")]
    a_docs = [_document("a")]
    _write_input(train_source, train_docs)
    _write_input(a_source, a_docs)
    train_summary = prepare_dataset(train_source, train_output)
    a_summary = prepare_dataset(a_source, a_output)
    folds = create_article_folds(train_docs)

    manifest = build_manifest(
        train_summary,
        a_summary,
        folds=folds,
        hpo_version="v2026-06-23",
        git_commit="deadbeef",
    )

    assert manifest["sources"]["train"]["filename"] == train_source.name
    assert manifest["sources"]["a_list"]["sha256"] == a_summary.input_sha256
    assert manifest["outputs"]["train"]["sha256"] == train_summary.output_sha256
    assert manifest["hpo"]["version"] == "v2026-06-23"
    assert manifest["counts"]["train"]["documents"] == 1
    assert manifest["counts"]["a_list"]["patient_mentions"] == 1
    assert manifest["folds"]["seed"] == folds.seed
    assert manifest["git_commit"] == "deadbeef"
