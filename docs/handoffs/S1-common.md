# S1 Common Offset Validation Handoff

## Commits

- Start commit: `ba4d0b6724cc8b7d7b77c0067cad18e41b439e51`
- Implementation end commit: `ba21e74aa5e28a00bd6964cc35b78bec335f02c2`
- Branch: `codex/task1-data-foundation`

## Completed

- Added exact half-open global span resolution in `src/patientphex/common/offsets.py`.
- Added `LocatedSpan`, `OffsetError`, and `SpanIssue`.
- Implemented section-local conversion, exact source slicing, text validation, and document-level validation for patient mentions and entities.
- Added `scripts/validate_offsets.py`; it returns exit code 1 when any invalid span exists and exit code 2 for input/read errors.
- Exported the Offset API from `patientphex.common`.
- Preserved the optional official `full_text[].title` field in the existing schema model; no raw data was changed.

## Files changed in the implementation commit

- `src/patientphex/common/offsets.py`
- `src/patientphex/common/__init__.py`
- `tests/common/test_offsets.py`
- `scripts/validate_offsets.py`

## Verification commands and results

```bash
conda run -n patientphex-task1 pytest -q tests/common/test_offsets.py
# 15 passed

conda run -n patientphex-task1 pytest -q tests/common
# 22 passed

conda run -n patientphex-task1 python -m compileall -q src scripts
# exit 0

conda run -n patientphex-task1 python scripts/validate_offsets.py \
  --input /mnt/data/wzh/AIcourse/patientphex-2026-data/downloads/PatientData/PatientPheX-train.jsonl
# Documents: 80; Patient mentions: 677; Entities: 6027;
# Valid spans: 6704; Invalid spans: 0

conda run -n patientphex-task1 python scripts/validate_offsets.py \
  --input /mnt/data/wzh/AIcourse/patientphex-2026-data/downloads/PatientData/PatientPheX-A.jsonl
# Documents: 20; Patient mentions: 147; Entities: 0;
# Valid spans: 147; Invalid spans: 0
```

## Resources and runtime

- Input source: `/mnt/data/wzh/AIcourse/patientphex-2026-data/downloads/PatientData/`.
- The input source has no writable file or directory entries and was not modified.
- `CUDA_VISIBLE_DEVICES` was not set; this validation is CPU-only and uses no checkpoint.
- Duration was not captured by the remote shell; all commands above completed in the same session.

## Known issues and failures

- The first real-data scan found an optional `full_text[].title` field not listed in the initial README/schema assumptions. The model and regression test now preserve it losslessly.
- No known remaining offset validation failures.

## Next session input and acceptance

The next session should consume the validated official files and implement the common document parser/offset preparation into `processed/documents.jsonl` and article-level `processed/folds.json`. It must retain original offsets and pass `pytest -q tests/common` before Task 1 baseline work begins.