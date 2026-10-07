# DNQ-DLC

Release candidate for **Dynamic-Neighbourhood Quality-Guided Deep Latent
Competition (DNQ-DLC)**, a closed-loop overtaking controller for multi-vehicle
racing. The controller builds an ego-centric interaction graph from the vehicles
that matter at the current decision step, predicts their short-horizon
interaction with candidate ego actions through an action-conditioned graph world
model, and ranks candidates by progress, containment, interaction quality,
boundary risk and uncertainty before committing the first action.

> **Release status.** The package is kept in an author-owned repository until the
> manuscript is submitted. Before changing visibility, complete the
> track-and-media provenance gate in [ASSET_LICENSES.md](ASSET_LICENSES.md) and
> insert the final citation metadata.

## What the evaluation shows

Every method is evaluated on the same 48 cases: 12 procedurally generated
circuits crossed with fleet sizes of 4, 6, 8 and 10 vehicles. Within a case all
methods face the same track, initial state and opponent behaviour. An overtake is
scored from recorded telemetry in nested tiers, so a pass counts only when it
survives a sustained lead, the absence of contact, on-track execution, post-pass
stability, and a racing rival rather than one already off the surface.

The proposed controller is reported as the mean over five draws of its training
recipe, each DLC variant over four, and each continuous-control family over five
training seeds.

| Method | Cases completed | Strict tier | Racing-rival tier | Grass fraction | Rank gain |
|---|---:|---:|---:|---:|---:|
| DNQ-DLC | 45.8 | 20.2 [14, 26] | 11.0 [6, 15] | 0.157 | 4.88 |
| DNQ-DLC, shield off | 44.6 | 20.6 | 8.8 | 0.169 | 4.68 |
| Rule expert | 45 | 12 | 7 | 0.299 | 3.98 |
| DLC-IT (matched) | 41.0 | 17.5 [15, 20] | 10.5 | 0.311 | 3.98 |
| DLC-JT (matched) | 41.5 | 18.5 [14, 23] | 12.5 | 0.364 | 4.19 |
| DLC-JTO (matched) | 45.5 | 13.5 [11, 16] | 8.0 | 0.457 | 2.49 |
| PPO | 35.8 | 6.4 | 3.2 | 0.721 | 0.47 |
| SAC | 10.2 | 1.6 | 0 | 0.331 | 0.10 |
| TD3 | 8.2 | 2.2 | 0.2 | 0.245 | 0.11 |

Brackets span the draws of that recipe. Rank gain and containment separate the
proposed controller from every comparator draw; the strict-tier range overlaps
the three world-model variants, and the sizes of those margins belong to the
draw rather than to the recipe, which is why the endpoint is reported as counts
with intervals. The rule expert matches the pass count but converts fewer passes
into strict-tier and racing-rival successes.

Three measurements support the three mechanisms. Re-packing the released expert
episodes under three admission rules at the same three-slot budget and
retraining under an identical recipe gives 21 strict-tier cases for the
interaction ranking against 17 for the nearest opponents and 15 for a fixed
identity window. Removing the recovery shield leaves the strict tier unchanged at
20.6 cases and costs the racing-rival tier and two completions, so the shielded
endpoint is the last clause of the graded tier rather than the strict tier. The
quality score leaves the rule anchor on 92 % of decision steps, and the imagined
rollout of the ego position is 0.45-0.47 m in error at a one-step horizon and
0.85-1.18 m at four steps.

What the evaluation does not establish: the simulator is two-dimensional with
planar kinematics and a contact response, not a tyre-slip or load-transfer
model; the learned comparators are trained under their own budgets and none is
trained to convergence, so the table characterises the systems as evaluated;
fleet sizes of 4 to 10 vehicles and one procedural track family bound the
transfer claims; and nothing here is evidence for real vehicles. See
[MODEL_CARD.md](MODEL_CARD.md) and [DATA_CARD.md](DATA_CARD.md).

## Baseline provenance

DLC-IT, DLC-JT and DLC-JTO are retrained implementations of the
individual-transition, joint-transition and joint-transition-plus-observer
variants introduced in [Deep Latent Competition](https://arxiv.org/abs/2102.09812),
packed and trained under the observation layout of this paper.

PPO, SAC and TD3 follow their original publications and use Stable-Baselines3.
Rule Expert is an author-implemented telemetry controller rather than a method
adopted from an external paper. [BASELINE_PROVENANCE.md](BASELINE_PROVENANCE.md)
holds the complete mapping and source links.

## Repository contents

| Path | Contents |
|---|---|
| `code/` | Simulator, controller, evaluation, analysis and figure scripts, and the unit tests |
| `reproduce/` | Release-relative quickstart configuration and the manifest rebuilders |
| `configs/` | The 98 frozen experiment configurations of the released run matrix |
| `checkpoints/` | Proposed controller (submitted draw, further draws, admission-rule controls), DLC variants and their training draws, and the 15 continuous-control checkpoints |
| `source_data/` | Frozen per-case evaluation tables, audit tables and statistical reports |
| `paper/` | Manuscript sources, the six figures they use, and the compiled PDF |
| `docs/` | Earlier evidence portal retained for its simulation clips; the numbers it quotes are superseded by `paper/` |
| `materials/` | Local archive manifest and per-file SHA-256 record |
| `release_manifest.json` | Content digest of the evaluated snapshot `tits-2026-09-29` |

`release_manifest.json` covers 1755 files, 101,832,622 bytes and carries the
digest `sha256:2d3af4413d04ff96bfd1a85bdc8c9d1b57f48f2a40b3cdac46dd8913225ece98`.
Recompute it over a copy of this repository with

```bash
bash reproduce/rebuild_release_manifest.sh
```

The recipe is a SHA-256 over sorted `<root>/<path>:<digest>` lines, so the value
depends on file contents and not on where the copy is checked out. The recorded
trajectories behind the raw runs are 8.5 GB and are not part of the snapshot.

## Installation

The validated environment is Linux with Python 3.10 and the versions recorded in
`environment.yml`:

```bash
conda env create -f environment.yml
conda activate dnq-dlc
python -m pip install -e .
```

CPU execution is sufficient to reproduce the statistical analysis. Closed-loop
evaluation is substantially faster on a CUDA-capable GPU. The simulator uses
legacy Gym/Box2D and may need system OpenGL libraries for rendering.

## Run one case

```bash
python code/scripts/run_tits_dynamic_graph_evaluation.py \
  --config reproduce/dnq_dlc_release.json \
  --out-dir outputs/reproduction_run \
  --algorithms ours_dnq_dlc,rule_expert_gate,dlc_joint_transition_observer \
  --num-agents 4 --seed 101 --max-steps 2200 --no-gif
```

This is a functional check on one case, not a rerun of the 48-case evaluation.
Hardware, graphics drivers and floating-point libraries can shift individual
trajectories.

## Tests

The suite runs in this layout, from the repository root or from `code/`:

```bash
cd code && PYTHONPATH=$PWD python -m unittest discover -s tests -p 'test_*.py'
```

It needs the simulator dependencies, so run it in the environment of
`environment.yml` (146 tests, one skipped when an artifact of the development
tree is absent). Continuous integration runs the checks that need no simulator:
it compiles the sources, audits the static-site links, recomputes the release
digest, and recomputes the five-draw means of the proposed controller from the
frozen per-case table to compare them with the manuscript.

## Figures and clips

`paper/figures/` holds the six figures of the manuscript. `docs/` keeps the
earlier static portal, including the simulation clips recorded for the first
evaluation, with its own link audit and revision manifest; open
`docs/index.html` locally. The workflow in `.github/workflows/` is prepared to
deploy it once the repository is public.

## Licensing and responsible use

Software is distributed under the [MIT License](LICENSE), subject to retained
upstream notices. Author-owned source data, figures, clips and self-trained
checkpoints are distributed under [CC BY 4.0](LICENSE-ASSETS.md), with the scope
and track-related exclusions in [ASSET_LICENSES.md](ASSET_LICENSES.md). Do not
use this controller in real vehicles or safety-critical systems.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md),
[CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md) before contributing or redistributing
assets. The simulator implementation is derived from Multi-Car Racing and OpenAI
Gym CarRacing; the controller is methodologically related to *Deep Latent
Competition: Learning to Race Using Visual Control Policies in Latent Space*
(Schwarting et al., 2021, arXiv:2102.09812).

## Citation

Author names, affiliations, ORCID identifiers, the paper title and DOI, and the
software DOI will be added once the manuscript is frozen.
`CITATION.cff.template` holds the metadata skeleton; the release candidate is not
a citable record.
