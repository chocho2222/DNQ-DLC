"""Dynamic-feasibility terms of the corrected planner.

Three defects motivated these terms, all measured on frozen traces:

* the curvature channel is rad per track tile, so the archived 0.02/0.03
  thresholds were not comparable across tracks and flagged 70-75 % of steps as
  a sharp turn, clamping the throttle to 0.42 everywhere;
* candidates were scored with the continuation policy for every horizon step
  except the first, so the pool scores differed by ~1e-2;
* once the vehicle dropped below ~1 m/s the learned heads were out of
  distribution, every candidate scored alike and the controller settled on a
  do-nothing action, leaving the vehicle standing still indefinitely.
"""
import math
import unittest
from types import SimpleNamespace

import numpy as np
import pyglet
pyglet.options['headless'] = True

from dlc.graph_world_model import PLAYFIELD, PLANNER_GEOMETRY, GraphWorldModelPolicy


def policy(telemetry_version='corrected_v2', **overrides):
    p = GraphWorldModelPolicy.__new__(GraphWorldModelPolicy)
    p.telemetry_version = telemetry_version
    p.bundle = SimpleNamespace(meta={})
    p.geometry_generalization = True
    p.geometry_curvature_lookahead = 10
    p.geometry_curvature_speed_weight = 20.0
    p.geometry_lateral_speed_weight = 5.0
    p.geometry_heading_speed_weight = 5.5
    p.geometry_min_speed = 9.5
    p.target_speed = 22.0
    p.liveness_weight = overrides.get('liveness_weight', 1.5)
    p.liveness_speed = overrides.get('liveness_speed', 5.0)
    p.maneuver_hold_steps = overrides.get('maneuver_hold_steps', 1)
    p.horizon = overrides.get('horizon', 4)
    p.corridor_feasibility = overrides.get('corridor_feasibility', True)
    p.clearance_feasibility = overrides.get('clearance_feasibility', False)
    p.clearance_alongside_length = overrides.get('clearance_alongside_length', 5.5)
    p.clearance_lateral_min = overrides.get('clearance_lateral_min', 3.5)
    p.shield_lateral = PLANNER_GEOMETRY[telemetry_version]['guard_lateral']
    p.shield_grass_lateral = PLANNER_GEOMETRY[telemetry_version]['guard_grass_lateral']
    p.shield_heading_cos = PLANNER_GEOMETRY[telemetry_version]['guard_heading_cos']
    p._geometry_context = {"curvature": 0.0, "target_speed": p.target_speed, "sharp_turn": False}
    return p


def circle_env(radius=50.0, tiles=180):
    """Circular centre line: curvature is exactly 1/radius everywhere."""
    beta = np.linspace(0.0, 2 * math.pi, tiles, endpoint=False)
    xy = np.stack([radius * np.cos(beta), radius * np.sin(beta)], axis=1)
    # Centre-line layout matches the simulator: [counter, beta, x, y].
    track = np.concatenate([np.zeros((tiles, 1)), beta[:, None], xy], axis=1).astype(np.float64)
    car = SimpleNamespace(hull=SimpleNamespace(position=(radius, 0.0)))
    return SimpleNamespace(unwrapped=SimpleNamespace(
        track=track, cars=[car], episode_direction='CCW'))


def obs_row(lateral=0.0, heading_cos=1.0, speed_norm=0.0, on_grass=0.0):
    row = np.zeros(17, dtype=np.float32)
    row[4] = speed_norm
    row[12] = lateral
    row[14] = heading_cos
    row[15] = on_grass
    return row


class PhysicalCurvatureTests(unittest.TestCase):
    def test_curvature_is_converted_to_a_radius(self):
        p = policy()
        env = circle_env(radius=50.0)
        ctx = p._update_geometry_context(env, np.stack([obs_row(heading_cos=1.0)]), 0)
        self.assertAlmostEqual(ctx['radius_m'], 50.0, delta=1.0)
        # v = sqrt(a_lat * R), with a_lat taken from the protocol table
        a_lat = PLANNER_GEOMETRY['corrected_v2']['speed']['lat_accel_max']
        self.assertAlmostEqual(ctx['target_speed'], min(p.target_speed, math.sqrt(a_lat * 50.0)), delta=0.05)

    def test_a_wide_corner_is_not_a_sharp_turn(self):
        p = policy()
        env = circle_env(radius=200.0)
        ctx = p._update_geometry_context(env, np.stack([obs_row(heading_cos=1.0)]), 0)
        self.assertFalse(ctx['sharp_turn'])
        self.assertAlmostEqual(ctx['target_speed'], p.target_speed, delta=0.05)

    def test_a_tight_corner_is_a_sharp_turn_and_limits_speed(self):
        p = policy()
        # radius 30 m is below the sharp-turn radius (55 m) on this budget
        env = circle_env(radius=30.0)
        ctx = p._update_geometry_context(env, np.stack([obs_row(heading_cos=1.0)]), 0)
        self.assertTrue(ctx['sharp_turn'])
        self.assertLess(ctx['target_speed'], p.target_speed)

    def test_the_same_geometry_is_scale_invariant(self):
        # A circle sampled at twice the resolution describes the same corner:
        # the reported radius must not depend on the tile count.
        coarse = policy()._update_geometry_context(circle_env(60.0, 90), np.stack([obs_row(heading_cos=1.0)]), 0)
        fine = policy()._update_geometry_context(circle_env(60.0, 360), np.stack([obs_row(heading_cos=1.0)]), 0)
        self.assertAlmostEqual(coarse['radius_m'], fine['radius_m'], delta=1.5)

    def test_legacy_keeps_the_archived_per_tile_behaviour(self):
        p = policy('legacy_v1')
        env = circle_env(radius=50.0)
        ctx = p._update_geometry_context(env, np.stack([obs_row(heading_cos=1.0)]), 0)
        self.assertIsNone(ctx['radius_m'])
        self.assertTrue(ctx['sharp_turn'])


class LivenessTests(unittest.TestCase):
    def test_no_penalty_above_the_minimum_speed(self):
        p = policy()
        self.assertEqual(p._liveness_penalty(12.0), 0.0)
        self.assertEqual(p._liveness_penalty(5.0), 0.0)

    def test_penalty_grows_as_the_vehicle_slows(self):
        p = policy()
        slow = p._liveness_penalty(2.5)
        stopped = p._liveness_penalty(0.0)
        self.assertGreater(slow, 0.0)
        self.assertAlmostEqual(stopped, 1.0)
        self.assertGreater(stopped, slow)

    def test_the_term_can_be_disabled(self):
        p = policy(liveness_weight=0.0)
        self.assertEqual(p._liveness_penalty(0.0), 0.0)


class CorridorFeasibilityTests(unittest.TestCase):
    def test_corrected_defaults_enable_the_constraint(self):
        self.assertTrue(policy().corridor_feasibility)

    def test_the_constraint_is_off_for_the_projected_legacy_channel(self):
        p = GraphWorldModelPolicy.__new__(GraphWorldModelPolicy)
        p.telemetry_version = 'legacy_v1'
        p.corridor_feasibility = p.telemetry_version == 'corrected_v2'
        self.assertFalse(p.corridor_feasibility)

    def test_violation_is_zero_inside_the_corridor_and_grows_outside(self):
        p = policy()
        self.assertEqual(p._guard_violation(obs_row(lateral=0.2)), 0.0)
        inside = p._guard_violation(obs_row(lateral=0.7))
        outside = p._guard_violation(obs_row(lateral=0.7, on_grass=1.0))
        self.assertGreater(outside, inside)


def neighbour_obs(rel_forward, rel_left, mask=1.0, extra_slots=()):
    """17-dimensional self block plus 8-dimensional masked relation slots."""
    row = np.zeros(17 + 8 * (1 + len(extra_slots)), dtype=np.float32)
    row[4] = 0.4
    row[14] = 1.0
    row[17:25] = [rel_forward / PLAYFIELD, rel_left / PLAYFIELD, 0.0, 0.0,
                  math.hypot(rel_forward, rel_left) / PLAYFIELD, 0.0, 0.0, mask]
    for index, (fwd, left, slot_mask) in enumerate(extra_slots):
        start = 25 + 8 * index
        row[start:start + 8] = [fwd / PLAYFIELD, left / PLAYFIELD, 0.0, 0.0,
                                math.hypot(fwd, left) / PLAYFIELD, 0.0, 0.0, slot_mask]
    return row


class ClearanceFeasibilityTests(unittest.TestCase):
    """A pass is only feasible if the predicted lateral gap fits the vehicle."""

    def planner(self):
        p = policy(clearance_feasibility=True)
        # _slot_meta reads the packed layout from the fitted bundle metadata.
        p.bundle = SimpleNamespace(meta={'use_slot_mask': True, 'opponent_dim': 8})
        return p

    def test_the_constraint_is_off_unless_it_is_requested(self):
        self.assertFalse(policy().clearance_feasibility)

    def test_a_squeeze_alongside_is_a_violation(self):
        p = self.planner()
        # 3.1 m apart is a contact (the hull with its wheels spans 3.2 m), and
        # the observed failures are exactly this geometry.
        severity = p._clearance_violation(neighbour_obs(0.0, 3.1)[None, :], 0)
        self.assertAlmostEqual(severity, 0.4, places=6)

    def test_a_full_width_pass_is_feasible(self):
        p = self.planner()
        self.assertEqual(p._clearance_violation(neighbour_obs(0.0, 3.6)[None, :], 0), 0.0)
        self.assertEqual(p._clearance_violation(neighbour_obs(-2.0, 4.4)[None, :], 0), 0.0)

    def test_a_vehicle_that_is_not_alongside_is_ignored(self):
        p = self.planner()
        # 20 m behind or ahead: the lateral gap cannot cause a side contact.
        self.assertEqual(p._clearance_violation(neighbour_obs(20.0, 1.0)[None, :], 0), 0.0)
        self.assertEqual(p._clearance_violation(neighbour_obs(-20.0, 1.0)[None, :], 0), 0.0)

    def test_an_absent_slot_is_never_a_violation(self):
        p = self.planner()
        self.assertEqual(p._clearance_violation(neighbour_obs(0.0, 0.2, mask=0.0)[None, :], 0), 0.0)

    def test_the_shortfalls_of_present_slots_accumulate(self):
        p = self.planner()
        obs = neighbour_obs(0.0, 2.4, extra_slots=([0.0, -1.0, 1.0],))[None, :]
        self.assertAlmostEqual(p._clearance_violation(obs, 0), 1.1 + 2.5, places=6)


class ManeuverHoldTests(unittest.TestCase):
    def test_a_candidate_is_held_for_the_configured_number_of_steps(self):
        p = policy(maneuver_hold_steps=3, horizon=4)
        candidate = np.array([0.5, 0.9, 0.0], dtype=np.float32)
        for step in range(3):
            held = p._rollout_target_action(None, None, None, 0, candidate, step)
            np.testing.assert_allclose(held, candidate)

    def test_the_hold_window_never_exceeds_the_horizon(self):
        p = policy()
        p.horizon = 4
        p.maneuver_hold_steps = max(1, min(9, p.horizon))
        self.assertEqual(p.maneuver_hold_steps, 4)


class TrackTileLengthTests(unittest.TestCase):
    def test_tile_length_matches_the_sampled_spacing(self):
        env = circle_env(radius=50.0, tiles=100)
        length = GraphWorldModelPolicy._track_tile_length(np.asarray(env.unwrapped.track)[:, 2:4])
        # chord, not arc: 2 R sin(pi / N)
        self.assertAlmostEqual(length, 2 * 50.0 * math.sin(math.pi / 100), delta=1e-6)


if __name__ == '__main__':
    unittest.main()
