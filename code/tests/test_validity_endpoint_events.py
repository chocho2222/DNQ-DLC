"""Event detection of the validity endpoint.

The endpoint is the paper's measurement instrument, so its own failure modes
matter more than the controllers'. Every case here is built from the geometry
the simulator actually produces: the sparse layout places the front row at
tile ~2 and the rear (ego) row at tile ~274 of a 303-tile lap, i.e. the two rows
straddle the wrap point.
"""
import unittest

import numpy as np

from scripts.audit_validity_endpoint_v3 import (
    circular_delta,
    detect_events,
    track_geometry,
    unwrapped_progress,
)


def circular_track(tiles=303):
    radius = 1064.0 / (2 * np.pi)
    beta = np.linspace(0.0, 2 * np.pi, tiles, endpoint=False)
    points = np.stack([radius * np.cos(beta), radius * np.sin(beta)], axis=1)
    track = np.concatenate([np.zeros((tiles, 1)), beta[:, None], points], axis=1)
    return track, points


def synthetic_trace(start_tile, speed_tiles, steps, tiles=303):
    """Two agents driving forward at a constant tile rate from given tiles."""
    first, second = start_tile if isinstance(start_tile, tuple) else (start_tile, 0)
    positions = [np.array([0.0, 0.0]), np.array([0.0, 0.0])]
    trace = []
    for step in range(steps):
        trace.append({
            "step": step,
            "track_index": [int((first + speed_tiles[0] * step) % tiles),
                            int((second + speed_tiles[1] * step) % tiles)],
            "positions": [p.tolist() for p in positions],
        })
    return trace


class WrapPointTests(unittest.TestCase):
    def test_the_circular_delta_takes_the_short_way_round(self):
        self.assertAlmostEqual(circular_delta(274.0, 2.0, 303.0), -31.0)
        self.assertAlmostEqual(circular_delta(2.0, 274.0, 303.0), 31.0)

    def test_a_pass_between_rows_that_straddle_the_start_line_is_detected(self):
        # Front row at tile 2, ego at tile 274 (the sparse layout). The ego
        # covers ground faster and must be reported as passing the front car.
        track, points = circular_track()
        cumulative, lap, _ = track_geometry(points)
        # 0.6 tiles/step for the front car, 1.2 for the ego.
        trace = synthetic_trace((274, 2), (1.2, 0.6), 260)
        events = detect_events(trace, 0, cumulative, lap, 20.0, 4.0)
        self.assertEqual([e["opponent"] for e in events], [1])
        event = events[0]
        self.assertLess(event["rel"][event["start_index"]], -4.0)
        self.assertGreaterEqual(event["rel"][event["complete_index"]], 4.0)

    def test_a_slower_ego_that_never_passes_produces_no_event(self):
        track, points = circular_track()
        cumulative, lap, _ = track_geometry(points)
        trace = synthetic_trace((274, 2), (0.5, 0.9), 400)
        self.assertEqual(detect_events(trace, 0, cumulative, lap, 20.0, 4.0), [])

    def test_the_initial_displacement_is_the_reported_relative_gap(self):
        track, points = circular_track()
        cumulative, lap, _ = track_geometry(points)
        trace = synthetic_trace((274, 2), (0.0, 0.0), 2)
        target = unwrapped_progress(trace, 0, cumulative, lap)[0]
        other = unwrapped_progress(trace, 1, cumulative, lap)[0]
        offset = (target - other) - circular_delta(target, other, lap)
        self.assertAlmostEqual(target - other - offset, -31.0 * 3.5, delta=1.0)


if __name__ == "__main__":
    unittest.main()
