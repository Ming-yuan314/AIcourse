# Task 1 environment compatibility

The lightweight Task 1 foundation environment is `patientphex-task1` on
`linux-64`.

- Conda: 24.11.3
- Channel: `conda-forge`
- Python: 3.11.16 (declared as `python=3.11`)
- pytest: 8.3.5
- Scope: JSONL schema, offset-preserving IO, and unit tests. Heavy model and
  CUDA packages are intentionally deferred until their compatibility is tested.

Recreate the declared environment with:

```bash
conda env create -f environments/task1-conda.yml
```

For the exact linux-64 package set, use:

```bash
conda create --name patientphex-task1 --file environments/task1-conda-linux-64.lock
```

Run the foundation tests with:

```bash
conda run --name patientphex-task1 pytest -q tests/common
```