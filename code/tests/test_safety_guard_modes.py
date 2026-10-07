"""The safety guard must not silently replace the planner it guards."""
import unittest
from types import SimpleNamespace

import numpy as np
import pyglet
pyglet.options['headless'] = True

from dlc.graph_world_model import PLANNER_GEOMETRY, GraphWorldModelPolicy


def guard_policy(telemetry_version, mode=None, **overrides):
    p = GraphWorldModelPolicy.__new__(GraphWorldModelPolicy)
    p.telemetry_version = telemetry_version
    p.bundle = SimpleNamespace(meta={'use_slot_mask': True, 'opponent_dim': 8})
    p.overtake_aware_planner = True
    p.recovery_enabled = True
    p.hard_safety_shield = True
    geometry = PLANNER_GEOMETRY[telemetry_version]
    p.shield_lateral = overrides.get('shield_lateral', geometry['guard_lateral'])
    p.shield_grass_lateral = overrides.get('shield_grass_lateral', geometry['guard_grass_lateral'])
    p.shield_heading_cos = overrides.get('shield_heading_cos', geometry['guard_heading_cos'])
    p.shield_mode = mode or ('takeover' if telemetry_version == 'legacy_v1' else 'filter')
    p.guard_penalty_weight = overrides.get('guard_penalty_weight', 0.0 if p.shield_mode == 'takeover' else 2.0)
    p._guard_active = False
    p._last_rollout_violation = 0.0
    return p


def row(lateral=0.0, heading_cos=1.0, on_grass=0.0, backward=0.0):
    obs = np.zeros(17, dtype=np.float32)
    obs[12] = lateral                  # corrected_v2 stores a left-positive offset
    obs[14] = heading_cos
    obs[15] = on_grass
    obs[16] = backward
    return obs


class SafetyGuardModeTests(unittest.TestCase):
    def test_guard_thresholds_sit_between_the_racing_lane_and_the_roadside(self):
        lane = 4.4 / (40.0 / 6.0)      # joint-clearance teacher's own lane offset
        corrected = PLANNER_GEOMETRY['corrected_v2']
        self.assertGreater(corrected['guard_lateral'], lane)
        for table in PLANNER_GEOMETRY.values():
            self.assertLess(table['guard_lateral'], 1.0)
            self.assertLess(table['guard_grass_lateral'], table['guard_lateral'])

    def test_the_teacher_lane_does_not_trigger_the_corrected_guard(self):
        p = guard_policy('corrected_v2')
        self.assertFalse(p._needs_hard_recovery(row(lateral=4.4 / (40.0 / 6.0))))
        self.assertTrue(p._needs_hard_recovery(row(lateral=0.95)))

    def test_legacy_defaults_are_unchanged(self):
        p = guard_policy('legacy_v1')
        self.assertEqual(p.shield_lateral, 0.62)
        self.assertEqual(p.shield_grass_lateral, 0.48)
        self.assertEqual(p.shield_mode, 'takeover')

    def test_corrected_default_is_filtering_not_takeover(self):
        p = guard_policy('corrected_v2')
        self.assertEqual(p.shield_mode, 'filter')
        self.assertGreater(p.guard_penalty_weight, 0.0)

    def test_violation_severity_is_ordered(self):
        p = guard_policy('corrected_v2')
        clean = p._guard_violation(row(lateral=0.2))
        near_edge = p._guard_violation(row(lateral=0.95))
        grass = p._guard_violation(row(lateral=0.95, on_grass=1.0))
        backward = p._guard_violation(row(lateral=0.95, on_grass=1.0, backward=1.0))
        self.assertEqual(clean, 0.0)
        self.assertLess(clean, near_edge)
        self.assertLess(near_edge, grass)
        self.assertLess(grass, backward)

    def test_head_targets_are_kept_ahead_of_the_budget_cut(self):
        p = guard_policy('corrected_v2')
        p.use_handcrafted_candidates = True
        p.profile = 'nominal'
        p.overtake_aware_planner = False
        p.candidates = 2
        p._geometry_context = {}
        p._speed_limited_action = lambda action, obs_row: np.asarray(action, dtype=np.float32)
        guard = np.array([0.9, 0.5, 0.0], dtype=np.float32)
        pool = p._candidate_pool(
            np.array([0.0, 0.5, 0.0], dtype=np.float32),
            np.array([0.1, 0.5, 0.0], dtype=np.float32),
            target_obs=None,
            head_targets=[guard],
        )
        self.assertTrue(any(np.allclose(item, guard) for item in pool))


if __name__ == '__main__':
    unittest.main()
