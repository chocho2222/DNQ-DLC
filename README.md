# DNQ-DLC

Official release candidate for **Dynamic-Neighborhood Quality-Guided Deep
Latent Competition (DNQ-DLC)**, a simulator framework for online multi-car
overtaking. The framework dynamically constructs a local interaction graph
from surrounding vehicles; it is not tied to a fixed neural interface.

> **Release status:** the scientific package is maintained in a private
> author-owned repository until manuscript submission. Before changing the
> repository to public, complete the track/media provenance gate in
> [ASSET_LICENSES.md](ASSET_LICENSES.md) and insert the final citation metadata.

## Main evidence

On 200 matched simulator cases, DNQ-DLC completed at least one overtake in
171 cases (85.5%), compared with 143 cases (71.5%) for Rule Expert. The paired
difference was +14.0 percentage points (95% paired bootstrap CI 6.5 to 21.5;
two-sided exact McNemar p = 0.000617).

For the vehicle-count extrapolation stratum (N=7-8), DNQ-DLC achieved 67/80
(83.75%) and Rule Expert 45/80 (56.25%). This supports generalization within
the evaluated simulator and vehicle-count range. It is not evidence of
unrestricted transfer to arbitrary traffic, tracks, sensors, or real vehicles.

These results support an advantage of the **complete DNQ-DLC framework** on
the evaluated benchmark. They do not isolate dynamic graph construction as
the sole cause of the improvement and do not establish universal safety or
overall performance optimality. See [MODEL_CARD.md](MODEL_CARD.md) and
[DATA_CARD.md](DATA_CARD.md) for limitations.

## Repository contents

| Path | Contents |
|---|---|
| `code/` | Simulator, DNQ-DLC/DLC implementations, evaluation and analysis scripts |
| `configs/` | Release-relative experiment configurations |
| `checkpoints/` | DNQ-DLC, DLC and RL checkpoints; see asset licence status before reuse |
| `source_data/` | Frozen source tables and statistical reports |
| `docs/` | GitHub Pages-ready evidence site, figures, tables and 22 simulation videos |
| `materials/` | Release archive manifests and checksums inventory |

## Installation

The validated environment uses Linux, Python 3.10 and the versions recorded
in `environment.yml`:

```bash
conda env create -f environment.yml
conda activate dnq-dlc
python -m pip install -e .
```

CPU execution is sufficient for statistical reproduction. Closed-loop model
evaluation is substantially faster with a CUDA-capable GPU. The simulator
uses legacy Gym/Box2D and may require system OpenGL libraries for rendering.

## Reproduce the primary result

From the repository root:

```bash
python code/export_e1_primary_endpoint_analysis.py \
  --source source_data/E1_primary/online_benchmark_nature_direct_source_data.csv \
  --output-dir outputs/e1_primary_endpoint
```

The expected primary comparison is 171/200 versus 143/200, a paired
difference of 0.140, 95% CI [0.065, 0.215], and exact McNemar
p = 0.0006173783. Frozen outputs are in `source_data/E1_primary/`.

## Run one closed-loop case

```bash
python code/run_tits_dynamic_graph_evaluation.py \
  --config configs/dnq_dlc_release.json \
  --out-dir outputs/reproduction_run \
  --algorithms v6_runtime_dynamic_neighborhood_safe,rule_expert_gate,dlc_joint_transition_observer \
  --num-agents 4 --seed 101 --max-steps 2200 --no-gif
```

This is a functional check, not a replacement for the frozen 200-case matched
evaluation. Hardware, graphics drivers and floating-point libraries can affect
trajectory-level reproducibility.

## Figures and video evidence

The research-artifact site in `docs/` contains editable SVG/PDF figures,
downloadable frozen source data, and 22 MP4 simulation clips linked to the
corresponding experiments. After the repository is public, the prepared Pages
workflow will deploy it at `https://chocho2222.github.io/DNQ-DLC/`. Until then,
open `docs/index.html` locally.

## Licensing and responsible use

Software is distributed under the [MIT License](LICENSE), subject to retained
upstream notices. Author-owned source data, figures, simulation videos and
self-trained checkpoints are distributed under
[CC BY 4.0](LICENSE-ASSETS.md), with the scope and track-related exclusions in
[ASSET_LICENSES.md](ASSET_LICENSES.md). Do not use this research controller in
real vehicles or safety-critical systems.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md),
[CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and the
[Code of Conduct](CODE_OF_CONDUCT.md) before contributing or redistributing
assets.

The simulator implementation is derived from Multi-Car Racing and OpenAI Gym
CarRacing. The controller is methodologically inspired by *Deep Latent
Competition: Learning to Race Using Visual Control Policies in Latent Space*
(Schwarting et al., 2021, arXiv:2102.09812). See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Citation

Author names, affiliations, ORCID identifiers, paper title/DOI and the final
software DOI will be added after the manuscript is frozen. A metadata template
is provided in `CITATION.cff.template`; do not cite the release-candidate
placeholder as a published record.

## Release checklist

The repository URL, tag, commit hash, Pages URL and archival DOI will be
recorded after authenticated publication. See
[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) and
[PUBLISHING.md](PUBLISHING.md) for the remaining gates.
