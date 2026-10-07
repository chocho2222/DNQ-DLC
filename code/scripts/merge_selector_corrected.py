#!/usr/bin/env python
"""Merge four GPU shards of the corrected selector-only rerun."""
import csv, json, hashlib
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'outputs/selector_only_corrected_20260912'
OUT=BASE/'aggregate'
ALG=['dnq_dlc_full','fixed_identity','nearest_neighbor']

def ci_boot(x, seed=20260912, B=50000):
    x=np.asarray(x,dtype=float)
    if len(x)==0:return [None,None]
    if len(x)==1:return [float(x[0]),float(x[0])]
    rng=np.random.default_rng(seed); idx=rng.integers(0,len(x),size=(B,len(x)))
    m=x[idx].mean(1); return [float(np.quantile(m,.025)),float(np.quantile(m,.975))]

def main():
    rows=[]
    for shard in sorted(BASE.glob('gpu*/**/summaries/*.summary.json')):
        d=json.loads(shard.read_text()); d['_source']=str(shard); rows.append(d)
    OUT.mkdir(parents=True,exist_ok=True)
    fields=['algorithm','track_path','num_agents','seed','overtake_success_rate','on_track_overtake_rate','elegant_overtake_rate','target_grass_rate','collision_or_contact_proxy','rank_gain','target_progress','compute_latency_ms','source']
    with (OUT/'episode_rows.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for d in rows:w.writerow({k:d.get(k,'') for k in fields[:-1]}|{'source':d['_source']})
    report={'row_count':len(rows),'expected_rows':96,'duplicate_keys':[],'algorithms':{},'paired':{},'selector_diagnostics':{}}
    key=lambda d:(d.get('track_path'),int(d['num_agents']),int(d['seed']))
    for a in ALG:
        rr=[d for d in rows if d['algorithm']==a]; report['algorithms'][a]={'n':len(rr)}
        for m in ['overtake_success_rate','on_track_overtake_rate','elegant_overtake_rate','target_grass_rate','collision_or_contact_proxy','rank_gain']:
            v=np.array([float(d[m]) for d in rr if d.get(m) not in ('',None)],float)
            report['algorithms'][a][m]={'mean':float(v.mean()) if len(v) else None,'sd':float(v.std(ddof=1)) if len(v)>1 else None,'ci95_bootstrap':ci_boot(v)}
        switches=[]; selection_delays=[]
        for d in rr:
            t=json.loads(Path(d['_source']).parents[1].joinpath('traces',Path(d['_source']).name.replace('.summary.json','.trace.json')).read_text())
            ids=[]
            for r in t:
                pre=r.get('pre_action_neighbor_ids',[]); ego=int(d.get('target_agent',int(d['num_agents'])-1))
                ids.append(tuple(pre[ego][:3]) if pre and len(pre)>ego else ())
            switches.append(sum(x!=y for x,y in zip(ids,ids[1:])))
            selection_delays.append(len(ids))
        report['selector_diagnostics'][a]={'mean_switches':float(np.mean(switches)) if switches else None,'sd_switches':float(np.std(switches,ddof=1)) if len(switches)>1 else None}
    groups={a:{key(d):d for d in rows if d['algorithm']==a} for a in ALG}
    full=groups['dnq_dlc_full']
    for a in ALG[1:]:
        common=sorted(set(full)&set(groups[a])); item={'n':len(common),'metrics':{}}
        for m in ['overtake_success_rate','on_track_overtake_rate','elegant_overtake_rate','target_grass_rate','collision_or_contact_proxy','rank_gain']:
            x=np.array([float(full[k][m])-float(groups[a][k][m]) for k in common])
            item['metrics'][m]={'full_minus_variant_mean':float(x.mean()) if len(x) else None,'ci95_bootstrap':ci_boot(x),'full_better':int(sum(x>0)),'ties':int(sum(x==0)),'full_worse':int(sum(x<0))}
        report['paired'][a]=item
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    (OUT/'manifest.json').write_text(json.dumps({'source_shards':[str(p) for p in sorted(BASE.glob('gpu*/run_manifest.json'))],'rows':len(rows),'config_sha256':hashlib.sha256((BASE/'config.json').read_bytes()).hexdigest(),'status':'exploratory selector-only; physical contact not replayed'},indent=2))
    print(json.dumps({'rows':len(rows),'out':str(OUT),'paired':{k:v['n'] for k,v in report['paired'].items()}},indent=2))

if __name__=='__main__':main()
