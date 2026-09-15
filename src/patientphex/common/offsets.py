"""Exact global character offset resolution for PatientPheX documents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .schema import Document, Section


@dataclass(frozen=True, slots=True)
class LocatedSpan:
    section_index: int
    section_type: str
    global_offset: int
    local_offset: int
    length: int
    text: str


class OffsetError(ValueError):
    """Raised when a global span cannot be resolved unambiguously."""

    def __init__(self, error_code: str, offset: int, length: int, detail: str) -> None:
        self.error_code = error_code
        self.offset = offset
        self.length = length
        super().__init__(f"{error_code}: offset={offset}, length={length}; {detail}")


@dataclass(frozen=True, slots=True)
class SpanIssue:
    pmc_id: str
    span_type: str
    item_path: str
    offset: int
    length: int
    error_code: str
    message: str


def _section_range(section: Section) -> tuple[int, int]:
    return section.offset, section.offset + len(section.text)


def _error(error_code: str, offset: int, length: int, detail: str) -> OffsetError:
    return OffsetError(error_code, offset, length, detail)


def locate_span(
    sections: Sequence[Section],
    offset: int,
    length: int,
) -> LocatedSpan:
    """Locate a positive half-open global span in exactly one section."""
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise _error("INVALID_OFFSET", offset, length, "offset must be a non-negative integer")
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        raise _error("INVALID_LENGTH", offset, length, "length must be a positive integer")

    stop = offset + length
    ranges = [(_section_range(section), index, section) for index, section in enumerate(sections)]
    nonempty = [(start, end, index, section) for (start, end), index, section in ranges if end > start]
    if not nonempty:
        raise _error("OUTSIDE_SECTIONS", offset, length, "no non-empty sections are available")

    containing = [
        (start, end, index, section)
        for start, end, index, section in nonempty
        if start <= offset and stop <= end
    ]
    if len(containing) > 1:
        raise _error(
            "AMBIGUOUS_SECTION",
            offset,
            length,
            "section overlap causes ambiguous coverage",
        )
    if len(containing) == 1:
        start, _end, index, section = containing[0]
        local_offset = offset - start
        return LocatedSpan(
            section_index=index,
            section_type=section.section_type,
            global_offset=offset,
            local_offset=local_offset,
            length=length,
            text=section.text[local_offset : local_offset + length],
        )

    article_start = min(start for start, _end, _index, _section in nonempty)
    article_end = max(end for _start, end, _index, _section in nonempty)
    if offset < article_start or stop > article_end:
        raise _error(
            "OUTSIDE_SECTIONS",
            offset,
            length,
            f"span lies outside section bounds [{article_start}, {article_end})",
        )

    intersecting = [
        (start, end, index, section)
        for start, end, index, section in nonempty
        if start < stop and offset < end
    ]
    if not intersecting:
        raise _error("SECTION_GAP", offset, length, "span lies in a gap between sections")

    cursor = offset
    for start, end, _index, _section in sorted(intersecting, key=lambda item: (item[0], item[1])):
        if start > cursor:
            raise _error("SECTION_GAP", offset, length, "span crosses a gap between sections")
        cursor = max(cursor, end)
        if cursor >= stop:
            break
    if cursor < stop:
        raise _error("SECTION_GAP", offset, length, "span crosses a gap between sections")
    raise _error("CROSSES_SECTION", offset, length, "span crosses more than one section")


def get_span_text(
    sections: Sequence[Section],
    offset: int,
    length: int,
) -> str:
    """Return the exact source slice for a resolvable global span."""
    return locate_span(sections, offset, length).text


def validate_span_text(
    sections: Sequence[Section],
    offset: int,
    length: int,
    expected_text: str,
) -> LocatedSpan:
    """Resolve a span and verify its source text without normalizing it."""
    located = locate_span(sections, offset, length)
    if located.text != expected_text:
        expected_length = len(expected_text) if isinstance(expected_text, str) else -1
        actual_length = len(located.text)
        raise _error(
            "TEXT_MISMATCH",
            offset,
            length,
            "expected length "
            f"{expected_length}, actual length {actual_length}; "
            f"section_index={located.section_index}, local_offset={located.local_offset}",
        )
    return located


def _issue_for_span(
    document: Document,
    span_type: str,
    item_path: str,
    offset: int,
    length: int,
    expected_text: str,
) -> SpanIssue | None:
    try:
        validate_span_text(document.full_text, offset, length, expected_text)
    except OffsetError as error:
        message = f"{document.pmc_id} {item_path}: {error}"
        return SpanIssue(
            pmc_id=document.pmc_id,
            span_type=span_type,
            item_path=item_path,
            offset=offset,
            length=length,
            error_code=error.error_code,
            message=message,
        )
    return None


def validate_document_spans(document: Document) -> list[SpanIssue]:
    """Validate every patient mention and phenotype entity in a document."""
    issues: list[SpanIssue] = []
    for patient_index, patient in enumerate(document.patient):
        for mention_index, mention in enumerate(patient.mention):
            path = f"patient[{patient_index}].mention[{mention_index}]"
            issue = _issue_for_span(
                document,
                "patient_mention",
                path,
                mention.offset,
                mention.length,
                mention.text,
            )
            if issue is not None:
                issues.append(issue)
    for entity_index, entity in enumerate(document.entities):
        path = f"entities[{entity_index}]"
        issue = _issue_for_span(
            document,
            "entity",
            path,
            entity.offset,
            entity.length,
            entity.text,
        )
        if issue is not None:
            issues.append(issue)
    return issues


__all__ = [
    "LocatedSpan",
    "OffsetError",
    "SpanIssue",
    "get_span_text",
    "locate_span",
    "validate_document_spans",
    "validate_span_text",
]