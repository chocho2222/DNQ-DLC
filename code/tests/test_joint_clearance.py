import unittest
import pyglet
pyglet.options['headless'] = True
import numpy as np
from dlc.joint_clearance_pilot import JointClearanceConfig, candidate_future, clearance


class JointClearanceTests(unittest.TestCase):
    def test_blocking_front_and_clear_side_are_distinguished(self):
        c = JointClearanceConfig()
        times, s, d = candidate_future(4.4, 20, 0, 4.4, 20, c)
        front = {'id': 2, 'gap': 15, 'speed': 12, 'lateral': 4.4, 'lateral_speed': 0}
        self.assertEqual(clearance(times, s, d, [front], c)[1], [2])
        front['lateral'] = 0
        self.assertTrue(clearance(times, s, d, [front], c)[0])

    def test_side_car_blocks_crossing_even_if_final_lane_clear(self):
        c = JointClearanceConfig()
        t, s, d = candidate_future(-4.4, 13, 0, 4.4, 13, c)
        side = {'id': 3, 'gap': 0, 'speed': 13, 'lateral': 0, 'lateral_speed': 0}
        self.assertIn(3, clearance(t, s, d, [side], c)[1])

    def test_fast_rear_is_checked_even_when_behind_now(self):
        c = JointClearanceConfig()
        t, s, d = candidate_future(0, 13, 0, 0, 13, c)
        rear = {'id': 4, 'gap': -15, 'speed': 25, 'lateral': 0, 'lateral_speed': 0}
        self.assertIn(4, clearance(t, s, d, [rear], c)[1])

    def test_boundary_is_not_ignored_and_braking_never_reverses(self):
        c = JointClearanceConfig()
        t, s, d = candidate_future(6, 2, 0, 6, 0, c)
        self.assertTrue(clearance(t, s, d, [], c)[3])
        self.assertTrue(np.all(np.diff(s) >= 0))

    def test_inward_recovery_remains_available_at_current_boundary(self):
        c = JointClearanceConfig()
        t, s, d = candidate_future(4.9, 10, 0, 0, 8, c)
        self.assertFalse(clearance(t, s, d, [], c)[3])
        t, s, d = candidate_future(4.9, 10, 0, 5.5, 8, c)
        self.assertTrue(clearance(t, s, d, [], c)[3])


if __name__ == '__main__':
    unittest.main()
