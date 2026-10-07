"""Reversing the admitted slot order must not change which vehicles are admitted."""
import unittest

import numpy as np

from dlc.graph_policy import EGO_DIM, pack_dynamic_neighbor_obs

SLOT_DIM = 8
OBS_DIM = EGO_DIM + 4 * SLOT_DIM


def slot(forward, lateral):
    values = np.zeros(SLOT_DIM, dtype=np.float32)
    values[:7] = [forward, lateral, 0.0, 0.0, np.hypot(forward, lateral), 0.0, 1.0]
    values[7] = 1.0
    return values


def observation():
    row = np.zeros(OBS_DIM, dtype=np.float32)
    for index, values in enumerate([slot(0.2, 0.0), slot(0.1, 0.01), slot(-0.1, 0.02), slot(0.5, 0.6)]):
        row[EGO_DIM + index * SLOT_DIM:EGO_DIM + (index + 1) * SLOT_DIM] = values
    return row


class ReverseSlotOrderTest(unittest.TestCase):
    def test_reversal_keeps_the_set_and_flips_the_order(self):
        raw = np.stack([observation()], axis=0)
        forward = pack_dynamic_neighbor_obs(raw, target_obs_dim=OBS_DIM, max_neighbors=3,
                                            selection_mode="nearest", telemetry_version="corrected_v2")
        reversed_ = pack_dynamic_neighbor_obs(raw, target_obs_dim=OBS_DIM, max_neighbors=3,
                                              selection_mode="nearest", telemetry_version="corrected_v2",
                                              reverse_ranked=True)
        first = forward[0, EGO_DIM:].reshape(-1, SLOT_DIM)[:3, :7]
        second = reversed_[0, EGO_DIM:].reshape(-1, SLOT_DIM)[:3, :7]
        np.testing.assert_allclose(np.sort(first, axis=0), np.sort(second, axis=0), atol=1e-6)
        self.assertFalse(np.allclose(first, second), "reversal did not change the slot order")

    def test_reversal_is_inert_when_only_one_vehicle_is_admitted(self):
        raw = np.stack([observation()], axis=0)
        forward = pack_dynamic_neighbor_obs(raw, target_obs_dim=OBS_DIM, max_neighbors=1,
                                            selection_mode="nearest", telemetry_version="corrected_v2")
        reversed_ = pack_dynamic_neighbor_obs(raw, target_obs_dim=OBS_DIM, max_neighbors=1,
                                              selection_mode="nearest", telemetry_version="corrected_v2",
                                              reverse_ranked=True)
        np.testing.assert_allclose(forward, reversed_, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
