# Asset licence register

This register records the author's confirmed ownership decisions and the
remaining public-release boundary. It does not relicense third-party material.

| Asset | Location | Terms | Status |
|---|---|---|---|
| Original DNQ-DLC software | `code/dlc/`, experiment and analysis scripts | MIT | Author confirmed |
| Modified simulator software | `code/gym_multi_car_racing/` | Upstream MIT with original notices retained; author modifications under MIT | Confirmed |
| Generated source data | `source_data/`, `docs/tables/` | CC BY 4.0 | Author confirmed |
| Author-created figures | `docs/assets/analysis_figures/` | CC BY 4.0, subject to the simulation-frame boundary below | Author confirmed |
| Author-created simulation videos | `docs/assets/videos/` | CC BY 4.0, subject to the track boundary below | Author confirmed |
| DNQ-DLC checkpoints | `checkpoints/dnq_dlc/` | CC BY 4.0 | Self-trained; author confirmed |
| DLC baseline checkpoints | `checkpoints/dlc_baselines/`, `checkpoints/dlc_jto_training_seeds/` | CC BY 4.0 | Self-trained; author confirmed |
| RL baseline checkpoints | `checkpoints/rl_baselines/` | CC BY 4.0 | Self-trained in this simulator; author confirmed |

## Track and game-asset boundary

The repository does not contain Assetto Corsa executables, car/track models,
textures, `.kn5` files, or extracted game-resource archives. The packaged RL
checkpoint metadata records procedural training tracks. Some evidence metadata
references author-created `tracks/*.npz` geometries such as
`monza_scaled.npz`; those geometry files are not distributed in this release.

Before making the repository public, the authors must document that every
custom track geometry was independently created or is otherwise redistributable.
If any geometry was extracted from Assetto Corsa or another proprietary game,
do not publish that geometry or claim CC BY 4.0 rights over it. Review rendered
videos and figure panels based on such geometry and either:

1. replace them with procedurally generated or independently created tracks;
2. obtain explicit redistribution permission; or
3. keep the affected media outside the public release.

Names such as "Monza-like" describe a test geometry and do not imply
affiliation with, or endorsement by, the game publisher or circuit owner.

## Licence interpretation

- The MIT licence applies to project-authored software and retained upstream
  MIT code.
- CC BY 4.0 applies only to author-owned research assets identified above.
- Each Python dependency remains under its own licence.
- Third-party trademarks, proprietary game assets and external track data are
  excluded from both project licences.
