#!/usr/bin/env python
import argparse
import csv
import json
from collections import Counter
from pathlib import Path


METHOD_SUITE = {
    "lane_base_only": "main",
    "overtake_base_only": "main",
    "graph_adaptive_shield": "adaptive",
    "expert_gate_only": "expert",
    "dagger_v2_graph_expert_gate_shield": "dagger_v2",
    "dagger_v2_graph_expert_gate_more_graph": "dagger_v2_more_graph",
}

FULL_METHOD = {
    "dagger_v2_graph_expert_gate_shield": "graph_expert_gate_shield",
    "dagger_v2_graph_expert_gate_more_graph": "graph_expert_gate_shield_more_graph",
}

PRIORITY_LISTS = [
    [
        "dagger_v2_graph_expert_gate_more_graph",
        "dagger_v2_graph_expert_gate_shield",
        "expert_gate_only",
        "graph_adaptive_shield",
        "overtake_base_only",
        "lane_base_only",
    ],
    [
        "dagger_v2_graph_expert_gate_shield",
        "dagger_v2_graph_expert_gate_more_graph",
        "expert_gate_only",
        "graph_adaptive_shield",
        "overtake_base_only",
        "lane_base_only",
    ],
    [
        "graph_adaptive_shield",
        "dagger_v2_graph_expert_gate_more_graph",
        "dagger_v2_graph_expert_gate_shield",
        "overtake_base_only",
        "expert_gate_only",
        "lane_base_only",
    ],
    [
        "overtake_base_only",
        "graph_adaptive_shield",
        "dagger_v2_graph_expert_gate_more_graph",
        "dagger_v2_graph_expert_gate_shield",
        "expert_gate_only",
        "lane_base_only",
    ],
    [
        "expert_gate_only",
        "dagger_v2_graph_expert_gate_more_graph",
        "dagger_v2_graph_expert_gate_shield",
        "graph_adaptive_shield",
        "overtake_base_only",
        "lane_base_only",
    ],
    [
        "lane_base_only",
        "overtake_base_only",
        "graph_adaptive_shield",
        "expert_gate_only",
        "dagger_v2_graph_expert_gate_shield",
        "dagger_v2_graph_expert_gate_more_graph",
    ],
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def priority_map(priority):
    return {method: len(priority) - index for index, method in enumerate(priority)}


def load_full_rows(root, report):
    rows = {}
    needed_suites = {METHOD_SUITE[method] for method in report["methods"]}
    loaded = {}
    for suite, rel_path in report["suite_paths"].items():
        if suite in needed_suites and (root / rel_path).exists():
            loaded[suite] = load_json(root / rel_path)
    for method in report["methods"]:
        suite = loaded[METHOD_SUITE[method]]
        full_method = FULL_METHOD.get(method, method)
        for row in suite["rows"]:
            if row["method"] == full_method:
                rows[(method, int(row["seed"]))] = row
    return rows


def candidate_score(row, params):
    progress_weight, grass_weight, rank_penalty, first_ahead_bonus = params
    return (
        progress_weight * float(row["probe_progress"])
        - grass_weight * float(row["probe_grass"])
        - rank_penalty * max(0, int(row["probe_rank"]) - 1)
        + first_ahead_bonus * int(row["probe_first_ahead_step"] is not None)
    )


def decide(report, full_rows, params, priority):
    priorities = priority_map(priority)
    decisions = []
    for seed in report["seeds"]:
        seed = int(seed)
        rows = [row for row in report["probe_rows"] if int(row["seed"]) == seed and row["status"] == "PASS"]
        selected = max(rows, key=lambda row: (candidate_score(row, params), priorities.get(row["method"], 0)))
        full = full_rows[(selected["method"], seed)]
        oracle_method = max(
            report["methods"],
            key=lambda method: (
                full_rows[(method, seed)]["validation_status"] == "PASS",
                priorities.get(method, 0),
            ),
        )
        oracle = full_rows[(oracle_method, seed)]
        decisions.append(
            {
                "seed": seed,
                "selected_method": selected["method"],
                "selected_status": full["validation_status"],
                "score": candidate_score(selected, params),
                "probe_progress": selected["probe_progress"],
                "probe_grass": selected["probe_grass"],
                "probe_rank": selected["probe_rank"],
                "oracle_method": oracle_method,
                "oracle_status": oracle["validation_status"],
                "selector_miss": oracle["validation_status"] == "PASS" and full["validation_status"] != "PASS",
                "candidate_gap": oracle["validation_status"] != "PASS",
            }
        )
    return decisions


def pass_count(decisions):
    return sum(row["selected_status"] == "PASS" for row in decisions)


def grid_params():
    for progress_weight in [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0]:
        for grass_weight in [0.0, 0.25, 0.5, 1.0, 1.75, 2.5, 3.5, 5.0, 7.0]:
            for rank_penalty in [0.0, 0.15, 0.3, 0.45, 0.7, 1.0, 1.5]:
                for first_ahead_bonus in [0.0, 0.05, 0.1, 0.2, 0.4]:
                    yield (progress_weight, grass_weight, rank_penalty, first_ahead_bonus)


def params_dict(params):
    return {
        "progress_weight": params[0],
        "grass_weight": params[1],
        "rank_penalty": params[2],
        "first_ahead_bonus": params[3],
    }


def top_probe_rows(report, seeds):
    out = []
    for seed in seeds:
        rows = [row for row in report["probe_rows"] if int(row["seed"]) == int(seed)]
        rows.sort(key=lambda row: row["probe_score"], reverse=True)
        out.append(
            {
                "seed": int(seed),
                "top_probe_methods": [
                    {
                        "method": row["method"],
                        "probe_score": row["probe_score"],
                        "probe_progress": row["probe_progress"],
                        "probe_grass": row["probe_grass"],
                        "probe_rank": row["probe_rank"],
                    }
                    for row in rows[:6]
                ],
            }
        )
    return out


def build_report(root):
    heldout1 = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout_expanded.json")
    heldout2 = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout2_expanded.json")
    expanded = load_json(root / "tables" / "expanded_selector_generalization.json")
    full_h1 = load_full_rows(root, heldout1)
    full_h2 = load_full_rows(root, heldout2)

    rows = []
    for params in grid_params():
        for priority in PRIORITY_LISTS:
            train_decisions = decide(heldout1, full_h1, params, priority)
            test_decisions = decide(heldout2, full_h2, params, priority)
            rows.append(
                {
                    "params": params_dict(params),
                    "priority": priority,
                    "heldout1_pass_count": pass_count(train_decisions),
                    "heldout2_pass_count": pass_count(test_decisions),
                    "heldout2_decisions": test_decisions,
                }
            )

    train_perfect = [row for row in rows if row["heldout1_pass_count"] == heldout1["n"]]
    best_train_perfect = max(train_perfect, key=lambda row: row["heldout2_pass_count"])
    distribution = Counter(row["heldout2_pass_count"] for row in train_perfect)
    residual = expanded["summaries"]["heldout2_expanded"]["selector_miss_seeds"]

    return {
        "root": str(root),
        "train_set": "heldout1_expanded",
        "test_set": "heldout2_expanded",
        "methods": heldout1["methods"],
        "grid": {
            "parameter_count": len(list(grid_params())),
            "priority_count": len(PRIORITY_LISTS),
            "total_configs": len(rows),
            "heldout1_perfect_configs": len(train_perfect),
        },
        "original_expanded_selector": {
            "heldout1": {
                "pass_count": expanded["summaries"]["heldout1_expanded"]["pass_count"],
                "n": expanded["summaries"]["heldout1_expanded"]["n"],
            },
            "heldout2": {
                "pass_count": expanded["summaries"]["heldout2_expanded"]["pass_count"],
                "n": expanded["summaries"]["heldout2_expanded"]["n"],
            },
            "heldout2_oracle": {
                "pass_count": expanded["summaries"]["heldout2_expanded"]["oracle_pass_count"],
                "n": expanded["summaries"]["heldout2_expanded"]["n"],
            },
        },
        "train_perfect_test_distribution": dict(sorted(distribution.items())),
        "best_train_perfect": best_train_perfect,
        "grid_rows": [
            {
                "params": row["params"],
                "priority": row["priority"],
                "heldout1_pass_count": row["heldout1_pass_count"],
                "heldout2_pass_count": row["heldout2_pass_count"],
            }
            for row in rows
        ],
        "residual_selector_miss_probe_ambiguity": top_probe_rows(heldout2, residual),
        "interpretation": (
            "A heldout1-only expanded selector distillation does not improve beyond the online expanded "
            "selector: the best heldout1-perfect grid configuration remains at 7/10 on heldout2. Because the "
            "expanded heldout2 oracle is 10/10, the residual gap is a selector-learning problem rather than a "
            "candidate-coverage problem. This negative result argues for richer learned selectors and new "
            "held-out validation, not more scalar probe-score retuning."
        ),
    }


def write_csv(report, root):
    path = root / "tables" / "expanded_selector_distillation_grid.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "progress_weight",
            "grass_weight",
            "rank_penalty",
            "first_ahead_bonus",
            "priority",
            "heldout1_pass_count",
            "heldout2_pass_count",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["grid_rows"]:
            writer.writerow(
                {
                    **row["params"],
                    "priority": ",".join(row["priority"]),
                    "heldout1_pass_count": row["heldout1_pass_count"],
                    "heldout2_pass_count": row["heldout2_pass_count"],
                }
            )
    return path


def write_markdown(report, path):
    original = report["original_expanded_selector"]
    best = report["best_train_perfect"]
    lines = [
        "# Expanded Selector Distillation Report",
        "",
        report["interpretation"],
        "",
        "## Setup",
        "",
        f"- Train/calibration set: `{report['train_set']}`",
        f"- Test set: `{report['test_set']}`",
        f"- Methods: {', '.join(report['methods'])}",
        f"- Grid configs: {report['grid']['total_configs']}",
        f"- Heldout1-perfect configs: {report['grid']['heldout1_perfect_configs']}",
        "",
        "## Main Result",
        "",
        f"- Online expanded selector heldout1: {original['heldout1']['pass_count']}/{original['heldout1']['n']}",
        f"- Online expanded selector heldout2: {original['heldout2']['pass_count']}/{original['heldout2']['n']}",
        f"- Expanded heldout2 oracle over same candidates: {original['heldout2_oracle']['pass_count']}/{original['heldout2_oracle']['n']}",
        f"- Best heldout1-perfect grid selector on heldout2: {best['heldout2_pass_count']}/{original['heldout2']['n']}",
        "",
        "## Heldout2 Distribution Among Heldout1-perfect Selectors",
        "",
        "| heldout2 pass count | number of heldout1-perfect configs |",
        "|---:|---:|",
    ]
    for pass_value, count in report["train_perfect_test_distribution"].items():
        lines.append(f"| {pass_value} | {count} |")
    lines.extend(
        [
            "",
            "## Best Heldout1-perfect Configuration",
            "",
            f"- Params: `{best['params']}`",
            f"- Priority: `{', '.join(best['priority'])}`",
            "",
            "| seed | selected | status | oracle | oracle status | score |",
            "|---:|---|---|---|---|---:|",
        ]
    )
    for row in best["heldout2_decisions"]:
        lines.append(
            f"| {row['seed']} | {row['selected_method']} | {row['selected_status']} | "
            f"{row['oracle_method']} | {row['oracle_status']} | {row['score']:.3f} |"
        )
    lines.extend(["", "## Residual Selector-miss Probe Ambiguity", ""])
    for item in report["residual_selector_miss_probe_ambiguity"]:
        lines.extend([f"### Seed {item['seed']}", "", "| method | probe score | progress | grass | rank |", "|---|---:|---:|---:|---:|"])
        for row in item["top_probe_methods"]:
            lines.append(
                f"| {row['method']} | {row['probe_score']:.3f} | {row['probe_progress']:.3f} | "
                f"{row['probe_grass']:.3f} | {row['probe_rank']} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export expanded heldout1-to-heldout2 selector distillation diagnostic.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    out_json = root / "tables" / "expanded_selector_distillation_report.json"
    out_md = root / "tables" / "expanded_selector_distillation_report.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    out_csv = write_csv(report, root)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "best_heldout2": report["best_train_perfect"]["heldout2_pass_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
