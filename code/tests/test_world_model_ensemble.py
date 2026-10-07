"""Fusion of several world-model instances inside one planner.

The submitted controller loads one checkpoint per training seed and averages
their transition, reward, risk and auxiliary quality predictions at rollout
time, inflating the uncertainty head by the disagreement between members. These
tests fix the fusion arithmetic, the single-member pass-through and the guards
that keep incompatible members apart. They use stub members so they do not need
a checkpoint on disk.
"""
import unittest

import torch

from dlc.graph_world_model import GraphWorldModelPolicy
from dlc.policies import make_policy


class _Member:
    def __init__(self, next_mu, logvar, reward, risk, quality=None, meta=None):
        self.next_mu = next_mu
        self.logvar = logvar
        self.reward = reward
        self.risk = risk
        self.quality = quality
        self.meta = dict(meta or {})

    def transition(self, obs_tensor, act_tensor):
        quality = None if self.quality is None else torch.as_tensor(self.quality)[None, ...]
        return {
            "next_mu": torch.as_tensor(self.next_mu)[None, ...],
            "next_logvar": torch.as_tensor(self.logvar)[None, ...],
            "reward_mu": torch.as_tensor(self.reward)[None, ...],
            "reward_logvar": torch.zeros_like(torch.as_tensor(self.reward))[None, ...],
            "risk_logits": torch.as_tensor(self.risk)[None, ...],
            "quality_pred": quality,
            "attn_entropy": torch.zeros(1, 1),
        }


def _policy(members):
    policy = GraphWorldModelPolicy.__new__(GraphWorldModelPolicy)
    policy.bundles = members
    policy.bundle = members[0]
    policy.ensemble_size = len(members)
    return policy


class WorldModelEnsembleTests(unittest.TestCase):
    def test_single_member_is_a_pass_through(self):
        member = _Member([[0.0, 0.0]], [[-1.0, -1.0]], [0.0, 0.0], [0.0, 0.0])
        policy = _policy([member])
        out = policy._ensemble_transition(torch.zeros(1, 1), torch.zeros(1, 1))
        reference = member.transition(None, None)
        self.assertEqual(sorted(out), sorted(reference))
        for key, value in reference.items():
            if value is None:
                self.assertIsNone(out[key])
            else:
                self.assertTrue(torch.allclose(out[key], value), key)

    def test_state_head_is_the_member_mean(self):
        first = _Member([[0.0, 0.0]], [[0.0, 0.0]], [1.0, 0.0], [0.0, 0.0])
        second = _Member([[2.0, 4.0]], [[0.0, 0.0]], [3.0, 2.0], [1.0, 1.0])
        policy = _policy([first, second])
        out = policy._ensemble_transition(torch.zeros(1, 1), torch.zeros(1, 1))
        self.assertTrue(torch.allclose(out["next_mu"], torch.tensor([[[1.0, 2.0]]])))
        self.assertTrue(torch.allclose(out["reward_mu"], torch.tensor([[2.0, 1.0]])))
        self.assertTrue(torch.allclose(out["risk_logits"], torch.tensor([[0.5, 0.5]])))

    def test_disagreement_enters_the_uncertainty_head(self):
        # Equal aleatoric variance across members, non-zero spread between the
        # member means: the fused log-variance must exceed log(aleatoric).
        first = _Member([[0.0, 0.0]], [[0.0, 0.0]], [0.0, 0.0], [0.0, 0.0])
        second = _Member([[2.0, 0.0]], [[0.0, 0.0]], [0.0, 0.0], [0.0, 0.0])
        policy = _policy([first, second])
        out = policy._ensemble_transition(torch.zeros(1, 1), torch.zeros(1, 1))
        expected = torch.log(torch.tensor(1.0) + torch.tensor(1.0))
        self.assertAlmostEqual(float(out["next_logvar"][0, 0, 0]), float(expected), places=5)
        self.assertAlmostEqual(float(out["next_logvar"][0, 0, 1]), 0.0, places=5)

    def test_unanimous_members_keep_the_aleatoric_variance(self):
        first = _Member([[0.0]], [[0.5]], [0.0], [0.0])
        second = _Member([[0.0]], [[0.5]], [0.0], [0.0])
        policy = _policy([first, second])
        out = policy._ensemble_transition(torch.zeros(1, 1), torch.zeros(1, 1))
        self.assertAlmostEqual(float(out["next_logvar"][0, 0, 0]), 0.5, places=5)

    def test_quality_head_is_averaged_when_present(self):
        first = _Member([[0.0]], [[0.0]], [0.0], [0.0], quality=[[0.0, 0.0]])
        second = _Member([[0.0]], [[0.0]], [0.0], [0.0], quality=[[2.0, 1.0]])
        policy = _policy([first, second])
        out = policy._ensemble_transition(torch.zeros(1, 1), torch.zeros(1, 1))
        self.assertTrue(torch.allclose(out["quality_pred"][0, 0], torch.tensor([1.0, 0.5])))

    def test_mean_only_fusion_drops_the_disagreement(self):
        # With the epistemic term switched off the fused log-variance is the
        # mean of the members' own variances, so two members that disagree on
        # the mean no longer inflate the uncertainty the planner sees.
        first = _Member([[0.0]], [[0.5]], [0.0], [0.0])
        second = _Member([[2.0]], [[0.5]], [0.0], [0.0])
        policy = _policy([first, second])
        policy.ensemble_epistemic = False
        out = policy._ensemble_transition(torch.zeros(1, 1), torch.zeros(1, 1))
        self.assertAlmostEqual(float(out["next_logvar"][0, 0, 0]), 0.5, places=5)
        self.assertTrue(torch.allclose(out["next_mu"], torch.tensor([[[1.0]]])))

    def test_members_must_share_one_protocol(self):
        first = _Member([[0.0]], [[0.0]], [0.0], [0.0], meta={"telemetry_version": "corrected_v2"})
        second = _Member([[0.0]], [[0.0]], [0.0], [0.0], meta={"telemetry_version": "legacy_v1"})
        policy = GraphWorldModelPolicy.__new__(GraphWorldModelPolicy)
        policy.bundles = [first, second]
        policy.bundle = first
        with self.assertRaises(ValueError):
            policy._check_ensemble_compatibility()

    def test_only_graphworld_checkpoints_can_be_ensembled(self):
        with self.assertRaises(ValueError):
            make_policy(["a.pt", "b.pt"])
        with self.assertRaises(ValueError):
            make_policy([])


if __name__ == "__main__":
    unittest.main()
