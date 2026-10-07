#!/usr/bin/env python
"""Summarize the frozen paper data with reproducible descriptive statistics."""

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "outputs/tits_dynamic_graph_expanded/current_paper_data_20260916"
OUT = PACK / "analysis"


def rows(path):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def num(v):
    if v is None or v == "" or str(v).lower() in {"none", "null", "nan"}:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def mean_sd_ci(values):
    n = len(values)
    if not n:
        return (None, None, None, None, 0)
    mu = sum(values) / n
    sd = math.sqrt(sum((x - mu) ** 2 for x in values) / (n - 1)) if n > 1 else 0.0
    # Normal approximation keeps this report dependency-free; binary endpoints
    # use the Wilson intervals produced by the audit tool.
    half = 1.96 * sd / math.sqrt(n) if n > 1 else 0.0
    return (mu, sd, mu - half, mu + half, n)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        if isinstance(data, list):
            fields = []
            for r in data:
                for k in r:
                    if k not in fields:
                        fields.append(k)
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader(); w.writerows(data)
        else:
            json.dump(data, fh, indent=2)


def main():
    summary = rows(PACK / "standard_summary_metrics.csv")
    metric_names = [
        "target_progress", "rank_gain", "target_grass_rate", "target_backward_rate",
        "target_mean_abs_lateral", "target_heading_error_mean_rad", "target_mean_speed",
        "collision_or_contact_proxy", "min_pair_distance", "compute_latency_ms",
        "compute_latency_p95_ms",
    ]
    grouped = defaultdict(list)
    for r in summary:
        for metric in metric_names:
            x = num(r.get(metric))
            if x is not None:
                grouped[(r["experiment_id"], r["algorithm"], metric)].append(x)
    stats = []
    for (experiment, algorithm, metric), values in sorted(grouped.items()):
        mu, sd, lo, hi, n = mean_sd_ci(values)
        stats.append({"experiment_id": experiment, "algorithm": algorithm, "metric": metric,
                      "n": n, "mean": mu, "sd": sd, "ci95_low": lo, "ci95_high": hi})
    write(OUT / "grouped_continuous_stats.csv", stats)

    strict = rows(PACK / "strict_endpoint_aggregate.csv")
    # The audit aggregate already contains exact n/count/rate/Wilson bounds.
    endpoint_rows = []
    for r in strict:
        endpoint_rows.append({k: r.get(k) for k in
                              ["dataset", "algorithm", "endpoint", "n", "count", "rate",
                               "wilson_low", "wilson_high", "ok_rows", "censored_rows"]})
    write(OUT / "strict_endpoint_stats.csv", endpoint_rows)

    # Case-paired E6 deltas against the full method. This avoids treating the
    # eight ablations as independent scenario samples.
    e6 = [r for r in summary if r["experiment_id"] == "E6_ablation"]
    base = {(r["case_index"], r["seed"], r["num_agents"], r["track_id"]): r
            for r in e6 if r["algorithm"] == "ours_full_v6_safe"}
    paired = []
    for r in e6:
        if r["algorithm"] == "ours_full_v6_safe":
            continue
        key = (r["case_index"], r["seed"], r["num_agents"], r["track_id"])
        b = base.get(key)
        if not b:
            continue
        out = {"case_index": r["case_index"], "track_id": r["track_id"],
               "num_agents": r["num_agents"], "seed": r["seed"],
               "algorithm": r["algorithm"]}
        for metric in ["target_progress", "rank_gain", "target_grass_rate", "target_backward_rate",
                       "target_mean_abs_lateral", "target_heading_error_mean_rad",
                       "compute_latency_ms"]:
            a, z = num(r.get(metric)), num(b.get(metric))
            if a is not None and z is not None:
                out[metric + "_delta_vs_full"] = a - z
        paired.append(out)
    write(OUT / "e6_paired_case_deltas.csv", paired)

    # Aggregate paired deltas by ablation and retain direction counts. The
    # case is the unit of comparison because all variants share the same seed
    # and scenario in E6.
    paired_metrics = [
        "target_progress", "rank_gain", "target_grass_rate",
        "target_backward_rate", "target_mean_abs_lateral",
        "target_heading_error_mean_rad", "compute_latency_ms",
    ]
    paired_stats = []
    for algorithm in sorted({r["algorithm"] for r in paired}):
        subset = [r for r in paired if r["algorithm"] == algorithm]
        for metric in paired_metrics:
            values = [num(r.get(metric + "_delta_vs_full")) for r in subset]
            values = [x for x in values if x is not None]
            mu, sd, lo, hi, n = mean_sd_ci(values)
            paired_stats.append({
                "algorithm": algorithm,
                "metric": metric,
                "n": n,
                "mean_delta_vs_full": mu,
                "sd": sd,
                "ci95_low": lo,
                "ci95_high": hi,
                "wins_positive_delta": sum(x > 0 for x in values),
                "ties": sum(x == 0 for x in values),
                "wins_negative_delta": sum(x < 0 for x in values),
            })
    write(OUT / "e6_paired_stats.csv", paired_stats)

    manifest = {
        "summary_rows": len(summary), "strict_rows": len(strict),
        "e6_rows": len(e6), "e6_base_rows": len(base),
        "e6_paired_rows": len(paired), "continuous_metrics": metric_names,
        "e6_paired_metrics": paired_metrics,
        "ci_definition": "mean +/- 1.96*SD/sqrt(n); endpoint intervals are Wilson intervals from strict audits",
    }
    write(OUT / "analysis_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
