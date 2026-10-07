"""Preserve implementation checks and smoke inference separately from efficacy."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pyglet
pyglet.options['headless'] = True
import numpy as np
from dlc.graph_world_model import GraphWorldModelPolicy
from dlc.rollout import make_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--smoke-model', required=True, type=Path)
    parser.add_argument('--colors-only', action='store_true')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    color_command = [sys.executable, '-c', "import runpy; runpy.run_path('tests/test_algorithm_colors.py', run_name='__main__')"]
    if args.colors_only:
        result = subprocess.run(color_command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (args.out/'rendered_color_checks.log').write_text(result.stdout)
        (args.out/'checks.json').write_text(json.dumps({'command': color_command, 'exit_code': result.returncode,
            'correction': 'Color tests are function-based; unittest discovery previously ran zero of them.'}, indent=2))
        print(result.stdout)
        raise SystemExit(result.returncode)
    checks = []
    for pattern in ['test_corrected*.py', 'test_contact_guard.py', 'test_training_packing.py']:
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v']
        result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (args.out/(pattern.replace('*', 'all')+'.log')).write_text(result.stdout)
        checks.append({'command': command, 'exit_code': result.returncode})
    result = subprocess.run(color_command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (args.out/'rendered_color_checks.log').write_text(result.stdout)
    checks.append({'command': color_command, 'exit_code': result.returncode})
    model = GraphWorldModelPolicy(args.smoke_model, device='cpu', max_neighbors=3,
                                 planner_horizon=2, planner_candidates=3)
    if model.bundle.meta.get('data_split') != 'development_smoke':
        raise ValueError('This verification is only for the separately marked smoke checkpoint')
    env = make_env(num_agents=4, seed=920003, telemetry_version='corrected_v2',
                   neighbor_order='identity', observation_type='telemetry_dynamic')
    records = []
    try:
        obs = env.reset()
        for step in range(3):
            action = model.act(env, obs)
            assert np.isfinite(action).all()
            records.append({'step': step, 'obs': obs.tolist(), 'action': action.tolist(),
                            'decision_debug': model.last_decision_debug})
            obs, _, _, _ = env.step(action)
    finally:
        env.close()
    rejected = False
    try:
        GraphWorldModelPolicy(args.smoke_model, device='cpu', learned_quality_weight=1.)
    except ValueError as error:
        rejected = 'untrained quality head' in str(error)
    assert rejected
    (args.out/'inference_smoke.json').write_text(json.dumps({'records': records,
        'inactive_quality_head_rejected': rejected, 'model_sha256': hashlib.sha256(args.smoke_model.read_bytes()).hexdigest(),
        'scope': '3-step implementation smoke; no performance conclusions'}, indent=2))
    regression = subprocess.run([sys.executable, 'scripts/check_legacy_contact_replay.py'], cwd=ROOT,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (args.out/'legacy_physics_regression.log').write_text(regression.stdout)
    checks.append({'command': 'check_legacy_contact_replay.py', 'exit_code': regression.returncode})
    (args.out/'checks.json').write_text(json.dumps(checks, indent=2))
    for p in [*sorted((ROOT/'dlc').glob('*.py')), *sorted((ROOT/'tests').glob('test_corrected*.py')),
              ROOT/'tests/test_training_packing.py', ROOT/'tests/test_contact_guard.py',
              ROOT/'scripts/train_graph_risk_world_model.py', Path(__file__).resolve()]:
        target = args.out/'source'/p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
    print(json.dumps(checks, indent=2))
    if any(c['exit_code'] for c in checks):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
