#!/usr/bin/env python
"""Aggregate the matched full/no-world-model pilot without changing episode data."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def action_key(action):
    return tuple(np.round(np.asarray(action, dtype=np.float64), 7).tolist())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="outputs/world_model_utility_matched_pilot_20260912")
    ap.add_argument("--out", default="outputs/world_model_utility_matched_pilot_20260912/aggregate")
    ap.add_argument("--counterfactual-root", default="outputs/world_model_counterfactual_pilot_20260912")
    args = ap.parse_args()
    root, out = Path(args.root), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    summaries = sorted(root.glob("*/summaries/*.summary.json"))
    traces = {p.name: p for p in root.glob("*/traces/*.trace.json")}
    rows = []
    for p in summaries:
        x = read_json(p)
        x["summary_file"] = str(p)
        rows.append(x)
    episodes = []
    for x in rows:
        trace_path = Path(x["trace_path"])
        trace = read_json(trace_path)
        mode = x.get("world_model_mode", "full")
        episodes.append({
            "case_key": f"{x.get('track_path')}|n{x.get('num_agents')}|seed{x.get('seed')}",
            "track_path": x.get("track_path"), "num_agents": x.get("num_agents"),
            "seed": x.get("seed"), "mode": mode,
            "steps_run": x.get("steps_run"), "rank_gain": x.get("rank_gain"),
            "target_progress": x.get("target_progress"),
            "overtake_success": x.get("overtake_success"),
            "on_track_overtake_rate": x.get("on_track_overtake_rate"),
            "elegant_overtake_rate": x.get("elegant_overtake_rate"),
            "target_grass_rate": x.get("target_grass_rate"),
            "collision_or_contact_proxy": x.get("collision_or_contact_proxy"),
            "compute_latency_ms": x.get("compute_latency_ms"),
            "trace_file": str(trace_path),
        })
    episode_csv = out / "episode_level.csv"
    fields = list(episodes[0]) if episodes else []
    with episode_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(episodes)

    pair_rows = []
    for case_key in sorted({e["case_key"] for e in episodes}):
        pair = {e["mode"]: e for e in episodes if e["case_key"] == case_key}
        if not {"full", "no_world_model"}.issubset(pair):
            continue
        full = next(x for x in rows if x["world_model_mode"] == "full" and f"{x.get('track_path')}|n{x.get('num_agents')}|seed{x.get('seed')}" == case_key)
        nw = next(x for x in rows if x["world_model_mode"] == "no_world_model" and f"{x.get('track_path')}|n{x.get('num_agents')}|seed{x.get('seed')}" == case_key)
        tf = read_json(Path(full["trace_path"])); tn = read_json(Path(nw["trace_path"]))
        common = min(len(tf), len(tn)); exact_pool = 0; selected_same = 0; ranking_corr = []
        top1_regret = []
        for i in range(common):
            df = tf[i].get("target_policy_debug", {}); dn = tn[i].get("target_policy_debug", {})
            cf = df.get("candidate_scores", []); cn = dn.get("candidate_scores", [])
            af = [c.get("action") for c in cf]; an = [c.get("action") for c in cn]
            if af == an and af:
                exact_pool += 1
                sf = np.asarray([c.get("score", np.nan) for c in cf], dtype=float)
                sn = np.asarray([c.get("score", np.nan) for c in cn], dtype=float)
                if np.isfinite(sf).all() and np.isfinite(sn).all() and len(sf) > 1:
                    rank_f = np.argsort(np.argsort(-sf)); rank_n = np.argsort(np.argsort(-sn))
                    ranking_corr.append(float(np.corrcoef(rank_f, rank_n)[0, 1]) if np.std(rank_f) and np.std(rank_n) else 1.0)
                    selected_same += int(np.argmax(sf) == np.argmax(sn))
                    # No post-hoc physical oracle is inferred; this is only score disagreement.
                    top1_regret.append(float(np.max(sf) - sf[int(np.argmax(sn))]))
        pair_rows.append({
            "case_key": case_key, "common_steps": common,
            "candidate_pool_exact_match_rate": exact_pool / common if common else None,
            "selected_action_same_rate": selected_same / exact_pool if exact_pool else None,
            "mean_rank_correlation": float(np.mean(ranking_corr)) if ranking_corr else None,
            "mean_full_score_regret_of_no_world_top1": float(np.mean(top1_regret)) if top1_regret else None,
            "full_rank_gain": pair["full"]["rank_gain"], "no_world_model_rank_gain": pair["no_world_model"]["rank_gain"],
            "full_progress": pair["full"]["target_progress"], "no_world_model_progress": pair["no_world_model"]["target_progress"],
        })
    pair_csv = out / "matched_pair_level.csv"
    pf = list(pair_rows[0]) if pair_rows else []
    with pair_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pf); w.writeheader(); w.writerows(pair_rows)
    manifest = {
        "study": "world_model_utility_matched_pilot_20260912",
        "evidence_level": "exploratory matched pilot",
        "endpoint_status": "No episode reached full-lap completion within the 600-step pilot horizon; no completion claim is made.",
        "interpretation_boundary": "Ranking disagreement and trajectory diagnostics do not establish causal safety or physical collision prediction.",
        "source_episode_count": len(rows), "paired_case_count": len(pair_rows),
        "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in summaries},
        "outputs": {"episode_level": str(episode_csv), "matched_pair_level": str(pair_csv)},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report = {"manifest": manifest, "episode_rows": episodes, "matched_rows": pair_rows}
    cf_rows = []
    cf_root = Path(args.counterfactual_root)
    for tp in sorted(cf_root.glob("*/traces/*.trace.json")):
        trace = read_json(tp)
        corr, same, n, regret = [], 0, 0, []
        for row in trace:
            d = row.get("target_policy_debug", {})
            a = d.get("candidate_scores", []); b = d.get("counterfactual_candidate_scores", [])
            if not a or not b or len(a) != len(b):
                continue
            sa = np.asarray([z.get("score", np.nan) for z in a], dtype=float)
            sb = np.asarray([z.get("score", np.nan) for z in b], dtype=float)
            if not (np.isfinite(sa).all() and np.isfinite(sb).all()):
                continue
            n += 1
            ra = np.argsort(np.argsort(-sa)); rb = np.argsort(np.argsort(-sb))
            corr.append(float(np.corrcoef(ra, rb)[0, 1]) if np.std(ra) and np.std(rb) else 1.0)
            same += int(np.argmax(sa) == np.argmax(sb))
            regret.append(float(np.max(sa) - sa[int(np.argmax(sb))]))
        cf_rows.append({"trace_file": str(tp), "steps": len(trace), "matched_steps": n,
                        "selected_action_agreement": same / n if n else None,
                        "mean_rank_correlation": float(np.mean(corr)) if corr else None,
                        "mean_full_score_regret": float(np.mean(regret)) if regret else None})
    report["same_state_counterfactual_rows"] = cf_rows
    (out / "same_state_counterfactual.csv").write_text(
        "trace_file,steps,matched_steps,selected_action_agreement,mean_rank_correlation,mean_full_score_regret\n" +
        "\n".join(",".join(str(r.get(k, "")) for k in ["trace_file","steps","matched_steps","selected_action_agreement","mean_rank_correlation","mean_full_score_regret"]) for r in cf_rows) + "\n", encoding="utf-8")
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"episodes": len(rows), "pairs": len(pair_rows), "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
