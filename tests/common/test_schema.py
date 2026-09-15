import pytest

from patientphex.common.schema import Document, SchemaError


def sample_document():
    return {
        "pmc_id": "PMC123",
        "pmid": "12345678",
        "patient": [
            {
                "patient_id": "P1",
                "mention": [
                    {"text": "patient", "offset": 0, "length": 7},
                    {"text": "a child", "offset": 8, "length": 7},
                ],
            }
        ],
        "full_text": [
            {
                "section_type": "TITLE",
                "type": "front",
                "offset": 0,
                "text": "patient a child",
            }
        ],
        "entities": [
            {
                "identifier": "HP:0000001",
                "type": "Phenotype",
                "offset": 0,
                "length": 7,
                "text": "patient",
                "note": None,
            }
        ],
        "association": [
            {"patient_id": "P1", "phenotype": ["HP:0000001"]}
        ],
    }


def test_document_round_trips_official_fields():
    raw = sample_document()
    document = Document.from_dict(raw)

    assert document.pmc_id == "PMC123"
    assert document.pmid == "12345678"
    assert document.patient[0].mention[1].text == "a child"
    assert document.full_text[0].offset == 0
    assert document.entities[0].identifier == "HP:0000001"
    assert document.association[0].phenotype == ("HP:0000001",)
    assert document.to_dict() == raw


def test_document_preserves_optional_section_title():
    raw = sample_document()
    raw["full_text"][0]["title"] = "Keywords"

    document = Document.from_dict(raw)

    assert document.full_text[0].title == "Keywords"
    assert document.to_dict() == raw


def test_document_rejects_missing_required_field():
    raw = sample_document()
    del raw["entities"]

    with pytest.raises(SchemaError, match="entities"):
        Document.from_dict(raw)


def test_document_rejects_inconsistent_entity_length():
    raw = sample_document()
    raw["entities"][0]["length"] = 99

    with pytest.raises(SchemaError, match="length"):
        Document.from_dict(raw)