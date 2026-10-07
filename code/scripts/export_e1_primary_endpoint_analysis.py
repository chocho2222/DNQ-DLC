#!/usr/bin/env python
"""Export the matched E1 overtaking-success primary-endpoint analysis.

The analysis is intentionally restricted to the frozen 200-case E1 source
table.  It treats each (benchmark, vehicle count, seed) tuple as a matched
case and compares the complete DNQ-DLC controller with every reported
baseline on the binary overtaking-success endpoint.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


PROPOSED = "v6_runtime_dynamic_neighborhood_safe"
COMPARATORS = [
    "rule_expert_gate",
    "rule_safety_gate",
    "dlc_joint_transition_observer",
    "ppo_continuous",
    "sac_continuous",
    "td3_continuous",
]
LABELS = {
    PROPOSED: "DNQ-DLC",
    "rule_expert_gate": "Rule Expert",
    "rule_safety_gate": "Safety Rule",
    "dlc_joint_transition_observer": "DLC-JTO",
    "ppo_continuous": "PPO legacy",
    "sac_continuous": "SAC legacy",
    "td3_continuous": "TD3 legacy",
}
CASE_KEYS = ["benchmark", "num_agents", "seed"]


def wilson_interval(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")
    p = k / n
    denominator = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denominator
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def exact_mcnemar_p(a_only: int, b_only: int) -> float:
    """Two-sided exact McNemar/binomial p value for discordant pairs."""
    n = a_only + b_only
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(a_only, b_only) + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def paired_bootstrap_interval(
    proposed: np.ndarray,
    comparator: np.ndarray,
    samples: int,
    seed: int,
) -> tuple[float, float]:
    differences = proposed.astype(float) - comparator.astype(float)
    rng = np.random.default_rng(seed)
    n = len(differences)
    # Chunking avoids allocating a samples-by-n matrix for larger reruns.
    boot_means: list[np.ndarray] = []
    remaining = samples
    while remaining > 0:
        chunk = min(5000, remaining)
        indices = rng.integers(0, n, size=(chunk, n))
        boot_means.append(differences[indices].mean(axis=1))
        remaining -= chunk
    boot = np.concatenate(boot_means)
    low, high = np.quantile(boot, [0.025, 0.975])
    return float(low), float(high)


def holm_adjust(p_values: list[float]) -> list[float]:
    order = np.argsort(np.asarray(p_values, dtype=float))
    adjusted = np.empty(len(p_values), dtype=float)
    running = 0.0
    m = len(p_values)
    for rank, index in enumerate(order):
        value = min(1.0, (m - rank) * p_values[index])
        running = max(running, value)
        adjusted[index] = running
    return adjusted.tolist()


def matched_vectors(success: pd.DataFrame, comparator: str) -> pd.DataFrame:
    subset = success[success["algorithm"].isin([PROPOSED, comparator])].copy()
    duplicated = subset.duplicated(CASE_KEYS + ["algorithm"], keep=False)
    if duplicated.any():
        raise ValueError(f"Duplicate matched-case rows detected for {comparator}")
    wide = subset.pivot(index=CASE_KEYS, columns="algorithm", values="value_display")
    if PROPOSED not in wide or comparator not in wide:
        raise ValueError(f"Missing algorithm in matched table: {comparator}")
    if wide[[PROPOSED, comparator]].isna().any().any():
        raise ValueError(f"Unmatched E1 cases detected for {comparator}")
    return wide.reset_index()


def comparison_row(wide: pd.DataFrame, comparator: str, samples: int, seed: int) -> dict:
    proposed = wide[PROPOSED].to_numpy(dtype=int)
    baseline = wide[comparator].to_numpy(dtype=int)
    both_success = int(np.sum((proposed == 1) & (baseline == 1)))
    proposed_only = int(np.sum((proposed == 1) & (baseline == 0)))
    comparator_only = int(np.sum((proposed == 0) & (baseline == 1)))
    neither = int(np.sum((proposed == 0) & (baseline == 0)))
    ci_low, ci_high = paired_bootstrap_interval(proposed, baseline, samples, seed)
    p_value = exact_mcnemar_p(proposed_only, comparator_only)
    return {
        "comparator": comparator,
        "comparator_label": LABELS[comparator],
        "n_paired": int(len(wide)),
        "dnq_successes": int(proposed.sum()),
        "dnq_success_rate": float(proposed.mean()),
        "comparator_successes": int(baseline.sum()),
        "comparator_success_rate": float(baseline.mean()),
        "paired_difference": float((proposed - baseline).mean()),
        "paired_bootstrap_ci95_low": ci_low,
        "paired_bootstrap_ci95_high": ci_high,
        "both_success": both_success,
        "dnq_only_success": proposed_only,
        "comparator_only_success": comparator_only,
        "neither_success": neither,
        "discordant_pairs": proposed_only + comparator_only,
        "mcnemar_exact_p": p_value,
    }


def stratum_rows(success: pd.DataFrame, samples: int, seed: int) -> list[dict]:
    output: list[dict] = []
    selected = [PROPOSED, "rule_expert_gate", "dlc_joint_transition_observer"]
    success = success.copy()
    success["vehicle_count_stratum"] = np.where(
        success["num_agents"] <= 6, "N=4-6 training range", "N=7-8 extrapolation"
    )
    for stratum_index, (stratum, frame) in enumerate(success.groupby("vehicle_count_stratum", sort=False)):
        for algorithm in selected:
            values = frame[frame["algorithm"] == algorithm]["value_display"].to_numpy(dtype=int)
            k, n = int(values.sum()), int(len(values))
            low, high = wilson_interval(k, n)
            output.append({
                "vehicle_count_stratum": stratum,
                "algorithm": algorithm,
                "algorithm_label": LABELS[algorithm],
                "n": n,
                "successes": k,
                "success_rate": k / n,
                "wilson_ci95_low": low,
                "wilson_ci95_high": high,
                "paired_difference_vs_rule_expert": float("nan"),
                "paired_bootstrap_ci95_low_vs_rule_expert": float("nan"),
                "paired_bootstrap_ci95_high_vs_rule_expert": float("nan"),
                "mcnemar_exact_p_vs_rule_expert": float("nan"),
            })

        # The proposed-vs-rule contrast is the prespecified stratum contrast.
        pair = frame[frame["algorithm"].isin([PROPOSED, "rule_expert_gate"])].pivot(
            index=CASE_KEYS, columns="algorithm", values="value_display"
        ).reset_index()
        proposed = pair[PROPOSED].to_numpy(dtype=int)
        rule = pair["rule_expert_gate"].to_numpy(dtype=int)
        lo, hi = paired_bootstrap_interval(proposed, rule, samples, seed + 100 + stratum_index)
        proposed_only = int(np.sum((proposed == 1) & (rule == 0)))
        rule_only = int(np.sum((proposed == 0) & (rule == 1)))
        for row in output:
            if row["vehicle_count_stratum"] == stratum and row["algorithm"] == PROPOSED:
                row["paired_difference_vs_rule_expert"] = float((proposed - rule).mean())
                row["paired_bootstrap_ci95_low_vs_rule_expert"] = lo
                row["paired_bootstrap_ci95_high_vs_rule_expert"] = hi
                row["mcnemar_exact_p_vs_rule_expert"] = exact_mcnemar_p(proposed_only, rule_only)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="outputs/tits_dynamic_graph_expanded/e1_200_summary/tables/online_benchmark_nature_direct_source_data.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/tits_dynamic_graph_expanded/e1_primary_endpoint_20260716",
    )
    parser.add_argument("--bootstrap", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=20260716)
    args = parser.parse_args()

    source_path = Path(args.source)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source = pd.read_csv(source_path)
    success = source[source["metric"] == "overtake_success_rate"].copy()
    success["value_display"] = success["value_display"].astype(int)

    rows = []
    for index, comparator in enumerate(COMPARATORS):
        wide = matched_vectors(success, comparator)
        if len(wide) != 200:
            raise ValueError(f"Expected 200 paired E1 cases for {comparator}, found {len(wide)}")
        rows.append(comparison_row(wide, comparator, args.bootstrap, args.seed + index))
    adjusted = holm_adjust([row["mcnemar_exact_p"] for row in rows])
    for row, adjusted_p in zip(rows, adjusted):
        row["mcnemar_holm_p"] = adjusted_p

    comparisons = pd.DataFrame(rows)
    comparisons.to_csv(output_dir / "e1_primary_paired_success.csv", index=False)
    comparisons[[
        "comparator", "comparator_label", "n_paired", "both_success",
        "dnq_only_success", "comparator_only_success", "neither_success",
        "discordant_pairs",
    ]].to_csv(output_dir / "e1_primary_discordance.csv", index=False)

    strata = pd.DataFrame(stratum_rows(success, args.bootstrap, args.seed))
    strata.to_csv(output_dir / "e1_vehicle_count_strata.csv", index=False)

    report = {
        "analysis": "Matched binary overtaking-success primary endpoint",
        "source": str(source_path),
        "case_keys": CASE_KEYS,
        "primary_algorithm": PROPOSED,
        "primary_comparator": "rule_expert_gate",
        "bootstrap_resamples": args.bootstrap,
        "bootstrap_seed": args.seed,
        "confidence_interval": "percentile paired case bootstrap",
        "hypothesis_test": "two-sided exact McNemar test",
        "multiplicity": "Holm adjustment across six reported comparator tests",
        "comparisons": rows,
        "vehicle_count_strata": strata.replace({np.nan: None}).to_dict(orient="records"),
        "claim_boundary": (
            "The analysis supports a complete-framework advantage in the evaluated simulator benchmark; "
            "it does not attribute the success difference to dynamic neighbor selection alone."
        ),
    }
    (output_dir / "e1_primary_endpoint_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(comparisons.to_string(index=False))
    print(f"\nWrote primary-endpoint outputs to {output_dir}")


if __name__ == "__main__":
    main()
