"""Typed data model for the official PatientPheX JSONL records."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


class SchemaError(ValueError):
    """Raised when a JSON value does not match the official record schema."""


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaError(f"{path} must be an object")
    return value


def _keys(
    value: Mapping[str, Any],
    required: set[str],
    path: str,
    *,
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    missing = required - set(value)
    if missing:
        names = ", ".join(sorted(missing))
        raise SchemaError(f"{path} is missing required field(s): {names}")
    extra = set(value) - required - optional
    if extra:
        names = ", ".join(sorted(extra))
        raise SchemaError(f"{path} has unexpected field(s): {names}")


def _string(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise SchemaError(f"{path} must be a string")
    return value


def _integer(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaError(f"{path} must be an integer")
    if value < 0:
        raise SchemaError(f"{path} must be non-negative")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise SchemaError(f"{path} must be an array")
    return value


@dataclass(frozen=True, slots=True)
class PatientMention:
    text: str
    offset: int
    length: int

    @classmethod
    def from_dict(cls, value: Any, path: str = "mention") -> "PatientMention":
        payload = _mapping(value, path)
        _keys(payload, {"text", "offset", "length"}, path)
        text = _string(payload["text"], f"{path}.text")
        assert text is not None
        offset = _integer(payload["offset"], f"{path}.offset")
        length = _integer(payload["length"], f"{path}.length")
        if length != len(text):
            raise SchemaError(f"{path}.length must equal len({path}.text)")
        return cls(text=text, offset=offset, length=length)

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "offset": self.offset, "length": self.length}


@dataclass(frozen=True, slots=True)
class Patient:
    patient_id: str
    mention: tuple[PatientMention, ...]

    @classmethod
    def from_dict(cls, value: Any, path: str = "patient") -> "Patient":
        payload = _mapping(value, path)
        _keys(payload, {"patient_id", "mention"}, path)
        patient_id = _string(payload["patient_id"], f"{path}.patient_id")
        assert patient_id is not None
        mentions = tuple(
            PatientMention.from_dict(item, f"{path}.mention[{index}]")
            for index, item in enumerate(_list(payload["mention"], f"{path}.mention"))
        )
        return cls(patient_id=patient_id, mention=mentions)

    def to_dict(self) -> dict[str, Any]:
        return {"patient_id": self.patient_id, "mention": [item.to_dict() for item in self.mention]}


@dataclass(frozen=True, slots=True)
class Section:
    section_type: str
    type: str
    offset: int
    text: str
    title: str | None = None
    _title_present: bool = field(default=False, compare=False, repr=False)

    @classmethod
    def from_dict(cls, value: Any, path: str = "full_text") -> "Section":
        payload = _mapping(value, path)
        _keys(payload, {"section_type", "type", "offset", "text"}, path, optional={"title"})
        section_type = _string(payload["section_type"], f"{path}.section_type")
        section_kind = _string(payload["type"], f"{path}.type")
        text = _string(payload["text"], f"{path}.text")
        title = _string(payload["title"], f"{path}.title", nullable=True) if "title" in payload else None
        assert section_type is not None and section_kind is not None and text is not None
        return cls(
            section_type=section_type,
            type=section_kind,
            offset=_integer(payload["offset"], f"{path}.offset"),
            text=text,
            title=title,
            _title_present="title" in payload,
        )

    def to_dict(self) -> dict[str, Any]:
        value = {"section_type": self.section_type, "type": self.type, "offset": self.offset, "text": self.text}
        if self._title_present:
            value["title"] = self.title
        return value


@dataclass(frozen=True, slots=True)
class Entity:
    identifier: str
    type: str
    offset: int
    length: int
    text: str
    note: str | None

    @classmethod
    def from_dict(cls, value: Any, path: str = "entities") -> "Entity":
        payload = _mapping(value, path)
        _keys(payload, {"identifier", "type", "offset", "length", "text", "note"}, path)
        identifier = _string(payload["identifier"], f"{path}.identifier")
        entity_type = _string(payload["type"], f"{path}.type")
        text = _string(payload["text"], f"{path}.text")
        note = _string(payload["note"], f"{path}.note", nullable=True)
        assert identifier is not None and entity_type is not None and text is not None
        length = _integer(payload["length"], f"{path}.length")
        if length != len(text):
            raise SchemaError(f"{path}.length must equal len({path}.text)")
        return cls(
            identifier=identifier,
            type=entity_type,
            offset=_integer(payload["offset"], f"{path}.offset"),
            length=length,
            text=text,
            note=note,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "type": self.type,
            "offset": self.offset,
            "length": self.length,
            "text": self.text,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class Association:
    patient_id: str
    phenotype: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: Any, path: str = "association") -> "Association":
        payload = _mapping(value, path)
        _keys(payload, {"patient_id", "phenotype"}, path)
        patient_id = _string(payload["patient_id"], f"{path}.patient_id")
        assert patient_id is not None
        phenotype = tuple(
            _string(item, f"{path}.phenotype[{index}]")  # type: ignore[misc]
            for index, item in enumerate(_list(payload["phenotype"], f"{path}.phenotype"))
        )
        return cls(patient_id=patient_id, phenotype=phenotype)  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, Any]:
        return {"patient_id": self.patient_id, "phenotype": list(self.phenotype)}


@dataclass(frozen=True, slots=True)
class Document:
    pmc_id: str
    pmid: str | None
    patient: tuple[Patient, ...]
    full_text: tuple[Section, ...]
    entities: tuple[Entity, ...]
    association: tuple[Association, ...]

    @classmethod
    def from_dict(cls, value: Any) -> "Document":
        payload = _mapping(value, "document")
        fields = {"pmc_id", "pmid", "patient", "full_text", "entities", "association"}
        _keys(payload, fields, "document")
        pmc_id = _string(payload["pmc_id"], "document.pmc_id")
        pmid = _string(payload["pmid"], "document.pmid", nullable=True)
        assert pmc_id is not None
        return cls(
            pmc_id=pmc_id,
            pmid=pmid,
            patient=tuple(
                Patient.from_dict(item, f"document.patient[{index}]")
                for index, item in enumerate(_list(payload["patient"], "document.patient"))
            ),
            full_text=tuple(
                Section.from_dict(item, f"document.full_text[{index}]")
                for index, item in enumerate(_list(payload["full_text"], "document.full_text"))
            ),
            entities=tuple(
                Entity.from_dict(item, f"document.entities[{index}]")
                for index, item in enumerate(_list(payload["entities"], "document.entities"))
            ),
            association=tuple(
                Association.from_dict(item, f"document.association[{index}]")
                for index, item in enumerate(_list(payload["association"], "document.association"))
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pmc_id": self.pmc_id,
            "pmid": self.pmid,
            "patient": [item.to_dict() for item in self.patient],
            "full_text": [item.to_dict() for item in self.full_text],
            "entities": [item.to_dict() for item in self.entities],
            "association": [item.to_dict() for item in self.association],
        }


__all__ = [
    "Association",
    "Document",
    "Entity",
    "Patient",
    "PatientMention",
    "SchemaError",
    "Section",
]