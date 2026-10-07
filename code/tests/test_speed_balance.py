"""BC reweighting must amplify the standing-start regime without exploding."""
import unittest

import numpy as np

from scripts.train_graph_risk_world_model import (
    SPEED_BALANCE_EDGES,
    speed_balance_table,
    speed_bin_frequencies,
)


def transitions(speeds):
    return [{"obs": np.array([[0.0] * 4 + [speed / 50.0]])} for speed in speeds]


class SpeedBalanceTests(unittest.TestCase):
    def test_frequencies_are_a_distribution(self):
        rows = transitions([0.0] * 2 + [10.0] * 6 + [21.0] * 92)
        freq = speed_bin_frequencies(rows)
        self.assertAlmostEqual(float(freq.sum()), 1.0, places=9)
        self.assertAlmostEqual(float(freq[0]), 0.02, places=9)

    def test_zero_alpha_is_identity(self):
        freq = speed_bin_frequencies(transitions([0.0, 10.0, 21.0]))
        weights, _ = speed_balance_table(SPEED_BALANCE_EDGES, freq, 0.0)
        np.testing.assert_allclose(weights, np.ones_like(weights))

    def test_tempered_weights_are_monotone_in_rarity(self):
        # bins: 0 -> [0,1) rare, 3 -> [6,12) dominant, 5 -> [18,21.5) mid
        freq = speed_bin_frequencies(transitions([0.0] * 1 + [10.0] * 90 + [21.0] * 9))
        weights, _ = speed_balance_table(SPEED_BALANCE_EDGES, freq, 0.5)
        self.assertAlmostEqual(float(freq[0]), 0.01, places=9)
        self.assertGreater(weights[0], weights[5])
        self.assertGreater(weights[5], weights[3])

    def test_empty_bin_does_not_divide_by_zero(self):
        freq = np.zeros(len(SPEED_BALANCE_EDGES) - 1)
        weights, _ = speed_balance_table(SPEED_BALANCE_EDGES, freq, 0.5)
        self.assertTrue(np.isfinite(weights).all())


if __name__ == "__main__":
    unittest.main()
