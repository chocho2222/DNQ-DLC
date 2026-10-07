"""Diagnose training labels and executed control paths without changing endpoints."""
import argparse
import csv
import json
import hashlib
from pathlib import Path
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--evaluation', type=Path, nargs='+', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    training, execution, hashes = [], [], {}
    for case in sorted((args.dataset/'raw').glob('episode_*')):
        summary = json.loads((case/'summary.json').read_text())
        path = case/'transitions.npz'
        hashes[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
        with np.load(path) as data:
            risk = data['risk'][:, -1] > .5
            obs = data['next_obs'][:, -1]
            grass = obs[:, 15] > .5
            reverse = obs[:, 16] > .5
            lateral = np.abs(obs[:, 12])
            training.append({'episode': summary['episode'], 'seed': summary['seed'], 'steps': len(risk),
                'contact_free_retained_completion': summary['endpoint']['contact_free_completion'],
                'whole_episode_ego_contact': summary['endpoint']['ego_contact_any'],
                'risk_positive_steps': int(risk.sum()),
                'risk_positive_with_no_center_grass_or_reverse': int((risk & ~grass & ~reverse).sum()),
                'lateral_above_default_hard_recovery_0p62': int((lateral > .62).sum()),
                'risk_label': 'grass OR reverse OR abs(normalized_lateral)>0.45; not physical contact'})
    for root in args.evaluation:
        for summary in json.loads((root/'summary.json').read_text()):
            case = root/summary['case_id']
            path = case/'trace.json'
            hashes[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
            trace = json.loads(path.read_text())
            debug = [r.get('planner_debug') or {} for r in trace]
            first_event = min((e['retained_step'] for e in summary['endpoint']['events']), default=None)
            ego = summary['num_agents']-1
            execution.append({'source': root.name, 'case_id': summary['case_id'],
                'method': summary['method'], 'status': summary['status'], 'steps': len(trace),
                'contact_free_retained_completion': summary['endpoint']['contact_free_completion'],
                'ego_contact_any': summary['endpoint']['ego_contact_any'],
                'center_grass_any': summary['endpoint']['ego_center_offtrack_any'],
                'hard_recovery_steps': sum(bool(d.get('hard_recovery', False)) for d in debug),
                'candidate_ranking_steps': sum(d.get('candidate_count', 0) > 0 for d in debug),
                'post_retention_contact_steps': sum(r['step'] > first_event and any(ego in c['agents'] for c in r['contacts'])
                     for r in trace) if first_event is not None else None,
                'decision_mean_ms': float(np.mean([r['latency_s']*1000 for r in trace])) if trace else None,
                'scope': 'observed episode diagnostic; failed or superseded runs retained under source name'})
    for name, rows in [('training_labels.csv',training), ('executed_control_paths.csv',execution)]:
        with (args.out/name).open('w',newline='') as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    result = {'training_steps': sum(r['steps'] for r in training),
        'risk_positive_steps': sum(r['risk_positive_steps'] for r in training),
        'risk_positive_without_center_grass_or_reverse': sum(r['risk_positive_with_no_center_grass_or_reverse'] for r in training),
        'teacher_steps_above_default_recovery_threshold': sum(r['lateral_above_default_hard_recovery_0p62'] for r in training),
        'interpretation': 'Lateral proxy and recovery thresholds can oppose on-track passing offsets. Counts do not establish causal attribution or real collision prediction.',
        'source_sha256': hashes}
    (args.out/'summary.json').write_text(json.dumps(result, indent=2))
    (args.out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps({k:v for k,v in result.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    main()
