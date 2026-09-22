from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from patientphex.common.hpo import (
    HPOVersionError,
    HPOQueryStatus,
    load_hpo,
)


DATA_ROOT = Path("/mnt/data/wzh/AIcourse/patientphex-2026-data")
OBO_PATH = DATA_ROOT / "ontology" / "hp-2026-06-23.obo"


SAMPLE_OBO = '''format-version: 1.2
data-version: hp/releases/2026-06-23

[Term]
id: HP:0000001
name: All

[Term]
id: HP:0000118
name: Phenotypic abnormality
synonym: "Root alias" EXACT []
is_a: HP:0000001 ! All

[Term]
id: HP:0001000
name: Child One
alt_id: HP:0099000
synonym: "Shared label" EXACT []
synonym: "Loose label" RELATED []
is_a: HP:0000118 ! Phenotypic abnormality

[Term]
id: HP:0001001
name: Child Two
synonym: "Shared label" EXACT []
is_a: HP:0000118 ! Phenotypic abnormality

[Term]
id: HP:0001002
name: Related Only
synonym: "Loose label" RELATED []
is_a: HP:0000118 ! Phenotypic abnormality

[Term]
id: HP:0002000
name: Outside branch
is_a: HP:0000001 ! All

[Term]
id: HP:0003000
name: obsolete Old phenotype
is_obsolete: true
replaced_by: HP:0001000
is_a: HP:0000118 ! Phenotypic abnormality
'''


def _write_sample(path: Path, *, version: str = "hp/releases/2026-06-23") -> None:
    path.write_text(SAMPLE_OBO.replace("hp/releases/2026-06-23", version), encoding="utf-8")


def test_rejects_wrong_data_version(tmp_path: Path) -> None:
    path = tmp_path / "wrong.obo"
    _write_sample(path, version="hp/releases/2025-01-01")

    with pytest.raises(HPOVersionError, match="hp/releases/2026-06-23"):
        load_hpo(path)


def test_root_and_valid_descendants_are_in_allowed_branch(tmp_path: Path) -> None:
    path = tmp_path / "sample.obo"
    _write_sample(path)
    index = load_hpo(path)

    assert index.is_in_branch("HP:0000118")
    assert index.is_in_branch("HP:0001000")
    assert not index.is_in_branch("HP:0002000")
    assert index.lookup_id("HP:0002000").status is HPOQueryStatus.OUTSIDE_BRANCH


def test_name_and_exact_synonym_queries_are_case_insensitive(tmp_path: Path) -> None:
    path = tmp_path / "sample.obo"
    _write_sample(path)
    index = load_hpo(path)

    assert index.find_by_name("child one") == frozenset({"HP:0001000"})
    assert index.find_by_name("ROOT ALIAS") == frozenset({"HP:0000118"})
    assert index.find_by_name("shared label") == frozenset({"HP:0001000", "HP:0001001"})
    assert index.find_by_name("loose label") == frozenset()
    assert index.find_by_name("loose label", exact_only=False) == frozenset({"HP:0001000", "HP:0001002"})


def test_alt_id_resolves_only_to_valid_primary_id(tmp_path: Path) -> None:
    path = tmp_path / "sample.obo"
    _write_sample(path)
    index = load_hpo(path)

    result = index.lookup_id("HP:0099000")
    assert result.status is HPOQueryStatus.VALID
    assert result.canonical_id == "HP:0001000"
    assert index.get_term("HP:0099000").id == "HP:0001000"


def test_unknown_and_obsolete_ids_are_distinguished(tmp_path: Path) -> None:
    path = tmp_path / "sample.obo"
    _write_sample(path)
    index = load_hpo(path)

    assert index.lookup_id("HP:9999999").status is HPOQueryStatus.UNKNOWN
    obsolete = index.lookup_id("HP:0003000")
    assert obsolete.status is HPOQueryStatus.OBSOLETE
    assert obsolete.replacement_ids == ("HP:0001000",)
    with pytest.raises(LookupError, match="obsolete"):
        index.get_term("HP:0003000")


def test_official_obo_is_used_for_integration_queries() -> None:
    index = load_hpo(OBO_PATH)

    assert index.version == "hp/releases/2026-06-23"
    assert index.is_in_branch("HP:0000118")
    assert index.is_in_branch("HP:0000119")
    assert not index.is_in_branch("HP:0000001")
    assert index.find_by_name("phenotypic abnormality") == frozenset({"HP:0000118"})
    assert len(index.allowed_ids) > 1000
    assert len(index.exact_name_index) > 1000
    assert len(index.all_name_index) >= len(index.exact_name_index)
    assert len(index.alt_id_map) > 0


def test_official_obo_hash_is_available_for_handoff_record() -> None:
    digest = hashlib.sha256(OBO_PATH.read_bytes()).hexdigest()

    assert len(digest) == 64
