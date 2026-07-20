# RL Multi-seed Randomized Evaluation

- Valid summaries: 144
- Invalid summaries: 0

| family | training seeds | cases/seed | success mean [range] | desirable mean [range] | grass mean [range] | rank gain mean [range] |
|---|---:|---|---|---|---|---|
| DNQ-DLC | 1 | [12] | 1.000 [1.000, 1.000] | 0.054 [0.054, 0.054] | 0.115 [0.115, 0.115] | 2.167 [2.167, 2.167] |
| PPO | 3 | [12] | 0.694 [0.667, 0.750] | 0.410 [0.333, 0.500] | 0.876 [0.743, 0.957] | 0.278 [0.000, 0.750] |
| Rule expert | 1 | [12] | 0.917 [0.917, 0.917] | 0.417 [0.417, 0.417] | 0.220 [0.220, 0.220] | 2.000 [2.000, 2.000] |
| SAC | 3 | [12] | 0.889 [0.833, 0.917] | 0.287 [0.000, 0.444] | 0.236 [0.161, 0.379] | 1.250 [0.500, 2.250] |
| Safety rule | 1 | [12] | 0.917 [0.917, 0.917] | 0.347 [0.347, 0.347] | 0.151 [0.151, 0.151] | 2.333 [2.333, 2.333] |
| TD3 | 3 | [12] | 0.806 [0.750, 0.917] | 0.148 [0.028, 0.333] | 0.080 [0.000, 0.192] | 0.917 [0.083, 2.500] |

Ranges are across independent training seeds, not confidence intervals.
