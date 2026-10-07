#!/usr/bin/env python
import argparse
import csv
import json
import math
from pathlib import Path


ORDER = (
    "dlc_individual_transition",
    "dlc_joint_transition",
    "dlc_joint_transition_observer",
    "rule_expert_gate",
    "v6_runtime_dynamic_neighborhood_safe",
)


def read_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def wilson(k, n, z=1.959963984540054):
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den
    low = center - half
    high = center + half
    if abs(low) < 1e-15:
        low = 0.0
    if abs(high - 1.0) < 1e-15:
        high = 1.0
    return max(0.0, low), min(1.0, high)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--statistics", default="outputs/tits_dynamic_graph_expanded/e1_200_summary/tables/online_benchmark_nature_direct_statistics.csv")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph_expanded/e1_200_summary/tables")
    args = parser.parse_args()

    rows = read_csv(args.statistics)
    index = {(r["algorithm"], r["metric"]): r for r in rows}
    out = []

    for algorithm in ORDER:
        success = index[(algorithm, "overtake_success_rate")]
        desirable = index[(algorithm, "elegant_overtake_rate")]
        completion = index[(algorithm, "completion_time_capped")]

        n_cases = int(success["n"])
        success_rate = float(success["mean"])
        success_count = int(round(success_rate * n_cases))
        success_low, success_high = wilson(success_count, n_cases)

        desirable_mean = float(desirable["mean"])
        all_zero = desirable_mean == 0.0
        completion_n = int(completion["n"])
        out.append({
            "algorithm": algorithm,
            "algorithm_label": success["algorithm_label"],
            "n_cases": n_cases,
            "success_count": success_count,
            "success_rate": success_rate,
            "success_ci95_low": success_low,
            "success_ci95_high": success_high,
            "success_ci_method": "Wilson score interval",
            "desirable_mean_per_episode": desirable_mean,
            "desirable_ci95_low": "" if all_zero else desirable["ci95_low"],
            "desirable_ci95_high": "" if all_zero else desirable["ci95_high"],
            "desirable_ci_method": (
                "all 200 episode-level proportions were zero; no population interval reported"
                if all_zero else
                "case bootstrap from source statistics"
            ),
            "completion_n_successes": completion_n,
            "completion_mean_steps": completion["mean"],
            "completion_ci95_low": completion["ci95_low"],
            "completion_ci95_high": completion["ci95_high"],
            "completion_ci_method": (
                "descriptive case bootstrap; highly unstable because n<20"
                if 0 < completion_n < 20 else
                "case bootstrap from successful episodes"
            ),
            "source_statistics": args.statistics,
        })

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "retrained_dlc_table_source.csv"
    fields = list(out[0])
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)

    dictionary_path = out_dir / "retrained_dlc_table_data_dictionary.md"
    dictionary_path.write_text("""# Retrained DLC Table Data Dictionary

- Unit of analysis: one simulator episode/case; 200 cases per algorithm.
- Success: binary indicator that the target completed at least one overtake. The table uses Wilson 95% confidence intervals.
- Desirable overtaking: episode-level proportion of overtakes satisfying the implemented desirable criteria; cases with no qualifying overtake contribute zero. Nonzero methods use the existing case-bootstrap interval. When all 200 values are zero, the table reports the empirical all-zero result without presenting a degenerate interval as population uncertainty.
- Completion time: start-to-completion simulation steps, conditioned on successful episodes. The sample count is always shown. DLC-JT and DLC-JTO estimates are descriptive and unstable because only 2 and 18 episodes, respectively, succeeded.
- The table uses one frozen seed-1 DLC checkpoint set selected from four trained candidates by the documented round-robin rule. Online results are not averages over four DLC training seeds.
- Source statistics: online_benchmark_nature_direct_statistics.csv.
- Release provenance: paper_dlc_release_manifest.json and paper_dlc_artifact_checksums.csv.
""", encoding="utf-8")

    report = {
        "status": "pass",
        "source": args.statistics,
        "rows": out,
        "outputs": {
            "table_source_csv": str(csv_path),
            "data_dictionary": str(dictionary_path),
        },
    }
    report_path = out_dir / "retrained_dlc_table_source.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["outputs"], indent=2))


if __name__ == "__main__":
    main()
