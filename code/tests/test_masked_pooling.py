"""Masked-observation pooling must honour the requested pooling mode.

The corrected telemetry path always sets ``use_slot_mask``. In the archived
code that branch pooled the opponent slots with a masked mean and ignored
``pooling_mode`` entirely, so a checkpoint trained with ``attention`` never
weighted one admitted vehicle over another: only the set membership reached the
transition head. These tests pin the repaired behaviour, the retained mean
option, and the empty-neighbourhood fallback.
"""
import unittest

import numpy as np
import torch

from dlc.graph_world_model import EGO_DIM, GraphTransitionModel

SLOT_DIM = 8 # seven relation features plus the occupancy mask
OBS_DIM = EGO_DIM + 3 * SLOT_DIM


def observation(slots):
    row = np.zeros(OBS_DIM, dtype=np.float32)
    row[4] = 0.3 # ego speed channel
    for index, values in enumerate(slots):
        start = EGO_DIM + index * SLOT_DIM
        row[start:start + SLOT_DIM] = values
    return row


def slot(forward, lateral, valid=True):
    values = np.zeros(SLOT_DIM, dtype=np.float32)
    values[:7] = [forward, lateral, 0.0, 0.0, forward, lateral, 1.0]
    values[7] = 1.0 if valid else 0.0
    return values


def build(masked_pooling, seed=0):
    torch.manual_seed(seed)
    return GraphTransitionModel(
        obs_dim=OBS_DIM, action_dim=3, num_agents=4, hidden_dim=16,
        pooling_mode="attention", masked_pooling=masked_pooling,
        use_slot_mask=True, slot_feature_dim=7,
    ).eval()


def differentiate(model):
    """Give the attention head a non-degenerate projection.

    A freshly initialised head produces logits that differ by ~1e-4 across
    slots, which makes the softmax indistinguishable from a uniform average. The
    tests below need weights that actually favour one admitted vehicle.
    """
    with torch.no_grad():
        model.relation_attention.weight.copy_(
            torch.linspace(-1.0, 1.0, model.hidden_dim).reshape(1, -1))
        model.relation_attention.bias.zero_()
    return model


def forward(model, rows):
    obs = torch.as_tensor(np.stack(rows, axis=0)[None, ...] - 0.0, dtype=torch.float32)
    action = torch.zeros(1, len(rows), 3)
    with torch.no_grad():
        return model(obs, action)


class MaskedPoolingTest(unittest.TestCase):
    def test_attention_entropy_differs_from_the_mask_pattern(self):
        model = differentiate(build("attention"))
        out = forward(model, [observation([slot(1.0, 0.2), slot(1.4, -0.3), slot(0.0, 0.0, False)])])
        entropy = float(out["attn_entropy"][0])
        uniform_two = float(np.log(2.0))
        self.assertLess(entropy, uniform_two - 1e-6,
                        "attention weights are the occupancy mask, not learned weights")

    def test_masked_slot_features_cannot_change_the_prediction(self):
        model = build("attention")
        first = forward(model, [observation([slot(1.0, 0.2), slot(1.4, -0.3), slot(0.5, 0.0, False)])])
        second = forward(model, [observation([slot(1.0, 0.2), slot(1.4, -0.3), slot(-9.0, 4.0, False)])])
        torch.testing.assert_close(first["next_mu"], second["next_mu"])

    def test_attention_output_is_not_the_masked_mean(self):
        model = differentiate(build("attention"))
        rows = [observation([slot(1.0, 0.2), slot(1.4, -0.3), slot(0.0, 0.0, False)])]
        attention = forward(model, rows)["next_mu"]
        mean_model = build("mean")
        mean_model.load_state_dict(model.state_dict())
        mean_model.eval()
        mean = forward(mean_model, rows)["next_mu"]
        self.assertGreater(float((attention - mean).abs().max()), 1e-6)

    def test_mean_mode_is_permutation_invariant(self):
        model = build("mean")
        first = forward(model, [observation([slot(1.0, 0.2), slot(1.4, -0.3), slot(0.6, 0.1)])])
        second = forward(model, [observation([slot(0.6, 0.1), slot(1.0, 0.2), slot(1.4, -0.3)])])
        torch.testing.assert_close(first["next_mu"], second["next_mu"], atol=1e-6, rtol=1e-6)

    def test_attention_survives_an_empty_neighbourhood(self):
        model = build("attention")
        out = forward(model, [observation([slot(0.0, 0.0, False)] * 3)])
        self.assertTrue(bool(torch.isfinite(out["next_mu"]).all()))
        self.assertEqual(float(out["attn_entropy"][0]), 0.0)


if __name__ == "__main__":
    unittest.main()
