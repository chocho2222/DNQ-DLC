"""The retrained DLC actors must see the observation they were trained on.

Those baselines are trained on the packed slot rows the proposed pipeline
consumes, but the closed-loop runner may expose every vehicle when the
neighbour budget is unbounded. These tests pin the runtime packer to the
stored dataset rows and check that the wrapper only repacks when it has to.
"""
import gzip
import json
import os
import unittest

import numpy as np

from dlc.graph_policy import EGO_DIM, pack_dynamic_neighbor_obs
from dlc.policies import PackedActorPolicy

DATASET_EPISODE = ("outputs/tits_dynamic_graph_expanded/corrected_v2_20260920/"
                   "dataset_k15/raw/episode_00000_n6_seed13")
SLOT_DIM = 8
TARGET_SLOTS = 3


def unbounded_observation(agents=6, slots=4):
    obs = np.zeros((agents, EGO_DIM + slots * SLOT_DIM), dtype=np.float32)
    for agent in range(agents):
        obs[agent, 4] = 0.3
        obs[agent, 12] = 0.02 * (agent - 1)
        for slot in range(slots):
            start = EGO_DIM + slot * SLOT_DIM
            forward = 0.04 + 0.02 * slot + 0.01 * agent
            lateral = 0.01 * (slot + 1) * (1.0 if agent % 2 else -1.0)
            obs[agent, start:start + 7] = [forward, lateral, 0.0, 0.0, forward, lateral, 1.0]
            obs[agent, start + 7] = 1.0
    return obs


class FakeInner:
    def __init__(self, obs_dim, agents):
        self.bundle = type("Bundle", (), {})()
        self.bundle.obs_mean = np.zeros((agents, obs_dim), dtype=np.float32)
        self.seen = None
        self.resets = 0

    def reset(self):
        self.resets += 1

    def act(self, env, obs):
        self.seen = np.asarray(obs).shape
        return np.zeros((np.asarray(obs).shape[0], 3), dtype=np.float32)


class PackedActorPolicyTest(unittest.TestCase):
    def test_repacking_reproduces_the_stored_dataset_rows(self):
        episode = DATASET_EPISODE
        npz = os.path.join(episode, "transitions.npz")
        records = os.path.join(episode, "step_records.jsonl.gz")
        if not (os.path.exists(npz) and os.path.exists(records)):
            self.skipTest("archived expert dataset is not present")
        stored = np.load(npz)["obs"]
        with gzip.open(records, "rt") as handle:
            steps = [json.loads(line) for line in handle]
        self.assertEqual(len(steps), stored.shape[0])
        worst = 0.0
        for index, step in enumerate(steps):
            full = np.asarray(step["full_obs"], dtype=np.float32)
            repacked = pack_dynamic_neighbor_obs(
                full,
                target_obs_dim=stored.shape[-1],
                max_neighbors=TARGET_SLOTS,
                selection_mode="interaction",
                telemetry_version="corrected_v2",
            )
            worst = max(worst, float(np.abs(repacked - stored[index]).max()))
        self.assertEqual(worst, 0.0)

    def test_wrapper_repacks_only_a_wider_observation(self):
        obs = unbounded_observation()
        packed_dim = EGO_DIM + TARGET_SLOTS * SLOT_DIM
        inner = FakeInner(packed_dim, obs.shape[0])
        PackedActorPolicy(inner, max_neighbors=TARGET_SLOTS).act(None, obs)
        self.assertEqual(inner.seen, (obs.shape[0], packed_dim))

        already_packed = unbounded_observation(slots=TARGET_SLOTS)
        inner = FakeInner(packed_dim, already_packed.shape[0])
        PackedActorPolicy(inner, max_neighbors=TARGET_SLOTS).act(None, already_packed)
        self.assertEqual(inner.seen, already_packed.shape)

    def test_reset_and_agent_binding_are_forwarded(self):
        inner = FakeInner(EGO_DIM + TARGET_SLOTS * SLOT_DIM, 4)
        inner.set_controlled_agent = lambda agent_id: setattr(inner, "agent", agent_id)
        policy = PackedActorPolicy(inner, max_neighbors=TARGET_SLOTS)
        policy.reset()
        policy.set_controlled_agent(2)
        self.assertEqual(inner.resets, 1)
        self.assertEqual(inner.agent, 2)


if __name__ == "__main__":
    unittest.main()
