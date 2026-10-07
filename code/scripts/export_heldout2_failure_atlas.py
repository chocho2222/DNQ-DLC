#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


METHOD_LABELS = {
    "lane_base_only": "lane-only rule baseline",
    "overtake_base_only": "overtake rule baseline",
    "graph_adaptive_shield": "graph actor + adaptive shield",
    "expert_gate_only": "expert-gate rule candidate",
    "dagger_v2_graph_expert_gate_shield": "DAgger-v2 graph + expert-gate shield",
    "graph_expert_gate_shield": "DAgger-v2 graph + expert-gate shield",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pass_status(value):
    return str(value).upper() == "PASS"


def failure_flags(row):
    if pass_status(row.get("validation_status") or row.get("status")):
        return []
    flags = []
    if not row.get("target_completed_lap"):
        flags.append("incomplete_lap")
    if row.get("target_final_rank_by_tiles") != 1:
        flags.append("not_first")
    if row.get("target_grass_rate", 0.0) > 0.08:
        flags.append("target_grass")
    if row.get("max_grass_rate", 0.0) > 0.40:
        flags.append("traffic_grass")
    if row.get("mean_tile_progress", 1.0) < 0.60:
        flags.append("low_mean_progress")
    if row.get("first_ahead_step") is None:
        flags.append("no_first_ahead")
    return flags or ["validator_fail"]


def load_method_rows(root, suite_paths):
    rows = {}
    for suite_rel in suite_paths:
        suite = load_json(root / suite_rel)
        for row in suite["rows"]:
            method = row["method"]
            if "heldout2_graph_dagger_recovery_v2_suite" in suite_rel and method == "graph_adaptive_shield":
                continue
            if method == "graph_expert_gate_shield":
                method = "dagger_v2_graph_expert_gate_shield"
            rows[(int(row["seed"]), method)] = row
    return rows


def normalize_method_name(method):
    if method is None:
        return method
    method = str(method)
    if ":" in method:
        method = method.split(":", 1)[1]
    if method == "graph_expert_gate_shield":
        return "dagger_v2_graph_expert_gate_shield"
    return method


def recommendation(error_type, seed, selected, oracle, passing_methods):
    if error_type == "candidate_gap":
        return (
            "Expand candidate-policy coverage: prioritize a boundary-constrained or recovery-specialized "
            f"candidate on seed {seed}, because no current candidate passes the strict validator."
        )
    if error_type == "selector_miss":
        methods = ", ".join(passing_methods) if passing_methods else oracle
        return (
            "Improve selector features or learned selection: a passing candidate exists "
            f"({methods}), but the probe selected {selected}."
        )
    return "Retain as positive evidence for the current candidate pool and selector."


def build_atlas(root):
    selector = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout2_dagger_v2.json")
    calibration = load_json(root / "tables" / "selector_calibration.json")
    heldout = load_json(root / "tables" / "heldout_generalization.json")

    suite_paths = [
        "evaluations/heldout2_multiseed_suite/multiseed_suite_summary.json",
        "evaluations/heldout2_adaptive_suite/multiseed_suite_summary.json",
        "evaluations/heldout2_expert_gate_suite/multiseed_suite_summary.json",
        "evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
    ]
    method_rows = load_method_rows(root, suite_paths)
    methods = list(selector["methods"])
    decisions = {int(item["seed"]): item for item in selector["decisions"]}
    calibrated = {int(item["seed"]): item for item in calibration["test_heldout2"]["decisions"]}

    seed_rows = []
    method_matrix = []
    for seed in selector["seeds"]:
        seed = int(seed)
        decision = decisions[seed]
        cal = calibrated.get(seed, {})
        selected = normalize_method_name(decision["selected_method"])
        oracle = normalize_method_name(decision["oracle_method"])
        selected_status = decision["selected_full_status"]
        oracle_status = decision["oracle_status"]
        passing_methods = []
        failing_methods = []
        failure_by_method = {}

        for method in methods:
            row = method_rows.get((seed, method), {})
            status = row.get("validation_status") or row.get("status") or "MISSING"
            flags = failure_flags(row) if row else ["missing_row"]
            if pass_status(status):
                passing_methods.append(method)
            else:
                failing_methods.append(method)
            failure_by_method[method] = flags
            method_matrix.append(
                {
                    "seed": seed,
                    "method": method,
                    "method_label": METHOD_LABELS.get(method, method),
                    "status": status,
                    "target_completed_lap": row.get("target_completed_lap"),
                    "target_final_rank_by_tiles": row.get("target_final_rank_by_tiles"),
                    "target_grass_rate": row.get("target_grass_rate"),
                    "max_grass_rate": row.get("max_grass_rate"),
                    "target_tile_progress": row.get("target_tile_progress"),
                    "mean_tile_progress": row.get("mean_tile_progress"),
                    "first_ahead_step": row.get("first_ahead_step"),
                    "failure_flags": "+".join(flags),
                    "summary": row.get("summary"),
                    "gif": row.get("gif"),
                }
            )

        if pass_status(selected_status):
            error_type = "pass"
        elif not pass_status(oracle_status):
            error_type = "candidate_gap"
        else:
            error_type = "selector_miss"

        seed_rows.append(
            {
                "seed": seed,
                "selected_method": selected,
                "selected_status": selected_status,
                "oracle_method": oracle,
                "oracle_status": oracle_status,
                "calibrated_selected": cal.get("selected_method"),
                "calibrated_status": cal.get("selected_status"),
                "error_type": error_type,
                "passing_methods": passing_methods,
                "failing_methods": failing_methods,
                "selected_probe_score": decision.get("probe_score"),
                "selected_probe_progress": decision.get("probe_progress"),
                "selected_probe_grass": decision.get("probe_grass"),
                "selected_full_progress": decision.get("selected_full_progress"),
                "selected_full_grass": decision.get("selected_full_grass"),
                "selected_full_rank": decision.get("selected_full_rank"),
                "oracle_full_status": oracle_status,
                "failure_by_method": failure_by_method,
                "recommendation": recommendation(error_type, seed, selected, oracle, passing_methods),
            }
        )

    summary = {
        "n": len(seed_rows),
        "pass_count": sum(row["error_type"] == "pass" for row in seed_rows),
        "candidate_gap_count": sum(row["error_type"] == "candidate_gap" for row in seed_rows),
        "selector_miss_count": sum(row["error_type"] == "selector_miss" for row in seed_rows),
        "candidate_gap_seeds": [row["seed"] for row in seed_rows if row["error_type"] == "candidate_gap"],
        "selector_miss_seeds": [row["seed"] for row in seed_rows if row["error_type"] == "selector_miss"],
        "pass_seeds": [row["seed"] for row in seed_rows if row["error_type"] == "pass"],
        "heldout2_selector": heldout["sets"]["heldout2"]["selector"],
        "interpretation": (
            "Heldout2 failures separate into candidate-policy coverage gaps and selector misses. "
            "Candidate-gap seeds require new policy candidates; selector-miss seeds require richer or learned selection."
        ),
    }
    return {
        "root": str(root),
        "selector_source": "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
        "calibration_source": "tables/selector_calibration.json",
        "suite_sources": suite_paths,
        "methods": methods,
        "summary": summary,
        "seed_rows": seed_rows,
        "method_matrix": method_matrix,
    }


def write_csv(report, root):
    seed_csv = root / "tables" / "heldout2_failure_atlas_seed_rows.csv"
    matrix_csv = root / "tables" / "heldout2_failure_atlas_method_matrix.csv"
    seed_fields = [
        "seed",
        "selected_method",
        "selected_status",
        "oracle_method",
        "oracle_status",
        "calibrated_selected",
        "calibrated_status",
        "error_type",
        "passing_methods",
        "failing_methods",
        "selected_probe_score",
        "selected_probe_progress",
        "selected_probe_grass",
        "selected_full_progress",
        "selected_full_grass",
        "selected_full_rank",
        "recommendation",
    ]
    with seed_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=seed_fields)
        writer.writeheader()
        for row in report["seed_rows"]:
            writer.writerow(
                {
                    key: (
                        ";".join(row[key])
                        if key in {"passing_methods", "failing_methods"}
                        else row.get(key)
                    )
                    for key in seed_fields
                }
            )
    matrix_fields = [
        "seed",
        "method",
        "method_label",
        "status",
        "target_completed_lap",
        "target_final_rank_by_tiles",
        "target_grass_rate",
        "max_grass_rate",
        "target_tile_progress",
        "mean_tile_progress",
        "first_ahead_step",
        "failure_flags",
        "summary",
        "gif",
    ]
    with matrix_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=matrix_fields)
        writer.writeheader()
        for row in report["method_matrix"]:
            writer.writerow({key: row.get(key) for key in matrix_fields})
    return seed_csv, matrix_csv


def write_markdown(report, path):
    s = report["summary"]
    lines = [
        "# Heldout2 Failure Atlas",
        "",
        "This atlas decomposes the second held-out batch at seed level. It is intended for reviewer-facing failure analysis and next-experiment planning.",
        "",
        "## Summary",
        "",
        f"- Seeds: {s['n']}",
        f"- Selector passes: {s['pass_count']}/{s['n']}",
        f"- Candidate-policy gaps: {s['candidate_gap_count']} ({', '.join(map(str, s['candidate_gap_seeds'])) or 'none'})",
        f"- Selector misses: {s['selector_miss_count']} ({', '.join(map(str, s['selector_miss_seeds'])) or 'none'})",
        f"- Passing seeds: {', '.join(map(str, s['pass_seeds'])) or 'none'}",
        "",
        "Interpretation:",
        "",
        s["interpretation"],
        "",
        "## Seed-level Decisions",
        "",
        "| seed | selected | selected status | oracle | oracle status | passing candidates | error type | next action |",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for row in report["seed_rows"]:
        passing = ", ".join(row["passing_methods"]) if row["passing_methods"] else "none"
        lines.append(
            f"| {row['seed']} | {row['selected_method']} | {row['selected_status']} | "
            f"{row['oracle_method']} | {row['oracle_status']} | {passing} | "
            f"{row['error_type']} | {row['recommendation']} |"
        )
    lines.extend(
        [
            "",
            "## Candidate Matrix",
            "",
            "| seed | method | status | failure flags | target progress | target grass | rank |",
            "|---:|---|---|---|---:|---:|---:|",
        ]
    )
    for row in report["method_matrix"]:
        progress = row.get("target_tile_progress")
        grass = row.get("target_grass_rate")
        rank = row.get("target_final_rank_by_tiles")
        lines.append(
            f"| {row['seed']} | {row['method']} | {row['status']} | {row['failure_flags']} | "
            f"{progress if progress is not None else ''} | {grass if grass is not None else ''} | "
            f"{rank if rank is not None else ''} |"
        )
    lines.extend(
        [
            "",
            "## Reporting Boundary",
            "",
            "- Candidate-gap seeds do not prove selector failure; they show that the current candidate pool lacks a strict-passing option.",
            "- Selector-miss seeds do not prove policy failure; they show that a passing candidate exists but the current probe score selected another method.",
            "- This atlas should be reported together with `tables/selector_calibration.md` and `tables/heldout_generalization.md`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export seed-level heldout2 failure atlas.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_atlas(root)
    out_json = root / "tables" / "heldout2_failure_atlas.json"
    out_md = root / "tables" / "heldout2_failure_atlas.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    seed_csv, matrix_csv = write_csv(report, root)
    write_markdown(report, out_md)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "seed_csv": str(seed_csv),
                "matrix_csv": str(matrix_csv),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
