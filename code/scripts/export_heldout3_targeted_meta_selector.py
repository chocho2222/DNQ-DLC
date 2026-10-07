#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


FULL_METHOD = {
    "dagger_v2_graph_expert_gate_shield": "graph_expert_gate_shield",
    "dagger_v2_graph_expert_gate_more_graph": "graph_expert_gate_shield_more_graph",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_full_rows(root, report):
    suites = {
        suite_name: load_json(root / rel_path)
        for suite_name, rel_path in report["suite_paths"].items()
        if (root / rel_path).exists()
    }
    rows = {}
    for method in report["methods"]:
        suite_name = method_suite(report, method)
        suite = suites[suite_name]
        full_method = FULL_METHOD.get(method, method)
        for row in suite["rows"]:
            if row["method"] == full_method:
                rows[(method, int(row["seed"]))] = row
    return rows


def method_suite(report, method):
    for probe in report["probe_rows"]:
        if probe["method"] == method:
            method_key = probe.get("method_key", "")
            if ":" in method_key:
                prefix = method_key.split(":", 1)[0]
                mapping = {
                    "main": "main",
                    "adaptive": "adaptive",
                    "expert": "expert",
                    "dagger_v2": "dagger_v2_more_graph"
                    if "more_graph" in method
                    else "dagger_v2",
                    "heldout3_targeted": "heldout3_traffic_adaptive_conservative",
                }
                return mapping[prefix]
    raise KeyError(method)


def build_rows(root, report):
    full = load_full_rows(root, report)
    rows = []
    for probe in report["probe_rows"]:
        if probe["status"] != "PASS":
            continue
        method = probe["method"]
        seed = int(probe["seed"])
        full_row = full[(method, seed)]
        progress = float(probe["probe_progress"])
        grass = float(probe["probe_grass"])
        rank = int(probe["probe_rank"])
        first_ahead = int(probe["probe_first_ahead_step"] is not None)
        rows.append(
            {
                "seed": seed,
                "method": method,
                "probe_score": float(probe["probe_score"]),
                "probe_progress": progress,
                "probe_grass": grass,
                "probe_rank": rank,
                "probe_first_ahead": first_ahead,
                "probe_steps_ratio": float(probe["probe_steps_run"]) / float(report["probe_steps"]),
                "progress_minus_grass": progress - grass,
                "rank_progress": progress / max(rank, 1),
                "full_status": full_row["validation_status"],
                "label": int(full_row["validation_status"] == "PASS"),
            }
        )
    return rows


def feature_matrix(rows, methods, include_method=True):
    matrix = []
    for row in rows:
        values = [
            row["probe_score"],
            row["probe_progress"],
            row["probe_grass"],
            row["probe_rank"],
            row["probe_first_ahead"],
            row["probe_steps_ratio"],
            row["progress_minus_grass"],
            row["rank_progress"],
        ]
        if include_method:
            values.extend(int(row["method"] == method) for method in methods)
        matrix.append(values)
    return np.asarray(matrix, dtype=float)


def make_models():
    return {
        "loso_logreg_feature_only": {
            "include_method": False,
            "model": make_pipeline(
                StandardScaler(),
                LogisticRegression(class_weight="balanced", max_iter=2000, random_state=0),
            ),
        },
        "loso_logreg_feature_method": {
            "include_method": True,
            "model": make_pipeline(
                StandardScaler(),
                LogisticRegression(class_weight="balanced", max_iter=2000, random_state=0),
            ),
        },
        "loso_rf_feature_method": {
            "include_method": True,
            "model": RandomForestClassifier(
                n_estimators=400,
                max_depth=4,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=0,
            ),
        },
        "loso_extratrees_feature_method": {
            "include_method": True,
            "model": ExtraTreesClassifier(
                n_estimators=400,
                max_depth=4,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=0,
            ),
        },
    }


def rank_by_probe(rows):
    return sorted(rows, key=lambda row: row["probe_score"], reverse=True)


def seed_oracle(rows):
    return max(rows, key=lambda row: (row["label"], row["probe_score"]))


def summarize(decisions):
    return {
        "n": len(decisions),
        "pass_count": sum(row["selected_status"] == "PASS" for row in decisions),
        "oracle_pass_count": sum(row["oracle_status"] == "PASS" for row in decisions),
        "failed_seeds": [row["seed"] for row in decisions if row["selected_status"] != "PASS"],
        "selector_miss_seeds": [row["seed"] for row in decisions if row["selector_miss"]],
        "candidate_gap_seeds": [row["seed"] for row in decisions if row["candidate_gap"]],
    }


def evaluate_loso(rows, methods, spec):
    seeds = sorted({row["seed"] for row in rows})
    decisions = []
    include_method = spec["include_method"]
    for seed in seeds:
        train = [row for row in rows if row["seed"] != seed]
        test = [row for row in rows if row["seed"] == seed]
        model = spec["model"]
        labels = np.asarray([row["label"] for row in train])
        if len(set(labels.tolist())) < 2:
            ranked = rank_by_probe(test)
            selected = ranked[0]
            score = selected["probe_score"]
        else:
            model.fit(feature_matrix(train, methods, include_method), labels)
            probs = model.predict_proba(feature_matrix(test, methods, include_method))[:, 1]
            score, selected = max(zip(probs.tolist(), test), key=lambda item: item[0])
        oracle = seed_oracle(test)
        decisions.append(
            {
                "seed": seed,
                "selected_method": selected["method"],
                "selected_status": selected["full_status"],
                "selected_score": float(score),
                "selected_probe_score": selected["probe_score"],
                "oracle_method": oracle["method"],
                "oracle_status": oracle["full_status"],
                "selector_miss": oracle["label"] == 1 and selected["label"] == 0,
                "candidate_gap": oracle["label"] == 0,
            }
        )
    return decisions


def evaluate_oracle_signal(rows):
    decisions = []
    for seed in sorted({row["seed"] for row in rows}):
        seed_rows = [row for row in rows if row["seed"] == seed]
        oracle = seed_oracle(seed_rows)
        decisions.append(
            {
                "seed": seed,
                "selected_method": oracle["method"],
                "selected_status": oracle["full_status"],
                "selected_score": oracle["probe_score"],
                "selected_probe_score": oracle["probe_score"],
                "oracle_method": oracle["method"],
                "oracle_status": oracle["full_status"],
                "selector_miss": False,
                "candidate_gap": oracle["label"] == 0,
            }
        )
    return decisions


def build_report(root):
    report = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout3_targeted_expanded.json")
    rows = build_rows(root, report)
    methods = report["methods"]

    variants = {}
    flat_rows = []
    for name, spec in make_models().items():
        decisions = evaluate_loso(rows, methods, spec)
        variants[name] = {
            "summary": summarize(decisions),
            "decisions": decisions,
        }
        for decision in decisions:
            flat_rows.append({"variant": name, **decision})

    oracle_decisions = evaluate_oracle_signal(rows)
    deployed = load_json(root / "tables" / "heldout3_targeted_selector_generalization.json")
    best_name, best_variant = max(
        variants.items(),
        key=lambda item: (item[1]["summary"]["pass_count"], -len(item[1]["summary"]["selector_miss_seeds"])),
    )
    return {
        "root": str(root),
        "source_selector": "tables/portfolio_probe_selector_1200_heldout3_targeted_expanded.json",
        "methods": methods,
        "samples": len(rows),
        "seeds": report["seeds"],
        "deployed_targeted_selector": deployed["targeted_selector"],
        "oracle": summarize(oracle_decisions),
        "variants": variants,
        "best_variant": best_name,
        "best_summary": best_variant["summary"],
        "rows": flat_rows,
        "interpretation": (
            "This is a within-heldout3 leave-one-seed-out selector diagnostic. It tests whether the saved "
            "1200-step probe features contain enough signal to recover a better selector when labels from "
            "neighboring heldout3 seeds are allowed. It is not external validation, because each fold trains "
            "on the same heldout3 stress distribution. A positive result would motivate a pre-registered "
            "selector trained before heldout4; a weak result would indicate that richer probe features or "
            "longer probes are needed."
        ),
    }


def write_outputs(root, report, prefix):
    tables = root / "tables"
    out_json = tables / f"{prefix}.json"
    out_md = tables / f"{prefix}.md"
    out_csv = tables / f"{prefix}_rows.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "variant",
            "seed",
            "selected_method",
            "selected_status",
            "selected_score",
            "selected_probe_score",
            "oracle_method",
            "oracle_status",
            "selector_miss",
            "candidate_gap",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({key: row[key] for key in fieldnames})

    lines = [
        "# Heldout3 Targeted Meta-Selector Diagnostic",
        "",
        "## Summary",
        "",
        (
            "- Deployed targeted selector: "
            f"{report['deployed_targeted_selector']['pass_count']}/{report['deployed_targeted_selector']['n']}."
        ),
        f"- Candidate oracle over the same pool: {report['oracle']['oracle_pass_count']}/{report['oracle']['n']}.",
        (
            f"- Best LOSO meta-selector: `{report['best_variant']}` with "
            f"{report['best_summary']['pass_count']}/{report['best_summary']['n']} strict PASS."
        ),
        f"- Best LOSO selector misses: {report['best_summary']['selector_miss_seeds']}.",
        f"- Candidate gaps under the same pool: {report['oracle']['candidate_gap_seeds']}.",
        "",
        "## Variants",
        "",
        "| variant | pass | oracle | failed seeds | selector misses | candidate gaps |",
        "|---|---:|---:|---|---|---|",
    ]
    for name, variant in report["variants"].items():
        summary = variant["summary"]
        lines.append(
            f"| {name} | {summary['pass_count']}/{summary['n']} | "
            f"{summary['oracle_pass_count']}/{summary['n']} | {summary['failed_seeds']} | "
            f"{summary['selector_miss_seeds']} | {summary['candidate_gap_seeds']} |"
        )
    lines.extend(["", "## Best Variant Decisions", "", "| seed | selected | status | oracle | oracle status |", "|---:|---|---|---|---|"])
    for row in report["variants"][report["best_variant"]]["decisions"]:
        lines.append(
            f"| {row['seed']} | {row['selected_method']} | {row['selected_status']} | "
            f"{row['oracle_method']} | {row['oracle_status']} |"
        )
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}


def main():
    parser = argparse.ArgumentParser(description="Export heldout3 targeted leave-one-seed-out meta-selector diagnostics.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--prefix", default="heldout3_targeted_meta_selector")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    print(json.dumps(write_outputs(root, report, args.prefix), indent=2))


if __name__ == "__main__":
    main()
