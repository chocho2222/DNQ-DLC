import unittest
import pyglet
pyglet.options['headless'] = True
import numpy as np
from dlc.training_packing import pack_transition_pair


class TrainingPackingTests(unittest.TestCase):
    def test_nearest_swap_does_not_change_target_identity(self):
        obs = np.zeros((1, 41), dtype=np.float32)
        obs[0, 6] = obs[0, 14] = 1
        obs[0, 17:25] = [.06, 0, 0, 0, .06, 0, 1, 1]
        obs[0, 25:33] = [.09, 0, 0, 0, .09, 0, 1, 1]
        after = obs.copy()
        after[0, 17] = after[0, 21] = .10
        after[0, 25] = after[0, 29] = .02
        packed, target, ids = pack_transition_pair(obs, after, [[4, 7, -1]], [[4, 7, -1]], 1, 'nearest')
        self.assertEqual(ids, [[4]])
        np.testing.assert_array_equal(packed[0, 17:25], obs[0, 17:25])
        np.testing.assert_array_equal(target[0, 17:25], after[0, 17:25])
        _, _, following_ids = pack_transition_pair(after, after, [[4, 7, -1]], [[4, 7, -1]], 1, 'nearest')
        self.assertEqual(following_ids, [[7]])

    def test_padding_has_zero_mask_at_both_times(self):
        obs = np.zeros((1, 25), dtype=np.float32)
        a, b, ids = pack_transition_pair(obs, obs, [[-1]], [[-1]], 3)
        self.assertEqual(a.shape, (1, 41))
        self.assertEqual(ids, [[]])
        self.assertFalse(a.any() or b.any())


if __name__ == '__main__':
    unittest.main()
