"""Paired development diagnostics; two seeds do not support efficacy claims."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def main(source, out, additional=()):
    out.mkdir(parents=True, exist_ok=False)
    summaries = [(root, s) for root in [source, *additional]
                 for s in json.loads((root/'summary.json').read_text())]
    inputs, rows, initial_by_key = {}, [], {}
    for root, s in summaries:
        case = root/s['case_id']
        paths = [case/'summary.json', case/'trace.json', case/'initial.json']
        for p in paths:
            inputs[str(p.resolve())] = hashlib.sha256(p.read_bytes()).hexdigest()
        trace = json.loads(paths[1].read_text())
        initial = json.loads(paths[2].read_text())
        key = (s['seed'], s['num_agents'], s['method'])
        geometry = {k: initial[k] for k in ['track', 'positions', 'hull_angles', 'obs']}
        if key in initial_by_key and geometry != initial_by_key[key]:
            raise ValueError(f'Matching failed: {key}')
        initial_by_key[key] = geometry
        ego = s['num_agents']-1
        endpoint = s['endpoint']
        contact = [any(ego in c['agents'] for c in r['contacts']) for r in trace]
        e = endpoint['events']
        rows.append({
            'case_id': root.name+'/'+s['case_id'], 'seed': s['seed'], 'num_agents': s['num_agents'],
            'method': s['method'], 'variant': s['variant'], 'status': s['status'],
            'termination': s['termination'], 'steps': len(trace),
            'eligible': endpoint['eligible'], 'target_ids': json.dumps(endpoint['target_ids']),
            'lead_retained_completion': endpoint['lead_retained_completion'],
            'contact_free_completion': endpoint['contact_free_completion'],
            'center_ontrack_contact_free_completion': endpoint['center_ontrack_contact_free_completion'],
            'ego_contact_any': any(contact), 'ego_contact_steps': sum(contact),
            'contact_exposure_seconds': sum(contact)/50,
            'all_case_center_grass_fraction': float(np.mean([r['obs'][ego][15] > .5 for r in trace])) if trace else None,
            'mean_speed_observed_steps': float(np.mean([r['obs'][ego][4]*50 for r in trace])) if trace else None,
            'guard_intervention_steps': sum(bool((r.get('contact_guard') or {}).get('active')) for r in trace),
            'success_conditioned_retention_time_s': min(v['retained_step'] for v in e)/50 if e else None,
            'observed_duration_s': len(trace)/50})
    with (out/'episode_metrics.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    grouped = []
    for method in sorted({r['method'] for r in rows}):
        for variant in sorted({r['variant'] for r in rows}):
            group = [r for r in rows if r['method'] == method and r['variant'] == variant]
            grouped.append({'method': method, 'variant': variant, 'n': len(group),
                **{k: sum(r[k] for r in group) for k in ['eligible', 'lead_retained_completion',
                    'contact_free_completion', 'center_ontrack_contact_free_completion', 'ego_contact_any']},
                'mean_contact_steps': float(np.mean([r['ego_contact_steps'] for r in group])),
                'mean_center_grass_fraction': float(np.mean([r['all_case_center_grass_fraction'] for r in group]))})
    result = {'scope': 'descriptive development only; 2 shared seeds across vehicle counts, not independent map replications',
              'matching': 'exact initial map, poses and full observations verified for every guard pair',
              'episodes': len(rows), 'paired_cases': len(initial_by_key), 'groups': grouped,
              'limitations': ['No DNQ checkpoint evaluated in this comparison.',
                'Guard is an explicitly new intervention, not a retroactive relabeling of the archived method.',
                'Episode duration can differ after environment termination; contact counts are observed-duration outcomes.',
                'On-track metric uses center-point grass flag, not entire vehicle containment.',
                'No statistical significance tests or confirmatory inference from this pilot.'],
              'source_sha256': inputs}
    (out/'summary.json').write_text(json.dumps(result, indent=2))
    (out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--additional', nargs='*', default=[], type=Path)
    a = p.parse_args()
    main(a.source, a.out, a.additional)
