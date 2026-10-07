"""Explicit new development variants, sharing a fixed checkpoint and action pool.

The footprint formulas are local geometric proxies, not collision probabilities
or exact road-polygon containment. Archived planner defaults are unchanged.
"""
from dataclasses import asdict, dataclass
import math
import numpy as np
import torch

from dlc.graph_world_model import GraphWorldModelPolicy
from dlc.observation_layout import opponent_slots
from dlc.policies import TRACK_WIDTH


@dataclass(frozen=True)
class PhysicalQualityConfig:
    version: str = 'physical_quality_pilot_v1'
    half_length: float = 2.8
    half_width: float = 1.6
    edge_buffer: float = .2
    pair_buffer: float = .4
    lane_offset: float = 4.4
    recovery_heading_cos: float = .55
    boundary_weight: float = 8.
    contact_weight: float = 8.
    heading_weight: float = .42
    progress_scale: float = 10.


def footprint_terms(row, config=None):
    c = config or PhysicalQualityConfig()
    row = np.asarray(row)
    heading = math.atan2(float(row[13]), float(row[14]))
    extent = c.half_width*abs(math.cos(heading))+c.half_length*abs(math.sin(heading))
    edge_margin = TRACK_WIDTH - abs(float(row[12]))*TRACK_WIDTH-extent-c.edge_buffer
    near_contact = 0.
    min_pair_margin = None
    for other in opponent_slots(row, masked=True):
        angle = math.atan2(float(other[5]), float(other[6]))
        longitudinal = c.half_length*(1+abs(math.cos(angle)))+c.half_width*abs(math.sin(angle))+c.pair_buffer
        lateral = c.half_width*(1+abs(math.cos(angle)))+c.half_length*abs(math.sin(angle))+c.pair_buffer
        margin = max(abs(float(other[0]))*(2000/6)/longitudinal,
                     abs(float(other[1]))*(2000/6)/lateral)-1
        min_pair_margin = margin if min_pair_margin is None else min(min_pair_margin, margin)
        near_contact = max(near_contact, max(0., -margin))
    return {'edge_margin': edge_margin, 'edge_violation': max(-edge_margin, 0.),
            'overlap_proxy': near_contact, 'min_pair_margin': min_pair_margin,
            'heading_error': abs(heading), 'grass': float(row[15] > .5), 'reverse': float(row[16] > .5)}


class PhysicalQualityPilot(GraphWorldModelPolicy):
    def __init__(self, model_path, device='cpu', scoring='physical'):
        super().__init__(model_path, device=device, neighbor_mode='dynamic', max_neighbors=3,
                         neighbor_selection_mode='interaction', planner_horizon=4, planner_candidates=18)
        if self.telemetry_version != 'corrected_v2' or scoring not in ['legacy', 'physical']:
            raise ValueError('Physical-quality pilot requires corrected checkpoint and known scoring')
        self.physical_config = PhysicalQualityConfig()
        self.scoring = scoring
        self.bundle.transition.eval()
        self.bundle.proposal_actor.eval()
        self.prediction_debug = {}

    def _needs_hard_recovery(self, obs_row):
        terms = footprint_terms(obs_row, self.physical_config)
        return bool(terms['edge_margin'] < 0 or terms['grass'] or terms['reverse']
                    or obs_row[14] < self.physical_config.recovery_heading_cos)

    def _speed_limited_action(self, action, obs_row):
        action = np.asarray(action, dtype=np.float32).copy()
        terms = footprint_terms(obs_row, self.physical_config)
        speed = float(obs_row[4])*50
        target = self.target_speed
        if terms['edge_margin'] < 0 or terms['grass'] or terms['reverse'] or obs_row[14] < .72:
            target = min(target, 12.)
        if speed > target+2:
            action[1] = min(action[1], .08)
            action[2] = max(action[2], .28)
        return np.clip(action, [-1, 0, 0], [1, 1, 1]).astype(np.float32)

    def _candidate_pool(self, proposal_target, background_target, target_obs=None, extra_targets=None):
        if target_obs is None:
            raise ValueError('Physical candidate generation requires current state')
        row, c = target_obs, self.physical_config
        pool = [np.asarray(proposal_target), np.asarray(background_target)]
        pool.extend(np.asarray(a) for a in extra_targets or [])
        speed = float(row[4])*50
        d = float(row[12])*TRACK_WIDTH
        heading = math.atan2(float(row[13]), float(row[14]))
        for lane in [c.lane_offset, -c.lane_offset, 0., float(np.clip(d, -c.lane_offset, c.lane_offset))]:
            steer = -(1.5*heading+math.atan2(1.6*(lane-d), max(speed, 5.)+3.))
            for target_speed in [21., 13., 8., 0.]:
                delta = target_speed-speed
                pool.append(np.array([np.clip(steer,-1,1), np.clip(.12*delta,0,.6), np.clip(-.15*delta,0,.8)]))
        result, seen = [], set()
        for action in pool:
            action = self._speed_limited_action(action, row)
            key = tuple(np.round(action, 3))
            if key not in seen:
                seen.add(key); result.append(action)
        return result[:self.candidates]

    def _score_candidate_pool(self, obs, proposal_actions, background_policies, candidate_pool,
                              target_agent, quality_actions=None):
        if quality_actions is not None:
            raise ValueError('This controlled pilot does not enable a quality actor')
        size = len(candidate_pool)
        imagined = np.repeat(np.asarray(obs)[None], size, axis=0)
        scores = np.zeros(size)
        first_predictions = None
        horizon_records = []
        for step in range(self.horizon):
            full_actions = np.stack([self._background_action(o, background_policies) for o in imagined])
            if step == 0:
                full_actions[:, target_agent] = candidate_pool
            else:
                flat = imagined.reshape(-1, imagined.shape[-1])
                full_actions[:, target_agent] = self._proposal_actions(flat).reshape(size, len(obs), 3)[:, target_agent]
            with torch.no_grad():
                out = self.bundle.transition(torch.as_tensor(self.bundle.normalize_obs(imagined), dtype=torch.float32, device=self.device),
                    torch.as_tensor(self.bundle.normalize_action(full_actions), dtype=torch.float32, device=self.device))
                following = self.bundle.denormalize_obs(out['next_mu'].cpu().numpy())
                following = self._preserve_rollout_masks(imagined, following)
                rewards = out['reward_mu'].cpu().numpy()[:, target_agent]
                risks = torch.sigmoid(out['risk_logits']).cpu().numpy()[:, target_agent]
                uncertainty = np.clip(out['next_logvar'].cpu().numpy()[:, target_agent, 0]
                                      +out['reward_logvar'].cpu().numpy()[:, target_agent], -2, 4)
            if step == 0:
                first_predictions = following.copy()
            terms_this_step = []
            for i in range(size):
                imitation = self._imitation_penalty(full_actions[i,target_agent], proposal_actions[target_agent])
                if self.scoring == 'legacy':
                    ov, lane, grass, close, elegance = super()._state_quality_terms(imagined[i], following[i], target_agent)
                    progress = float(following[i,target_agent,9]-imagined[i,target_agent,9])
                    value = (rewards[i]+self.progress_weight*progress+self.overtake_weight*ov
                        -self.risk_weight*risks[i]-self.uncertainty_weight*uncertainty[i]
                        -self.imitation_weight*imitation-self.lane_quality_weight*lane
                        -self.grass_penalty_weight*grass-self.close_gap_penalty_weight*close
                        -self.elegance_barrier_weight*elegance)
                    terms = {'legacy_risk': float(risks[i]), 'lane_penalty': lane, 'grass_penalty': grass}
                else:
                    row = following[i,target_agent]
                    terms = footprint_terms(row, self.physical_config)
                    direction = np.array([-row[5],row[6]], dtype=float)
                    direction /= max(np.linalg.norm(direction), 1e-8)
                    progress = float(np.dot(row[2:4]*50,direction))*.02/self.physical_config.progress_scale
                    c = self.physical_config
                    value = (self.progress_weight*progress
                        - c.boundary_weight*(terms['edge_violation']+terms['grass']+terms['reverse'])
                        - c.contact_weight*terms['overlap_proxy']-c.heading_weight*terms['heading_error']
                        - self.imitation_weight*imitation)
                scores[i] += self.gamma**step*float(value)
                terms_this_step.append({**terms, 'step_score': float(value)})
            horizon_records.append(terms_this_step)
            imagined = following
        if not np.isfinite(scores).all():
            raise ValueError('Nonfinite candidate score')
        best = int(np.argmax(scores))
        self.prediction_debug = {'scoring': self.scoring, 'candidate_first_next_ego': first_predictions[:,target_agent].tolist(),
            'selected_next_obs': first_predictions[best].tolist(), 'rollout_terms': horizon_records,
            'old_risk_head_used_for_ranking': self.scoring == 'legacy',
            'uncertainty_used_for_ranking': self.scoring == 'legacy',
            'reward_head_used_for_ranking': self.scoring == 'legacy'}
        return scores.tolist()

    def act(self, env, obs):
        self.prediction_debug = {}
        action = super().act(env, obs)
        self.last_decision_debug.update(physical_config=asdict(self.physical_config), scoring=self.scoring,
            prediction_debug=self.prediction_debug, current_footprint=footprint_terms(obs[-1], self.physical_config))
        return action
