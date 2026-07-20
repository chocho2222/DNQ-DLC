# Third-party notices

DNQ-DLC includes or adapts third-party software. Their original notices and
licence terms remain in force.

## Multi-Car Racing / Gym CarRacing

The simulator code under `code/gym_multi_car_racing/` is derived from the
Multi-Car Racing environment and OpenAI Gym CarRacing. The retained MIT notice
is in [LICENSE](LICENSE).

- Upstream project: https://github.com/igilitschenski/multi_car_racing
- Original OpenAI Gym project: https://github.com/openai/gym
- Licence: MIT

## Python dependencies

Runtime dependencies are declared in `pyproject.toml` and
`environment.yml`. Each dependency is distributed under its own licence;
installing the environment does not relicense those packages under this
project's MIT licence.

## Deep Latent Competition

DNQ-DLC retains the world-model planning lineage of:

W. Schwarting, A. Pierson, J. Alonso-Mora, S. Karaman and D. Rus, "Deep
Latent Competition: Learning to Race Using Visual Control Policies in Latent
Space," arXiv:2102.09812, 2021.

The manuscript labels DLC-IT, DLC-JT, and DLC-JTO refer to the
individual-transition, joint-transition, and joint-transition-plus-observer
variants introduced in that study. The implementations and checkpoints in
this repository were independently produced and trained by the DNQ-DLC
authors; they are not official code or checkpoints from the cited paper.

## Reinforcement-learning baselines

The PPO, SAC, and TD3 comparisons follow the original algorithm publications:

- PPO: https://arxiv.org/abs/1707.06347
- SAC: https://proceedings.mlr.press/v80/haarnoja18b.html
- TD3: https://proceedings.mlr.press/v80/fujimoto18a.html

Training and checkpoint loading use Stable-Baselines3:
https://www.jmlr.org/papers/v22/20-1364.html. The distributed RL checkpoints
were trained by the DNQ-DLC authors.

Rule Expert and Safety Rule are author-implemented telemetry controls and do
not claim provenance from an external algorithm paper. Their definitions are
recorded in code/dlc/policies.py and summarized in
[BASELINE_PROVENANCE.md](BASELINE_PROVENANCE.md).

## Assetto Corsa and custom tracks

Assetto Corsa is referenced only as part of the authors' experimental
inspiration and track-design provenance. No Assetto Corsa game binaries,
models, textures or extracted resource archives are intentionally distributed.
Assetto Corsa and related names are trademarks of their respective owners.
The public-release restrictions for custom geometry and rendered media are in
[ASSET_LICENSES.md](ASSET_LICENSES.md).

## Models, tracks and media

Third-party or jointly produced checkpoints, track geometry and media are not
covered merely by the software licence. Their release status is recorded in
[ASSET_LICENSES.md](ASSET_LICENSES.md). Material excluded there is not covered
by the project software or research-asset licences.
