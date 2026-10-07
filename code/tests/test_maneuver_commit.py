"""The manoeuvre commitment must admit the partner and nothing else.

``maneuver_commit_steps`` holds the car the ego is passing in the admitted set
even when its instantaneous relevance score would drop it. These tests pin the
two properties the runtime depends on: the partner is admitted when the score
alone would exclude it, and the commitment never invents a vehicle that the
observation does not carry.
"""
import unittest

import numpy as np

from dlc.graph_policy import EGO_DIM, pack_dynamic_neighbor_obs

SLOT_DIM = 8
SOURCES = 4
OBS_DIM = EGO_DIM + SOURCES * SLOT_DIM


def slot(forward, lateral, valid=True):
    values = np.zeros(SLOT_DIM, dtype=np.float32)
    values[:7] = [forward, lateral, 0.0, 0.0, np.hypot(forward, lateral),
                  0.0, 1.0]
    values[7] = 1.0 if valid else 0.0
    return values


def observation(slots):
    row = np.zeros(OBS_DIM, dtype=np.float32)
    for index, values in enumerate(slots):
        row[EGO_DIM + index * SLOT_DIM:EGO_DIM + (index + 1) * SLOT_DIM] = values
    return np.stack([row], axis=0)


def admitted(raw, k, commit=None):
    packed = pack_dynamic_neighbor_obs(
        raw, fill=np.zeros(SLOT_DIM, dtype=np.float32), target_obs_dim=OBS_DIM,
        max_neighbors=k, selection_mode="interaction", telemetry_version="corrected_v2",
        commit_order=None if commit is None else [commit],
    )
    block = packed[0, EGO_DIM:].reshape(-1, SLOT_DIM)[:k]
    return [tuple(np.round(row[:7], 6)) for row in block if row[7] > 0.5]


class ManeuverCommitTest(unittest.TestCase):
    def test_commit_promotes_a_car_the_rule_would_drop(self):
        # Slot 0 sits at the peak of the rule's front-gap term and wins the
        # single admitted slot; slot 1 is the car being passed and loses it.
        raw = observation([slot(0.066, 0.0), slot(0.05, 0.004), slot(-0.05, 0.01),
                           slot(0.3, 0.5)])
        without = admitted(raw, 1)
        with_commit = admitted(raw, 1, commit=[1])
        self.assertNotIn(tuple(np.round(slot(0.05, 0.004)[:7], 6)), without)
        self.assertIn(tuple(np.round(slot(0.05, 0.004)[:7], 6)), with_commit)
        self.assertEqual(len(with_commit), 1)

    def test_commit_cannot_admit_an_invalid_slot(self):
        raw = observation([slot(0.066, 0.0), slot(0.05, 0.004, valid=False),
                           slot(-0.05, 0.01), slot(0.3, 0.5)])
        with_commit = admitted(raw, 1, commit=[1])
        self.assertNotIn(tuple(np.round(slot(0.05, 0.004)[:7], 6)), with_commit)

    def test_commit_is_inert_when_the_car_is_already_admitted(self):
        raw = observation([slot(0.066, 0.0), slot(0.05, 0.004), slot(-0.05, 0.01),
                           slot(0.3, 0.5)])
        without = admitted(raw, 3)
        with_commit = admitted(raw, 3, commit=[1])
        self.assertEqual(sorted(without), sorted(with_commit))

    def test_commit_moves_the_partner_to_the_front(self):
        raw = observation([slot(0.066, 0.0), slot(0.05, 0.004), slot(-0.05, 0.01),
                           slot(0.3, 0.5)])
        packed = pack_dynamic_neighbor_obs(
            raw, fill=np.zeros(SLOT_DIM, dtype=np.float32), target_obs_dim=OBS_DIM,
            max_neighbors=3, selection_mode="interaction", telemetry_version="corrected_v2",
            commit_order=[[1]],
        )
        first = packed[0, EGO_DIM:EGO_DIM + 7]
        np.testing.assert_allclose(first, slot(0.05, 0.004)[:7], atol=1e-6)


if __name__ == "__main__":
    unittest.main()
