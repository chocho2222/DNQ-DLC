"""Lateral thresholds must be expressed in the protocol's own cross-track units."""
import unittest
from types import SimpleNamespace

import numpy as np
import pyglet
pyglet.options['headless'] = True

from dlc.graph_world_model import PLANNER_GEOMETRY, GraphWorldModelPolicy

HALF_WIDTH_M = 40.0 / 6.0
ENV_LATERAL_SPACING_HALF_WIDTHS = 2.2 / HALF_WIDTH_M  # 0.33


def planner(telemetry_version):
    p = GraphWorldModelPolicy.__new__(GraphWorldModelPolicy)
    p.telemetry_version = telemetry_version
    p.bundle = SimpleNamespace(meta={'use_slot_mask': True, 'opponent_dim': 8})
    p.separation_scale = 0.0 if telemetry_version == 'legacy_v1' else 1.0
    p.overtake_aware_planner = True
    p.geometry_generalization = False
    p.elegance_barrier = False
    p.target_speed = 22.0
    p._geometry_context = {}
    return p


def obs(ego_lateral, heading_cos=1.0, on_grass=False, forward_gap=None, ahead_count=1):
    row = np.zeros(41, dtype=np.float32)
    row[4] = 0.4
    row[12] = -ego_lateral          # corrected_v2 stores left-positive offset
    row[14] = heading_cos
    row[15] = 1.0 if on_grass else 0.0
    if forward_gap is not None:
        row[17:25] = [forward_gap / (2000 / 6), 0.0, -5.0 / 50.0, 0.0,
                      forward_gap / (2000 / 6), 0.0, 1.0, 1.0]
    return np.stack([row, row.copy()])


class PlannerLateralGeometryTests(unittest.TestCase):
    def test_tables_are_protocol_specific(self):
        self.assertNotEqual(PLANNER_GEOMETRY['corrected_v2'], PLANNER_GEOMETRY['legacy_v1'])
        for table in PLANNER_GEOMETRY.values():
            self.assertLess(table['lane_free'], table['edge'])

    def test_corrected_thresholds_clear_the_environment_lane_spacing(self):
        table = PLANNER_GEOMETRY['corrected_v2']
        self.assertGreater(table['pass_open'], ENV_LATERAL_SPACING_HALF_WIDTHS)
        self.assertGreater(table['edge'], ENV_LATERAL_SPACING_HALF_WIDTHS)

    def test_a_side_by_side_pass_is_not_zeroed_under_corrected_units(self):
        p = planner('corrected_v2')
        gap = 8.0
        _, _, _, _, _ = p._state_quality_terms(obs(gap, forward_gap=gap), obs(gap, forward_gap=gap - 2.0), 0)
        overtake, lane_penalty, grass_penalty, _, _ = p._state_quality_terms(
            obs(ENV_LATERAL_SPACING_HALF_WIDTHS, forward_gap=gap),
            obs(ENV_LATERAL_SPACING_HALF_WIDTHS, forward_gap=gap - 3.0),
            0,
        )
        self.assertGreater(overtake, 0.0, 'a lane-width offset must not cancel the overtake score')
        self.assertLess(grass_penalty, 1.0)

    def test_at_the_road_edge_the_overtake_credit_is_withdrawn(self):
        p = planner('corrected_v2')
        edge = PLANNER_GEOMETRY['corrected_v2']['edge']
        overtake, _, _, _, _ = p._state_quality_terms(
            obs(edge + 0.05, forward_gap=8.0), obs(edge + 0.05, forward_gap=5.0), 0)
        self.assertLessEqual(overtake, 0.0)

    def test_legacy_thresholds_are_unchanged(self):
        p = planner('legacy_v1')
        self.assertEqual(p.planner_geometry, PLANNER_GEOMETRY['legacy_v1'])
        # a legacy offset of 0.5 could never be recorded, but the inherited
        # constant must still be the one that ships for archive reproduction
        self.assertEqual(p.planner_geometry['edge'], 0.46)


if __name__ == '__main__':
    unittest.main()
