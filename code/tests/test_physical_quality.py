import unittest
import pyglet
pyglet.options['headless'] = True
import numpy as np
from dlc.physical_quality_pilot import footprint_terms, PhysicalQualityConfig, PhysicalQualityPilot


class PhysicalQualityTests(unittest.TestCase):
    def row(self, lateral=4.4):
        row = np.zeros(41, dtype=np.float32)
        row[6] = row[14] = 1
        row[12] = lateral/(40/6)
        return row

    def test_ontrack_passing_is_not_boundary_violation(self):
        for d in [-4.4, 0, 4.4]:
            self.assertGreater(footprint_terms(self.row(d))['edge_margin'], 0)
        self.assertLess(footprint_terms(self.row(5.5))['edge_margin'], 0)

    def test_heading_changes_body_extent(self):
        row = self.row(4.4)
        row[13], row[14] = 1, 0
        self.assertLess(footprint_terms(row)['edge_margin'], 0)

    def test_front_side_and_rear_overlap_not_only_center_distance(self):
        for forward, left in [(5,0), (-5,0), (0,3)]:
            row = self.row(0)
            row[17:25] = [forward/(2000/6),left/(2000/6),0,0,.02,0,1,1]
            self.assertGreater(footprint_terms(row)['overlap_proxy'], 0)
            row[24] = 0
            self.assertEqual(footprint_terms(row)['overlap_proxy'], 0)

    def test_same_side_by_side_longitudinal_position_can_be_clear(self):
        row = self.row(0)
        row[17:25] = [0,4.4/(2000/6),0,0,.02,0,1,1]
        self.assertEqual(footprint_terms(row)['overlap_proxy'],0)

    def test_lane_offset_does_not_force_brake_or_recovery(self):
        p = PhysicalQualityPilot.__new__(PhysicalQualityPilot)
        p.physical_config = PhysicalQualityConfig()
        p.target_speed = 22
        row = self.row(); row[4] = 20/50
        self.assertFalse(p._needs_hard_recovery(row))
        np.testing.assert_allclose(p._speed_limited_action([0,.6,0], row), [0,.6,0])


if __name__ == '__main__':
    unittest.main()
