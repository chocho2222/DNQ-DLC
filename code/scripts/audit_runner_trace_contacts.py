#!/usr/bin/env python
"""Exact Box2D contact replay for runner traces with initial-state records."""
import argparse, json
from pathlib import Path
import numpy as np
from dlc.rollout import make_env

def audit(tp):
    tp=Path(tp); ip=tp.with_name(tp.name.replace('.trace.json','.initial.json'))
    trace=json.loads(tp.read_text()); initial=json.loads(ip.read_text())
    env=make_env(num_agents=initial['num_agents'], seed=initial['seed'], observation_type='telemetry_dynamic',
                 start_order=list(range(initial['num_agents'])), line_spacing=5, lateral_spacing=2.2,
                 track_path=initial['track_path'], max_neighbors=0, telemetry_version='corrected_v2', neighbor_order='relevance')
    e=env.unwrapped; env.reset();
    max_err=0.; mismatches=0; contact_steps=[]; ego=e.num_agents-1
    try:
        max_err=max(max_err,float(np.max(np.abs(np.asarray([c.hull.position for c in e.cars])-np.asarray(initial['positions'])))))
        for i,row in enumerate(trace,1):
            e.vehicle_contacts.clear_step(); env.step(np.asarray(row['action'],dtype=np.float32))
            pos=np.asarray([c.hull.position for c in e.cars]); max_err=max(max_err,float(np.max(np.abs(pos-np.asarray(row['positions'])))))
            actual={tuple(c['agents']) for c in e.vehicle_contacts.snapshot(e.world)}
            expected={tuple(c['agents']) for c in row.get('contacts',[])}
            if actual!=expected: mismatches+=1
            if any(ego in pair for pair in actual): contact_steps.append(i)
    finally: env.close()
    return {'trace':str(tp),'steps':len(trace),'max_position_error':max_err,'contact_mismatch_steps':mismatches,
            'ego_contact_steps':len(contact_steps),'first_ego_contact_step':min(contact_steps) if contact_steps else None,
            'exact_replay':bool(max_err<1e-5 and mismatches==0)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    rows=[audit(p) for p in sorted(Path(a.root).glob('**/traces/*.trace.json'))]
    Path(a.out).write_text(json.dumps({'scope':'post-hoc exact Box2D replay','rows':rows},indent=2))
    print(json.dumps({'cases':len(rows),'exact':sum(r['exact_replay'] for r in rows),'ego_contact_cases':sum(r['ego_contact_steps']>0 for r in rows)}))
if __name__=='__main__': main()
