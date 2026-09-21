"""Shared PatientPheX data contracts and IO helpers."""
from .io import JSONLReadError, load_jsonl, read_jsonl, write_jsonl
from .offsets import (
    LocatedSpan,
    OffsetError,
    SpanIssue,
    get_span_text,
    locate_span,
    validate_document_spans,
    validate_span_text,
)
from .preparation import (
    FoldAssignment,
    PreparationError,
    PreparationSummary,
    build_manifest,
    create_article_folds,
    prepare_dataset,
)
from .schema import Association, Document, Entity, Patient, PatientMention, SchemaError, Section

__all__ = [
    "Association",
    "Document",
    "Entity",
    "FoldAssignment",
    "JSONLReadError",
    "LocatedSpan",
    "OffsetError",
    "Patient",
    "PatientMention",
    "PreparationError",
    "PreparationSummary",
    "SchemaError",
    "Section",
    "SpanIssue",
    "build_manifest",
    "create_article_folds",
    "get_span_text",
    "load_jsonl",
    "locate_span",
    "prepare_dataset",
    "read_jsonl",
    "validate_document_spans",
    "validate_span_text",
    "write_jsonl",
]
