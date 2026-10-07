"""Align predictions with the physical identities selected before each real action.

Executed-action prediction audit only; unexecuted candidates have no factual
outcome in these traces. Persistence is a one-step diagnostic reference.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pyglet
pyglet.options['headless'] = True
import numpy as np
from dlc.physical_quality_pilot import footprint_terms
from dlc.training_packing import pack_transition_pair


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    totals, hashes = [], {}
    for summary in json.loads((a.source/'summary.json').read_text()):
        case = a.source/summary['case_id']
        initial = json.loads((case/'initial.json').read_text())
        trace = json.loads((case/'trace.json').read_text())
        hashes[str(case/'trace.json')] = hashlib.sha256((case/'trace.json').read_bytes()).hexdigest()
        dest = a.out/case.name
        dest.mkdir()
        n, ego = summary['num_agents'], summary['num_agents']-1
        previous = np.asarray(initial['obs'], dtype=np.float32)
        ids = [[j for j in range(n) if j != i] for i in range(n)]
        rows, predictions, truth, persistence, steps, selections = [], [], [], [], [], []
        last_set, switches, recovery = None, 0, 0
        for r in trace:
            following = np.asarray(r['obs'], dtype=np.float32)
            packed, successor, selected = pack_transition_pair(previous, following, ids, r['opponent_ids'])
            current_set = frozenset(selected[ego])
            switches += int(last_set is not None and current_set != last_set)
            last_set = current_set
            d = r['planner_debug']
            recovery += int(d['hard_recovery'])
            prediction = d.get('prediction_debug', {})
            selections.append({'step': r['step'], 'selected_before_action': selected,
                               'hard_recovery': d['hard_recovery']})
            if prediction:
                predicted = np.asarray(prediction['selected_next_obs'], dtype=np.float32)[ego]
                actual, current = successor[ego], packed[ego]
                candidates = np.asarray(prediction['candidate_first_next_ego'], dtype=np.float32)
                pred_terms, actual_terms = footprint_terms(predicted), footprint_terms(actual)
                scores = np.asarray([v['score'] for v in d['candidate_scores']])
                ordered = np.sort(scores)
                contact = any(ego in c['agents'] for c in r['contacts'])
                rows.append({'step': r['step'], 'candidates': len(scores),
                    'score_range': float(np.ptp(scores)),
                    'score_top_two_margin': float(ordered[-1]-ordered[-2]) if len(scores)>1 else None,
                    'predicted_speed_range_world_units_s': float(np.ptp(candidates[:,4])*50),
                    'predicted_lateral_range_world_units': float(np.ptp(candidates[:,12])*(40/6)),
                    'speed_error_world_units_s': float((predicted[4]-actual[4])*50),
                    'lateral_error_world_units': float((predicted[12]-actual[12])*(40/6)),
                    'predicted_overlap_proxy': pred_terms['overlap_proxy'],
                    'observed_overlap_proxy': actual_terms['overlap_proxy'],
                    'physical_contact_this_step': contact,
                    'predicted_edge_margin': pred_terms['edge_margin'],
                    'observed_edge_margin': actual_terms['edge_margin'],
                    'selected_action_index': int(np.argmax(scores))})
                predictions.append(predicted); truth.append(actual); persistence.append(current); steps.append(r['step'])
            previous, ids = following, r['opponent_ids']
        with (dest/'executed_predictions.csv').open('x', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]) if rows else ['step'])
            writer.writeheader(); writer.writerows(rows)
        with (dest/'selected_opponents.jsonl').open('x') as file:
            for selection in selections:
                file.write(json.dumps(selection)+'\n')
        np.savez_compressed(dest/'aligned_one_step_predictions.npz', steps=steps,
                           predicted=predictions, actual=truth, persistence=persistence)
        result = {'case_id': case.name, 'method': summary['method'], 'steps': len(trace),
            'ranking_steps': len(rows), 'hard_recovery_steps': recovery, 'opponent_set_switches': switches,
            'scope': 'ranking-step-conditioned diagnostics; no counterfactual outcome claim'}
        if rows:
            pred, actual, prior = map(np.asarray, [predictions,truth,persistence])
            for label, indices, scale in [('speed', [4], 50), ('lateral', [12], 40/6),
                                           ('heading_sin_cos', [13,14], 1),
                                           ('relative_position', [17,18,25,26,33,34], 2000/6)]:
                result[label+'_model_rmse'] = float(np.sqrt(np.mean(((pred[:,indices]-actual[:,indices])*scale)**2)))
                result[label+'_persistence_rmse'] = float(np.sqrt(np.mean(((prior[:,indices]-actual[:,indices])*scale)**2)))
            result['physical_contact_ranking_steps'] = sum(r['physical_contact_this_step'] for r in rows)
            result['predicted_overlap_ranking_steps'] = sum(r['predicted_overlap_proxy'] > 0 for r in rows)
            result['mean_predicted_candidate_speed_range'] = float(np.mean([r['predicted_speed_range_world_units_s'] for r in rows]))
            result['mean_predicted_candidate_lateral_range'] = float(np.mean([r['predicted_lateral_range_world_units'] for r in rows]))
        totals.append(result)
    (a.out/'summary.json').write_text(json.dumps({'scope': __doc__, 'cases': totals, 'source_sha256': hashes}, indent=2))
    (a.out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps(totals, indent=2))


if __name__ == '__main__':
    main()
