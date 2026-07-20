# Baseline provenance

This document identifies which comparison methods come from prior literature
and which are author-implemented controls.

| Manuscript label | Provenance | Implementation in this repository |
|---|---|---|
| DLC-IT | Individual-transition baseline introduced in Schwarting et al., *Deep Latent Competition* (2021) | Independently reimplemented and retrained by the DNQ-DLC authors |
| DLC-JT | Joint-transition baseline introduced in Schwarting et al., *Deep Latent Competition* (2021) | Independently reimplemented and retrained by the DNQ-DLC authors |
| DLC-JTO | Joint-transition-plus-observer method introduced in Schwarting et al., *Deep Latent Competition* (2021) | Independently reimplemented and retrained by the DNQ-DLC authors |
| PPO | Schulman et al., *Proximal Policy Optimization Algorithms* (2017) | Trained and evaluated through Stable-Baselines3 |
| SAC | Haarnoja et al., *Soft Actor-Critic* (ICML 2018) | Trained and evaluated through Stable-Baselines3 |
| TD3 | Fujimoto et al., *Addressing Function Approximation Error in Actor-Critic Methods* (ICML 2018) | Trained and evaluated through Stable-Baselines3 |
| Rule Expert | Author-implemented telemetry rule controller | Defined by TelemetryExpertGatePolicy in code/dlc/policies.py |
| Safety Rule | Author-implemented conservative barrier/density rule controller | Defined by TelemetryBarrierExpertGatePolicy in code/dlc/policies.py |
| DNQ-DLC | Method proposed in the accompanying manuscript | Implemented in the graph-world-model and evaluation modules |

## Primary sources

- W. Schwarting, A. Pierson, J. Alonso-Mora, S. Karaman, and D. Rus,
  [Deep Latent Competition: Learning to Race Using Visual Control Policies in Latent Space](https://arxiv.org/abs/2102.09812),
  arXiv:2102.09812, 2021.
- J. Schulman et al.,
  [Proximal Policy Optimization Algorithms](https://arxiv.org/abs/1707.06347),
  arXiv:1707.06347, 2017.
- T. Haarnoja et al.,
  [Soft Actor-Critic](https://proceedings.mlr.press/v80/haarnoja18b.html),
  ICML, 2018.
- S. Fujimoto, H. van Hoof, and D. Meger,
  [Addressing Function Approximation Error in Actor-Critic Methods](https://proceedings.mlr.press/v80/fujimoto18a.html),
  ICML, 2018.
- A. Raffin et al.,
  [Stable-Baselines3: Reliable Reinforcement Learning Implementations](https://www.jmlr.org/papers/v22/20-1364.html),
  JMLR, 2021.

The DLC and RL checkpoints distributed here were trained by the DNQ-DLC
authors. They are not official model files released by the cited authors.
