#!/usr/bin/env python
import argparse
import csv
import itertools
import json
from pathlib import Path


DEFAULT_PRIORITY = [
    "dagger_v2_graph_expert_gate_shield",
    "expert_gate_only",
    "graph_adaptive_shield",
    "overtake_base_only",
    "lane_base_only",
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def priority_map(names):
    return {name: len(names) - idx for idx, name in enumerate(names)}


def score(row, weights):
    return (
        weights["progress_weight"] * float(row["probe_progress"])
        - weights["grass_weight"] * float(row["probe_grass"])
        - weights["rank_penalty"] * max(0, int(row["probe_rank"]) - 1)
        + weights["first_ahead_bonus"] * int(row.get("probe_first_ahead_step") is not None)
    )


def index_selector_report(report):
    full = {}
    for decision in report["decisions"]:
        full[(decision["selected_method"], decision["seed"])] = {
            "validation_status": decision["selected_full_status"],
            "target_progress": decision["selected_full_progress"],
            "target_grass": decision["selected_full_grass"],
            "target_rank": decision["selected_full_rank"],
        }
    for row in report["probe_rows"]:
        if row["status"] != "PASS":
            continue
        # The selector report does not duplicate every full row, so recover the full status
        # from the original suite paths when needed in load_full_rows().
        pass
    return full


def load_full_rows(root, report):
    rows = {}
    suite_paths = report["suite_paths"]
    method_to_suite = {}
    method_to_full_method = {}
    for method in report["methods"]:
        if method == "dagger_v2_graph_expert_gate_shield":
            method_to_suite[method] = "dagger_v2"
            method_to_full_method[method] = "graph_expert_gate_shield"
        elif method == "graph_adaptive_shield":
            method_to_suite[method] = "adaptive"
            method_to_full_method[method] = method
        elif method == "expert_gate_only":
            method_to_suite[method] = "expert"
            method_to_full_method[method] = method
        else:
            method_to_suite[method] = "main"
            method_to_full_method[method] = method
    loaded = {}
    for suite_name, rel_path in suite_paths.items():
        path = root / rel_path
        if path.exists():
            loaded[suite_name] = load_json(path)
    for method in report["methods"]:
        suite = loaded[method_to_suite[method]]
        full_method = method_to_full_method[method]
        for row in suite["rows"]:
            if row["method"] == full_method:
                rows[(method, row["seed"])] = row
    return rows


def evaluate(report, full_rows, weights, priority):
    decisions = []
    for seed in report["seeds"]:
        candidates = [
            row for row in report["probe_rows"]
            if row["seed"] == seed and row["status"] == "PASS"
        ]
        selected = max(
            candidates,
            key=lambda row: (score(row, weights), priority.get(row["method"], 0)),
        )
        full = full_rows[(selected["method"], seed)]
        oracle_method = max(
            report["methods"],
            key=lambda method: (
                full_rows[(method, seed)]["validation_status"] == "PASS",
                priority.get(method, 0),
            ),
        )
        oracle = full_rows[(oracle_method, seed)]
        decisions.append(
            {
                "seed": seed,
                "selected_method": selected["method"],
                "selected_status": full["validation_status"],
                "selected_score": score(selected, weights),
                "oracle_method": oracle_method,
                "oracle_status": oracle["validation_status"],
                "oracle_available": oracle["validation_status"] == "PASS",
                "selector_miss": (
                    oracle["validation_status"] == "PASS"
                    and full["validation_status"] != "PASS"
                ),
                "candidate_gap": oracle["validation_status"] != "PASS",
            }
        )
    pass_count = sum(row["selected_status"] == "PASS" for row in decisions)
    oracle_count = sum(row["oracle_status"] == "PASS" for row in decisions)
    return {
        "weights": weights,
        "n": len(decisions),
        "pass_count": pass_count,
        "pass_rate": pass_count / len(decisions) if decisions else None,
        "oracle_pass_count": oracle_count,
        "oracle_pass_rate": oracle_count / len(decisions) if decisions else None,
        "selector_miss_count": sum(row["selector_miss"] for row in decisions),
        "candidate_gap_count": sum(row["candidate_gap"] for row in decisions),
        "decisions": decisions,
    }


def weight_grid():
    for progress, grass, rank, first in itertools.product(
        [0.75, 1.0, 1.25, 1.5],
        [0.5, 1.0, 1.75, 2.5, 3.5],
        [0.15, 0.3, 0.45, 0.7, 1.0],
        [0.0, 0.05, 0.1, 0.2],
    ):
        yield {
            "progress_weight": progress,
            "grass_weight": grass,
            "rank_penalty": rank,
            "first_ahead_bonus": first,
        }


def choose_weights(train_report, train_full_rows, priority):
    scored = []
    for weights in weight_grid():
        result = evaluate(train_report, train_full_rows, weights, priority)
        # Secondary terms prefer simpler, safer scores after maximizing pass count.
        scored.append(
            (
                result["pass_count"],
                -result["selector_miss_count"],
                -weights["grass_weight"],
                -weights["rank_penalty"],
                result,
            )
        )
    scored.sort(key=lambda item: item[:4], reverse=True)
    return scored[0][4], [item[4] for item in scored[:10]]


def write_report(root, report, prefix):
    table_dir = root / "tables"
    out_json = table_dir / f"{prefix}.json"
    out_md = table_dir / f"{prefix}.md"
    out_csv = table_dir / f"{prefix}_decisions.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "evaluation",
            "seed",
            "selected_method",
            "selected_status",
            "oracle_method",
            "oracle_status",
            "selector_miss",
            "candidate_gap",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for eval_name in ["train_heldout1", "test_heldout2"]:
            for row in report[eval_name]["decisions"]:
                writer.writerow({"evaluation": eval_name, **{key: row[key] for key in fieldnames if key != "evaluation"}})
    lines = [
        "# Selector Calibration Report",
        "",
        "## Summary",
        "",
        "| evaluation | pass | oracle | selector misses | candidate gaps |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in ["current_heldout1", "current_heldout2", "train_heldout1", "test_heldout2"]:
        item = report[name]
        lines.append(
            f"| {name} | {item['pass_count']}/{item['n']} | {item['oracle_pass_count']}/{item['n']} | "
            f"{item['selector_miss_count']} | {item['candidate_gap_count']} |"
        )
    lines.extend(
        [
            "",
            "## Selected Weights",
            "",
            "```json",
            json.dumps(report["selected_weights"], indent=2),
            "```",
            "",
            "## Heldout2 Calibrated Decisions",
            "",
            "| seed | selected | status | oracle | oracle status | error type |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for row in report["test_heldout2"]["decisions"]:
        error = "candidate_gap" if row["candidate_gap"] else ("selector_miss" if row["selector_miss"] else "")
        lines.append(
            f"| {row['seed']} | {row['selected_method']} | {row['selected_status']} | "
            f"{row['oracle_method']} | {row['oracle_status']} | {error} |"
        )
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}


def main():
    parser = argparse.ArgumentParser(description="Calibrate online selector scores across held-out sets.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--prefix", default="selector_calibration")
    args = parser.parse_args()
    root = Path(args.root)
    priority = priority_map(DEFAULT_PRIORITY)
    h1 = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout_dagger_v2.json")
    h2 = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout2_dagger_v2.json")
    h1_full = load_full_rows(root, h1)
    h2_full = load_full_rows(root, h2)
    current_h1 = evaluate(h1, h1_full, h1["score_weights"], priority)
    current_h2 = evaluate(h2, h2_full, h2["score_weights"], priority)
    train_best, top_train = choose_weights(h1, h1_full, priority)
    test_best = evaluate(h2, h2_full, train_best["weights"], priority)
    report = {
        "root": str(root),
        "priority": DEFAULT_PRIORITY,
        "current_heldout1": current_h1,
        "current_heldout2": current_h2,
        "train_heldout1": train_best,
        "test_heldout2": test_best,
        "selected_weights": train_best["weights"],
        "top_train_candidates": top_train,
        "interpretation": (
            "A score-only calibration on heldout1 does not solve heldout2. If heldout2 remains below its "
            "oracle, the residual is selector calibration; if the oracle itself is low, the candidate policy "
            "pool is also insufficient. This decomposition should guide the next experiment toward both "
            "candidate-policy expansion and selector distillation."
        ),
    }
    print(json.dumps(write_report(root, report, args.prefix), indent=2))


if __name__ == "__main__":
    main()
