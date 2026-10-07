import unittest

import numpy as np

from dlc.graph_policy import pack_dynamic_neighbor_obs
from dlc.policies import StableBaselinesActorPolicy


class _Unwrapped:
    telemetry_version = "corrected_v2"
    allow_legacy_checkpoint_migration = False


class _Env:
    unwrapped = _Unwrapped()


def _policy(meta, expected_obs_dim=41):
    """A loader instance without importing or loading a stable-baselines3 model."""
    policy = object.__new__(StableBaselinesActorPolicy)
    policy.meta = dict(meta)
    policy.expected_obs_dim = expected_obs_dim
    return policy


def _four_vehicle_row():
    obs = np.zeros((1, 41), dtype=np.float32)
    obs[0, 6] = 1.0
    obs[0, 14] = 1.0
    # Three live slots whose relevance order is the reverse of the row order.
    obs[0, 17:25] = [0.05, 0.00, 0.0, 0.0, 0.05, 0.0, 1.0, 1.0]
    obs[0, 25:33] = [0.30, 0.01, 0.0, 0.0, 0.30, 0.0, 1.0, 1.0]
    obs[0, 33:41] = [0.12, 0.02, 0.0, 0.0, 0.12, 0.0, 1.0, 1.0]
    return obs


class RlLoaderPackingTests(unittest.TestCase):
    def test_checkpoint_without_declared_packing_is_passed_through(self):
        obs = _four_vehicle_row()
        policy = _policy({"telemetry_version": "corrected_v2"})
        adapted = policy._adapt_observation(_Env(), obs)
        np.testing.assert_array_equal(adapted, obs)

    def test_declared_runtime_packing_is_applied_at_matching_width(self):
        obs = _four_vehicle_row()
        policy = _policy({
            "telemetry_version": "corrected_v2",
            "observation_packing": "runtime_interaction_packing_to_3_slots",
            "max_neighbors": 3,
        })
        adapted = policy._adapt_observation(_Env(), obs)
        expected = pack_dynamic_neighbor_obs(
            obs, target_obs_dim=41, max_neighbors=3,
            selection_mode="interaction", telemetry_version="corrected_v2",
        )
        np.testing.assert_allclose(adapted, expected)
        self.assertFalse(np.allclose(adapted, obs))

    def test_declared_and_undeclared_agree_when_the_width_already_differs(self):
        obs = np.zeros((1, 57), dtype=np.float32)
        obs[0, 6] = 1.0
        obs[0, 14] = 1.0
        for slot, distance in enumerate((0.05, 0.30, 0.12, 0.20, 0.40)):
            start = 17 + slot * 8
            obs[0, start:start + 8] = [distance, 0.01, 0.0, 0.0, distance, 0.0, 1.0, 1.0]
        declared = _policy({
            "telemetry_version": "corrected_v2",
            "observation_packing": "runtime_interaction_packing_to_3_slots",
            "max_neighbors": 3,
        })._adapt_observation(_Env(), obs)
        undeclared = _policy({"telemetry_version": "corrected_v2"})._adapt_observation(_Env(), obs)
        np.testing.assert_allclose(declared, undeclared)
        self.assertEqual(declared.shape, (1, 41))


if __name__ == "__main__":
    unittest.main()
