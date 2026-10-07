"""Coordinate and action semantics, independent of any fitted checkpoint."""
import math
import unittest
from types import SimpleNamespace

import numpy as np
import pyglet
pyglet.options['headless'] = True

from dlc.graph_world_model import GraphWorldModelPolicy
from dlc.graph_policy import _rank_opponent_slots
from dlc.policies import TelemetryOvertakePolicy, TrackFollowPolicy


class CorrectedPlannerTests(unittest.TestCase):
    def planner(self):
        p = GraphWorldModelPolicy.__new__(GraphWorldModelPolicy)
        p.telemetry_version = 'corrected_v2'
        p.bundle = SimpleNamespace(meta={'use_slot_mask': True, 'opponent_dim': 8})
        p.use_handcrafted_candidates = True
        p.overtake_aware_planner = True
        p.recovery_enabled = True
        p.use_geometry_recovery = False
        p._geometry_context = {}
        p.target_speed = 22
        p.geometry_generalization = False
        p.profile = 'nominal'
        p.candidates = 30
        p.corridor_return_weight = 0.0
        p.corridor_return_candidates = 0
        p.corridor_return_gain = 1.4
        p.corridor_return_heading_gain = 1.6
        p.corridor_recovery_cross_track = False
        p.shield_lateral = 0.76
        p.corridor_return_gate = 0.76
        p.corridor_return_defer_lateral = 1.0
        p._speed_limited_action = lambda action, row: action
        return p

    def observation(self, angle=0, left=2, gap=20, closing=5):
        row = np.zeros(41, dtype=np.float32)
        row[5:7] = [math.sin(angle), math.cos(angle)]
        row[14] = 1
        forward = np.array([-math.sin(angle), math.cos(angle)])
        row[17:25] = [gap/(2000/6), left/(2000/6),
                      *(-closing*forward/50), math.hypot(gap, left)/(2000/6), 0, 1, 1]
        return row

    def test_world_velocity_projection_is_rotation_invariant(self):
        for angle in [0, .7, math.pi/2, math.pi, -math.pi/3]:
            p = self.planner()
            row = self.observation(angle)
            self.assertAlmostEqual(p._traffic_features(row)['nearest_closing_speed'], 5, places=5)
            row[19:21] *= -1
            self.assertEqual(p._traffic_features(row)['nearest_closing_speed'], 0)

    def test_geometry_recovery_steers_toward_track_not_farther_out(self):
        for angle in [0., .7, math.pi/2, -math.pi/3]:
            forward = np.array([-math.sin(angle), math.cos(angle)])
            left = np.array([-math.cos(angle), -math.sin(angle)])
            for side in [-1, 1]:
                hull = SimpleNamespace(position=side*3*left, angle=angle, linearVelocity=10*forward)
                base = SimpleNamespace(num_agents=1, cars=[SimpleNamespace(hull=hull)],
                    telemetry_version='corrected_v2', episode_direction='CCW',
                    track=[[0, angle, 0, 0], [0, angle, *(100*forward)]])
                action = TrackFollowPolicy(lookahead=0).act(SimpleNamespace(unwrapped=base), np.zeros((1, 25)))
                self.assertGreater(side*action[0, 0], 0)

    def test_fast_rear_opponent_receives_closing_priority(self):
        for angle in [0, math.pi/2, -math.pi/3]:
            row = self.observation(angle, gap=-10, closing=-6)
            row[25:33] = row[17:25]
            row[27:29] = 0
            ranked = _rank_opponent_slots(row, 8, True, 'interaction', telemetry_version='corrected_v2')
            np.testing.assert_allclose(ranked[0][2:4], row[19:21])

    def test_recovery_and_first_pass_candidate_steer_away(self):
        p = self.planner()
        for side in [-1, 1]:
            row = self.observation(left=side*2)
            row[12] = side*.2
            self.assertGreater(side*p._recovery_action(row, [0, .5, 0])[0], 0)
            row[12] = 0
            pool = p._candidate_pool([0, .1, 0], [0, .2, 0], row)
            turning = [action for action in pool if abs(action[0]) > .01]
            self.assertGreater(side*turning[0][0], 0)

    def test_cross_track_return_law_is_bounded_and_monotone(self):
        """A large offset commands full lock; the command never wraps."""
        p = self.planner()
        previous = -1.0
        for offset in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 40.0]:
            row = self.observation()
            row[12] = offset
            row[13] = 0.0
            row[14] = 1.0
            steer = p._cross_track_return_steer(row)
            self.assertGreaterEqual(steer, previous)
            self.assertLessEqual(abs(steer), 1.0)
            previous = steer
        # 17 m of offset is where the archived angle-based law wrapped and
        # inverted the command; the bounded law still pulls inward there.
        row = self.observation()
        row[12] = 2.55
        row[13] = 0.0
        row[14] = 1.0
        self.assertEqual(p._cross_track_return_steer(row), 1.0)
        row[12] = -2.55
        self.assertEqual(p._cross_track_return_steer(row), -1.0)

    def test_recovery_override_replaces_weak_lookahead_steering(self):
        p = self.planner()
        p.use_geometry_recovery = True
        p.corridor_recovery_cross_track = True
        p.geometry_recovery_policy = SimpleNamespace(
            act=lambda env, obs: np.array([[0.05, 0.5, 0.0]], dtype=np.float32))
        p._speed_limited_action = lambda action, row: action
        env = SimpleNamespace(unwrapped=SimpleNamespace(num_agents=1))
        row = self.observation()
        row[12] = 2.0
        row[13] = 0.0
        row[14] = 1.0
        action = p._geometry_recovery_action(env, row[None, :], 0, [0.0, 0.5, 0.0])
        self.assertEqual(float(action[0]), 1.0)
        # Inside the lane the lookahead command is left untouched.
        row[12] = 0.05
        action = p._geometry_recovery_action(env, row[None, :], 0, [0.0, 0.5, 0.0])
        self.assertAlmostEqual(float(action[0]), 0.05, places=6)

    def test_return_override_yields_to_a_car_alongside_inside_the_edge(self):
        """Both entry paths to the return law respect the alongside deferral."""
        p = self.planner()
        p.use_geometry_recovery = True
        p.corridor_recovery_cross_track = True
        p.geometry_recovery_policy = SimpleNamespace(
            act=lambda env, obs: np.array([[0.05, 0.5, 0.0]], dtype=np.float32))
        p._speed_limited_action = lambda action, row: action
        env = SimpleNamespace(unwrapped=SimpleNamespace(num_agents=1))
        # 0.80 half-widths sits between the gate (0.76) and the deferral limit
        # (1.0); heading_cos 0.8 is inside the heading path's own trigger.
        beside = self.observation(left=2.0, gap=2.0)
        beside[12] = 0.80
        beside[13] = 0.0
        beside[14] = 0.8
        self.assertGreaterEqual(int(p._traffic_features(beside)['alongside_count']), 1)
        self.assertFalse(p._corridor_return_active(beside))
        action = p._geometry_recovery_action(env, beside[None, :], 0, [0.0, 0.5, 0.0])
        self.assertAlmostEqual(float(action[0]), 0.05, places=6)
        # With no car alongside the same state is recovered.
        clear = self.observation(left=2.0, gap=40.0)
        clear[12] = 0.80
        clear[13] = 0.0
        clear[14] = 0.8
        self.assertEqual(int(p._traffic_features(clear)['alongside_count']), 0)
        self.assertTrue(p._corridor_return_active(clear))
        action = p._geometry_recovery_action(env, clear[None, :], 0, [0.0, 0.5, 0.0])
        self.assertEqual(float(action[0]), 1.0)

    def test_imagined_background_matches_real_adapter_and_ignores_padding(self):
        p = self.planner()
        row = self.observation()
        row[25:33] = [.001, 0, 0, 0, .001, 0, 1, 0]
        obs = np.stack([row, row])
        context = SimpleNamespace(unwrapped=SimpleNamespace(
            telemetry_version='corrected_v2', observation_type='telemetry_dynamic'))
        policies = [None, TelemetryOvertakePolicy()]
        actual = policies[1].act(context, obs)[1]
        imagined = p._background_action(obs, policies)
        np.testing.assert_array_equal(imagined[1], actual)
        np.testing.assert_array_equal(imagined[0], np.zeros(3))

    def test_decoder_cannot_create_or_remove_selected_opponents(self):
        p = self.planner()
        current = self.observation()[None, :]
        prediction = np.ones_like(current) * .9
        prediction[0, 24] = 0
        fixed = p._preserve_rollout_masks(current, prediction)
        self.assertEqual(fixed[0, 24], 1)
        np.testing.assert_array_equal(fixed[0, 25:], current[0, 25:])
        np.testing.assert_array_equal(fixed[0, :24], prediction[0, :24])
        p.telemetry_version = 'legacy_v1'
        legacy_fixed = p._preserve_rollout_masks(current, prediction)
        self.assertEqual(legacy_fixed[0, 24], 1)
        np.testing.assert_array_equal(legacy_fixed[0, 25:], current[0, 25:])

    def test_rollout_mask_preservation_rejects_incompatible_slot_width(self):
        p = self.planner()
        current = self.observation()[None, :]
        prediction = np.ones((1, 33), dtype=np.float32)
        with self.assertRaises(ValueError):
            p._preserve_rollout_masks(current, prediction)


if __name__ == '__main__':
    unittest.main()
