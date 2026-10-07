"""Unconditional grass fraction per arm: every step of every case.

The audit's grass_fraction is defined on the manoeuvre window, so it exists only
for cases that complete a pass. This script measures the whole episode instead,
which is defined for every case and therefore comparable across arms.
"""
import argparse, csv, glob, json, os, statistics as st
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--base", default="outputs/tits_dynamic_graph_expanded/"
                    "corrected_v2_20260920/main_final_20260922")
parser.add_argument("--out", default="/tmp/episode_grass.csv")
args = parser.parse_args()

rows = []
for case in sorted(glob.glob(f"{args.base}/M*_seed*")):
    for trace_path in sorted(glob.glob(f"{case}/traces/*.trace.json")):
        algo = os.path.basename(trace_path).rsplit(".trace.json", 1)[0]
        algo = algo.rsplit("_n", 1)[0]
        try:
            trace = json.load(open(trace_path))
        except Exception:
            continue
        flags, lat = [], []
        for step in trace:
            tel = step.get("telemetry")
            debug = step.get("target_policy_debug")
            if not tel:
                continue
            # Only the proposed arm records the planner debug block; in every
            # arm the controlled car is the last one in the field.
            agent = debug.get("target_agent") if debug else len(tel["on_grass"]) - 1
            if agent is None:
                continue
            flags.append(1.0 if float(tel["on_grass"][agent]) > 0.5 else 0.0)
            lat.append(abs(float(tel["lateral_error"][agent])))
        if not flags:
            continue
        rows.append({"algorithm": algo, "case": os.path.basename(case),
                     "episode_grass": float(np.mean(flags)),
                     "episode_lat": float(np.mean(lat)), "steps": len(flags)})

os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
with open(args.out, "w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
    writer.writeheader(); writer.writerows(rows)

for algo in sorted({r["algorithm"] for r in rows}):
    sub = [r for r in rows if r["algorithm"] == algo]
    print(f"{algo:32s} n={len(sub):>2d} grass={st.mean(r['episode_grass'] for r in sub):.4f} "
          f"|lat|={st.mean(r['episode_lat'] for r in sub):.4f}")
