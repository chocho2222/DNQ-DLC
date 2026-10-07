#!/usr/bin/env python
"""Run missing robustness cases from the frozen plan on one visible GPU."""
from __future__ import annotations
import argparse, csv, os, subprocess, time
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--plan',type=Path,required=True); p.add_argument('--shard',type=Path,required=True); p.add_argument('--gpu',required=True); p.add_argument('--config',required=True); p.add_argument('--python',default='/home/itrc/.conda/envs/vlm_planner/bin/python'); args=p.parse_args()
    # The frozen plan contains eight seeds (four cases per seed).  Partition
    # those seeds evenly across the four GPU shards.
    seeds={'s1':range(6501,6503),'s2':range(6503,6505),'s3':range(6505,6507),'s4':range(6507,6509)}
    with args.plan.open(encoding='utf-8',newline='') as h: rows=list(csv.DictReader(h))
    rows=[r for r in rows if int(r['seed']) in seeds.get(args.shard.name,())]
    logs=args.shard/'logs'; logs.mkdir(parents=True,exist_ok=True)
    for r in rows:
        track=r['track_path']; n=int(r['num_agents']); seed=int(r['seed']); case=args.shard/Path(track).stem/f'n{n}'/f'seed{seed}'; case.mkdir(parents=True,exist_ok=True)
        algs=[x for x in r['algorithms'].split(',') if x]
        expected=[case/'summaries'/f'{a}_n{n}_seed{seed}.summary.json' for a in algs]
        if all(x.exists() for x in expected): continue
        cmd=[args.python,'scripts/run_tits_dynamic_graph_evaluation.py','--config',args.config,'--algorithms',','.join(algs),'--out-dir',str(case),'--num-agents',str(n),'--seed',str(seed),'--max-steps','2200','--finish-mode','steps','--observation-type','telemetry_dynamic','--env-max-neighbors','0','--traffic-profile','mixed_traffic','--neighbor-order','relevance','--telemetry-version','legacy_v1','--observation-noise-std','0.0','--observation-noise-seed-offset','200000','--actuation-delay-steps','0','--randomize-scenario','--no-gif','--device','cuda:0','--track-path',track]
        env=dict(os.environ); env['CUDA_VISIBLE_DEVICES']=str(args.gpu); log=logs/f'{Path(track).stem}_n{n}_seed{seed}.gpu.log'; t=time.time()
        with log.open('w',encoding='utf-8') as h: rc=subprocess.run(cmd,stdout=h,stderr=subprocess.STDOUT,env=env,check=False).returncode
        print(f'{args.shard.name} {track} n{n} seed{seed}: rc={rc} summaries={sum(x.exists() for x in expected)} elapsed={time.time()-t:.1f}s',flush=True)
if __name__=='__main__': main()
