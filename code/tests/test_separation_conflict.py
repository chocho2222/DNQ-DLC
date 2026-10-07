"""Imagined states must be scored against the reference clearance model."""
import unittest
from types import SimpleNamespace

import numpy as np
import pyglet
pyglet.options['headless'] = True

from dlc.graph_world_model import (
    PLANNER_GEOMETRY,
    SEPARATION_HALF_LENGTH,
    SEPARATION_HALF_WIDTH,
    GraphWorldModelPolicy,
)


def policy(telemetry_version='corrected_v2', scale=1.0):
    p = GraphWorldModelPolicy.__new__(GraphWorldModelPolicy)
    p.telemetry_version = telemetry_version
    p.bundle = SimpleNamespace(meta={'use_slot_mask': True, 'opponent_dim': 8})
    p.separation_scale = scale
    return p


def row(along, lateral):
    obs = np.zeros(41, dtype=np.float32)
    obs[17:25] = [along / (2000 / 6), lateral / (2000 / 6), 0.0, 0.0,
                  np.hypot(along, lateral) / (2000 / 6), 0.0, 1.0, 1.0]
    return obs


class SeparationConflictTests(unittest.TestCase):
    def test_the_reference_controller_clearance_model_is_used(self):
        self.assertEqual(SEPARATION_HALF_LENGTH, 6.0)
        self.assertEqual(SEPARATION_HALF_WIDTH, 3.3)
        self.assertGreater(PLANNER_GEOMETRY['corrected_v2']['lane_free'], 0.0)

    def test_a_stacked_pair_is_a_conflict(self):
        p = policy()
        self.assertAlmostEqual(p._separation_conflict(row(3.0, 0.5)), 0.5, places=3)
        self.assertEqual(p._separation_conflict(row(0.0, 0.0)), 1.0)

    def test_a_side_by_side_pair_at_lane_spacing_is_clear(self):
        p = policy()
        self.assertEqual(p._separation_conflict(row(0.5, SEPARATION_HALF_WIDTH + 0.4)), 0.0)

    def test_a_car_far_ahead_is_clear(self):
        p = policy()
        self.assertEqual(p._separation_conflict(row(SEPARATION_HALF_LENGTH + 6.0, 0.0)), 0.0)

    def test_legacy_protocol_does_not_apply_the_term(self):
        p = policy('legacy_v1', scale=0.0)
        self.assertEqual(p._separation_conflict(row(0.0, 0.0)), 0.0)

    def test_inactive_slots_are_ignored(self):
        p = policy()
        obs = row(0.0, 0.0)
        obs[24] = 0.0            # mask bit of the only opponent slot
        self.assertEqual(p._separation_conflict(obs), 0.0)


if __name__ == '__main__':
    unittest.main()
