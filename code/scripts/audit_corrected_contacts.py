"""Extract first-contact precursors from saved v2 development episodes; no filtering."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def audit(source, out):
    out.mkdir(parents=True, exist_ok=False)
    rows, inputs = [], {}
    for summary_path in sorted(source.glob('n*_seed*/summary.json')):
        directory = summary_path.parent
        paths = [summary_path, directory/'initial.json', directory/'trace.json']
        data = [json.loads(p.read_text()) for p in paths]
        for p in paths:
            inputs[str(p.resolve())] = hashlib.sha256(p.read_bytes()).hexdigest()
        summary, initial, trace = data
        ego = summary['num_agents'] - 1
        first = next((i for i, r in enumerate(trace) if any(ego in c['agents'] for c in r['contacts'])), None)
        base = {k: summary[k] for k in ['case_id', 'seed', 'num_agents', 'method', 'status']}
        base['ego_contact_steps'] = sum(any(ego in c['agents'] for c in r['contacts']) for r in trace)
        if first is None:
            rows.append(dict(base, first_contact_step=None))
            continue
        current = trace[first]
        before = initial if first == 0 else trace[first-1]
        pos = np.asarray(before['positions'])
        angle = before['hull_angles'][ego]
        forward = np.array([-np.sin(angle), np.cos(angle)])
        left = np.array([-np.cos(angle), -np.sin(angle)])
        velocities = np.asarray(before.get('velocities', np.zeros_like(pos)))
        for other in sorted({j for c in current['contacts'] if ego in c['agents'] for j in c['agents'] if j != ego}):
            delta = pos[other] - pos[ego]
            closing = -np.dot(velocities[other] - velocities[ego], forward)
            row = dict(base, first_contact_step=current['step'], opponent_id=other,
                       precursor_step=current['step']-1, forward_gap=float(delta@forward),
                       left_gap=float(delta@left), longitudinal_closing_speed=float(closing),
                       ego_steer=current['action'][ego][0], ego_gas=current['action'][ego][1],
                       ego_brake=current['action'][ego][2],
                       opponent_action=json.dumps(current['action'][other]),
                       ego_speed=float(np.linalg.norm(velocities[ego])),
                       geometry_only_contact_class=('front' if delta@forward > 2 else 'rear' if delta@forward < -2 else 'alongside'))
            rows.append(row)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (out/'first_contact_precursors.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (out/'provenance.json').write_text(json.dumps({
        'source_sha256': inputs, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'units': 'simulator world units and seconds; not real-vehicle calibration',
        'scope': 'development diagnosis; geometry class is not fault attribution',
        'episode_count': len({r['case_id'] for r in rows}), 'records': rows}, indent=2))
    (out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    for row in rows:
        print(json.dumps(row))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    audit(args.source, args.out)
