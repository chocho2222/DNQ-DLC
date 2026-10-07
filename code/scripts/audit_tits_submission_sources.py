#!/usr/bin/env python3
"""Build unfiltered, source-grounded tables for the DNQ-DLC submission audit."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_E1 = ROOT / "outputs/tits_dynamic_graph_expanded/e1_200_summary/tables/online_benchmark_source_data.csv"
DEFAULT_E2 = ROOT / "outputs/tits_dynamic_graph_expanded/topjournal_revised_protocol_h600/e2_environment_generalization"
DEFAULT_E3 = ROOT / "outputs/tits_dynamic_graph_expanded/topjournal_revised_protocol_h600/e3_scale_extrapolation"
DEFAULT_E6 = ROOT / "outputs/tits_dynamic_graph_expanded/topjournal_revised_protocol_h600/e6_high_pressure_ablation"
DEFAULT_OUT = ROOT / "paper_rewriting_output_tits_dynamic_graph_draft_20260625/revision_audit_20260710/source_reconciliation"

METRICS = (
    "overtake_success_rate",
    "on_track_overtake_rate",
    "elegant_overtake_rate",
    "target_grass_rate",
    "overtake_start_to_complete_time",
    "compute_latency_ms",
)


def bootstrap_ci(values: list[float], seed: int = 20260710) -> tuple[float, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return float("nan"), float("nan")
    if array.size == 1:
        return float(array[0]), float(array[0])
    rng = np.random.default_rng(seed)
    draws = rng.choice(array, size=(4000, array.size), replace=True).mean(axis=1)
    low, high = np.quantile(draws, [0.025, 0.975])
    return float(low), float(high)


def finite_float(value):
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def summarize_rows(rows: list[dict], experiment: str) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        key = (
            experiment,
            str(row.get("condition", "")),
            int(row.get("num_agents", 0)),
            str(row.get("algorithm", "")),
        )
        groups[key].append(row)

    output = []
    for (experiment_id, condition, num_agents, algorithm), items in sorted(groups.items()):
        seeds = [int(item["seed"]) for item in items]
        physical_metrics = tuple(metric for metric in METRICS if metric != "compute_latency_ms")
        outcome_signatures = {
            tuple(finite_float(item.get(metric)) for metric in physical_metrics)
            for item in items
        }
        for metric in METRICS:
            values = [finite_float(item.get(metric)) for item in items]
            values = [value for value in values if value is not None]
            low, high = bootstrap_ci(values)
            output.append(
                {
                    "experiment": experiment_id,
                    "condition": condition,
                    "num_agents": num_agents,
                    "algorithm": algorithm,
                    "metric": metric,
                    "n_runs": len(items),
                    "n_defined": len(values),
                    "mean": float(np.mean(values)) if values else "",
                    "ci95_low": low if values else "",
                    "ci95_high": high if values else "",
                    "seed_min": min(seeds) if seeds else "",
                    "seed_max": max(seeds) if seeds else "",
                    "duplicate_seed_count": len(seeds) - len(set(seeds)),
                    "unique_metric_signature_count": len(outcome_signatures),
                }
            )
    return output


def load_summary_tree(root: Path) -> tuple[list[dict], list[str]]:
    rows = []
    errors = []
    for path in sorted(root.rglob("*.summary.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - audit path
            errors.append(f"{path}: {exc}")
            continue
        parts = path.parts
        condition = ""
        for part in parts:
            if part.startswith("E2_") or part.startswith("E3_") or part.startswith("E6_"):
                condition = part
                break
        rows.append(
            {
                "condition": condition,
                "num_agents": int(data.get("num_agents", 0)),
                "seed": int(data.get("seed", -1)),
                "algorithm": data.get("algorithm", ""),
                **{metric: data.get(metric) for metric in METRICS},
                "source_path": str(path.relative_to(ROOT)),
            }
        )
    return rows, errors


def load_e1(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            num_agents = int(float(row["num_agents"]))
            if num_agents <= 6:
                condition = "E1_train_range_N4_N6"
            else:
                condition = "E1_scale_extension_N7_N8"
            rows.append(
                {
                    "condition": condition,
                    "num_agents": num_agents,
                    "seed": int(float(row["seed"])),
                    "algorithm": row["algorithm"],
                    **{metric: row.get(metric) for metric in METRICS},
                    "source_path": str(path.relative_to(ROOT)),
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value):
    if value in (None, ""):
        return "--"
    return f"{float(value):.3f}"


def write_markdown(path: Path, summaries: list[dict], inventory: dict):
    selected = {
        "overtake_success_rate",
        "elegant_overtake_rate",
        "target_grass_rate",
        "overtake_start_to_complete_time",
        "compute_latency_ms",
    }
    lines = [
        "# Submission Source Reconciliation",
        "",
        "This report is generated from all discovered run summaries without case-quality filtering.",
        "",
        "## Inventory",
        "",
    ]
    for key, value in inventory.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Aggregated Metrics",
            "",
            "| Experiment | Condition | N | Algorithm | Metric | Runs | Defined | Mean [95% CI] | Duplicate seeds | Unique outcome signatures |",
            "|---|---|---:|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summaries:
        if row["metric"] not in selected:
            continue
        interval = f"{fmt(row['mean'])} [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}]"
        lines.append(
            f"| {row['experiment']} | {row['condition']} | {row['num_agents']} | "
            f"{row['algorithm']} | {row['metric']} | {row['n_runs']} | {row['n_defined']} | "
            f"{interval} | {row['duplicate_seed_count']} | {row['unique_metric_signature_count']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- Completion time is conditional on a completed overtaking event; its denominator is reported as `Defined`.",
            "- Grass exposure is aggregated across all runs, not only successful runs.",
            "- E1 is split into the training vehicle-count range (N=4--6) and scale extension (N=7--8).",
            "- E2 and E3 values must replace manually typed values in the manuscript.",
            "- E6 remains incomplete when no summary JSON files are present.",
            "- Repeated seeds are not independent robustness evidence when the unique outcome signature count is one.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e1", type=Path, default=DEFAULT_E1)
    parser.add_argument("--e2", type=Path, default=DEFAULT_E2)
    parser.add_argument("--e3", type=Path, default=DEFAULT_E3)
    parser.add_argument("--e6", type=Path, default=DEFAULT_E6)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    e1_rows = load_e1(args.e1)
    e2_rows, e2_errors = load_summary_tree(args.e2)
    e3_rows, e3_errors = load_summary_tree(args.e3)
    e6_rows, e6_errors = load_summary_tree(args.e6) if args.e6.exists() else ([], [])

    summaries = []
    summaries.extend(summarize_rows(e1_rows, "E1"))
    summaries.extend(summarize_rows(e2_rows, "E2"))
    summaries.extend(summarize_rows(e3_rows, "E3"))
    summaries.extend(summarize_rows(e6_rows, "E6"))

    inventory = {
        "e1_run_rows": len(e1_rows),
        "e2_summary_files": len(e2_rows),
        "e3_summary_files": len(e3_rows),
        "e6_summary_files": len(e6_rows),
        "parse_errors": len(e2_errors) + len(e3_errors) + len(e6_errors),
        "e6_status": "complete" if e6_rows else "missing_results",
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "reconciled_aggregate_metrics.csv", summaries)
    write_csv(args.out_dir / "e1_run_inventory.csv", e1_rows)
    write_csv(args.out_dir / "e2_run_inventory.csv", e2_rows)
    write_csv(args.out_dir / "e3_run_inventory.csv", e3_rows)
    write_markdown(args.out_dir / "SOURCE_RECONCILIATION.md", summaries, inventory)
    (args.out_dir / "source_reconciliation_manifest.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if e2_errors or e3_errors or e6_errors:
        (args.out_dir / "parse_errors.txt").write_text(
            "\n".join(e2_errors + e3_errors + e6_errors), encoding="utf-8"
        )
    print(json.dumps(inventory, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
