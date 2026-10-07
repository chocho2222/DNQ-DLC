import math
import unittest
from types import SimpleNamespace

import numpy as np
import pyglet
pyglet.options['headless'] = True

from dlc.rollout import make_env
from dlc.observation_layout import opponent_slots, rule_observation, require_checkpoint_version
from dlc.overtaking_endpoint import EndpointConfig, OvertakingEndpoint, TrackProgress
from dlc.policies import TelemetryLanePolicy, TelemetryOvertakePolicy
from dlc.graph_policy import pack_dynamic_neighbor_obs
from scripts.build_corrected_ablation_config import build, OVERRIDES
import json
from pathlib import Path

from _repo_paths import CONFIGS


class CorrectedProtocolTests(unittest.TestCase):
    def env(self, n=2, **kwargs):
        e = make_env(num_agents=n, seed=3, observation_type='telemetry_dynamic',
                     telemetry_version='corrected_v2', neighbor_order='identity', **kwargs)
        self.addCleanup(e.close)
        e.reset()
        return e

    def test_axes_and_lateral(self):
        e = self.env().unwrapped
        for heading in [0, math.pi/2, -math.pi/3]:
            forward, left = e._vehicle_axes(heading)
            e.cars[0].hull.angle = heading
            np.testing.assert_allclose(forward, e.cars[0].hull.GetWorldVector((0, 1)), atol=1e-7)
            self.assertAlmostEqual(np.dot(forward, left), 0)
            e.cars[0].hull.position = (0, 0)
            e.cars[1].hull.position = 20 * forward + 3 * left
            row = e._get_telemetry_dynamic_state()[0]
            np.testing.assert_allclose(row[17:19] * (2000/6), [20, 3], atol=1e-5)
        _, heading, x, y = e.track[10]
        left = e._vehicle_axes(heading)[1]
        e.cars[0].hull.position = np.array([x, y]) + left
        row = e._get_telemetry_dynamic_state()[0]
        self.assertGreater(row[12], 0)

    def test_contact_and_reset(self):
        env = self.env()
        e = env.unwrapped
        for i, car in enumerate(e.cars):
            car.hull.angle = 0
            car.hull.position = (0, i * 4.95)
            for wheel in car.wheels:
                wheel.position = car.hull.GetWorldPoint(wheel.joint.anchorA - car.hull.position)
        _, _, _, info = env.step(np.zeros((2, 3)))
        self.assertTrue(any(c['agents'] == [0, 1] for c in info['vehicle_contacts']))
        self.assertGreater(np.linalg.norm(np.array(e.cars[0].hull.position)-np.array(e.cars[1].hull.position)), 2)
        env.reset()
        self.assertEqual(e.vehicle_contacts.snapshot(e.world), [])

    def test_identity_selection(self):
        e = self.env(5, max_neighbors=None).unwrapped
        o = e._get_telemetry_dynamic_state()
        before = list(e.last_dynamic_neighbor_ids[4][:3])
        e.cars[0].hull.position, e.cars[3].hull.position = tuple(e.cars[3].hull.position), tuple(e.cars[0].hull.position)
        changed = e._get_telemetry_dynamic_state()
        self.assertEqual(before, e.last_dynamic_neighbor_ids[4][:3])
        packed = pack_dynamic_neighbor_obs(changed, target_obs_dim=41, max_neighbors=3, selection_mode='fixed')
        np.testing.assert_array_equal(packed[4, 17:24], changed[4, 17:24])
        self.assertFalse(np.array_equal(o[4], changed[4]))

    def test_mask_and_rule_directions(self):
        env = SimpleNamespace(unwrapped=SimpleNamespace(telemetry_version='corrected_v2', observation_type='telemetry_dynamic'))
        obs = np.zeros((1, 41), dtype=np.float32)
        obs[0, 14] = 1
        obs[0, 12] = .2  # left of center -> steer right (positive action)
        action = TelemetryLanePolicy().act(env, obs)
        self.assertGreater(action[0, 0], 0)
        obs[0, 12] = 0
        obs[0, 17:25] = [20/(2000/6), 2/(2000/6), 0, 0, .07, 0, 1, 1]
        obs[0, 25:33] = [1, 1, 0, 0, 0, 0, 1, 0]
        self.assertEqual(len(opponent_slots(obs[0])), 1)
        # Opponent on physical left -> avoid to right.
        self.assertGreater(TelemetryOvertakePolicy().act(env, obs)[0, 0], 0)
        obs[0, 4] = 1
        self.assertGreater(TelemetryLanePolicy().act(env, obs)[0, 2], 0)

    def test_legacy_checkpoint_rejected(self):
        env = self.env()
        with self.assertRaises(ValueError):
            require_checkpoint_version(env, {})
        require_checkpoint_version(env, {'telemetry_version': 'corrected_v2'})

    def test_progress_wrap_and_reverse(self):
        p = TrackProgress([[0, 0], [100, 0], [100, 100], [0, 100]])
        self.assertAlmostEqual(p.update([[0, 2]])[0], 398)
        self.assertAlmostEqual(p.update([[3, 0]])[0], 403)
        self.assertAlmostEqual(p.update([[0, 1]])[0], 399)

    def endpoint(self):
        return OvertakingEndpoint([0, 10, 30], 400, 0, EndpointConfig(hold_steps=3, horizon=20))

    def test_same_target_retention(self):
        ep = self.endpoint()
        for step, progress in enumerate([[17, 10, 30], [14, 10, 30], [17, 10, 30], [18, 10, 30]], 1):
            r = ep.update(step, progress, [], [False]*3, [False]*3)
            self.assertFalse(r['lead_retained_completion'])
        r = ep.update(5, [19, 10, 30], [], [False]*3, [False]*3)
        self.assertTrue(r['contact_free_completion'])
        self.assertEqual(r['events'][0]['target'], 1)

    def test_contact_invalidates_clean_pass(self):
        ep = self.endpoint()
        for step in range(1, 4):
            contacts = [{'agents': [0, 2]}] if step == 1 else []
            r = ep.update(step, [17, 10, 30], contacts, [False]*3, [False]*3)
        self.assertTrue(r['lead_retained_completion'])
        self.assertFalse(r['contact_free_completion'])

    def test_background_contact_and_grass(self):
        ep = self.endpoint()
        for step in range(1, 4):
            r = ep.update(step, [17, 10, 30], [{'agents': [1, 2]}], [True, False, False], [False]*3)
        self.assertTrue(r['contact_free_completion'])
        self.assertFalse(r['center_ontrack_contact_free_completion'])

    def test_ineligible_and_sequence_validation(self):
        ep = OvertakingEndpoint([0, -10], 400, 0)
        self.assertFalse(ep.result()['eligible'])
        with self.assertRaises(ValueError):
            ep.update(2, [20, 0], [], [False]*2, [False]*2)

    def test_initial_contact_is_not_ignored(self):
        ep = OvertakingEndpoint([0, 10], 400, 0,
                                EndpointConfig(hold_steps=1), initial_contacts=[{'agents': [0, 1]}])
        r = ep.update(1, [17, 10], [], [False]*2, [False]*2)
        self.assertTrue(r['lead_retained_completion'])
        self.assertFalse(r['contact_free_completion'])

    def test_ablation_inherits_every_other_parameter(self):
        source = json.loads((CONFIGS/'tits_dnq_attribution_ablation_20260710.json').read_text())
        config = build(source, 'new_world.graphworld.pt', 'new_actor.graph.pt')
        full = config['algorithms'][0]
        for variant in config['algorithms'][1:]:
            changes = {k for k in full if variant[k] != full[k]} - {'name', 'kind', 'label_cn'}
            self.assertEqual(changes, set(OVERRIDES[variant['name']]))
            self.assertEqual(variant['geometry_curvature_lookahead'], full['geometry_curvature_lookahead'])


if __name__ == '__main__':
    unittest.main()
