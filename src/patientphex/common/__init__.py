"""Shared PatientPheX data contracts and IO helpers."""
from .io import JSONLReadError, load_jsonl, read_jsonl
from .offsets import (
    LocatedSpan,
    OffsetError,
    SpanIssue,
    get_span_text,
    locate_span,
    validate_document_spans,
    validate_span_text,
)
from .schema import Association, Document, Entity, Patient, PatientMention, SchemaError, Section

__all__ = [
    "Association", "Document", "Entity", "JSONLReadError", "LocatedSpan", "OffsetError",
    "Patient", "PatientMention", "SchemaError", "Section", "SpanIssue", "get_span_text",
    "load_jsonl", "locate_span", "read_jsonl", "validate_document_spans", "validate_span_text",
]