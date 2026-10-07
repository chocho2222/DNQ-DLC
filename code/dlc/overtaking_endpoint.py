"""Versioned physical-position endpoint, independent of tile-visit rewards."""
from dataclasses import dataclass, asdict
import numpy as np


@dataclass(frozen=True)
class EndpointConfig:
    version: str = 'corrected_v2_pilot'
    initial_gap_min: float = 6.0
    initial_gap_max: float = 60.0
    pass_margin: float = 6.0
    hold_steps: int = 50
    horizon: int = 2200

    def __post_init__(self):
        if not (0 < self.initial_gap_min < self.initial_gap_max
                and self.pass_margin > 0 and self.hold_steps > 0 and self.horizon > 0):
            raise ValueError('Invalid endpoint thresholds')


class TrackProgress:
    def __init__(self, centerline):
        self.xy = np.asarray(centerline, dtype=float)
        self.edges = np.roll(self.xy, -1, axis=0) - self.xy
        self.lengths = np.linalg.norm(self.edges, axis=1)
        if np.any(self.lengths <= 0):
            raise ValueError('Centerline must not contain repeated consecutive points')
        self.offsets = np.r_[0, np.cumsum(self.lengths)[:-1]]
        self.length = float(self.lengths.sum())
        self.previous = None
        self.unwrapped = None

    def update(self, positions):
        delta = np.asarray(positions)[:, None, :] - self.xy[None, :, :]
        t = np.clip((delta * self.edges).sum(-1) / self.lengths**2, 0, 1)
        residual = delta - t[..., None] * self.edges
        idx = (residual**2).sum(-1).argmin(1)
        wrapped = self.offsets[idx] + t[np.arange(len(idx)), idx] * self.lengths[idx]
        if self.previous is None:
            self.unwrapped = wrapped.copy()
        else:
            self.unwrapped += (wrapped - self.previous + self.length / 2) % self.length - self.length / 2
        self.previous = wrapped
        return self.unwrapped.copy()


class OvertakingEndpoint:
    def __init__(self, initial_progress, track_length, ego, config=None,
                 initial_contacts=(), initial_on_grass=None, initial_backward=None):
        self.config = config or EndpointConfig()
        self.ego = int(ego)
        initial = np.asarray(initial_progress, dtype=float)
        gaps = (initial - initial[ego] + track_length / 2) % track_length - track_length / 2
        self.initial = initial
        self.gaps = gaps
        self.targets = [i for i, gap in enumerate(gaps) if i != ego
                        and self.config.initial_gap_min <= gap <= self.config.initial_gap_max]
        self.hold = {i: 0 for i in self.targets}
        self.events = []
        self.contacted = any(self.ego in c['agents'] for c in initial_contacts)
        self.offtrack = bool(initial_on_grass[self.ego]) if initial_on_grass is not None else False
        self.backward = bool(initial_backward[self.ego]) if initial_backward is not None else False
        self.step = 0

    def update(self, step, progress, contacts, on_grass, backward):
        if step != self.step + 1 or step > self.config.horizon:
            raise ValueError('Endpoint requires consecutive steps within horizon')
        self.step = step
        self.contacted |= any(self.ego in c['agents'] for c in contacts)
        self.offtrack |= bool(on_grass[self.ego])
        self.backward |= bool(backward[self.ego])
        displacement = np.asarray(progress) - self.initial
        for target in self.targets:
            lead = displacement[self.ego] - displacement[target] - self.gaps[target]
            self.hold[target] = self.hold[target] + 1 if lead >= self.config.pass_margin else 0
            if self.hold[target] == self.config.hold_steps and not any(e['target'] == target for e in self.events):
                self.events.append({'target': target, 'pass_step': step - self.config.hold_steps + 1,
                                    'retained_step': step, 'lead': float(lead),
                                    'contact_free': not self.contacted,
                                    'center_ontrack_contact_free': not (self.contacted or self.offtrack or self.backward)})
        return self.result()

    def result(self):
        return {'config': asdict(self.config), 'eligible': bool(self.targets),
                'target_ids': self.targets, 'steps': self.step, 'events': list(self.events),
                'lead_retained_completion': bool(self.events),
                'contact_free_completion': any(e['contact_free'] for e in self.events),
                'center_ontrack_contact_free_completion': any(e['center_ontrack_contact_free'] for e in self.events),
                'ego_contact_any': self.contacted, 'ego_center_offtrack_any': self.offtrack,
                'ego_backward_any': self.backward}
