# PatientPheX Project Status

## Current state

- Branch: `codex/task1-data-foundation`
- Latest implementation commit: `ba21e74aa5e28a00bd6964cc35b78bec335f02c2` (`feat(data): add exact global offset validation`)
- The Git worktree is clean after the implementation commit; the status document itself is pending in this documentation checkpoint.

## Completed foundations

- Lightweight Conda environment `patientphex-task1` is locked for linux-64.
- Official HPO `v2026-06-23` is fixed at the data-root ontology path.
- `downloads/PatientData` is preserved as a read-only original source.
- JSONL schema and strict reader are implemented and tested.
- Global offset resolution and validation are implemented and tested.

## Latest validation

- Offset tests: 15 passed.
- Common tests: 22 passed.
- Training source: 80 documents, 677 patient mentions, 6027 entities, 6704 valid spans, 0 invalid spans.
- A榜 source: 20 documents, 147 patient mentions, 0 entities, 147 valid spans, 0 invalid spans.
- `src` and `scripts` compile successfully with Python 3.11.

## Next action

Implement the remaining common preparation interfaces that generate
`processed/documents.jsonl` and `processed/folds.json`, then begin the Task 1
baseline only after those artifacts and common tests are green.