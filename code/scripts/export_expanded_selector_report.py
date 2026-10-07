#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def summarize_selector(report):
    failed = []
    selector_misses = []
    candidate_gaps = []
    pass_seeds = []
    for row in report["decisions"]:
        seed = int(row["seed"])
        if row["selected_full_status"] == "PASS":
            pass_seeds.append(seed)
            continue
        failed.append(seed)
        if row["oracle_status"] == "PASS":
            selector_misses.append(seed)
        else:
            candidate_gaps.append(seed)
    return {
        "n": report["n"],
        "pass_count": report["pass_count"],
        "oracle_pass_count": report["oracle_pass_count"],
        "pass_seeds": pass_seeds,
        "failed_seeds": failed,
        "selector_miss_seeds": selector_misses,
        "candidate_gap_seeds": candidate_gaps,
        "methods": report["methods"],
    }


def decision_rows(label, report):
    rows = []
    for row in report["decisions"]:
        if row["selected_full_status"] == "PASS":
            error = "pass"
        elif row["oracle_status"] == "PASS":
            error = "selector_miss"
        else:
            error = "candidate_gap"
        rows.append(
            {
                "evaluation": label,
                "seed": int(row["seed"]),
                "selected_method": row["selected_method"],
                "selected_status": row["selected_full_status"],
                "oracle_method": row["oracle_method"],
                "oracle_status": row["oracle_status"],
                "probe_score": row["probe_score"],
                "probe_progress": row["probe_progress"],
                "probe_grass": row["probe_grass"],
                "error_type": error,
            }
        )
    return rows


def build_report(root):
    old_h1 = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout_dagger_v2.json")
    old_h2 = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout2_dagger_v2.json")
    expanded_h1 = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout_expanded.json")
    expanded_h2 = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout2_expanded.json")
    candidate_expansion = load_json(root / "tables" / "heldout2_candidate_expansion.json")

    rows = []
    rows.extend(decision_rows("heldout1_original", old_h1))
    rows.extend(decision_rows("heldout2_original", old_h2))
    rows.extend(decision_rows("heldout1_expanded", expanded_h1))
    rows.extend(decision_rows("heldout2_expanded", expanded_h2))

    summaries = {
        "heldout1_original": summarize_selector(old_h1),
        "heldout2_original": summarize_selector(old_h2),
        "heldout1_expanded": summarize_selector(expanded_h1),
        "heldout2_expanded": summarize_selector(expanded_h2),
    }
    return {
        "root": str(root),
        "summaries": summaries,
        "candidate_expansion": candidate_expansion["expanded_oracle"],
        "rows": rows,
        "interpretation": (
            "Adding the expert-more-graph DAgger-v2 candidate improves the 1200-step online simulator-loop "
            "selector on heldout2 from 5/10 to 7/10 while preserving heldout1 at 10/10. The expanded "
            "heldout2 oracle is 10/10, so the remaining failed seeds are selector misses rather than "
            "candidate-policy gaps. This supports the next step of learned or calibrated selector design, "
            "not a robustness claim."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "evaluation",
            "seed",
            "selected_method",
            "selected_status",
            "oracle_method",
            "oracle_status",
            "probe_score",
            "probe_progress",
            "probe_grass",
            "error_type",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({key: row[key] for key in fieldnames})


def write_markdown(report, path):
    lines = [
        "# Expanded Selector Generalization",
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        "| evaluation | selector pass | oracle pass | failed seeds | selector misses | candidate gaps |",
        "|---|---:|---:|---|---|---|",
    ]
    for name, item in report["summaries"].items():
        lines.append(
            f"| {name} | {item['pass_count']}/{item['n']} | {item['oracle_pass_count']}/{item['n']} | "
            f"{', '.join(map(str, item['failed_seeds'])) or 'none'} | "
            f"{', '.join(map(str, item['selector_miss_seeds'])) or 'none'} | "
            f"{', '.join(map(str, item['candidate_gap_seeds'])) or 'none'} |"
        )
    lines.extend(
        [
            "",
            "## Heldout2 Expanded Decisions",
            "",
            "| seed | selected | status | oracle | oracle status | error type | probe score |",
            "|---:|---|---|---|---|---|---:|",
        ]
    )
    for row in report["rows"]:
        if row["evaluation"] != "heldout2_expanded":
            continue
        lines.append(
            f"| {row['seed']} | {row['selected_method']} | {row['selected_status']} | "
            f"{row['oracle_method']} | {row['oracle_status']} | {row['error_type']} | "
            f"{row['probe_score']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Reporting Boundary",
            "",
            "- This is an online-probe selector result because selection uses probe telemetry, not full-rollout outcomes.",
            "- The oracle columns remain diagnostic upper bounds.",
            "- The expanded selector improves heldout2 but does not establish broad robustness evidence.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export old-vs-expanded online selector generalization report.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    out_json = root / "tables" / "expanded_selector_generalization.json"
    out_md = root / "tables" / "expanded_selector_generalization.md"
    out_csv = root / "tables" / "expanded_selector_generalization_rows.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
