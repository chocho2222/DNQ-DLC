"""Construct controlled pilot variants without editing archived configurations."""
import argparse
from copy import deepcopy
import json
from pathlib import Path


OVERRIDES = {
    # The environment order is part of the selector factor.  Keeping it
    # explicit prevents a "fixed" policy from receiving relevance-sorted IDs.
    'fixed_identity': {'neighbor_mode': 'fixed_k', 'neighbor_selection_mode': 'fixed', 'neighbor_order': 'identity'},
    'nearest_neighbor': {'neighbor_selection_mode': 'nearest', 'neighbor_order': 'nearest'},
    'no_risk_uncertainty': {'planner_risk_weight': 0.0, 'planner_uncertainty_weight': 0.0},
    'no_hard_recovery': {'hard_safety_shield': False},
    'no_handcrafted_candidates': {'use_handcrafted_candidates': False},
}


def build(source, world_model, quality_actor):
    full = deepcopy(source['algorithms'][0])
    full.setdefault('hard_safety_shield', True)
    full.setdefault('use_handcrafted_candidates', True)
    full.setdefault('neighbor_order', 'relevance')
    full.update(policy=world_model, quality_proposal_path=quality_actor)
    records = [full]
    for name, changes in OVERRIDES.items():
        row = deepcopy(full)
        row.update(changes)
        row.update(name=name, label_cn=name, kind='controlled_pilot_ablation')
        changed = {k for k in full if row[k] != full[k]} - {'name', 'label_cn', 'kind'}
        if changed != set(changes):
            raise ValueError(f'Unexpected configuration difference: {name}: {changed}')
        records.append(row)
    return {'status': 'pilot_only_pending_corrected_training',
            'protocol': {'telemetry_version': 'corrected_v2', 'neighbor_order': 'identity',
                         'environment_exposes_all_neighbors': True, 'policy_neighbor_budget': 3,
                         'main_comparison_separate': True, 'override_whitelist': OVERRIDES},
            'algorithms': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='configs/tits_dnq_attribution_ablation_20260710.json')
    parser.add_argument('--out', required=True)
    parser.add_argument('--world-model', required=True)
    parser.add_argument('--quality-actor', required=True)
    args = parser.parse_args()
    result = build(json.loads(Path(args.source).read_text()), args.world_model, args.quality_actor)
    with Path(args.out).open('x') as f:
        json.dump(result, f, indent=2)


if __name__ == '__main__':
    main()
