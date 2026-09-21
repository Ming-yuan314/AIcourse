# S1 Data Preparation Handoff

## Commits

- Start commit: `4bedf01fe52602040b2d92cff74a3d8c5b681049`
- Implementation commit: `90ba1078cc84698ea35615b2a82780e9aefa360f`
- Branch: `codex/task1-data-foundation`

## Completed

- Added `write_jsonl()` with UTF-8, `ensure_ascii=False`, trailing newline, source-order preservation, temporary-file fsync, and atomic replacement.
- Writes inside the immutable `downloads/PatientData` tree are rejected.
- Added `prepare_dataset()` to validate non-empty/unique `pmc_id` values, validate all patient mentions and entities with `validate_document_spans()`, write an exact work copy, reload it, compare every `Document.to_dict()`, and report SHA256/count summaries.
- Added `create_article_folds()` using `SHA256(f"{seed}:{pmc_id}")` ordering and `index % n_folds`; assignments depend only on article IDs and the seed.
- Added `scripts/prepare_data.py` to generate the two work copies, `folds.json`, and `manifest.json` without embedding host-only paths in the manifest.
- Added focused preparation tests covering JSONL round trips, UTF-8, ordering, atomic temp cleanup, duplicate IDs, invalid spans, fold coverage/determinism, and manifest fields.

## Generated artifacts

Output directory:
`/mnt/data/wzh/AIcourse/patientphex-2026-data/processed`

| Artifact | SHA256 |
| --- | --- |
| `documents.jsonl` | `5029544d59a1e812de83c07a56d841c09b88cae222d4266fd2930b4c9a224786` |
| `a-documents.jsonl` | `dd734837cc1f9276ca15797db6807d71464a1f698808620d418a2a46712d95cd` |
| `folds.json` | `8254373348225374cd0cd3e69b939d999c95ebead814c9bae780ac5d88412a7f` |
| `manifest.json` | `71f194a74b0bb2a4242ce04e4261a0c27bd0c95c7ffd7db5b5fb016e62b77e54` |

`folds.json` records seed `20260915`, five folds, and 16 documents per fold. `manifest.json` records Git commit `90ba1078cc84698ea35615b2a82780e9aefa360f`, HPO version `v2026-06-23`, source/work-copy hashes, and all counts.

## Verification commands and results

```bash
cd /mnt/data/wzh/AIcourse/patientphex-2026

conda run -n patientphex-task1 pytest -q tests/common/test_preparation.py
# 7 passed

conda run -n patientphex-task1 pytest -q tests/common
# 29 passed

conda run -n patientphex-task1 pytest -q
# 29 passed

conda run -n patientphex-task1 python -m compileall -q src scripts
# exit 0

conda run -n patientphex-task1 python scripts/prepare_data.py \
  --train /mnt/data/wzh/AIcourse/patientphex-2026-data/downloads/PatientData/PatientPheX-train.jsonl \
  --a-list /mnt/data/wzh/AIcourse/patientphex-2026-data/downloads/PatientData/PatientPheX-A.jsonl \
  --output-dir /mnt/data/wzh/AIcourse/patientphex-2026-data/processed \
  --folds 5 --seed 20260915
# Train documents: 80; patients: 209; patient mentions: 677; entities: 6027; associations: 209
# A-list documents: 20; patients: 53; patient mentions: 147; entities: 0; associations: 0
```

The immutable source hashes remain:

- Train: `5029544d59a1e812de83c07a56d841c09b88cae222d4266fd2930b4c9a224786`
- A-list: `dd734837cc1f9276ca15797db6807d71464a1f698808620d418a2a46712d95cd`

`wc -l` reports 80 `documents.jsonl` records and 20 `a-documents.jsonl` records. No temporary `.tmp` files remain in `processed`.

## Resources and runtime

- Input source: `/mnt/data/wzh/AIcourse/patientphex-2026-data/downloads/PatientData/` (read-only; not modified).
- HPO fixed file: `/mnt/data/wzh/AIcourse/patientphex-2026-data/ontology/hp-2026-06-23.obo`.
- `CUDA_VISIBLE_DEVICES` was not set; this preparation is CPU-only and uses no model/checkpoint.

## Known issues and failures

- The first direct CLI attempt needed the repository `src` path inserted, matching the existing validation script; this is now fixed and the documented command succeeds.
- No known data preparation, offset, or fold validation failures remain.

## Next session input and acceptance

Consume `processed/documents.jsonl` and `processed/folds.json` as read-only preparation outputs. The next task is the HPO v2026-06-23 loader restricted to the `HP:0000118` branch; it must preserve these hashes and keep the original download directory untouched.
