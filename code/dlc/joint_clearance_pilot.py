"""Development-only joint lane/speed proposal; not a trained DNQ checkpoint.

The map and current telemetry define approximate Frenet futures. No simulator
lookahead, future opponent actions, or test outcomes are available to the policy.
"""
from dataclasses import asdict, dataclass
import math
import numpy as np

from dlc.overtaking_endpoint import TrackProgress
from dlc.policies import TRACK_WIDTH, wrap_to_pi


@dataclass(frozen=True)
class JointClearanceConfig:
    version: str = 'joint_clearance_pilot_v2'
    lane_offset: float = 4.4
    target_speed: float = 21.0
    horizon: float = 2.0
    sample_dt: float = .1
    lateral_response: float = 1.1
    acceleration: float = 5.0
    deceleration: float = 8.0
    pair_half_length: float = 6.0
    pair_half_width: float = 3.3
    boundary_margin: float = 1.8
    switch_penalty: float = 3.0


def candidate_future(lateral, speed, lateral_velocity, lane, target_speed, cfg):
    """Short constant-acceleration / damped lane-tracking approximation."""
    times = np.arange(0, cfg.horizon + cfg.sample_dt/2, cfg.sample_dt)
    v = float(speed)
    s, d, vd = 0., float(lateral), float(np.clip(lateral_velocity, -5, 5))
    longitudinal, lateral_path = [s], [d]
    for _ in times[1:]:
        a = np.clip((target_speed-v)*2, -cfg.deceleration, cfg.acceleration)
        new_v = max(0., v+a*cfg.sample_dt)
        s += .5*(v+new_v)*cfg.sample_dt
        v = new_v
        desired_vd = np.clip(cfg.lateral_response*(lane-d), -3., 3.)
        vd += np.clip(desired_vd-vd, -3*cfg.sample_dt, 3*cfg.sample_dt)
        d += vd*cfg.sample_dt
        longitudinal.append(s)
        lateral_path.append(d)
    return times, np.asarray(longitudinal), np.asarray(lateral_path)


def clearance(times, s_path, d_path, opponents, cfg):
    """Checks swept interval samples against all observed front/side/rear cars."""
    blockers, minimum = [], float('inf')
    for other in opponents:
        other_s = other['gap'] + other['speed']*times
        # Lateral drift is extrapolated for at most 0.6 s, not assumed known.
        other_d = other['lateral'] + other['lateral_speed']*np.minimum(times, .6)
        ds = np.abs(other_s-s_path)
        dd = np.abs(other_d-d_path)
        margin = np.maximum(ds/cfg.pair_half_length, dd/cfg.pair_half_width)-1
        minimum = min(minimum, float(margin.min()))
        if np.any(margin < 0):
            blockers.append(int(other['id']))
    limit = TRACK_WIDTH-cfg.boundary_margin
    # A current violation must permit inward recovery, not make stopping the
    # only option. Do not permit a larger excursion, and require return inside.
    boundary = (float(np.max(np.abs(d_path))) > max(limit, abs(d_path[0]))+.05
                or abs(d_path[-1]) > limit)
    return bool(not blockers and not boundary), blockers, minimum, bool(boundary)


class JointClearancePilot:
    name = 'joint_clearance_pilot'

    def __init__(self, config=None):
        self.config = config or JointClearanceConfig()
        self.reset()

    def reset(self):
        self.selected_lane = None
        self.last_decision_debug = {}
        self.progress = None

    def act(self, env, obs):
        e = env.unwrapped
        if e.telemetry_version != 'corrected_v2':
            raise ValueError('Joint-clearance pilot requires corrected telemetry')
        obs = np.asarray(obs)
        ego = len(obs)-1
        cfg = self.config
        if self.progress is None:
            self.progress = TrackProgress(np.asarray(e.track)[:, 2:])
        positions = obs[:, :2]*(2000/6)
        progress = self.progress.update(positions)
        gaps = (progress-progress[ego]+self.progress.length/2) % self.progress.length-self.progress.length/2
        lateral = obs[:, 12]*TRACK_WIDTH
        velocities = obs[:, 2:4]*50
        angles = np.arctan2(obs[:, 5], obs[:, 6]) + np.arctan2(obs[:, 13], obs[:, 14])
        forward = np.stack([-np.sin(angles), np.cos(angles)], axis=1)
        left = np.stack([-np.cos(angles), -np.sin(angles)], axis=1)
        vs = (velocities*forward).sum(1)
        vd = (velocities*left).sum(1)
        opponents = [{'id': i, 'gap': float(gaps[i]), 'lateral': float(lateral[i]),
                      'speed': float(vs[i]), 'lateral_speed': float(vd[i])}
                     for i in range(len(obs)) if i != ego and abs(gaps[i]) < 90]
        if self.selected_lane is None:
            self.selected_lane = cfg.lane_offset * (1 if lateral[ego] >= 0 else -1)
        track = np.asarray(e.track)
        idx = int(np.linalg.norm(track[:, 2:]-positions[ego], axis=1).argmin())
        look = (idx+3) % len(track)
        distance = max(np.linalg.norm(track[look, 2:]-track[idx, 2:]), 1.)
        curvature = wrap_to_pi(track[look, 1]-track[idx, 1])/distance
        speed_limit = min(cfg.target_speed, math.sqrt(5./max(abs(curvature), .001)))
        self.selected_lane = float(np.clip(self.selected_lane, -cfg.lane_offset, cfg.lane_offset))
        lanes = list(dict.fromkeys([self.selected_lane, cfg.lane_offset, -cfg.lane_offset, 0.,
                                  float(np.clip(lateral[ego], -cfg.lane_offset, cfg.lane_offset))]))
        speeds = list(dict.fromkeys([speed_limit, min(13., speed_limit), min(8., speed_limit), 0.]))
        records = []
        for lane in lanes:
            for speed in speeds:
                times, s_path, d_path = candidate_future(lateral[ego], vs[ego], vd[ego], lane, speed, cfg)
                feasible, blockers, margin, boundary = clearance(times, s_path, d_path, opponents, cfg)
                score = (s_path[-1] - cfg.switch_penalty*abs(lane-self.selected_lane)
                         - .15*abs(lane-lateral[ego]))
                records.append({'lane': lane, 'speed': speed, 'score': float(score), 'feasible': bool(feasible),
                                'blockers': blockers, 'minimum_margin': margin if np.isfinite(margin) else None,
                                'boundary': boundary, 'terminal_lateral': float(d_path[-1])})
        valid = [r for r in records if r['feasible']]
        if valid:
            selected = max(valid, key=lambda r: r['score'])
        else:
            # Diagnostic fallback, not a promise that unavoidable contact is solved.
            selected = max(records, key=lambda r: ((r['minimum_margin'] if r['minimum_margin'] is not None else 100.)
                         - 10*max(abs(r['terminal_lateral'])-(TRACK_WIDTH-cfg.boundary_margin), 0.)
                         - 2*float(r['boundary']), r['score']))
        self.selected_lane = selected['lane']
        lane_error = selected['lane']-float(lateral[ego])
        heading_error = math.atan2(obs[ego, 13], obs[ego, 14])
        steer = -(1.5*heading_error + math.atan2(1.6*lane_error, max(float(vs[ego]), 5.)+3.)
                  + math.atan(3.2*curvature))
        speed_error = selected['speed']-float(obs[ego, 4]*50)
        action = np.zeros((len(obs), 3), dtype=np.float32)
        action[ego] = [np.clip(steer, -1, 1), np.clip(.12*speed_error, 0, .60), np.clip(-.15*speed_error, 0, .8)]
        self.last_decision_debug = {'config': asdict(cfg), 'opponents': opponents,
            'candidates': records, 'selected': selected, 'no_feasible_candidate': not bool(valid),
            'ego_lateral': float(lateral[ego]), 'curvature': float(curvature),
            'action': action[ego].tolist(), 'prediction': 'deterministic approximate map-coordinate motion, not Graph-DLC'}
        return action
