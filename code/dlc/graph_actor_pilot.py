"""Run only the proposal actor from a newly fitted graph-world-model bundle."""
import numpy as np
import torch
from dlc.graph_policy import pack_dynamic_neighbor_obs, _opponent_fill_vector
from dlc.graph_world_model import GraphWorldModelBundle
from dlc.observation_layout import require_checkpoint_version


class GraphProposalPilot:
    name = 'graph_actor_pilot'

    def __init__(self, path, device='cpu'):
        self.device = torch.device(device)
        self.bundle = GraphWorldModelBundle.load(path, map_location=self.device)
        self.bundle.proposal_actor.to(self.device).eval()
        self.last_decision_debug = {}

    def reset(self):
        self.last_decision_debug = {}

    def act(self, env, obs):
        require_checkpoint_version(env, self.bundle.meta)
        packed = pack_dynamic_neighbor_obs(obs, fill=_opponent_fill_vector(self.bundle),
            target_obs_dim=self.bundle.meta['obs_dim'], max_neighbors=self.bundle.meta['max_neighbors'],
            selection_mode=self.bundle.meta.get('neighbor_selection', 'interaction'),
            telemetry_version=self.bundle.meta['telemetry_version'])
        with torch.no_grad():
            actions = self.bundle.proposal_actor(torch.as_tensor(self.bundle.normalize_obs(packed),
                dtype=torch.float32, device=self.device)).cpu().numpy()
        self.last_decision_debug = {'packed_obs': packed.tolist(), 'action': actions[-1].tolist(),
                                   'policy': 'learned proposal only; no world-model ranking or joint-clearance guard'}
        return np.asarray(actions, dtype=np.float32)
