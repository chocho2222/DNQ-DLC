"""Episode-level development evidence, preserving failures and candidate diagnostics."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', nargs='+', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    rows, phase_rows, matched, hashes = [], [], {}, {}
    for source in args.sources:
        summaries = json.loads((source/'summary.json').read_text())
        for summary in summaries:
            case = source/summary['case_id']
            raw = {}
            for name in ['summary.json', 'trace.json', 'initial.json']:
                path = case/name
                content = path.read_bytes()
                hashes[str(path.resolve())] = hashlib.sha256(content).hexdigest()
                raw[name] = json.loads(content)
            trace, initial = raw['trace.json'], raw['initial.json']
            key = (summary['seed'], summary['num_agents'])
            state = {k: initial[k] for k in ['track', 'positions', 'hull_angles', 'obs']}
            if key in matched and state != matched[key]:
                raise ValueError(f'Unmatched initial state: {case}')
            matched[key] = state
            ego = summary['num_agents']-1
            endpoint = summary.get('endpoint', {})
            target_ids = endpoint.get('target_ids', [])
            case_id = source.name+'/'+summary['case_id']
            contacts = np.array([any(ego in c['agents'] for c in r['contacts']) for r in trace])
            speeds = np.array([r['obs'][ego][4]*50 for r in trace])
            grass = np.array([r['obs'][ego][15] > .5 for r in trace])
            closest_gaps = [min(np.linalg.norm(np.asarray(r['positions'])[j]-np.asarray(r['positions'])[ego])
                               for j in range(ego)) for r in trace]
            debug = [r.get('planner_debug') or {} for r in trace]
            events = endpoint.get('events', [])
            target = events[0]['target'] if events else (target_ids[-1] if target_ids else None)
            center = np.asarray(initial['track'])[:, 2:]
            total = float(np.linalg.norm(np.roll(center, -1, axis=0)-center, axis=1).sum())
            phases = []
            # Diagnostic phase thresholds only. They do not redefine completion.
            for r in trace:
                if target is None:
                    phase = 'ineligible'
                else:
                    progress = r['progress_s']
                    # Progress is unwrapped by the collector. Align its initial lap.
                    gap = (progress[target]-progress[ego]+total/2) % total-total/2
                    phase = ('approach' if gap > 30 else 'closing' if gap > 6 else
                             'side_by_side' if gap >= -6 else 'post_pass_stabilization')
                phases.append(phase)
            first_contact = int(np.flatnonzero(contacts)[0]) if contacts.any() else None
            selected_lanes = [r.get('selected', {}).get('lane') for r in debug]
            considered = [tuple(o['id'] for o in r.get('opponents', [])) for r in debug]
            row = {'case_id': case_id, 'method': summary['method'], 'variant': summary['variant'],
                'seed': summary['seed'], 'num_agents': summary['num_agents'], 'status': summary['status'],
                'steps': len(trace), 'eligible': endpoint.get('eligible', False),
                'lead_retained_completion': endpoint.get('lead_retained_completion', False),
                'contact_free_completion': endpoint.get('contact_free_completion', False),
                'center_ontrack_contact_free_completion': endpoint.get('center_ontrack_contact_free_completion', False),
                'contact_any': bool(contacts.any()), 'contact_steps': int(contacts.sum()),
                'grass_fraction_observed_steps': float(grass.mean()) if len(trace) else None,
                'speed_mean_observed_steps': float(speeds.mean()) if len(trace) else None,
                'minimum_center_distance': min(closest_gaps) if closest_gaps else None,
                'first_contact_step': first_contact+1 if first_contact is not None else None,
                'first_contact_phase': phases[first_contact] if first_contact is not None else None,
                'success_conditioned_retention_time_s': min(e['retained_step'] for e in events)/50 if events else None,
                'stopped_steps_speed_lt_1': int((speeds < 1).sum()),
                'no_feasible_candidate_steps': sum(bool(d.get('no_feasible_candidate')) for d in debug),
                'lane_changes_gt_1_unit': sum(a is not None and b is not None and abs(a-b)>1 for a,b in zip(selected_lanes, selected_lanes[1:])),
                'considered_opponent_set_changes': sum(a != b for a,b in zip(considered, considered[1:])),
                'termination': summary.get('termination')}
            rows.append(row)
            for phase in sorted(set(phases)):
                indices = np.array([p == phase for p in phases])
                phase_rows.append({'case_id': case_id, 'phase': phase, 'diagnostic_target_id': target,
                    'steps': int(indices.sum()), 'duration_s': int(indices.sum())/50,
                    'contact_steps': int(contacts[indices].sum()),
                    'grass_steps': int(grass[indices].sum()),
                    'speed_mean': float(speeds[indices].mean()),
                    'scope': 'post-hoc diagnostic target; phases are not independent outcomes'})
    write_csv(args.out/'episode_metrics.csv', rows)
    write_csv(args.out/'phase_diagnostics.csv', phase_rows)
    groups = []
    for method, variant in sorted({(r['method'], r['variant']) for r in rows}):
        group = [r for r in rows if (r['method'],r['variant']) == (method,variant)]
        groups.append({'method': method, 'variant': variant, 'n': len(group),
            **{k: sum(r[k] for r in group) for k in ['lead_retained_completion','contact_free_completion',
                'center_ontrack_contact_free_completion','contact_any']},
            'mean_grass_fraction': float(np.mean([r['grass_fraction_observed_steps'] for r in group])),
            'total_no_feasible_steps': sum(r['no_feasible_candidate_steps'] for r in group),
            'total_stopped_steps': sum(r['stopped_steps_speed_lt_1'] for r in group)})
    result = {'scope': 'descriptive development; no DNQ attribution or significance claim',
        'matched_initial_states_verified': True, 'matched_seed_density_pairs': len(matched),
        'groups': groups, 'source_sha256': hashes,
        'phase_limits': 'Threshold-based diagnostics, eventual passed target or last eligible target; target selection uses outcome for description only.',
        'units': 'simulator world units, seconds; center distance is not body clearance',
        'metrics_scope': 'Contact and grass cover observed steps; completion time is success-conditioned. Natural early endings retained.'}
    (args.out/'summary.json').write_text(json.dumps(result, indent=2))
    (args.out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps({k:v for k,v in result.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    main()
