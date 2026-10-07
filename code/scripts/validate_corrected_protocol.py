"""Small closed-loop implementation validation, not algorithm efficacy evidence."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pyglet
pyglet.options['headless'] = True
import numpy as np
from dlc.rollout import make_env
from dlc.overtaking_endpoint import EndpointConfig, OvertakingEndpoint, TrackProgress
from dlc.policies import TelemetryLanePolicy, TelemetryExpertGatePolicy, TelemetryBarrierExpertGatePolicy
from dlc.contact_guard import FrontGapGuard, ContactGuardConfig
from dlc.joint_clearance_pilot import JointClearancePilot, JointClearanceConfig
from dlc.graph_actor_pilot import GraphProposalPilot
from dlc.graph_world_model import GraphWorldModelPolicy
from dlc.physical_quality_pilot import PhysicalQualityPilot, PhysicalQualityConfig
from scripts.tits_figure_style import bind_algorithm_colors


def json_scalar(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f'Unsupported JSON type: {type(value).__name__}')


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, default=json_scalar), encoding='utf-8')


def run_case(out, seed, num_agents, method, steps, guarded=False, pass_offset=None,
             graph_model=None, planner_device='cpu', line_spacing=5,
             lateral_spacing=3.0):
    variant = ('front_gap_guard_wide_pass' if pass_offset is not None else 'front_gap_guard') if guarded else 'unmodified'
    if method == 'joint_clearance_pilot':
        variant = JointClearanceConfig().version
    elif method.startswith('graph_'):
        variant = method+'_corrected_v2'
    case = out / (f'n{num_agents}_seed{seed}_{method}' + ('_guard' if guarded else ''))
    case.mkdir()
    env = make_env(num_agents=num_agents, seed=seed, observation_type='telemetry_dynamic',
                   start_order=list(range(num_agents)), line_spacing=line_spacing,
                   lateral_spacing=lateral_spacing,
                   telemetry_version='corrected_v2', neighbor_order='identity', max_neighbors=None)
    # Gym otherwise truncates at its registered 1000-step default.
    if hasattr(env, '_max_episode_steps'):
        env._max_episode_steps = steps + 1
    ego = num_agents - 1
    assignment = ['background_lane'] * num_agents
    assignment[ego] = method
    bind_algorithm_colors(env, assignment)
    policy = TelemetryExpertGatePolicy() if method == 'rule_expert_gate' else TelemetryBarrierExpertGatePolicy()
    if method == 'joint_clearance_pilot':
        policy = JointClearancePilot()
    elif method == 'graph_actor_pilot':
        policy = GraphProposalPilot(graph_model, device=planner_device)
    elif method == 'graph_dlc_pilot':
        policy = GraphWorldModelPolicy(graph_model, device=planner_device, max_neighbors=3, neighbor_mode='dynamic',
            neighbor_selection_mode='interaction', planner_horizon=4, planner_candidates=18)
    elif method in ['graph_physical_rules_pilot', 'graph_physical_quality_pilot']:
        policy = PhysicalQualityPilot(graph_model, device=planner_device,
            scoring='legacy' if method == 'graph_physical_rules_pilot' else 'physical')
    if pass_offset is not None:
        if not guarded:
            raise ValueError('Wide-pass development variant requires explicit guard')
        for member in [policy, policy.overtake_policy, policy.adaptive_policy]:
            if hasattr(member, 'pass_lane_offset'):
                member.pass_lane_offset = pass_offset
    bg = TelemetryLanePolicy(target_speed=13.0)
    guard = FrontGapGuard() if guarded else None
    config = EndpointConfig(horizon=steps)
    result = {'case_id': case.name, 'split': 'implementation_validation', 'method': method,
              'seed': seed, 'num_agents': num_agents, 'config': asdict(config),
              'variant': variant, 'guard_config': asdict(ContactGuardConfig()) if guarded else None,
              'pass_offset': pass_offset,
              'status': 'error', 'evidence': 'smoke only; no performance inference'}
    trace = []
    stream = (case/'trace.jsonl').open('x')
    endpoint = None
    try:
        obs = env.reset()
        e = env.unwrapped
        policy.reset()
        bg.reset()
        progress = TrackProgress(np.asarray(e.track)[:, 2:])
        initial = progress.update([list(c.hull.position) for c in e.cars])
        endpoint = OvertakingEndpoint(initial, progress.length, ego, config,
                                     e.vehicle_contacts.snapshot(e.world), obs[:, 15], obs[:, 16])
        write_json(case / 'initial.json', {'obs': obs.tolist(), 'track': e.track,
                   'positions': [list(c.hull.position) for c in e.cars],
                   'hull_angles': [float(c.hull.angle) for c in e.cars],
                   'contacts': e.vehicle_contacts.snapshot(e.world),
                   'colors': e.algorithm_color_assignment})
        for step in range(1, steps + 1):
            started = time.perf_counter()
            action = bg.act(env, obs)
            action[ego] = policy.act(env, obs)[ego]
            proposed = action[ego].copy()
            guard_debug = None
            if guard is not None:
                action[ego], guard_debug = guard.apply(obs[ego], proposed,
                    telemetry_version='corrected_v2', masked=True)
            latency = time.perf_counter() - started
            if not np.isfinite(action).all():
                raise ValueError('Nonfinite control')
            obs, reward, done, info = env.step(action)
            positions = [list(c.hull.position) for c in e.cars]
            s = progress.update(positions)
            endpoint.update(step, s, info['vehicle_contacts'], obs[:, 15], obs[:, 16])
            trace.append({'step': step, 'time_s': step/50, 'obs': obs.tolist(),
                          'positions': positions, 'hull_angles': [float(c.hull.angle) for c in e.cars],
                          'velocities': [list(c.hull.linearVelocity) for c in e.cars],
                          'action': action.tolist(), 'reward': reward.tolist(),
                          'progress_s': s.tolist(), 'contacts': info['vehicle_contacts'],
                          'opponent_ids': info['neighbor_ids'], 'latency_s': latency,
                          'proposed_ego_action': proposed.tolist(), 'contact_guard': guard_debug,
                          'planner_debug': getattr(policy, 'last_decision_debug', None),
                          'time_limit_truncated': bool(info.get('TimeLimit.truncated', False)),
                          'done': bool(done)})
            stream.write(json.dumps(trace[-1], default=json_scalar)+'\n')
            stream.flush()
            if done:
                result['termination'] = 'environment_done'
                break
        result.update(status='completed', termination=result.get('termination', 'validation_horizon'))
    except Exception as error:
        result['error'] = repr(error)
    finally:
        stream.close()
        if endpoint is not None:
            result['endpoint'] = endpoint.result()
        write_json(case / 'trace.json', trace)
        write_json(case / 'summary.json', result)
        env.close()
    print(case.name, result['status'], 'steps', len(trace), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--steps', type=int, default=300)
    parser.add_argument('--paired-guard', action='store_true', help='Development comparison only; no learned DNQ model')
    parser.add_argument('--guard-only', action='store_true')
    parser.add_argument('--pass-offset', type=float, default=None, help='Explicit development lane-offset intervention')
    parser.add_argument('--seeds', type=int, nargs='+', default=[910001, 910002])
    parser.add_argument('--methods', nargs='+', choices=['rule_expert_gate', 'rule_safety_gate', 'joint_clearance_pilot',
                                                      'graph_actor_pilot', 'graph_dlc_pilot',
                                                      'graph_physical_rules_pilot', 'graph_physical_quality_pilot'],
                        default=['rule_expert_gate', 'rule_safety_gate'])
    parser.add_argument('--vehicle-counts', nargs='+', type=int, default=[4, 6])
    parser.add_argument('--graph-model')
    parser.add_argument('--planner-device', default='cpu')
    parser.add_argument('--line-spacing', type=int, default=5)
    parser.add_argument('--lateral-spacing', type=float, default=3.0)
    args = parser.parse_args()
    if any(m.startswith('graph_') for m in args.methods) and not args.graph_model:
        parser.error('Learned pilot requires its explicitly versioned --graph-model')
    if 'joint_clearance_pilot' in args.methods and (args.guard_only or args.paired_guard or args.pass_offset is not None):
        parser.error('Joint-clearance pilot is a distinct intervention; do not compose implicit guards')
    if args.pass_offset is not None and not args.guard_only:
        parser.error('--pass-offset requires --guard-only; keep archived baseline configuration intact')
    os.chdir(ROOT)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    method_variants = {}
    for method in args.methods:
        if method == 'joint_clearance_pilot':
            method_variants[method] = [JointClearanceConfig().version]
        elif method.startswith('graph_'):
            method_variants[method] = [method+'_corrected_v2']
        elif args.guard_only:
            method_variants[method] = ['front_gap_guard_wide_pass' if args.pass_offset is not None else 'front_gap_guard']
        else:
            method_variants[method] = ['unmodified', 'front_gap_guard'] if args.paired_guard else ['unmodified']
    files = [ROOT/'gym_multi_car_racing/multi_car_racing.py', ROOT/'gym_multi_car_racing/contact_recorder.py',
             ROOT/'dlc/observation_layout.py', ROOT/'dlc/overtaking_endpoint.py', ROOT/'dlc/policies.py',
             ROOT/'dlc/contact_guard.py', ROOT/'dlc/graph_policy.py', ROOT/'dlc/graph_world_model.py',
             ROOT/'dlc/joint_clearance_pilot.py',
             ROOT/'dlc/graph_actor_pilot.py',
             ROOT/'dlc/physical_quality_pilot.py',
             ROOT/'dlc/rollout.py', ROOT/'scripts/tits_figure_style.py', Path(__file__)]
    snapshot = out/'source'
    snapshot.mkdir()
    hashes = {}
    for p in files:
        content = p.read_bytes()
        dest = snapshot/p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        hashes[str(p.relative_to(ROOT))] = hashlib.sha256(content).hexdigest()
    write_json(out/'protocol.json', {'purpose': __doc__, 'version': 'corrected_v2',
               'endpoint': asdict(EndpointConfig(horizon=args.steps)),
               'seeds': args.seeds, 'vehicle_counts': args.vehicle_counts,
               'joint_clearance_config': asdict(JointClearanceConfig()) if 'joint_clearance_pilot' in args.methods else None,
               'physical_quality_config': asdict(PhysicalQualityConfig()) if any('physical' in m for m in args.methods) else None,
               'graph_model': args.graph_model,
               'graph_model_sha256': hashlib.sha256(Path(args.graph_model).read_bytes()).hexdigest() if args.graph_model else None,
               'planner_device': args.planner_device, 'learned_planner_horizon': 4, 'learned_planner_candidates': 18,
               'learned_neighbor_mode': 'dynamic',
               'variants': list(dict.fromkeys(v for variants in method_variants.values() for v in variants)),
               'guard_only': args.guard_only, 'pass_offset': args.pass_offset,
               'variant_by_method': method_variants,
               'guard_config': asdict(ContactGuardConfig()) if args.paired_guard or args.guard_only else None,
               'gym_time_limit_steps': args.steps + 1,
               'comparison': 'same initial states and background controller rules; reactive trajectories may differ',
               'evidence': 'development only; no test-set inference and no DNQ performance claim',
               'methods': args.methods, 'source_sha256': hashes,
               'python': sys.version, 'platform': platform.platform(),
               'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
               'dirty_worktree': subprocess.check_output(['git', 'status', '--short'], text=True),
               'packages': {p: importlib.metadata.version(p) for p in ['numpy', 'gym', 'pyglet', 'shapely', 'torch']}})
    results = [run_case(out, seed, n, method, args.steps, guarded, args.pass_offset, args.graph_model, args.planner_device,
                        args.line_spacing, args.lateral_spacing)
               for seed in args.seeds
               for n in args.vehicle_counts for method in args.methods
               for guarded in ([True] if args.guard_only else [False, True] if args.paired_guard else [False])]
    write_json(out/'summary.json', results)
    if any(r['status'] != 'completed' for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
