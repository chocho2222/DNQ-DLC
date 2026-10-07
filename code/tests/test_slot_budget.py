"""A null max_neighbors must not hand the trained network an unbounded slot axis."""
import unittest
from types import SimpleNamespace

import pyglet
pyglet.options['headless'] = True

from dlc.graph_world_model import GraphWorldModelPolicy


def policy(max_neighbors, obs_dim=41, ego_dim=17, slot_feature_dim=7, use_slot_mask=True):
    p = GraphWorldModelPolicy.__new__(GraphWorldModelPolicy)
    p.max_neighbors = max_neighbors
    p.bundle = SimpleNamespace(meta={
        'obs_dim': obs_dim, 'ego_dim': ego_dim,
        'slot_feature_dim': slot_feature_dim, 'use_slot_mask': use_slot_mask,
    })
    p.slot_budget = p._derive_slot_budget()
    return p


class SlotBudgetTests(unittest.TestCase):
    def test_null_max_neighbors_uses_the_checkpoint_slot_count(self):
        self.assertEqual(policy(None).slot_budget, 3)

    def test_explicit_max_neighbors_wins(self):
        self.assertEqual(policy(5).slot_budget, 5)
        self.assertEqual(policy(2).slot_budget, 2)

    def test_unmasked_checkpoint_uses_the_bare_slot_width(self):
        self.assertEqual(policy(None, obs_dim=17 + 4 * 7, use_slot_mask=False).slot_budget, 4)

    def test_indivisible_width_falls_back_to_unbounded(self):
        self.assertEqual(policy(None, obs_dim=42).slot_budget, None)

    def test_budget_never_exceeds_the_checkpoint_width(self):
        budget = policy(None).slot_budget
        residual = 41 - 17 - budget * 8
        self.assertEqual(residual, 0)


if __name__ == '__main__':
    unittest.main()
