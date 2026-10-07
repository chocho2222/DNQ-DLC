"""Replay saved controls to audit complete hull/wheel road containment.

Only exact pose/contact replay yields verified results. No policy is rerun or
retuned. Original center-grass endpoints remain unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pyglet
pyglet.options['headless'] = True
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.prepared import prep
from dlc.rollout import make_env
from scripts.tits_figure_style import bind_algorithm_colors


def vehicle_polygons(car):
    return [Polygon([body.GetWorldPoint(v) for v in fixture.shape.vertices])
            for body in [car.hull, *car.wheels] for fixture in body.fixtures]


def run(source, out, summary, capture_frames=False):
    case = source/summary['case_id']
    dest = out/case.name
    dest.mkdir()
    initial = json.loads((case/'initial.json').read_text())
    trace = json.loads((case/'trace.json').read_text())
    n, ego = summary['num_agents'], summary['num_agents']-1
    env = make_env(num_agents=n, seed=summary['seed'], observation_type='telemetry_dynamic',
                   start_order=list(range(n)), line_spacing=5, lateral_spacing=3.0,
                   telemetry_version='corrected_v2', neighbor_order='identity')
    record = {'case_id': summary['case_id'], 'method': summary['method'], 'seed': summary['seed'],
              'num_agents': n, 'status': 'unverified', 'tolerance_world_units': 1e-7,
              'original_endpoint': summary['endpoint'],
              'source_sha256': {name: hashlib.sha256((case/name).read_bytes()).hexdigest()
                                for name in ['trace.json', 'summary.json', 'initial.json']}}
    contained, outside_area, poses = [], [], []
    screenshot_steps = {}
    if capture_frames:
        events = summary['endpoint']['events']
        screenshot_steps[1] = 'approach'
        if events:
            event = events[0]
            target = event['target']
            xy = np.asarray(initial['track'])[:, 2:]
            length = float(np.linalg.norm(np.roll(xy, -1, axis=0)-xy, axis=1).sum())
            side = min(trace[:event['pass_step']], key=lambda r:
                abs((r['progress_s'][target]-r['progress_s'][ego]+length/2) % length-length/2))
            screenshot_steps[side['step']] = 'side_by_side'
            screenshot_steps[event['pass_step']] = 'pass_margin_reached'
            screenshot_steps[event['retained_step']] = 'lead_retention_complete'
        first_contact = next((r['step'] for r in trace if any(ego in c['agents'] for c in r['contacts'])), None)
        if first_contact is not None:
            screenshot_steps[max(1, first_contact-25)] = 'before_first_contact'
            screenshot_steps[first_contact] = 'first_contact'
            screenshot_steps[min(len(trace), first_contact+25)] = 'after_first_contact'
    try:
        env.reset()
        e = env.unwrapped
        bind_algorithm_colors(env, [r['algorithm'] for r in initial['colors']])
        np.testing.assert_array_equal(np.asarray(e.track), np.asarray(initial['track']))
        np.testing.assert_array_equal([list(c.hull.position) for c in e.cars], initial['positions'])
        surface = unary_union(e.road_poly_shapely).buffer(1e-7)
        prepared = prep(surface)

        def capture():
            polys = vehicle_polygons(e.cars[ego])
            inside = all(prepared.covers(p) for p in polys)
            contained.append(inside)
            outside_area.append(0. if inside else float(unary_union(polys).difference(surface).area))
            poses.append([[float(b.position[0]), float(b.position[1]), float(b.angle)]
                          for b in [e.cars[ego].hull, *e.cars[ego].wheels]])

        capture()
        max_error = 0.
        for index, row in enumerate(trace, 1):
            if row['step'] != index:
                raise ValueError('Nonconsecutive trace')
            action = np.asarray(row['action'], dtype=np.float32)
            for i, car in enumerate(e.cars):
                car.steer(-action[i, 0]); car.gas(action[i, 1]); car.brake(action[i, 2])
            e.vehicle_contacts.clear_step()
            for car in e.cars:
                car.step(1/50)
            e.world.Step(1/50, 180, 60)
            e.t += 1/50
            positions = np.asarray([list(c.hull.position) for c in e.cars])
            error = float(np.max(np.abs(positions-row['positions'])))
            max_error = max(max_error, error)
            if error > 1e-6:
                raise ValueError(f'Pose mismatch at step {index}: {error}')
            np.testing.assert_allclose([float(c.hull.angle) for c in e.cars], row['hull_angles'], atol=1e-6, rtol=0)
            actual = {tuple(c['agents']) for c in e.vehicle_contacts.snapshot(e.world)}
            expected = {tuple(c['agents']) for c in row['contacts']}
            if actual != expected:
                raise ValueError(f'Contact mismatch at step {index}')
            capture()
            if index in screenshot_steps:
                from PIL import Image
                # Native simulator rendering. No pose or trajectory is altered.
                frame = e._render_window(ego, 'rgb_array')
                label = screenshot_steps[index]
                Image.fromarray(frame).save(dest/f'{index:05d}_{label}.png')
                (dest/f'{index:05d}_{label}.json').write_text(json.dumps({
                    'case_id': summary['case_id'], 'seed': summary['seed'], 'step': index,
                    'label': label, 'camera': 'native simulator ego-centered overhead view',
                    'ego_id': ego, 'initial_eligible_targets': summary['endpoint']['target_ids'],
                    'color_assignment': e.algorithm_color_assignment, 'recorded_step': row,
                    'scope': 'raw representative development image; not an estimate of overall performance'}, indent=2))
        contained_array = np.asarray(contained, dtype=bool)
        event_results = [{'target': event['target'], 'retained_step': event['retained_step'],
                         'full_vehicle_ontrack_contact_free': bool(event['contact_free'] and
                            contained_array[:event['retained_step']+1].all())}
                        for event in summary['endpoint']['events']]
        record.update(status='verified_exact', max_position_error=max_error, steps=len(trace),
                      full_vehicle_contained_entire_episode=bool(contained_array.all()),
                      outside_steps=int((~contained_array[1:]).sum()),
                      outside_fraction_observed_steps=float((~contained_array[1:]).mean()),
                      maximum_outside_area=float(max(outside_area)), events=event_results,
                      full_vehicle_ontrack_contact_free_completion=any(v['full_vehicle_ontrack_contact_free'] for v in event_results))
    except Exception as error:
        record['error'] = repr(error)
    finally:
        env.close()
        np.savez_compressed(dest/'footprint_replay.npz', contained=contained, outside_area=outside_area,
                            hull_and_wheel_poses=poses)
        (dest/'summary.json').write_text(json.dumps(record, indent=2))
    print(json.dumps({k:v for k,v in record.items() if k not in ['source_sha256','original_endpoint','events']}), flush=True)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--method', default='joint_clearance_pilot')
    p.add_argument('--cases', nargs='*')
    p.add_argument('--capture-frames', action='store_true')
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    rows = [r for r in json.loads((args.source/'summary.json').read_text()) if r['method'] == args.method]
    if args.cases:
        rows = [r for r in rows if r['case_id'] in args.cases]
        if len(rows) != len(args.cases):
            raise ValueError('Requested case missing or duplicated')
    from gym.envs.box2d import car_dynamics
    paths = [Path(__file__).resolve(), ROOT/'dlc/rollout.py',
             ROOT/'gym_multi_car_racing/multi_car_racing.py', ROOT/'gym_multi_car_racing/contact_recorder.py',
             Path(car_dynamics.__file__)]
    (args.out/'provenance.json').write_text(json.dumps({
        'source': str(args.source.resolve()), 'method': args.method,
        'scope': 'Post-hoc physical footprint diagnostic, not real-vehicle safety',
        'source_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}, indent=2))
    for path in paths:
        dest = args.out/'source'/path.name
        dest.parent.mkdir(exist_ok=True)
        dest.write_bytes(path.read_bytes())
    results = [run(args.source, args.out, r, args.capture_frames) for r in rows]
    (args.out/'summary.json').write_text(json.dumps(results, indent=2))
    if any(r['status'] != 'verified_exact' for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
