"""Check batched scoring against the scalar reference on retained real states."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pyglet
pyglet.options['headless'] = True
import numpy as np
import torch
from dlc.graph_policy import pack_dynamic_neighbor_obs
from dlc.graph_world_model import GraphWorldModelPolicy, _opponent_fill_vector
from dlc.physical_quality_pilot import PhysicalQualityPilot


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', required=True)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    torch.set_num_threads(1)
    policy = PhysicalQualityPilot(a.model, scoring='legacy')
    assert policy.overtake_aware_planner and not policy.disabled_heads
    assert policy.learned_quality_weight == 0 and not policy._quality_planner_enabled()
    checks = []
    for case in sorted(a.source.glob('n*_joint_clearance_pilot')):
        trace = json.loads((case/'trace.json').read_text())
        for index in [0, 300, 900]:
            raw = np.asarray(trace[index]['obs'], dtype=np.float32)
            obs = pack_dynamic_neighbor_obs(raw, fill=_opponent_fill_vector(policy.bundle),
                target_obs_dim=41, max_neighbors=3, selection_mode='interaction',
                telemetry_version='corrected_v2')
            ego = len(obs)-1
            proposal = policy._proposal_actions(obs)
            bg = policy._make_background_policies(len(obs))
            anchor = policy._background_action(obs, bg)[ego]
            pool = policy._candidate_pool(proposal[ego], anchor, obs[ego])
            policy.scoring = 'legacy'
            batch = policy._score_candidate_pool(obs, proposal, bg, pool, ego)
            scalar = [GraphWorldModelPolicy._score_candidate(policy, obs, proposal, bg, x, ego) for x in pool]
            np.testing.assert_allclose(batch, scalar, rtol=2e-5, atol=2e-5)
            assert np.argmax(batch) == np.argmax(scalar)
            policy.scoring = 'physical'
            np.testing.assert_array_equal(pool, policy._candidate_pool(proposal[ego], anchor, obs[ego]))
            physical = policy._score_candidate_pool(obs, proposal, bg, pool, ego)
            reverse = policy._score_candidate_pool(obs, proposal, bg, pool[::-1], ego)[::-1]
            np.testing.assert_allclose(physical, reverse, rtol=2e-5, atol=2e-5)
            checks.append({'case': case.name, 'step': index+1, 'candidates': len(pool),
                'max_batch_scalar_error': float(np.max(np.abs(np.asarray(batch)-scalar))),
                'same_legacy_argmax': True, 'physical_permutation_invariant': True})
    assert len(checks) >= 6
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open('x') as file:
        json.dump(checks, file, indent=2)
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
