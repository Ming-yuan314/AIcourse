# PatientPheX — Task 1 Agent Guide

This repository implements the PatientPheX competition system. This guide
applies to work on **Task 1: phenotype mention recognition and HPO
normalization**. The authoritative implementation plan is
`docs/superpowers/plans/2026-09-15-patientphex-implementation-plan.md`.

## Scope and success criteria

Task 1 consumes the prepared full-text documents, frozen HPO ontology, and
PhenoTagger candidates. It produces one record per `pmc_id` at:

```text
runs/<run_id>/task1_entities.jsonl
```

The baseline must combine HPO dictionary matching and PhenoTagger, normalize
mentions to the competition HPO release, and post-process duplicates,
overlaps, negation, and simple compound phenotypes. A single documented command
must generate the prediction file. Every emitted mention must satisfy:

```python
source[offset : offset + length] == text
```

Report non-zero Mention-F1 and Document-F1 on the fixed article-level folds,
and make the output pass the local submission validator.

## Non-negotiable constraints

- Code belongs in `/mnt/data/wzh/AIcourse/patientphex-2026`; data, models, caches,
  and experiment outputs belong in `/mnt/data/wzh/AIcourse/patientphex-2026-data`
  and must
  never be committed.
- `/mnt/data/wzh/AIcourse/patientphex-2026-data/downloads/PatientData/` is the
  immutable original source. Never rename, overwrite, delete, re-extract over,
  or clean files in that directory.
- The fixed HPO input is
  `/mnt/data/wzh/AIcourse/patientphex-2026-data/ontology/hp-2026-06-23.obo`.
- Use only HPO `v2026-06-23`, restricted to the `HP:0000118` branch.
- Do not alter raw full text in a way that changes character length. Preserve
  offsets against the original source text exactly.
- Do not use external human-annotated phenotype datasets. Public external
  resources must have their source and licence recorded in `docs/resources.md`.
- Split training and validation by article only. Never split sections,
  sentences, or entities from the same article across folds.
- Keep the whole inference system at or below 10B parameters.
- Work on only one session at a time. GPU 0 is the primary Task 1
  training/inference device; GPU 1 may run another fold, ablation, or shard of
  the same Task 1 stage only.
- Record `CUDA_VISIBLE_DEVICES`, random seed, configuration path, commit,
  elapsed time, logs, and checkpoint for every run.

## Required prerequisites

Do not start Task 1 implementation until S0 and S1 have succeeded:

- `processed/documents.jsonl` and article-level `processed/folds.json` exist.
- HPO `v2026-06-23` is available under the data root and its provenance is
  documented.
- Common JSONL parsing, section/global offset mapping, HPO loading, metrics,
  result merging, and validation pass `pytest -q tests/common`.
- The working tree is clean and the previous handoff has been read when there
  is a failing test or unfinished state.

At the beginning of every session, run:

```bash
git status
git log -5 --oneline
pytest -q
```

## Task 1 implementation order

Use test-driven development. Add a focused failing test, run it to confirm the
failure, implement the minimum behavior, and rerun the focused test before
continuing.

1. Create tests under `tests/task1/` from real training examples for dictionary
   matches, exact offsets, overlaps, negated mentions, and simple compound
   phenotypes.
2. Implement `src/patientphex/task1/dictionary.py` to build deterministic HPO
   name/synonym matching from the frozen ontology only.
3. Implement `src/patientphex/task1/phenotagger.py` and configure it to use
   the competition HPO release rather than an implicit default ontology.
4. Implement `candidates.py` to merge dictionary and PhenoTagger candidates
   without losing source span provenance.
5. Implement `normalization.py`: exact reliable matches map directly to HPO;
   no reliable mapping is handled by the documented `-1` rule.
6. Implement `postprocess.py` for deterministic duplicate removal, overlap
   resolution, negation filtering, and simple compound-phenotype handling.
7. Implement `pipeline.py`, `configs/task1/baseline.yaml`, and
   `scripts/run_task1.py` so one command writes the required JSONL artifact.
8. Evaluate on `processed/folds.json` with the common Mention-F1 and
   Document-F1 implementation, then validate the generated predictions.
9. Save the exact configuration, metrics, error examples, and timing in the
   experiment record; update the S2 handoff and project status.

Expected Task 1 files:

```text
src/patientphex/task1/dictionary.py
src/patientphex/task1/phenotagger.py
src/patientphex/task1/candidates.py
src/patientphex/task1/normalization.py
src/patientphex/task1/postprocess.py
src/patientphex/task1/pipeline.py
configs/task1/baseline.yaml
scripts/run_task1.py
tests/task1/
docs/handoffs/S2-task1-baseline.md
```

## Validation before handoff

Run at least:

```bash
pytest -q tests/task1
python scripts/run_task1.py --config configs/task1/baseline.yaml --run-id <run_id>
python scripts/evaluate.py --task task1 --predictions \
  "$PATIENTPHEX_DATA_ROOT/runs/<run_id>/task1_entities.jsonl" --folds \
  "$PATIENTPHEX_DATA_ROOT/processed/folds.json"
python scripts/validate_submission.py --task task1 --input \
  "$PATIENTPHEX_DATA_ROOT/runs/<run_id>/task1_entities.jsonl"
```

Replace placeholders with concrete values in run records, never in committed
source. If a planned CLI differs from the implemented common interface, update
this guide and the handoff with the exact supported command.

Before ending the session, update `PROJECT_STATUS.md` and
`docs/handoffs/S2-task1-baseline.md` with start/end commits, completed and
remaining work, changed files, exact commands, metrics, duration, GPU usage,
known failures, and the next session's input and acceptance condition. Commit
the completed baseline as:

```text
feat(task1): add reproducible baseline
```
