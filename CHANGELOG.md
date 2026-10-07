# Changelog

All notable changes to the research package are documented here.

## [Unreleased]

- Rebuilt the evaluation code, configurations, checkpoints and frozen tables from
  the 2026-09-29 evaluation. `code/scripts`, `code/dlc`,
  `code/gym_multi_car_racing` and `configs/` now carry the code that produced the
  manuscript numbers, and `code/tests` carries its unit tests.
- Added `release_manifest.json`, the content digest of the evaluated snapshot
  `tits-2026-09-29`, and `reproduce/rebuild_release_manifest.sh`, which
  recomputes it from a copy of this repository.
- Added `source_data/`, holding the per-case endpoint tables, containment and
  controller-signal audits, threshold-perturbation sweep, admission-rule
  isolation runs, held-out prediction checks and the qualitative-snapshot
  traces behind the manuscript figures.
- Replaced the checkpoints: the submitted controller, its four further training
  draws, the two admission-rule control models, the four DLC training draws, and
  the fifteen continuous-control checkpoints of the reported comparison.
- Replaced `paper/` with the current manuscript: `main.tex`, `references.bib`,
  the compiled PDF, the six figures it uses, and the figure provenance and
  source records. The earlier supplementary material and the figures of the
  first evaluation are no longer part of the package.
- Rewrote `README.md`, `MODEL_CARD.md` and `DATA_CARD.md` around the 48-case
  evaluation; the numbers previously quoted there came from the earlier
  200-case study.
- Added `materials/RELEASE_ARCHIVE_MANIFEST.*` regeneration through
  `reproduce/rebuild_archive_manifest.py`.
- `docs/` still hosts the earlier evidence portal and its simulation clips; the
  quantitative claims it reports are superseded by `paper/`.

## [0.1.0-rc.1] - 2026-07-16

- Added the DNQ-DLC implementation, simulator integration and release-relative
  configurations.
- Added DNQ-DLC, DLC and RL model checkpoints.
- Added the frozen 200-case matched primary-endpoint source data and analysis.
- Added publication figures, source tables and 22 simulation videos.
- Added the GitHub Pages-ready evidence site and release manifests.
- Added packaging, continuous integration and project governance files.
