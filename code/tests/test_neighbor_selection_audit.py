"""The dynamic relevance neighbourhood must be auditable by identity."""
import unittest

import numpy as np
import pyglet
pyglet.options['headless'] = True

from dlc.graph_policy import EGO_DIM, MASKED_OPPONENT_DIM, selected_neighbor_ids


def ego_block():
    row = np.zeros(EGO_DIM, dtype=np.float32)
    row[4] = 0.4
    row[14] = 1.0
    return row


def slot(forward, left, valid=True):
    values = np.zeros(MASKED_OPPONENT_DIM, dtype=np.float32)
    values[:7] = [forward, left, 0.0, 0.0, forward, left, 1.0]
    values[7] = 1.0 if valid else 0.0
    return values


def packed_row(slots):
    return np.concatenate([ego_block()] + [np.asarray(item, dtype=np.float32) for item in slots])


class NeighborSelectionAuditTests(unittest.TestCase):
    def test_selected_identities_come_from_the_exposed_set(self):
        row = packed_row([slot(0.02, 0.01), slot(-0.03, 0.02), slot(0.05, -0.01), slot(0.01, 0.0)])
        ids = selected_neighbor_ids(row, [4, 7, 9, 11], 3, selection_mode='interaction',
                                    telemetry_version='corrected_v2')
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), 3)
        self.assertTrue(set(ids).issubset({4, 7, 9, 11}))

    def test_invalid_slots_are_never_selected(self):
        row = packed_row([slot(0.0, 0.0, valid=False), slot(0.03, 0.0), slot(0.04, 0.0)])
        ids = selected_neighbor_ids(row, [1, 2, 3], 3, selection_mode='interaction',
                                    telemetry_version='corrected_v2')
        self.assertNotIn(1, ids)
        self.assertTrue(set(ids).issubset({2, 3}))

    def test_budget_bounds_the_returned_set(self):
        row = packed_row([slot(0.01, 0.0), slot(0.02, 0.0), slot(0.03, 0.0), slot(0.04, 0.0)])
        ids = selected_neighbor_ids(row, [0, 1, 2, 3], 2, selection_mode='interaction',
                                    telemetry_version='corrected_v2')
        self.assertLessEqual(len(ids), 2)


if __name__ == '__main__':
    unittest.main()
