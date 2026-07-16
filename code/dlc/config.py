from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict


@dataclass
class DLCConfig:
    seed: int = 0
    num_agents: int = 2
    train_episodes: int = 5
    eval_episodes: int = 10
    max_steps_per_episode: int = 1000
    observation_type: str = "telemetry"
    policy_name: str = "joint_transition_observer"
    opponent_policy_name: str = "joint_transition_observer"
    output_dir: str = "outputs"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def resolve_output_dir(self) -> Path:
        return Path(self.output_dir)

