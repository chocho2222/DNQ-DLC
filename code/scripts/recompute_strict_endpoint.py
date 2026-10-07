#!/usr/bin/env python
"""Recompute strict overtaking endpoints from frozen E1 traces and exact contact audit.

This is a post-hoc analysis: it never changes actions, checkpoints, or source rows.
Missing post-pass windows are censored and retained in the denominator.
"""
import csv, json, math, hashlib
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'outputs/tits_dynamic_graph_expanded/e1_200_summary/tables/online_benchmark_source_data.csv'
AUDIT = ROOT / 'outputs/contact_audit_20260910/episodes'
OUT = ROOT / 'outputs/strict_endpoint_audit_20260912'

def wilson(k, n, z=1.959963984540054):
    if n == 0: return (None, None)
    p = k / n; den = 1 + z*z/n
    cen = (p + z*z/(2*n))/den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return cen-half, cen+half

def scalar(x):
    return x.item() if isinstance(x, np.generic) else x

def strict_event(trace, ev, audit, hold=50, lateral=0.45, heading_cos=0.82):
    start, end = int(ev['start_step']), int(ev['complete_step'])
    stop = end + hold
    if stop > len(trace):
        return {'available': False, 'reason': 'post_pass_window_censored'}
    rows = trace[start-1:stop]
    ego = int(audit['target_agent']); opp = int(ev['opponent'])
    # Contact replay stores exact ego-pair steps; use event-level and post-pass union.
    contact_steps = set()
    for c in audit.get('events', []):
        # audit event records summarize pass windows; exact contacts are on contacts file
        for s in range(int(c.get('start_step', 0)), int(c.get('complete_step', 0))+1):
            if c.get('true_contact_steps_event', 0):
                contact_steps.add(s)
    # Load exact replay contacts if available.
    cp = audit.get('contacts_path')
    if cp and Path(cp).exists():
        import gzip
        with gzip.open(cp, 'rt') as fh:
            for row in json.load(fh):
                if ego in sum(([int(p) for p in pair] for pair in row.get('ego_pairs', [])), []):
                    contact_steps.add(int(row['step']))
    no_contact = not any(start <= s <= stop for s in contact_steps)
    grass = [bool(r['telemetry']['on_grass'][ego]) for r in rows]
    backward = [bool(r['telemetry']['backward'][ego]) for r in rows]
    lat = np.asarray([float(r['telemetry']['lateral_error'][ego]) for r in rows])
    hc = np.asarray([float(r['telemetry']['heading_cos'][ego]) for r in rows])
    on_track = (not any(grass)) and (not any(backward)) and bool(np.all(np.abs(lat) <= lateral)) and bool(np.all(hc >= heading_cos))
    # Preserve the same target identity and require relative progress to remain ahead at end+hold.
    p0 = float(trace[start-1]['telemetry']['progress'][ego] - trace[start-1]['telemetry']['progress'][opp])
    pend = float(trace[stop-1]['telemetry']['progress'][ego] - trace[stop-1]['telemetry']['progress'][opp])
    retained = pend > p0 and pend > 0.0
    speed = np.asarray([float(r['speed'][ego]) for r in rows[-hold:]])
    stable = bool(np.all(np.isfinite(speed)) and np.mean(speed) > 0.0 and np.max(np.abs(np.diff(lat[-hold:]))) < 0.25)
    return {'available': True, 'contact_free': no_contact, 'on_track': on_track,
            'lead_retained': retained, 'post_pass_stable': stable,
            'strict_completion': bool(no_contact and on_track and retained and stable),
            'min_gap_center': float(min(float(r.get('min_pair_distance', np.inf)) for r in rows)),
            'grass_fraction': float(np.mean(grass)), 'max_abs_lateral': float(np.max(np.abs(lat))),
            'min_heading_cos': float(np.min(hc)), 'lead_at_hold': pend}

def main():
    rows = list(csv.DictReader(SOURCE.open()))
    records=[]
    for row in rows:
        key=f"n{int(row['num_agents'])}_seed{int(row['seed'])}_{row['algorithm']}.json"
        ap=AUDIT/key
        if not ap.exists():
            records.append({'case_id':row['_benchmark']+'/procedural/n'+row['num_agents']+'/seed'+row['seed'], 'algorithm':row['algorithm'], 'status':'missing_audit'})
            continue
        audit=json.loads(ap.read_text())
        tp=Path(audit['trace_path']); trace=json.loads(tp.read_text())
        summary=json.loads(Path(audit['summary_path']).read_text())
        events=summary.get('overtake_events', [])
        outcomes=[strict_event(trace,e,audit) for e in events]
        avail=[o for o in outcomes if o.get('available')]
        audited_events = audit.get('events', [])
        event_cf_any = any(bool(e.get('contact_free_event')) for e in audited_events)
        event_ontrack_cf_any = any(bool(e.get('contact_free_and_legacy_ontrack')) for e in audited_events)
        post50_cf_any = any(bool(e.get('contact_free_through_post50')) for e in audited_events)
        strict=any(o.get('strict_completion') for o in avail)
        event_cf=any(o.get('contact_free') for o in avail)
        ontrack_cf=any(o.get('contact_free') and o.get('on_track') for o in avail)
        retain_cf=any(o.get('contact_free') and o.get('on_track') and o.get('lead_retained') for o in avail)
        records.append({'case_id':audit['case_id'],'algorithm':row['algorithm'],'seed':int(row['seed']),'num_agents':int(row['num_agents']),
                        'benchmark_completion':bool(summary.get('overtake_success')),'event_count':len(events),'available_event_count':len(avail),
                        'post50_censored':bool(events) and not bool(avail),'strict_completion':strict,
                        'event_contact_free':event_cf_any,'event_ontrack_contactfree':event_ontrack_cf_any,
                        'post50_contact_free':post50_cf_any,'contact_free_post50':event_cf,
                        'ontrack_contactfree_post50':ontrack_cf,'retained_contactfree_post50':retain_cf,
                        'ego_contact_any':bool(audit.get('ego_contact_any')),
                        'min_gap_center':min((o.get('min_gap_center',np.inf) for o in avail),default=np.nan),
                        'grass_fraction_post50':float(np.mean([o['grass_fraction'] for o in avail])) if avail else np.nan,
                        'failure_reasons':sorted(set('unavailable' if not o.get('available') else 'strict_fail' for o in outcomes))})
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'episode_level.csv').open('w',newline='') as f:
        fields=sorted({k for r in records for k in r})
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(records)
    agg=[]
    for alg in sorted({r['algorithm'] for r in records}):
        rr=[r for r in records if r['algorithm']==alg]; n=len(rr)
        for ep in ['benchmark_completion','event_contact_free','event_ontrack_contactfree','post50_contact_free','contact_free_post50','ontrack_contactfree_post50','retained_contactfree_post50','strict_completion']:
            k=sum(bool(r.get(ep)) for r in rr); lo,hi=wilson(k,n)
            agg.append({'algorithm':alg,'endpoint':ep,'n':n,'count':k,'rate':k/n if n else np.nan,'wilson_low':lo,'wilson_high':hi,
                        'available_events':sum(int(r.get('available_event_count',0)>0) for r in rr)})
    with (OUT/'aggregate.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=agg[0].keys()); w.writeheader(); w.writerows(agg)
    (OUT/'manifest.json').write_text(json.dumps({'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'hold_steps':50,'lateral_threshold':0.45,'heading_cos_threshold':0.82,'records':len(records),'note':'post-hoc; all 200 cases retained; missing windows censored','validity':'diagnostic only: legacy telemetry progress is visited-tile progress, not physical along-track progress; strict_completion must not be reported as a validated physical endpoint'},indent=2))
    print(json.dumps({'records':len(records),'out':str(OUT),'algorithms':len(set(r['algorithm'] for r in records))},indent=2))

if __name__=='__main__': main()
