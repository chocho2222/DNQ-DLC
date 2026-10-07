#!/usr/bin/env python
"""Summarize matched online evaluation across four DLC-JTO training checkpoints."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


DNQ = "v6_runtime_dynamic_neighborhood_safe"
RULE = "rule_expert_gate"
JTO = [f"dlc_jto_train_seed{seed}" for seed in range(4)]


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = k / n
    denominator = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denominator
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def exact_mcnemar(a_only: int, b_only: int) -> float:
    n = a_only + b_only
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(a_only, b_only) + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def paired_bootstrap(a: np.ndarray, b: np.ndarray, samples: int, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    delta = a.astype(float) - b.astype(float)
    means = np.empty(samples, dtype=float)
    for start in range(0, samples, 5000):
        stop = min(samples, start + 5000)
        indices = rng.integers(0, len(delta), size=(stop - start, len(delta)))
        means[start:stop] = delta[indices].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="outputs/tits_dynamic_graph_expanded/dlc_jto_checkpoint_generalization_20260716/matched_eval")
    parser.add_argument("--output-dir", default="outputs/tits_dynamic_graph_expanded/dlc_jto_checkpoint_generalization_20260716/aggregate")
    parser.add_argument("--bootstrap", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=20260716)
    args = parser.parse_args()

    rows = []
    for suite_path in sorted(Path(args.input_dir).glob("seed*/online_suite_n4_seed*.json")):
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
        for summary in suite["summaries"]:
            algorithm = summary["algorithm"]
            rows.append({
                "evaluation_seed": int(summary["seed"]),
                "algorithm": algorithm,
                "training_seed": int(algorithm.rsplit("seed", 1)[1]) if algorithm in JTO else np.nan,
                "success": int(bool(summary["overtake_success"])),
                "desirable_rate": float(summary["elegant_overtake_rate"]),
                "target_grass_rate": float(summary["target_grass_rate"]),
                "rank_gain": float(summary["rank_gain"]),
                "completion_time": summary.get("overtake_start_to_complete_time"),
                "policy": summary["policy"],
                "source_suite": str(suite_path),
            })
    data = pd.DataFrame(rows)
    expected = {DNQ, RULE, *JTO}
    if set(data.algorithm) != expected:
        raise ValueError(f"Algorithm set mismatch: {sorted(set(data.algorithm))}")
    counts = data.groupby("algorithm").size()
    if counts.nunique() != 1:
        raise ValueError(f"Unbalanced evaluation cases: {counts.to_dict()}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_dir / "dlc_jto_multicheckpoint_rows.csv", index=False)

    summary_rows = []
    for algorithm, frame in data.groupby("algorithm", sort=False):
        k, n = int(frame.success.sum()), int(len(frame))
        low, high = wilson(k, n)
        completed = pd.to_numeric(frame.completion_time, errors="coerce").dropna()
        summary_rows.append({
            "algorithm": algorithm,
            "training_seed": frame.training_seed.dropna().iloc[0] if frame.training_seed.notna().any() else np.nan,
            "n_cases": n,
            "successes": k,
            "success_rate": k / n,
            "wilson_ci95_low": low,
            "wilson_ci95_high": high,
            "mean_desirable_rate": float(frame.desirable_rate.mean()),
            "mean_target_grass_rate": float(frame.target_grass_rate.mean()),
            "mean_rank_gain": float(frame.rank_gain.mean()),
            "mean_completion_time_successes": float(completed.mean()) if len(completed) else np.nan,
            "successful_completion_count": int(len(completed)),
        })
    summaries = pd.DataFrame(summary_rows)
    summaries.to_csv(output_dir / "dlc_jto_multicheckpoint_summary.csv", index=False)

    comparisons = []
    dnq = data[data.algorithm == DNQ].set_index("evaluation_seed").sort_index()
    for index, algorithm in enumerate([RULE, *JTO]):
        comparator = data[data.algorithm == algorithm].set_index("evaluation_seed").loc[dnq.index]
        a = dnq.success.to_numpy(dtype=int)
        b = comparator.success.to_numpy(dtype=int)
        a_only = int(np.sum((a == 1) & (b == 0)))
        b_only = int(np.sum((a == 0) & (b == 1)))
        low, high = paired_bootstrap(a, b, args.bootstrap, args.seed + index)
        comparisons.append({
            "comparator": algorithm,
            "n_paired": len(a),
            "dnq_success_rate": float(a.mean()),
            "comparator_success_rate": float(b.mean()),
            "paired_difference": float((a - b).mean()),
            "paired_bootstrap_ci95_low": low,
            "paired_bootstrap_ci95_high": high,
            "dnq_only_success": a_only,
            "comparator_only_success": b_only,
            "mcnemar_exact_p": exact_mcnemar(a_only, b_only),
        })
    comparisons_df = pd.DataFrame(comparisons)
    comparisons_df.to_csv(output_dir / "dlc_jto_multicheckpoint_paired.csv", index=False)

    jto = summaries[summaries.algorithm.isin(JTO)].sort_values("training_seed")
    report = {
        "status": "pass",
        "evaluation_case_count": int(counts.iloc[0]),
        "evaluation_seeds": sorted(data.evaluation_seed.unique().astype(int).tolist()),
        "jto_training_seeds": [0, 1, 2, 3],
        "jto_success_rate_mean_across_checkpoints": float(jto.success_rate.mean()),
        "jto_success_rate_range_across_checkpoints": [float(jto.success_rate.min()), float(jto.success_rate.max())],
        "summary": summary_rows,
        "paired_comparisons": comparisons,
        "boundary": (
            "This small matched study measures sensitivity to four independently trained DLC-JTO checkpoints. "
            "It is supplementary and does not replace the 200-case primary analysis or establish DNQ-DLC training-seed robustness."
        ),
    }
    report_json = json.dumps(report, indent=2).replace("NaN", "null").replace("Infinity", "null")
    (output_dir / "dlc_jto_multicheckpoint_report.json").write_text(report_json + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
