"""Exact replay audit for the archived mixed-controller E4 tournament."""
import json
import sys
from pathlib import Path

import numpy as np
import pyglet
pyglet.options['headless'] = True
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dlc.rollout import make_env


def vehicle_polygons(car):
    return [Polygon([body.GetWorldPoint(vertex) for vertex in fixture.shape.vertices])
            for body in [car.hull, *car.wheels] for fixture in body.fixtures]


def audit_case(summary_path):
    summary_path = Path(summary_path)
    summary = json.loads(summary_path.read_text())
    trace_path = Path(summary['trace_path'])
    trace = json.loads(trace_path.read_text())
    suite_path = summary_path.parent.parent / (
        f"mixed_suite_n{summary['num_agents']}_seed{summary['seed']}.json")
    args = json.loads(suite_path.read_text())['args']
    env = make_env(
        num_agents=summary['num_agents'], seed=summary['seed'],
        observation_type=args['observation_type'],
        start_order=list(range(summary['num_agents'])),
        line_spacing=args['line_spacing'], lateral_spacing=args['lateral_spacing'],
        track_path=args['track_path'], max_neighbors=args['max_neighbors'])
    try:
        env.reset()
        e = env.unwrapped
        road_surface = unary_union(e.road_poly_shapely).buffer(1e-7)
        road = prep(road_surface)
        max_error = 0.0
        pair_steps = {}
        pair_first = {}
        target = summary.get('target_agent', summary['num_agents'] - 1)
        target_contained = []
        target_outside_area = []
        for step, row in enumerate(trace, 1):
            env.step(np.asarray(row['action'], dtype=np.float32))
            positions = np.asarray([list(car.hull.position) for car in e.cars])
            max_error = max(max_error, float(np.max(np.abs(positions - np.asarray(row['positions'])))))
            for contact in e.vehicle_contacts.snapshot(e.world):
                pair = str(tuple(contact['agents']))
                pair_steps[pair] = pair_steps.get(pair, 0) + 1
                pair_first.setdefault(pair, step)
            polygons = vehicle_polygons(e.cars[target])
            contained = all(road.covers(polygon) for polygon in polygons)
            target_contained.append(contained)
            target_outside_area.append(0.0 if contained else float(
                unary_union(polygons).difference(road_surface).area))
        target_contact_steps = sum(
            count for pair, count in pair_steps.items()
            if target in tuple(int(item) for item in pair[1:-1].split(', ') if item))
        return {
            'case': summary_path.parent.parent.name,
            'seed': summary['seed'],
            'assignment': summary['assignment'],
            'target_agent': target,
            'target_success_old_endpoint': summary.get('overtake_success'),
            'rank_gain': summary.get('rank_gain'),
            'steps': len(trace),
            'max_position_error': max_error,
            'pair_contact_steps': pair_steps,
            'pair_first_contact': pair_first,
            'target_contact_steps': target_contact_steps,
            'target_full_vehicle_contained_entire_episode': bool(all(target_contained)),
            'target_full_vehicle_outside_steps': int(sum(not item for item in target_contained)),
            'target_maximum_outside_area': float(max(target_outside_area, default=0.0)),
            'corrected_target_contact_free_and_contained': bool(
                not target_contact_steps and all(target_contained)),
        }
    finally:
        env.close()


def main():
    root = ROOT / 'outputs/tits_dynamic_graph_expanded/e4_four_controller_race_no_background'
    paths = sorted(root.glob('**/summaries/*.summary.json'))
    rows = []
    for path in paths:
        row = audit_case(path)
        rows.append(row)
        print(json.dumps(row), flush=True)
    out = root / 'corrected_contact_audit.json'
    out.write_text(json.dumps(rows, indent=2))
    print(json.dumps({'output': str(out), 'cases': len(rows)}))


if __name__ == '__main__':
    main()
