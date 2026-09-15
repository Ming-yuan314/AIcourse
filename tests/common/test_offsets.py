import pytest

from patientphex.common.offsets import (
    OffsetError,
    get_span_text,
    locate_span,
    validate_document_spans,
    validate_span_text,
)
from patientphex.common.schema import (
    Association,
    Document,
    Entity,
    Patient,
    PatientMention,
    Section,
)


def section(offset: int, text: str, section_type: str = "BODY") -> Section:
    return Section(section_type=section_type, type="body", offset=offset, text=text)


def document_with(*, mentions=(), entities=(), sections=None, pmc_id="PMC-OFFSET") -> Document:
    return Document(
        pmc_id=pmc_id,
        pmid=None,
        patient=(Patient(patient_id="P1", mention=tuple(mentions)),),
        full_text=tuple(sections or [section(0, "patient has fever")]),
        entities=tuple(entities),
        association=(Association(patient_id="P1", phenotype=()),),
    )


def assert_code(error: pytest.ExceptionInfo[OffsetError], code: str) -> None:
    assert error.value.error_code == code
    assert code in str(error.value)


def test_locate_span_at_global_offset_zero():
    located = locate_span([section(0, "abc")], 0, 1)

    assert located.section_index == 0
    assert located.local_offset == 0
    assert located.text == "a"


def test_locate_span_converts_nonzero_section_offset():
    located = locate_span([section(10, "abc")], 12, 1)

    assert located.local_offset == 2
    assert located.text == "c"


def test_locate_span_may_end_exactly_at_section_end():
    located = locate_span([section(10, "abc")], 11, 2)

    assert located.text == "bc"
    assert located.global_offset + located.length == 13


def test_locate_span_rejects_section_gap():
    error = pytest.raises(OffsetError, locate_span, [section(0, "abc"), section(5, "def")], 3, 2)

    assert_code(error, "SECTION_GAP")


def test_locate_span_rejects_crossing_contiguous_sections():
    error = pytest.raises(OffsetError, locate_span, [section(0, "abc"), section(3, "def")], 2, 2)

    assert_code(error, "CROSSES_SECTION")


def test_locate_span_rejects_span_beyond_last_section():
    error = pytest.raises(OffsetError, locate_span, [section(0, "abc")], 3, 1)

    assert_code(error, "OUTSIDE_SECTIONS")


def test_locate_span_rejects_negative_offset():
    error = pytest.raises(OffsetError, locate_span, [section(0, "abc")], -1, 1)

    assert_code(error, "INVALID_OFFSET")


def test_locate_span_rejects_nonpositive_length():
    error = pytest.raises(OffsetError, locate_span, [section(0, "abc")], 0, 0)

    assert_code(error, "INVALID_LENGTH")


def test_validate_span_text_rejects_mismatch_without_dumping_article():
    error = pytest.raises(OffsetError, validate_span_text, [section(0, "abc")], 0, 2, "ax")

    assert_code(error, "TEXT_MISMATCH")
    assert "expected length 2" in str(error.value)
    assert "actual length 2" in str(error.value)
    assert "abc" not in str(error.value)


def test_locate_span_rejects_overlapping_section_ambiguity():
    error = pytest.raises(OffsetError, locate_span, [section(0, "abcd"), section(2, "cdef")], 2, 2)

    assert_code(error, "AMBIGUOUS_SECTION")


def test_validate_document_spans_checks_patient_mentions():
    mention = PatientMention(text="fever", offset=12, length=5)
    document = document_with(mentions=(mention,), sections=[section(10, "xxfever")])

    assert validate_document_spans(document) == []


def test_validate_document_spans_checks_entities():
    entity = Entity(
        identifier="HP:0000001",
        type="Phenotype",
        offset=3,
        length=5,
        text="fever",
        note=None,
    )
    document = document_with(entities=(entity,), sections=[section(0, "xx fever")])

    assert validate_document_spans(document) == []


def test_validate_document_spans_accepts_empty_test_entities():
    document = document_with(entities=(), sections=[section(0, "test article")], pmc_id="PMC-A")

    assert validate_document_spans(document) == []


def test_validate_document_spans_includes_pmc_id_and_field_path():
    mention = PatientMention(text="fever", offset=99, length=5)
    document = document_with(mentions=(mention,), pmc_id="PMC-ERROR")

    issues = validate_document_spans(document)

    assert len(issues) == 1
    issue = issues[0]
    assert issue.pmc_id == "PMC-ERROR"
    assert issue.item_path == "patient[0].mention[0]"
    assert issue.error_code == "OUTSIDE_SECTIONS"
    assert "PMC-ERROR" in issue.message
    assert "patient[0].mention[0]" in issue.message


def test_get_span_text_returns_exact_source_slice():
    assert get_span_text([section(4, "a  b")], 5, 2) == "  "