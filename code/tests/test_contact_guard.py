import math
import unittest
import numpy as np
from dlc.contact_guard import FrontGapGuard


class ContactGuardTests(unittest.TestCase):
    def apply(self, gap=12, lateral=0, closing=10, angle=0, mask=1):
        row = np.zeros(25, dtype=np.float32)
        row[5:7] = [math.sin(angle), math.cos(angle)]
        forward = np.array([-math.sin(angle), math.cos(angle)])
        row[17:] = [gap/(2000/6), lateral/(2000/6), *(-closing*forward/50),
                    math.hypot(gap, lateral)/(2000/6), 0, 1, mask]
        return FrontGapGuard().apply(row, [.2, .65, 0], telemetry_version='corrected_v2', masked=True)

    def test_closing_front_is_braked_at_every_rotation(self):
        for angle in [0, .7, math.pi, -math.pi/2]:
            action, debug = self.apply(angle=angle)
            self.assertTrue(debug['active'])
            np.testing.assert_allclose(action, [.2, 0, .7])

    def test_receding_clear_side_rear_and_padding_do_not_trigger(self):
        for kwargs in [{'closing': -5}, {'lateral': 10}, {'gap': -10}, {'mask': 0}, {'gap': 60}]:
            action, debug = self.apply(**kwargs)
            self.assertFalse(debug['active'])
            np.testing.assert_allclose(action, [.2, .65, 0])

    def test_already_small_gap_is_braked_even_at_equal_speed(self):
        self.assertTrue(self.apply(gap=5.5, closing=0)[1]['active'])

    def test_legacy_coordinates_are_rejected(self):
        with self.assertRaises(ValueError):
            FrontGapGuard().apply(np.zeros(25), [0, 0, 0], telemetry_version='legacy_v1', masked=True)


if __name__ == '__main__':
    unittest.main()
