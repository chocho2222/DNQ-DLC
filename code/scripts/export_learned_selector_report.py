#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


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


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_full_rows(root, report):
    rows = {}
    loaded = {
        suite: load_json(root / rel_path)
        for suite, rel_path in report["suite_paths"].items()
        if (root / rel_path).exists()
    }
    for method in report["methods"]:
        suite = loaded[METHOD_SUITE[method]]
        full_method = FULL_METHOD.get(method, method)
        for row in suite["rows"]:
            if row["method"] == full_method:
                rows[(method, int(row["seed"]))] = row
    return rows


def candidate_rows(root, report):
    full = load_full_rows(root, report)
    rows = []
    for probe in report["probe_rows"]:
        method = probe["method"]
        seed = int(probe["seed"])
        full_row = full[(method, seed)]
        rows.append(
            {
                "seed": seed,
                "method": method,
                "probe_progress": float(probe["probe_progress"]),
                "probe_grass": float(probe["probe_grass"]),
                "probe_rank": int(probe["probe_rank"]),
                "probe_first_ahead": int(probe["probe_first_ahead_step"] is not None),
                "probe_steps_ratio": float(probe["probe_steps_run"]) / float(report["probe_steps"]),
                "full_status": full_row["validation_status"],
                "label": int(full_row["validation_status"] == "PASS"),
            }
        )
    return rows


def feature_matrix(rows, methods, include_method):
    matrix = []
    for row in rows:
        values = [
            row["probe_progress"],
            row["probe_grass"],
            row["probe_rank"],
            row["probe_first_ahead"],
            row["probe_steps_ratio"],
        ]
        if include_method:
            values.extend(int(row["method"] == method) for method in methods)
        matrix.append(values)
    return np.asarray(matrix, dtype=float)


def make_models():
    return {
        "feature_only_logreg": {
            "include_method": False,
            "model": make_pipeline(
                StandardScaler(),
                LogisticRegression(class_weight="balanced", max_iter=1000, random_state=0),
            ),
            "description": "balanced logistic regression over probe telemetry only",
        },
        "feature_plus_method_logreg": {
            "include_method": True,
            "model": make_pipeline(
                StandardScaler(),
                LogisticRegression(class_weight="balanced", max_iter=1000, random_state=0),
            ),
            "description": "balanced logistic regression over probe telemetry plus method identity",
        },
        "feature_only_rf": {
            "include_method": False,
            "model": RandomForestClassifier(
                n_estimators=200,
                max_depth=3,
                random_state=0,
                class_weight="balanced",
            ),
            "description": "shallow balanced random forest over probe telemetry only",
        },
        "feature_plus_method_rf": {
            "include_method": True,
            "model": RandomForestClassifier(
                n_estimators=200,
                max_depth=3,
                random_state=0,
                class_weight="balanced",
            ),
            "description": "shallow balanced random forest over probe telemetry plus method identity",
        },
    }


def evaluate(model, rows, methods, include_method):
    probs = model.predict_proba(feature_matrix(rows, methods, include_method))[:, 1]
    by_seed = {}
    for row, prob in zip(rows, probs):
        by_seed.setdefault(row["seed"], []).append((float(prob), row))
    decisions = []
    for seed in sorted(by_seed):
        prob, row = max(by_seed[seed], key=lambda item: item[0])
        oracle = max(by_seed[seed], key=lambda item: item[1]["label"])[1]
        decisions.append(
            {
                "seed": seed,
                "selected_method": row["method"],
                "selected_status": row["full_status"],
                "selected_probability": prob,
                "oracle_method": oracle["method"],
                "oracle_status": oracle["full_status"],
                "selector_miss": oracle["label"] == 1 and row["label"] == 0,
                "candidate_gap": oracle["label"] == 0,
            }
        )
    return decisions


def summarize(decisions):
    return {
        "n": len(decisions),
        "pass_count": sum(row["selected_status"] == "PASS" for row in decisions),
        "oracle_pass_count": sum(row["oracle_status"] == "PASS" for row in decisions),
        "failed_seeds": [row["seed"] for row in decisions if row["selected_status"] != "PASS"],
        "selector_miss_seeds": [row["seed"] for row in decisions if row["selector_miss"]],
        "candidate_gap_seeds": [row["seed"] for row in decisions if row["candidate_gap"]],
    }


def build_report(root):
    train_report = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout_expanded.json")
    test_report = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout2_expanded.json")
    external_report_path = root / "tables" / "portfolio_probe_selector_1200_heldout3_expanded.json"
    external_report = load_json(external_report_path) if external_report_path.exists() else None
    expanded = load_json(root / "tables" / "expanded_selector_generalization.json")
    train_rows = candidate_rows(root, train_report)
    test_rows = candidate_rows(root, test_report)
    external_rows = candidate_rows(root, external_report) if external_report else None
    methods = train_report["methods"]

    variants = {}
    rows = []
    for name, spec in make_models().items():
        include_method = spec["include_method"]
        model = spec["model"]
        model.fit(feature_matrix(train_rows, methods, include_method), np.asarray([row["label"] for row in train_rows]))
        train_decisions = evaluate(model, train_rows, methods, include_method)
        test_decisions = evaluate(model, test_rows, methods, include_method)
        external_decisions = evaluate(model, external_rows, methods, include_method) if external_rows else []
        variants[name] = {
            "description": spec["description"],
            "include_method": include_method,
            "train": summarize(train_decisions),
            "test": summarize(test_decisions),
            "external_heldout3": summarize(external_decisions) if external_rows else None,
            "train_decisions": train_decisions,
            "test_decisions": test_decisions,
            "external_heldout3_decisions": external_decisions,
        }
        split_decisions = [("train_heldout1", train_decisions), ("test_heldout2", test_decisions)]
        if external_rows:
            split_decisions.append(("external_heldout3", external_decisions))
        for split, decisions in split_decisions:
            for decision in decisions:
                rows.append({"variant": name, "split": split, **decision})

    primary = "feature_only_logreg"
    return {
        "root": str(root),
        "train_set": "heldout1_expanded",
        "test_set": "heldout2_expanded",
        "external_set": "heldout3_expanded" if external_rows else None,
        "methods": methods,
        "training_samples": len(train_rows),
        "test_samples": len(test_rows),
        "external_samples": len(external_rows) if external_rows else 0,
        "primary_variant": primary,
        "baseline_expanded_selector": {
            "heldout1": expanded["summaries"]["heldout1_expanded"],
            "heldout2": expanded["summaries"]["heldout2_expanded"],
        },
        "variants": variants,
        "rows": rows,
        "interpretation": (
            "A feature-only logistic learned selector trained on heldout1 probe telemetry improves heldout2 "
            "from 7/10 to 8/10, but it also reduces heldout1 from 10/10 to 9/10. Method-identity variants "
            "overfit the first held-out batch and drop to 5/10 on heldout2. On the external heldout3 batch, "
            "the primary learned selector falls to 4/10, matching the expanded online selector and below "
            "the 8/10 heldout3 oracle. This is an exploratory learned-selector diagnostic, not an accepted "
            "replacement selector or robustness result."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "variant",
            "split",
            "seed",
            "selected_method",
            "selected_status",
            "selected_probability",
            "oracle_method",
            "oracle_status",
            "selector_miss",
            "candidate_gap",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({key: row[key] for key in fieldnames})


def write_markdown(report, path):
    lines = [
        "# Learned Selector Report",
        "",
        report["interpretation"],
        "",
        "## Setup",
        "",
        f"- Train set: `{report['train_set']}`",
        f"- Test set: `{report['test_set']}`",
        f"- Candidate samples: {report['training_samples']} train, {report['test_samples']} test",
        f"- External samples: {report['external_samples']}",
        f"- Primary exploratory variant: `{report['primary_variant']}`",
        "",
        "## Variant Summary",
        "",
        "| variant | train pass | heldout2 pass | heldout2 oracle | heldout3 pass | heldout3 oracle | heldout3 failed seeds |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for name, variant in report["variants"].items():
        train = variant["train"]
        test = variant["test"]
        external = variant["external_heldout3"]
        if external:
            lines.append(
                f"| {name} | {train['pass_count']}/{train['n']} | {test['pass_count']}/{test['n']} | "
                f"{test['oracle_pass_count']}/{test['n']} | "
                f"{external['pass_count']}/{external['n']} | "
                f" {external['oracle_pass_count']}/{external['n']} | "
                f"{', '.join(map(str, external['failed_seeds'])) or 'none'} |"
            )
        else:
            lines.append(
                f"| {name} | {train['pass_count']}/{train['n']} | {test['pass_count']}/{test['n']} | "
                f"{test['oracle_pass_count']}/{test['n']} |  |  |  |"
            )
    lines.extend(
        [
            "",
            "## Primary Heldout2 Decisions",
            "",
            "| seed | selected | status | probability | oracle | oracle status | error type |",
            "|---:|---|---|---:|---|---|---|",
        ]
    )
    primary = report["variants"][report["primary_variant"]]
    for row in primary["test_decisions"]:
        error = "candidate_gap" if row["candidate_gap"] else ("selector_miss" if row["selector_miss"] else "pass")
        lines.append(
            f"| {row['seed']} | {row['selected_method']} | {row['selected_status']} | "
            f"{row['selected_probability']:.3f} | {row['oracle_method']} | {row['oracle_status']} | {error} |"
        )
    if primary["external_heldout3_decisions"]:
        lines.extend(
            [
                "",
                "## Primary Heldout3 Decisions",
                "",
                "| seed | selected | status | probability | oracle | oracle status | error type |",
                "|---:|---|---|---:|---|---|---|",
            ]
        )
        for row in primary["external_heldout3_decisions"]:
            error = "candidate_gap" if row["candidate_gap"] else ("selector_miss" if row["selector_miss"] else "pass")
            lines.append(
                f"| {row['seed']} | {row['selected_method']} | {row['selected_status']} | "
                f"{row['selected_probability']:.3f} | {row['oracle_method']} | {row['oracle_status']} | {error} |"
            )
    lines.extend(
        [
            "",
            "## Reporting Boundary",
            "",
            "- The primary learned selector is trained only on heldout1 expanded probe/full labels and tested on heldout2.",
            "- The primary variant improves heldout2 but does not preserve heldout1, so it is not an accepted replacement selector.",
            "- Heldout3 is an external validation batch and shows that the heldout2 improvement does not generalize.",
            "- The improvement to 8/10 does not establish broad robustness evidence.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export learned selector diagnostics for expanded candidate pool.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    out_json = root / "tables" / "learned_selector_report.json"
    out_md = root / "tables" / "learned_selector_report.md"
    out_csv = root / "tables" / "learned_selector_rows.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    primary = report["variants"][report["primary_variant"]]["test"]
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "primary_test": f"{primary['pass_count']}/{primary['n']}",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
