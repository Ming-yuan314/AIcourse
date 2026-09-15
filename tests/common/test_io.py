import json

import pytest

from patientphex.common.io import JSONLReadError, read_jsonl
from patientphex.common.schema import SchemaError
from tests.common.test_schema import sample_document


def test_read_jsonl_reads_documents_in_order(tmp_path):
    path = tmp_path / "documents.jsonl"
    rows = [sample_document(), {**sample_document(), "pmc_id": "PMC456"}]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    documents = list(read_jsonl(path))

    assert [document.pmc_id for document in documents] == ["PMC123", "PMC456"]


def test_read_jsonl_reports_malformed_line_number(tmp_path):
    path = tmp_path / "broken.jsonl"
    path.write_text(json.dumps(sample_document()) + "\n{not-json}\n", encoding="utf-8")

    with pytest.raises(JSONLReadError, match=r"line 2"):
        list(read_jsonl(path))


def test_read_jsonl_wraps_schema_errors_with_line_number(tmp_path):
    path = tmp_path / "invalid.jsonl"
    invalid = sample_document()
    del invalid["association"]
    path.write_text(json.dumps(invalid) + "\n", encoding="utf-8")

    with pytest.raises(JSONLReadError, match=r"line 1") as error:
        list(read_jsonl(path))

    assert isinstance(error.value.__cause__, SchemaError)