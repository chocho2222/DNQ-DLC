"""Exact-replay physical audit for one corrected mixed-controller pilot case."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pyglet
pyglet.options['headless'] = True
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dlc.rollout import make_env
from dlc.overtaking_endpoint import EndpointConfig, TrackProgress


def polygons(car):
    return [Polygon([body.GetWorldPoint(v) for v in fixture.shape.vertices])
            for body in [car.hull, *car.wheels] for fixture in body.fixtures]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--case', type=Path, required=True)
    p.add_argument('--target-agent', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    case = args.case.resolve()
    suite_path = next(case.glob('mixed_suite_n*_seed*.json'))
    suite = json.loads(suite_path.read_text())
    a = suite['args']
    trace = json.loads((case / 'traces' / f"mixed_n{a['num_agents']}_seed{a['seed']}_target{a['target_agent']}.trace.json").read_text())
    n, ego, seed = int(a['num_agents']), int(args.target_agent), int(a['seed'])
    env = make_env(num_agents=n, seed=seed, observation_type='telemetry_dynamic',
                   start_order=list(range(n)), line_spacing=a['line_spacing'],
                   lateral_spacing=a['lateral_spacing'], telemetry_version='corrected_v2',
                   neighbor_order='identity', max_neighbors=3)
    e = env.unwrapped
    env.reset()
    reset_positions = [list(c.hull.position) for c in e.cars]
    initial_contacts = [dict(c) for c in e.vehicle_contacts.snapshot(e.world) if ego in c['agents']]
    road_surface = unary_union(e.road_poly_shapely).buffer(1e-7)
    road = prep(road_surface)
    progress = TrackProgress(np.asarray(e.track)[:, 2:])
    initial = progress.update([list(c.hull.position) for c in e.cars])
    initial_gap = (initial - initial[ego] + progress.length / 2) % progress.length - progress.length / 2
    targets = [i for i, gap in enumerate(initial_gap) if i != ego and 6.0 <= gap <= 60.0]
    contained = []
    contact_steps = []
    positions = []
    try:
        for row in trace:
            action = np.asarray(row['action'], dtype=np.float32)
            env.step(action)
            positions.append([list(c.hull.position) for c in e.cars])
            contained.append(all(road.covers(poly) for poly in polygons(e.cars[ego])))
            contact_steps.append([dict(c) for c in e.vehicle_contacts.snapshot(e.world) if ego in c['agents']])
        lead_retained = False
        retained_target = None
        held = {t: 0 for t in targets}
        ep = TrackProgress(np.asarray(e.track)[:, 2:])
        p0 = ep.update(reset_positions)
        for step, pos in enumerate(positions, 1):
            pp = ep.update(pos)
            for t in targets:
                gap = pp[ego] - pp[t] - (p0[ego] - p0[t])
                held[t] = held[t] + 1 if gap >= 6.0 else 0
                if held[t] >= 50:
                    lead_retained = True; retained_target = t
        result = {
            'case_id': case.name, 'seed': seed, 'num_agents': n, 'target_agent': ego,
            'targets_initial_gap_6_60': targets, 'initial_gaps': initial_gap.tolist(),
            'steps': len(trace), 'initial_contacts': initial_contacts,
            'initial_contact_count': len(initial_contacts),
            'target_contact_steps': int(sum(bool(x) for x in contact_steps)),
            'target_contact_free_after_reset': not any(contact_steps),
            'target_contact_free_entire_episode': not initial_contacts and not any(contact_steps),
            'target_full_vehicle_contained_entire_episode': bool(all(contained)),
            'target_outside_steps': int(sum(not x for x in contained)),
            'lead_retained_50_steps': bool(lead_retained), 'retained_target': retained_target,
            'contact_free_ontrack_retained': bool(lead_retained and not initial_contacts and not any(contact_steps) and all(contained)),
            'contact_pairs': sorted({tuple(c['agents']) for row in contact_steps for c in row}),
            'evidence': 'exact replay of saved actions; development pilot, not confirmatory'
        }
    finally:
        env.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
