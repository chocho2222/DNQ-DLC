"""Save regression logs and exact dataset inclusion checks for the development stage."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True, type=Path)
    a = p.parse_args()
    out = a.root/'verification'
    out.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[1]
    commands = [[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v']
                for pattern in ['test_corrected*.py','test_joint_clearance.py','test_contact_guard.py','test_training_packing.py']]
    commands += [[sys.executable, '-c', "import runpy; runpy.run_path('tests/test_algorithm_colors.py', run_name='__main__')"],
                 [sys.executable, 'scripts/check_legacy_contact_replay.py']]
    checks = []
    for i, command in enumerate(commands):
        r = subprocess.run(command, cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out/f'check_{i}.log').write_text(r.stdout)
        checks.append({'command': command, 'exit_code': r.returncode})
    source = a.root/'pilot_training_data'
    model = a.root/'graph_model_pilot_cached'
    inputs = json.loads((model/'dataset_inputs.json').read_text())
    for path, expected in inputs['transitions_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    training = json.loads((source/'collection_summary.json').read_text())
    model_summary = json.loads((model/'train_summary.json').read_text())
    assert sum(r['steps'] for r in training) == model_summary['transitions'] == inputs['transitions']
    assert len(training) == model_summary['episodes'] == 8
    development = json.loads((a.root/'fresh_validation_v2/summary.json').read_text())
    assert {r['seed'] for r in training}.isdisjoint({r['seed'] for r in development})
    (out/'dataset_integrity.json').write_text(json.dumps({
        'all_saved_transition_hashes_match_fitted_inputs': True,
        'training_development_seed_sets_disjoint': True,
        'episodes': len(training), 'transitions': model_summary['transitions'],
        'failure_episodes_removed': 0,
        'fixed_final_update': model_summary['loss_final']['step'],
        'scope': 'pilot fit; no formal test-set or checkpoint-selection claim'}, indent=2))
    (out/'checks.json').write_text(json.dumps(checks, indent=2))
    print(json.dumps(checks, indent=2))
    if any(r['exit_code'] for r in checks):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
