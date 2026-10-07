#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


SUITES = [
    ("locked_main", "evaluations/multiseed_suite/multiseed_suite_summary.json"),
    ("locked_adaptive", "evaluations/adaptive_gate_suite/multiseed_suite_summary.json"),
    ("locked_recovery", "evaluations/recovery_adaptive_suite/multiseed_suite_summary.json"),
    ("heldout1_main", "evaluations/heldout_multiseed_suite/multiseed_suite_summary.json"),
    ("heldout1_adaptive", "evaluations/heldout_adaptive_suite/multiseed_suite_summary.json"),
    ("heldout1_expert", "evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json"),
    ("heldout1_dagger_v2", "evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json"),
    ("heldout2_main", "evaluations/heldout2_multiseed_suite/multiseed_suite_summary.json"),
    ("heldout2_adaptive", "evaluations/heldout2_adaptive_suite/multiseed_suite_summary.json"),
    ("heldout2_expert", "evaluations/heldout2_expert_gate_suite/multiseed_suite_summary.json"),
    ("heldout2_dagger_v2", "evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json"),
    ("heldout2_recovery_conservative", "evaluations/heldout2_dagger_v2_recovery_conservative_suite/multiseed_suite_summary.json"),
    ("heldout2_expert_more_graph", "evaluations/heldout2_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json"),
    ("heldout3_main", "evaluations/heldout3_multiseed_suite/multiseed_suite_summary.json"),
    ("heldout3_adaptive", "evaluations/heldout3_adaptive_suite/multiseed_suite_summary.json"),
    ("heldout3_expert", "evaluations/heldout3_expert_gate_suite/multiseed_suite_summary.json"),
    ("heldout3_dagger_v2", "evaluations/heldout3_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json"),
    ("heldout3_expert_more_graph", "evaluations/heldout3_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json"),
    ("heldout3_traffic_adaptive_conservative", "evaluations/heldout3_traffic_adaptive_conservative_suite/multiseed_suite_summary.json"),
    ("heldout3_targeted_recovery", "evaluations/heldout3_targeted_recovery_suite/multiseed_suite_summary.json"),
    ("heldout3_targeted_recovery_conservative_traffic", "evaluations/heldout3_targeted_recovery_conservative_traffic_suite/multiseed_suite_summary.json"),
    ("heldout4_main", "evaluations/heldout4_multiseed_suite/multiseed_suite_summary.json"),
    ("heldout4_adaptive", "evaluations/heldout4_adaptive_suite/multiseed_suite_summary.json"),
    ("heldout4_expert", "evaluations/heldout4_expert_gate_suite/multiseed_suite_summary.json"),
    ("heldout4_dagger_v2", "evaluations/heldout4_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json"),
    ("heldout4_expert_more_graph", "evaluations/heldout4_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json"),
    ("heldout4_traffic_adaptive_conservative", "evaluations/heldout4_traffic_adaptive_conservative_suite/multiseed_suite_summary.json"),
]


TARGET_GRASS_THRESHOLDS = [0.04, 0.06, 0.08, 0.10, 0.12]
ANY_GRASS_THRESHOLDS = [0.30, 0.35, 0.40, 0.45, 0.50]
MIN_MEAN_PROGRESS_THRESHOLDS = [0.55, 0.60, 0.65]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def row_passes(row, target_grass, any_grass, mean_progress, require_rank=True, require_lap=True, require_first_ahead=True):
    if require_lap and not as_bool(row.get("target_completed_lap")):
        return False
    if require_rank and int(row.get("target_final_rank_by_tiles", 999)) != 1:
        return False
    first_ahead = row.get("first_ahead_step")
    if require_first_ahead and (first_ahead is None or first_ahead == "" or int(first_ahead) < 10):
        return False
    if float(row.get("target_grass_rate", 1.0)) > target_grass:
        return False
    if float(row.get("max_grass_rate", 1.0)) > any_grass:
        return False
    if float(row.get("mean_tile_progress", 0.0)) < mean_progress:
        return False
    return True


def normalize_row(stage, row):
    return {
        "stage": stage,
        "method": row["method"],
        "seed": int(row["seed"]),
        "reported_status": row["validation_status"],
        "target_completed_lap": as_bool(row["target_completed_lap"]),
        "target_final_rank_by_tiles": int(row["target_final_rank_by_tiles"]),
        "target_grass_rate": float(row["target_grass_rate"]),
        "max_grass_rate": float(row["max_grass_rate"]),
        "target_tile_progress": float(row["target_tile_progress"]),
        "mean_tile_progress": float(row["mean_tile_progress"]),
        "first_ahead_step": None if row.get("first_ahead_step") in (None, "") else int(row["first_ahead_step"]),
        "summary": row.get("summary", ""),
    }


def collect_rows(root):
    rows = []
    missing = []
    threshold_snapshots = {}
    for stage, rel in SUITES:
        path = root / rel
        if not path.exists():
            missing.append(rel)
            continue
        data = load_json(path)
        threshold_snapshots[stage] = data.get("thresholds", {})
        for row in data.get("rows", []):
            rows.append(normalize_row(stage, row))
    return rows, missing, threshold_snapshots


def make_scenario_rows(rows):
    scenario_rows = []
    for target_grass in TARGET_GRASS_THRESHOLDS:
        for any_grass in ANY_GRASS_THRESHOLDS:
            for mean_progress in MIN_MEAN_PROGRESS_THRESHOLDS:
                for stage_method in sorted({(row["stage"], row["method"]) for row in rows}):
                    stage, method = stage_method
                    subset = [row for row in rows if row["stage"] == stage and row["method"] == method]
                    if not subset:
                        continue
                    strict_count = sum(row["reported_status"] == "PASS" for row in subset)
                    pass_count = sum(row_passes(row, target_grass, any_grass, mean_progress) for row in subset)
                    scenario_rows.append(
                        {
                            "stage": stage,
                            "method": method,
                            "n": len(subset),
                            "target_grass_threshold": target_grass,
                            "any_grass_threshold": any_grass,
                            "min_mean_progress": mean_progress,
                            "strict_pass_count": strict_count,
                            "sensitivity_pass_count": pass_count,
                            "delta_vs_strict": pass_count - strict_count,
                        }
                    )
    return scenario_rows


def make_method_summary(scenario_rows):
    summary = []
    for stage, method in sorted({(row["stage"], row["method"]) for row in scenario_rows}):
        subset = [row for row in scenario_rows if row["stage"] == stage and row["method"] == method]
        strict = subset[0]["strict_pass_count"] if subset else 0
        counts = [row["sensitivity_pass_count"] for row in subset]
        deltas = [row["delta_vs_strict"] for row in subset]
        summary.append(
            {
                "stage": stage,
                "method": method,
                "n": subset[0]["n"] if subset else 0,
                "strict_pass_count": strict,
                "min_sensitivity_pass_count": min(counts) if counts else 0,
                "max_sensitivity_pass_count": max(counts) if counts else 0,
                "max_abs_delta_vs_strict": max(abs(delta) for delta in deltas) if deltas else 0,
                "scenario_count": len(subset),
                "interpretation": (
                    "endpoint_sensitive"
                    if any(delta != 0 for delta in deltas)
                    else "stable_across_threshold_grid"
                ),
            }
        )
    return summary


def make_near_threshold_rows(rows):
    near = []
    for row in rows:
        margins = {
            "target_grass_margin_at_0_08": 0.08 - row["target_grass_rate"],
            "any_grass_margin_at_0_40": 0.40 - row["max_grass_rate"],
            "mean_progress_margin_at_0_60": row["mean_tile_progress"] - 0.60,
            "target_progress_margin_at_1_00": row["target_tile_progress"] - 1.00,
        }
        nearest_endpoint, nearest_margin = min(margins.items(), key=lambda item: abs(item[1]))
        if abs(nearest_margin) <= 0.03 or row["reported_status"] == "FAIL":
            near.append(
                {
                    "stage": row["stage"],
                    "method": row["method"],
                    "seed": row["seed"],
                    "reported_status": row["reported_status"],
                    "target_completed_lap": row["target_completed_lap"],
                    "target_final_rank_by_tiles": row["target_final_rank_by_tiles"],
                    "target_grass_rate": row["target_grass_rate"],
                    "max_grass_rate": row["max_grass_rate"],
                    "target_tile_progress": row["target_tile_progress"],
                    "mean_tile_progress": row["mean_tile_progress"],
                    "first_ahead_step": row["first_ahead_step"],
                    "nearest_endpoint": nearest_endpoint,
                    "nearest_margin": nearest_margin,
                    "summary": row["summary"],
                }
            )
    return sorted(near, key=lambda item: (abs(item["nearest_margin"]), item["stage"], item["method"], item["seed"]))


def make_gate_rows(rows):
    gates = [
        ("strict_all_gates", True, True, True),
        ("no_rank_gate", False, True, True),
        ("no_lap_gate", True, False, True),
        ("no_first_ahead_gate", True, True, False),
    ]
    gate_rows = []
    for stage, method in sorted({(row["stage"], row["method"]) for row in rows}):
        subset = [row for row in rows if row["stage"] == stage and row["method"] == method]
        strict = sum(row["reported_status"] == "PASS" for row in subset)
        for gate, require_rank, require_lap, require_first_ahead in gates:
            pass_count = sum(
                row_passes(
                    row,
                    target_grass=0.08,
                    any_grass=0.40,
                    mean_progress=0.60,
                    require_rank=require_rank,
                    require_lap=require_lap,
                    require_first_ahead=require_first_ahead,
                )
                for row in subset
            )
            gate_rows.append(
                {
                    "stage": stage,
                    "method": method,
                    "gate_variant": gate,
                    "n": len(subset),
                    "strict_pass_count": strict,
                    "variant_pass_count": pass_count,
                    "delta_vs_strict": pass_count - strict,
                }
            )
    return gate_rows


def write_csv(rows, path, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def build_report(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    rows, missing, threshold_snapshots = collect_rows(root)
    scenario_rows = make_scenario_rows(rows)
    method_summary = make_method_summary(scenario_rows)
    near_threshold_rows = make_near_threshold_rows(rows)
    gate_rows = make_gate_rows(rows)
    sensitive_methods = [row for row in method_summary if row["interpretation"] == "endpoint_sensitive"]
    return {
        "root": str(root),
        "title": "Endpoint Sensitivity Audit",
        "purpose": (
            "Assess how saved rollout PASS counts change under nearby endpoint-threshold grids and gate ablations, "
            "without rerunning policies or changing trajectory data."
        ),
        "scope": {
            "suite_specs": [{"stage": stage, "path": rel} for stage, rel in SUITES],
            "missing_suite_paths": missing,
            "target_grass_thresholds": TARGET_GRASS_THRESHOLDS,
            "any_grass_thresholds": ANY_GRASS_THRESHOLDS,
            "min_mean_progress_thresholds": MIN_MEAN_PROGRESS_THRESHOLDS,
            "threshold_snapshots": threshold_snapshots,
        },
        "summary": {
            "rollout_row_count": len(rows),
            "stage_method_count": len(method_summary),
            "scenario_count": len(scenario_rows),
            "endpoint_sensitive_stage_methods": len(sensitive_methods),
            "near_threshold_row_count": len(near_threshold_rows),
            "missing_suite_count": len(missing),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
        },
        "method_summary": method_summary,
        "scenario_rows": scenario_rows,
        "gate_rows": gate_rows,
        "near_threshold_rows": near_threshold_rows,
        "interpretation": (
            "This audit tests numerical endpoint sensitivity only. It does not create new validation evidence, "
            "does not relax the manuscript's strict endpoint, and should be used to identify which results depend "
            "most strongly on threshold choices."
        ),
    }


def write_markdown(report, path):
    lines = [
        "# Endpoint Sensitivity Audit",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Threshold Grid",
            "",
            f"- Target grass thresholds: {report['scope']['target_grass_thresholds']}",
            f"- Any-car grass thresholds: {report['scope']['any_grass_thresholds']}",
            f"- Minimum mean-progress thresholds: {report['scope']['min_mean_progress_thresholds']}",
            "",
            "## Most Endpoint-sensitive Stage-method Rows",
            "",
            "| stage | method | strict | min grid | max grid | max abs delta | interpretation |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    ranked = sorted(report["method_summary"], key=lambda row: row["max_abs_delta_vs_strict"], reverse=True)
    for row in ranked[:30]:
        lines.append(
            f"| {row['stage']} | {row['method']} | {row['strict_pass_count']}/{row['n']} | "
            f"{row['min_sensitivity_pass_count']}/{row['n']} | {row['max_sensitivity_pass_count']}/{row['n']} | "
            f"{row['max_abs_delta_vs_strict']} | {row['interpretation']} |"
        )
    lines.extend(
        [
            "",
            "## Gate Ablation",
            "",
            "Gate ablation rows are exported to `materials/ENDPOINT_SENSITIVITY_GATE_ROWS.csv`. "
            "They show how counts change when rank, lap-completion, or first-ahead gates are individually removed while keeping the default numeric thresholds.",
            "",
            "## Near-threshold Rows",
            "",
            "Near-threshold and failed rollout rows are exported to `materials/ENDPOINT_SENSITIVITY_NEAR_THRESHOLD_ROWS.csv` for reviewer inspection.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export endpoint sensitivity audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "ENDPOINT_SENSITIVITY_AUDIT.json"
    out_md = materials / "ENDPOINT_SENSITIVITY_AUDIT.md"
    scenario_csv = materials / "ENDPOINT_SENSITIVITY_SCENARIO_ROWS.csv"
    summary_csv = materials / "ENDPOINT_SENSITIVITY_METHOD_SUMMARY.csv"
    gate_csv = materials / "ENDPOINT_SENSITIVITY_GATE_ROWS.csv"
    near_csv = materials / "ENDPOINT_SENSITIVITY_NEAR_THRESHOLD_ROWS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(
        report["scenario_rows"],
        scenario_csv,
        [
            "stage",
            "method",
            "n",
            "target_grass_threshold",
            "any_grass_threshold",
            "min_mean_progress",
            "strict_pass_count",
            "sensitivity_pass_count",
            "delta_vs_strict",
        ],
    )
    write_csv(
        report["method_summary"],
        summary_csv,
        [
            "stage",
            "method",
            "n",
            "strict_pass_count",
            "min_sensitivity_pass_count",
            "max_sensitivity_pass_count",
            "max_abs_delta_vs_strict",
            "scenario_count",
            "interpretation",
        ],
    )
    write_csv(
        report["gate_rows"],
        gate_csv,
        ["stage", "method", "gate_variant", "n", "strict_pass_count", "variant_pass_count", "delta_vs_strict"],
    )
    write_csv(
        report["near_threshold_rows"],
        near_csv,
        [
            "stage",
            "method",
            "seed",
            "reported_status",
            "target_completed_lap",
            "target_final_rank_by_tiles",
            "target_grass_rate",
            "max_grass_rate",
            "target_tile_progress",
            "mean_tile_progress",
            "first_ahead_step",
            "nearest_endpoint",
            "nearest_margin",
            "summary",
        ],
    )
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "scenario_csv": str(scenario_csv),
                "summary_csv": str(summary_csv),
                "gate_csv": str(gate_csv),
                "near_threshold_csv": str(near_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
