# PatientPheX Project Status

## Current state

- Branch: `codex/task1-data-foundation`
- Latest implementation commit: `90ba1078cc84698ea35615b2a82780e9aefa360f` (`feat(data): prepare validated documents and article folds`)
- The immutable official download directory remains unchanged and read-only.
- Prepared artifacts are generated outside Git under the configured data root.

## Completed foundations

- Lightweight Conda environment `patientphex-task1` is locked for linux-64.
- Official HPO `v2026-06-23` is fixed at the data-root ontology path.
- Strict JSONL schema/reader, exact global offset validation, and atomic JSONL writing are implemented.
- Training and A-list work copies, deterministic article folds, and a portable manifest are generated.

## Latest validation

- Full test suite: `29 passed`.
- `python -m compileall -q src scripts`: exit 0.
- Training work copy: 80 documents, 209 patients, 677 patient mentions, 6027 entities, 209 associations, 0 invalid spans.
- A-list work copy: 20 documents, 53 patients, 147 patient mentions, 0 entities, 0 associations, 0 invalid spans.
- Article folds: 5 folds, each with 16 documents; every training `pmc_id` is assigned exactly once.
- Re-running the preparation command with the same seed produced identical hashes for all four artifacts.

## Next action

Implement the HPO `v2026-06-23` loader and the `HP:0000118` branch index. Do not begin Task 1 candidate generation until that common prerequisite is tested and handed off.
