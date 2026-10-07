"""Regression: new contact instrumentation must preserve archived physics."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pyglet
pyglet.options['headless'] = True
import numpy as np
from dlc.rollout import make_env


def main():
    root = ROOT/'outputs/contact_audit_20260910'
    d = json.loads((root/'episodes/n4_seed101_v6_runtime_dynamic_neighborhood_safe.json').read_text())
    s = json.loads(Path(d['summary_path']).read_text())
    trace = json.loads(Path(d['trace_path']).read_text())
    suite = json.loads(next(Path(d['summary_path']).parent.parent.glob('online_suite*.json')).read_text())['args']
    env = make_env(num_agents=4, seed=101, observation_type='telemetry_dynamic', start_order=s['start_order'],
                   line_spacing=suite['line_spacing'], lateral_spacing=suite['lateral_spacing'], max_neighbors=3)
    error, contacts = 0, 0
    try:
        env.reset()
        for r in trace:
            _, _, _, info = env.step(np.asarray(r['action'], dtype=np.float32))
            positions = np.asarray([list(c.hull.position) for c in env.unwrapped.cars])
            error = max(error, float(np.max(np.abs(positions - r['positions']))))
            contacts += any(3 in c['agents'] for c in info['vehicle_contacts'])
    finally:
        env.close()
    result = {'steps': len(trace), 'max_position_error': error, 'ego_contact_steps': contacts,
              'archived_audit_contact_steps': d['ego_contact_steps']}
    assert error == 0 and contacts == d['ego_contact_steps'], result
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
