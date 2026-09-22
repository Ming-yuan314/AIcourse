"""HPO v2026-06-23 loader and HP:0000118 branch index."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


EXPECTED_DATA_VERSION = "hp/releases/2026-06-23"
PHENOTYPIC_ABNORMALITY = "HP:0000118"


class HPOError(ValueError):
    """Base class for HPO loading and indexing errors."""


class HPOVersionError(HPOError):
    """Raised when an OBO file is not the frozen competition release."""


class HPOParseError(HPOError):
    """Raised when an OBO file is malformed or incomplete."""


class HPOQueryStatus(str, Enum):
    VALID = "valid"
    UNKNOWN = "unknown"
    OBSOLETE = "obsolete"
    OUTSIDE_BRANCH = "outside_branch"
    AMBIGUOUS = "ambiguous"


class HPOQueryError(LookupError):
    """Raised by ``get_term`` when an ID cannot be used as a prediction ID."""

    def __init__(self, requested_id: str, status: HPOQueryStatus, detail: str) -> None:
        self.requested_id = requested_id
        self.status = status
        super().__init__(f"HPO ID {requested_id!r} {detail}")


@dataclass(frozen=True, slots=True)
class HPOSynonym:
    text: str
    scope: str
    synonym_type: str | None = None


@dataclass(frozen=True, slots=True)
class HPOTerm:
    id: str
    name: str
    synonyms: tuple[HPOSynonym, ...] = ()
    parents: tuple[str, ...] = ()
    alt_ids: tuple[str, ...] = ()
    is_obsolete: bool = False
    replaced_by: tuple[str, ...] = ()

    @property
    def hpo_id(self) -> str:
        return self.id


@dataclass(frozen=True, slots=True)
class HPOIdLookup:
    requested_id: str
    status: HPOQueryStatus
    canonical_id: str | None = None
    term: HPOTerm | None = None
    replacement_ids: tuple[str, ...] = ()


def _normalise_name(value: str) -> str:
    return value.strip().casefold()


def _unescape_obo_text(value: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character != "\\" or index + 1 >= len(value):
            result.append(character)
            index += 1
            continue
        escaped = value[index + 1]
        if escaped == "n":
            result.append("\n")
        elif escaped == "t":
            result.append("\t")
        else:
            result.append(escaped)
        index += 2
    return "".join(result)


def _quoted_synonym(value: str, *, path: Path, line_number: int) -> HPOSynonym:
    if not value.startswith('"'):
        raise HPOParseError(f"{path}: line {line_number}: synonym must start with a quoted string")
    chars: list[str] = []
    index = 1
    escaped = False
    closing_index: int | None = None
    while index < len(value):
        character = value[index]
        if escaped:
            chars.append("\\" + character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == '"':
            closing_index = index
            break
        else:
            chars.append(character)
        index += 1
    if closing_index is None or escaped:
        raise HPOParseError(f"{path}: line {line_number}: unterminated synonym string")
    remainder = value[closing_index + 1 :].strip()
    fields = remainder.split()
    if not fields:
        raise HPOParseError(f"{path}: line {line_number}: synonym scope is missing")
    scope = fields[0].upper()
    synonym_type = fields[1] if len(fields) > 1 and fields[1] != "[" else None
    return HPOSynonym(
        text=_unescape_obo_text("".join(chars)),
        scope=scope,
        synonym_type=synonym_type,
    )


def _finish_stanza(
    stanza: dict[str, list[tuple[int, str]]],
    *,
    path: Path,
) -> HPOTerm:
    def one(field: str, required: bool = False) -> str | None:
        values = stanza.get(field, [])
        if not values:
            if required:
                line_number = next(iter(stanza.values()))[0][0] if stanza else 0
                raise HPOParseError(f"{path}: term at line {line_number} is missing {field}")
            return None
        return values[0][1].strip()

    term_id = one("id", required=True)
    name = one("name", required=True)
    assert term_id is not None and name is not None
    parents = tuple(value.split()[0] for _line, value in stanza.get("is_a", []) if value.split())
    alt_ids = tuple(value.split()[0] for _line, value in stanza.get("alt_id", []) if value.split())
    replaced_by = tuple(value.split()[0] for _line, value in stanza.get("replaced_by", []) if value.split())
    synonyms = tuple(
        _quoted_synonym(value, path=path, line_number=line_number)
        for line_number, value in stanza.get("synonym", [])
    )
    obsolete = (one("is_obsolete") or "").lower() == "true"
    return HPOTerm(
        id=term_id,
        name=name,
        synonyms=synonyms,
        parents=parents,
        alt_ids=alt_ids,
        is_obsolete=obsolete,
        replaced_by=replaced_by,
    )


def _parse_obo(path: Path) -> tuple[str, dict[str, HPOTerm]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise HPOError(f"cannot read HPO OBO file {path}: {error}") from error

    data_version: str | None = None
    terms: dict[str, HPOTerm] = {}
    stanza: dict[str, list[tuple[int, str]]] | None = None
    in_term = False

    def finish() -> None:
        nonlocal stanza
        if stanza is None:
            return
        term = _finish_stanza(stanza, path=path)
        if term.id in terms:
            raise HPOParseError(f"{path}: duplicate term ID {term.id}")
        terms[term.id] = term
        stanza = None

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            finish()
            in_term = False
            continue
        if line == "[Term]":
            finish()
            stanza = {}
            in_term = True
            continue
        if line.startswith("[") and line.endswith("]"):
            finish()
            in_term = False
            continue
        if not in_term:
            if line.startswith("data-version:"):
                value = line.split(":", 1)[1].strip()
                if data_version is not None and data_version != value:
                    raise HPOParseError(f"{path}: conflicting data-version values")
                data_version = value
            continue
        if ":" not in line:
            raise HPOParseError(f"{path}: line {line_number}: malformed OBO field")
        field, value = line.split(":", 1)
        assert stanza is not None
        stanza.setdefault(field, []).append((line_number, value.strip()))
    finish()

    if data_version != EXPECTED_DATA_VERSION:
        actual = data_version if data_version is not None else "<missing>"
        raise HPOVersionError(
            f"unsupported HPO data-version {actual!r}; expected {EXPECTED_DATA_VERSION!r}"
        )
    if PHENOTYPIC_ABNORMALITY not in terms:
        raise HPOParseError(f"{path}: required root term {PHENOTYPIC_ABNORMALITY} is missing")
    return data_version, terms


class HPOIndex:
    """Read-only query index restricted to the Phenotypic abnormality branch."""

    def __init__(self, version: str, terms: Mapping[str, HPOTerm]) -> None:
        self.version = version
        self.root_id = PHENOTYPIC_ABNORMALITY
        self.terms = MappingProxyType(dict(terms))

        root = self.terms[self.root_id]
        if root.is_obsolete:
            raise HPOParseError(f"required root term {self.root_id} is obsolete")

        children: dict[str, set[str]] = {}
        for term in self.terms.values():
            for parent in term.parents:
                children.setdefault(parent, set()).add(term.id)
        allowed: set[str] = set()
        pending = [self.root_id]
        while pending:
            term_id = pending.pop()
            if term_id in allowed:
                continue
            term = self.terms.get(term_id)
            if term is None or term.is_obsolete:
                continue
            allowed.add(term_id)
            pending.extend(children.get(term_id, ()))
        self.allowed_ids = frozenset(allowed)

        alt_map: dict[str, set[str]] = {}
        for term in self.terms.values():
            for alt_id in term.alt_ids:
                alt_map.setdefault(alt_id, set()).add(term.id)
        self.alt_id_map = MappingProxyType({key: frozenset(value) for key, value in alt_map.items()})

        exact: dict[str, set[str]] = {}
        all_names: dict[str, set[str]] = {}
        for term_id in self.allowed_ids:
            term = self.terms[term_id]
            normalised_name = _normalise_name(term.name)
            exact.setdefault(normalised_name, set()).add(term_id)
            all_names.setdefault(normalised_name, set()).add(term_id)
            for synonym in term.synonyms:
                normalised_synonym = _normalise_name(synonym.text)
                all_names.setdefault(normalised_synonym, set()).add(term_id)
                if synonym.scope == "EXACT":
                    exact.setdefault(normalised_synonym, set()).add(term_id)
        self.exact_name_index = MappingProxyType(
            {key: frozenset(value) for key, value in exact.items()}
        )
        self.all_name_index = MappingProxyType(
            {key: frozenset(value) for key, value in all_names.items()}
        )

    def lookup_id(self, hpo_id: str) -> HPOIdLookup:
        """Return status and canonical term for a primary or alternate ID."""
        requested = hpo_id.strip()
        term = self.terms.get(requested)
        canonical_id = requested
        if term is None:
            candidates = self.alt_id_map.get(requested)
            if not candidates:
                return HPOIdLookup(requested_id=requested, status=HPOQueryStatus.UNKNOWN)
            if len(candidates) != 1:
                return HPOIdLookup(requested_id=requested, status=HPOQueryStatus.AMBIGUOUS)
            canonical_id = next(iter(candidates))
            term = self.terms[canonical_id]
        if term.is_obsolete:
            return HPOIdLookup(
                requested_id=requested,
                status=HPOQueryStatus.OBSOLETE,
                canonical_id=None,
                term=term,
                replacement_ids=term.replaced_by,
            )
        if canonical_id not in self.allowed_ids:
            return HPOIdLookup(
                requested_id=requested,
                status=HPOQueryStatus.OUTSIDE_BRANCH,
                canonical_id=None,
                term=term,
            )
        return HPOIdLookup(
            requested_id=requested,
            status=HPOQueryStatus.VALID,
            canonical_id=canonical_id,
            term=term,
        )

    def get_term(self, hpo_id: str) -> HPOTerm:
        """Return a valid branch term or raise a status-bearing query error."""
        result = self.lookup_id(hpo_id)
        if result.status is HPOQueryStatus.VALID and result.term is not None:
            return result.term
        if result.status is HPOQueryStatus.UNKNOWN:
            detail = "was not found"
        elif result.status is HPOQueryStatus.OBSOLETE:
            detail = "is obsolete and cannot be predicted"
        elif result.status is HPOQueryStatus.OUTSIDE_BRANCH:
            detail = "is outside the allowed HP:0000118 branch"
        else:
            detail = "has an ambiguous alternate-ID mapping"
        raise HPOQueryError(result.requested_id, result.status, detail)

    def find_by_name(self, text: str, *, exact_only: bool = True) -> frozenset[str]:
        """Return all valid primary IDs matching a name or synonym."""
        index = self.exact_name_index if exact_only else self.all_name_index
        return index.get(_normalise_name(text), frozenset())

    def is_in_branch(self, hpo_id: str) -> bool:
        return self.lookup_id(hpo_id).status is HPOQueryStatus.VALID

    def lookup_name(self, text: str, *, exact_only: bool = True) -> frozenset[str]:
        return self.find_by_name(text, exact_only=exact_only)


def load_hpo(path: str | Path) -> HPOIndex:
    """Load and index the frozen HPO release at ``path``."""
    source = Path(path)
    version, terms = _parse_obo(source)
    return HPOIndex(version, terms)


__all__ = [
    "EXPECTED_DATA_VERSION",
    "HPOError",
    "HPOIdLookup",
    "HPOIndex",
    "HPOParseError",
    "HPOQueryError",
    "HPOQueryStatus",
    "HPOSynonym",
    "HPOTerm",
    "HPOVersionError",
    "PHENOTYPIC_ABNORMALITY",
    "load_hpo",
]
