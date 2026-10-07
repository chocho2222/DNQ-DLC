#!/usr/bin/env python
"""Aggregate the completed matched risk/uncertainty pilot without filtering outcomes."""
import csv, glob, json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/single_factor_risk_uncertainty_pilot_20260912"
OUT = BASE / "aggregate"
OUT.mkdir(parents=True, exist_ok=True)

paths = sorted(BASE.glob("gpu*/**/summaries/*.summary.json"))
rows = [json.loads(p.read_text()) for p in paths if "preflight" not in str(p)]
fields = sorted({k for r in rows for k in r})
with (OUT / "episode_level.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

key = lambda r: (r["track_path"], int(r["num_agents"]), int(r["seed"]))
by = {}
for r in rows: by.setdefault(key(r), {})[r["algorithm"]] = r
metrics = ["overtake_success", "on_track_overtake_rate", "elegant_overtake_rate", "target_grass_rate", "min_pair_distance", "overtake_start_to_complete_time"]
pairs = []
for k, d in sorted(by.items()):
    if set(d) != {"dnq_dlc_full", "no_risk_uncertainty"}: continue
    out = {"track_path": k[0], "num_agents": k[1], "seed": k[2]}
    for m in metrics:
        a, b = d["dnq_dlc_full"].get(m), d["no_risk_uncertainty"].get(m)
        out[m+"_full"] = a; out[m+"_ablation"] = b
        out[m+"_difference"] = (a-b) if isinstance(a,(int,float)) and isinstance(b,(int,float)) else None
    pairs.append(out)
with (OUT / "matched_pairs.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=sorted({k for r in pairs for k in r})); w.writeheader(); w.writerows(pairs)

summary = {"study":"single_factor_risk_uncertainty_pilot_20260912", "evidence_level":"exploratory", "episode_count":len(rows), "matched_case_count":len(pairs), "algorithms":{}}
for a in ["dnq_dlc_full", "no_risk_uncertainty"]:
    rr=[r for r in rows if r["algorithm"]==a]
    summary["algorithms"][a]={"n":len(rr), "metrics":{}}
    for m in metrics:
        v=[r[m] for r in rr if isinstance(r.get(m),(int,float))]
        summary["algorithms"][a]["metrics"][m]={"n":len(v),"mean":mean(v) if v else None}
summary["interpretation"]="Completion is unchanged in this pilot; quality and timing differences are descriptive and not causal safety evidence."
(OUT/"report.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
print(json.dumps(summary,indent=2))
