"""The frozen-identity ablation must keep the vehicles chosen at step one.

The archived selector ablation compared the dynamic ranking against a "fixed"
baseline that kept the first slots in observation order. When the number of
opponents equals the slot budget those two configurations receive the same set
of vehicles and differ only in slot order, which the mean-pooled actor discards,
so the comparison cannot say anything about dynamic relevance. These tests pin
the replacement: a frozen set of source slots, reused across decision steps.
"""
import unittest
from types import SimpleNamespace

import numpy as np
import pyglet
pyglet.options['headless'] = True

from dlc.graph_policy import (
    EGO_DIM,
    MASKED_OPPONENT_DIM,
    RELEVANCE_V2_STICKY_BONUS,
    _infer_source_layout,
    _rank_opponent_slot_entries,
    _rank_opponent_slots,
    pack_dynamic_neighbor_obs,
)
from dlc.graph_world_model import GraphWorldModelPolicy, escalation_feasible_indices


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


def observation(slots):
    return np.concatenate([ego_block()] + [np.asarray(item, dtype=np.float32) for item in slots])[None, :]


def rank(obs_row, mode="interaction"):
    slot_dim, _, use_slot_mask = _infer_source_layout(np.asarray(obs_row).shape[-1])
    return _rank_opponent_slot_entries(
        obs_row, slot_dim=slot_dim, use_slot_mask=use_slot_mask, selection_mode=mode
    )


class FrozenIdentityAblationTests(unittest.TestCase):
    def test_ranked_entries_report_the_source_slot_index(self):
        obs = observation([slot(0.02, 0.01), slot(0.05, 0.0), slot(0.03, 0.02)])[0]
        entries = rank(obs)
        self.assertEqual(sorted(index for index, _ in entries), [0, 1, 2])
        # The indexed features are the features the plain ranking returns.
        for (_, features), plain in zip(
            entries,
            _rank_opponent_slots(
                obs, slot_dim=MASKED_OPPONENT_DIM, use_slot_mask=True, selection_mode="interaction"
            ),
        ):
            np.testing.assert_allclose(features, plain)

    def test_frozen_order_keeps_the_named_vehicles_in_the_named_slots(self):
        obs = observation([slot(0.02, 0.01), slot(0.05, 0.0), slot(0.03, 0.02)])
        packed = pack_dynamic_neighbor_obs(
            obs, max_neighbors=2, selection_mode="fixed_initial", slot_order=[[2, 0]]
        )
        np.testing.assert_allclose(packed[0, EGO_DIM:EGO_DIM + 7], obs[0, EGO_DIM + 2 * MASKED_OPPONENT_DIM:EGO_DIM + 2 * MASKED_OPPONENT_DIM + 7])
        np.testing.assert_allclose(packed[0, EGO_DIM + MASKED_OPPONENT_DIM:EGO_DIM + MASKED_OPPONENT_DIM + 7], obs[0, EGO_DIM:EGO_DIM + 7])

    def test_a_masked_frozen_vehicle_pads_instead_of_sliding_a_later_one(self):
        obs = observation([slot(0.02, 0.01), slot(0.05, 0.0, valid=False), slot(0.03, 0.02)])
        packed = pack_dynamic_neighbor_obs(
            obs, max_neighbors=2, selection_mode="fixed_initial", slot_order=[[1, 2]]
        )
        # Slot 1 is padded and masked rather than replaced by vehicle 2.
        self.assertEqual(float(packed[0, EGO_DIM + 7]), 0.0)
        self.assertEqual(float(packed[0, EGO_DIM + MASKED_OPPONENT_DIM + 7]), 1.0)
        np.testing.assert_allclose(
            packed[0, EGO_DIM + MASKED_OPPONENT_DIM:EGO_DIM + MASKED_OPPONENT_DIM + 7],
            obs[0, EGO_DIM + 2 * MASKED_OPPONENT_DIM:EGO_DIM + 2 * MASKED_OPPONENT_DIM + 7],
        )

    def test_frozen_order_is_reused_after_the_scene_moves(self):
        policy = GraphWorldModelPolicy.__new__(GraphWorldModelPolicy)
        policy.telemetry_version = 'corrected_v2'
        policy.slot_budget = 1
        policy._frozen_slot_order = {}

        first = observation([slot(0.02, 0.01), slot(0.05, 0.0)])
        expected = [index for index, _ in rank(first[0])][:1]
        self.assertEqual(policy._frozen_neighbor_order(first[0]), [expected])

        # The scene moves, so a fresh ranking would admit a different vehicle;
        # the frozen set must still name the one chosen at the first step.
        later = observation([slot(-0.05, 0.0), slot(0.02, 0.01)])
        self.assertNotEqual([index for index, _ in rank(later[0])][:1], expected)
        self.assertEqual(policy._frozen_neighbor_order(later[0]), [expected])

    def test_backfill_keeps_slots_filled_while_opponents_remain(self):
        # Three opponents, all far outside the relevance radius, so the plain
        # relevance rule admits none of them.
        far = [slot(0.30 + 0.02 * index, 0.0) for index in range(3)]
        obs = observation(far)
        plain = _rank_opponent_slots(
            obs[0], slot_dim=MASKED_OPPONENT_DIM, use_slot_mask=True, selection_mode="interaction"
        )
        self.assertEqual(plain, [])
        backfilled = _rank_opponent_slots(
            obs[0],
            slot_dim=MASKED_OPPONENT_DIM,
            use_slot_mask=True,
            selection_mode="interaction_backfill",
            min_keep=2,
        )
        self.assertEqual(len(backfilled), 2)
        packed = pack_dynamic_neighbor_obs(
            obs, max_neighbors=2, selection_mode="interaction_backfill", min_neighbors=2
        )
        self.assertEqual(float(packed[0, EGO_DIM + 7]), 1.0)
        self.assertEqual(float(packed[0, EGO_DIM + MASKED_OPPONENT_DIM + 7]), 1.0)

    def test_relevance_v2_admits_a_vehicle_the_archived_radius_rule_drops(self):
        # 120 m ahead: outside the archived 80 m radius and outside its 70 m
        # forward window, so the archived rule removes it from the graph.
        obs = observation([slot(120 / (2000 / 6), 0.0)])[0]
        archived = _rank_opponent_slots(
            obs, slot_dim=MASKED_OPPONENT_DIM, use_slot_mask=True, selection_mode="interaction"
        )
        self.assertEqual(archived, [])
        v2 = _rank_opponent_slots(
            obs, slot_dim=MASKED_OPPONENT_DIM, use_slot_mask=True, selection_mode="relevance_v2"
        )
        self.assertEqual(len(v2), 1)

    def test_relevance_v2_orders_by_time_to_collision_before_distance(self):
        # Slot 0 is farther away but closing; slot 1 is nearer and matched in
        # speed. TTC, not raw distance, decides which one is admitted first.
        close_slot = slot(0.10, 0.0)
        close_slot[2] = -0.30                      # closing at 15 m/s
        slow_slot = slot(0.05, 0.0)                # 10 m ahead, matched speed
        obs = observation([close_slot, slow_slot])[0]
        entries = rank(obs, mode="relevance_v2")
        self.assertEqual([index for index, _ in entries][:1], [0])

    def test_relevance_v2_sticky_term_retains_the_committed_vehicle(self):
        obs = observation([slot(0.05, 0.0), slot(0.10, 0.0)])[0]
        plain = _rank_opponent_slot_entries(
            obs, slot_dim=MASKED_OPPONENT_DIM, use_slot_mask=True, selection_mode="relevance_v2"
        )
        self.assertEqual([index for index, _ in plain][:1], [0])
        sticky = {1}
        with_sticky = _rank_opponent_slot_entries(
            obs,
            slot_dim=MASKED_OPPONENT_DIM,
            use_slot_mask=True,
            selection_mode="relevance_v2",
            sticky=sticky,
        )
        self.assertEqual([index for index, _ in with_sticky][:1], [1])
        self.assertGreater(RELEVANCE_V2_STICKY_BONUS, 0.0)

    def test_escalation_keeps_only_candidates_that_never_entered_the_guarded_state(self):
        self.assertEqual(escalation_feasible_indices([0.0, 0.4, 0.0, 1.2]), {0, 2})
        self.assertEqual(escalation_feasible_indices([0.1, 0.2]), set())


if __name__ == '__main__':
    unittest.main()
