# Contributing

Thank you for improving DNQ-DLC. Contributions should preserve the distinction
between frozen paper evidence and exploratory results.

## Before opening a change

1. Search existing issues and describe the scientific or engineering problem.
2. Do not commit credentials, personal data, proprietary tracks, or assets
   whose redistribution rights are unclear.
3. Put new exploratory outputs under `outputs/`; this path is ignored by Git.
4. Do not overwrite frozen tables in `source_data/` without documenting the
   experiment protocol, random seeds and reason for the revision.

## Development setup

```bash
conda env create -f environment.yml
conda activate dnq-dlc
python -m pip install -e ".[dev]"
```

Before submitting a pull request, run:

```bash
python -m compileall -q code
python code/export_e1_primary_endpoint_analysis.py \
  --source source_data/E1_primary/online_benchmark_nature_direct_source_data.csv \
  --output-dir outputs/e1_primary_endpoint_check
```

## Pull requests

State the affected experiment, expected behavior, tests run and any changes to
reported numbers. Model or dataset changes must include provenance, licence,
file size, checksum and a model/data card update. By contributing, you confirm
that you have the right to submit the material under the repository's stated
licences.
