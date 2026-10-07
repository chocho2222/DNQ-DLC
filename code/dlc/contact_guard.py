"""Opt-in development braking guard; not part of archived DNQ-DLC.

Uses current telemetry and a conservative rectangular footprint approximation.
This is a front-gap intervention, not a collision-free control guarantee.
"""
from dataclasses import dataclass, asdict
import math

import numpy as np
from dlc.observation_layout import opponent_slots


@dataclass(frozen=True)
class ContactGuardConfig:
    version: str = 'front_gap_pilot_v1'
    half_length: float = 2.8
    half_width: float = 1.6
    longitudinal_margin: float = 1.0
    lateral_margin: float = 0.4
    reaction_time: float = 0.4
    assumed_deceleration: float = 8.0
    lateral_horizon: float = 0.6
    brake: float = 0.7

    def __post_init__(self):
        values = [self.half_length, self.half_width, self.longitudinal_margin,
                  self.lateral_margin, self.reaction_time, self.assumed_deceleration,
                  self.lateral_horizon]
        if not all(math.isfinite(x) and x > 0 for x in values) or not 0 < self.brake <= 1:
            raise ValueError('Invalid contact guard parameters')


class FrontGapGuard:
    def __init__(self, config=None):
        self.config = config or ContactGuardConfig()

    def apply(self, row, action, *, telemetry_version, masked):
        if telemetry_version != 'corrected_v2':
            raise ValueError('Front-gap guard requires corrected physical axes')
        row = np.asarray(row)
        action = np.asarray(action, dtype=np.float32).copy()
        if not np.isfinite(row).all() or not np.isfinite(action).all():
            raise ValueError('Nonfinite guard input')
        c = self.config
        forward = np.array([-row[5], row[6]], dtype=float)
        norm = np.linalg.norm(forward)
        if norm < 1e-6:
            raise ValueError('Undefined ego heading')
        forward /= norm
        left = np.array([-forward[1], forward[0]])
        threats = []
        for slot_index, slot in enumerate(opponent_slots(row, masked=masked)):
            gap, lateral = slot[:2] * (2000/6)
            if gap <= 0:
                continue  # Cannot avoid a rear impact by braking into it.
            relative_velocity = slot[2:4] * 50
            closing = max(-float(relative_velocity@forward), 0.)
            lateral_future = float(lateral + relative_velocity@left*c.lateral_horizon)
            swept_left = min(abs(lateral), abs(lateral_future)) if lateral*lateral_future > 0 else 0.
            theta = math.atan2(float(slot[5]), float(slot[6]))
            opponent_length = abs(math.cos(theta))*c.half_length + abs(math.sin(theta))*c.half_width
            opponent_width = abs(math.sin(theta))*c.half_length + abs(math.cos(theta))*c.half_width
            if swept_left > c.half_width + opponent_width + c.lateral_margin:
                continue
            desired_gap = (c.half_length + opponent_length + c.longitudinal_margin
                           + closing*c.reaction_time + closing**2/(2*c.assumed_deceleration))
            if gap < desired_gap:
                threats.append({'valid_slot_index': slot_index, 'forward_gap': float(gap),
                                'lateral_gap': float(lateral), 'closing_speed': closing,
                                'desired_gap': desired_gap})
        if threats:
            action[1] = 0.
            action[2] = max(float(action[2]), c.brake)
        return action, {'active': bool(threats), 'threats': threats, 'config': asdict(c)}
