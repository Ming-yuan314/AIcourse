# PatientPheX Project Status

## Current state

- Branch: `codex/task1-data-foundation`
- Latest implementation commit: `cc50566` (`feat(data): add frozen HPO branch index`)
- The immutable official download directory and frozen HPO file remain unchanged.
- Common data foundation, offset validation, preparation/folds, and HPO branch indexing are implemented.

## Completed foundations

- Lightweight Conda environment `patientphex-task1` is locked for linux-64.
- Official HPO `v2026-06-23` is fixed at the data-root ontology path.
- Strict JSONL schema/reader, exact global offset validation, atomic JSONL writing, validated work copies, and deterministic article folds are implemented.
- `src/patientphex/common/hpo.py` loads only `hp/releases/2026-06-23`, indexes the `HP:0000118` branch, and exposes status-aware ID and name/synonym queries.

## Latest validation

- HPO-focused tests: 7 passed.
- Common tests: 36 passed.
- `python -m compileall -q src scripts`: exit 0.
- Official HPO parsed terms: 20,413.
- Valid terms in the `HP:0000118` branch: 19,120.
- Formal-name/EXACT-synonym index keys: 41,107.
- All-name/synonym index keys: 43,670.
- `alt_id` entries: 3,964.
- HPO SHA256: `a5092cbdf605f568403cf7380d9173014015692433b2cc631bc5c1b053876b1b`.
- Follow-up parser fix: `EXACT []` and other empty-xref synonym records now keep `synonym_type=None` instead of recording `[]`.
- HPO-focused tests after the fix: 8 passed; common tests: 37 passed.

## Next action

Implement the Task 1 dictionary candidate generator using `HPOIndex.find_by_name()` with exact formal names and EXACT synonyms. Do not add text matching, PhenoTagger, SapBERT, or model training to the common HPO loader.

The HPO loader stage is fully passed after commit `0b99a3b` (`fix(data): parse empty HPO synonym types`).
