"""The admission rank must reach the model unchanged, and only as information.

A permutation-invariant pooling cannot see the order in which the admission
rule wrote the slots, so the closed-loop packer and the training packer both
write the rank of each admitted slot as an extra feature. These tests pin the
two packers to each other (they must agree bit for bit on the same input), pin
the stored-dataset promotion to the priority packer, and check that the model
reads the channel.
"""
import unittest

import numpy as np
import torch

from dlc.graph_policy import EGO_DIM, pack_dynamic_neighbor_obs
from dlc.graph_world_model import GraphTransitionModel
from dlc.training_packing import pack_transition_pair, promote_priority_channel

SLOT_DIM = 8
PRIORITY_SLOT_DIM = 9
SOURCES = 4
AGENTS = 3


def raw_observation(valid_counts, forward_offset=0.0):
    obs = np.zeros((AGENTS, EGO_DIM + SOURCES * SLOT_DIM), dtype=np.float32)
    for agent in range(AGENTS):
        obs[agent, 4] = 0.3
        obs[agent, 12] = 0.02 * (agent - 1)
        for slot in range(SOURCES):
            if slot >= valid_counts[agent]:
                continue
            start = EGO_DIM + slot * SLOT_DIM
            forward = 0.04 + 0.02 * slot + 0.01 * agent + forward_offset
            lateral = 0.01 * (slot + 1) * (1.0 if agent % 2 else -1.0)
            obs[agent, start:start + 7] = [forward, lateral, 0.0, 0.0,
                                           forward, lateral, 1.0]
            obs[agent, start + 7] = 1.0
    return obs


def closed_loop_pack(obs, k, fill=None, **kwargs):
    return pack_dynamic_neighbor_obs(
        obs,
        fill=np.zeros(SLOT_DIM, dtype=np.float32) if fill is None else fill,
        target_obs_dim=EGO_DIM + k * PRIORITY_SLOT_DIM,
        max_neighbors=k,
        selection_mode="interaction",
        telemetry_version="corrected_v2",
        **kwargs,
    )


def training_pack(obs, k, priority=True):
    ids = [[int(i) for i in range(SOURCES)] for _ in range(AGENTS)]
    packed, _, _ = pack_transition_pair(
        obs, obs, ids, ids, k=k, selection="interaction", priority=priority)
    return packed


class PackerAgreement(unittest.TestCase):
    def test_closed_loop_packer_writes_what_training_writes(self):
        for valid, k in (([4, 4, 4], 3), ([4, 2, 1], 3), ([4, 3, 2], 5)):
            with self.subTest(valid=valid, k=k):
                obs = raw_observation(valid)
                self.assertTrue(np.array_equal(
                    closed_loop_pack(obs, k), training_pack(obs, k)))

    def test_promotion_of_a_stored_dataset_equals_priority_packing(self):
        obs = raw_observation([4, 2, 1])
        k = 3
        stored = training_pack(obs, k, priority=False)
        promoted = promote_priority_channel([{"obs": stored, "next_obs": stored}], k)[0]
        self.assertTrue(np.array_equal(promoted["obs"], training_pack(obs, k)))

    def test_promotion_is_idempotent_and_rejects_a_wrong_width(self):
        obs = raw_observation([4, 4, 4])
        k = 3
        stored = training_pack(obs, k, priority=False)
        promoted = promote_priority_channel([{"obs": stored, "next_obs": stored}], k)[0]
        again = promote_priority_channel([promoted], k)[0]
        self.assertTrue(np.array_equal(promoted["obs"], again["obs"]))
        with self.assertRaises(ValueError):
            promote_priority_channel([{"obs": stored, "next_obs": stored}], 2)

    def test_rank_column_falls_with_the_admission_order(self):
        obs = raw_observation([4, 4, 4])
        packed = closed_loop_pack(obs, 3)
        ranks = packed[:, EGO_DIM + 7::PRIORITY_SLOT_DIM]
        self.assertTrue(np.allclose(ranks, [[1.0, 0.5, 0.0]] * AGENTS))
        masks = packed[:, EGO_DIM + 8::PRIORITY_SLOT_DIM]
        self.assertTrue(np.array_equal(masks, np.ones((AGENTS, 3), dtype=np.float32)))

    def test_promotion_leaves_masked_slots_without_a_rank(self):
        obs = raw_observation([4, 2, 1])
        k = 3
        stored = training_pack(obs, k, priority=False)
        promoted = promote_priority_channel([{"obs": stored, "next_obs": stored}], k)[0]["obs"]
        ranks = promoted[:, EGO_DIM + 7::PRIORITY_SLOT_DIM]
        self.assertTrue(np.array_equal(
            ranks, np.array([[1.0, 0.5, 0.0], [1.0, 0.5, 0.0], [1.0, 0.0, 0.0]],
                            dtype=np.float32)))

    def test_empty_slots_stay_masked_and_unranked(self):
        packed = closed_loop_pack(raw_observation([4, 1, 1]), 3)
        self.assertTrue(np.array_equal(
            packed[:, EGO_DIM + 8::PRIORITY_SLOT_DIM],
            np.array([[1, 1, 1], [1, 0, 0], [1, 0, 0]], dtype=np.float32)))
        self.assertTrue(np.array_equal(packed[1, EGO_DIM + 2 * PRIORITY_SLOT_DIM:],
                                       np.zeros(PRIORITY_SLOT_DIM, dtype=np.float32)))


def model():
    torch.manual_seed(0)
    return GraphTransitionModel(
        obs_dim=EGO_DIM + 3 * PRIORITY_SLOT_DIM, action_dim=3, num_agents=AGENTS,
        hidden_dim=16, pooling_mode="attention", masked_pooling="attention",
        use_slot_mask=True, slot_feature_dim=8,
    ).eval()


def predict(net, observation):
    with torch.no_grad():
        return net(torch.as_tensor(observation[None, ...], dtype=torch.float32),
                   torch.zeros(1, AGENTS, 3))["next_mu"].numpy()


class ChannelIsRead(unittest.TestCase):
    def test_the_rank_channel_changes_the_prediction(self):
        obs = raw_observation([4, 4, 4])
        packed = closed_loop_pack(obs, 3)
        swapped = packed.copy()
        first, second = EGO_DIM, EGO_DIM + PRIORITY_SLOT_DIM
        swapped[:, first + 7], swapped[:, second + 7] = (
            swapped[:, second + 7], swapped[:, first + 7].copy())
        difference = np.abs(predict(model(), packed) - predict(model(), swapped)).max()
        self.assertGreater(float(difference), 1e-6)

    def test_swapping_whole_slots_leaves_the_prediction_unchanged(self):
        obs = raw_observation([4, 4, 4])
        packed = closed_loop_pack(obs, 3)
        swapped = packed.copy()
        first, second = EGO_DIM, EGO_DIM + PRIORITY_SLOT_DIM
        swapped[:, first:first + PRIORITY_SLOT_DIM] = packed[:, second:second + PRIORITY_SLOT_DIM]
        swapped[:, second:second + PRIORITY_SLOT_DIM] = packed[:, first:first + PRIORITY_SLOT_DIM]
        self.assertTrue(np.allclose(predict(model(), packed), predict(model(), swapped),
                                    atol=1e-6))


if __name__ == "__main__":
    unittest.main()
