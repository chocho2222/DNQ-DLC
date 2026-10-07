#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


SELECTOR_SOURCES = [
    {
        "stage": "heldout1_original",
        "role": "first held-out selector validation",
        "seed_set": "heldout1",
        "source": "tables/portfolio_probe_selector_1200_heldout_dagger_v2.json",
        "evidence": "tables/heldout_generalization.md",
    },
    {
        "stage": "heldout2_original",
        "role": "second held-out stress repeat",
        "seed_set": "heldout2",
        "source": "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
        "evidence": "tables/heldout_generalization.md",
    },
    {
        "stage": "heldout1_expanded",
        "role": "regression check after candidate expansion",
        "seed_set": "heldout1",
        "source": "tables/portfolio_probe_selector_1200_heldout_expanded.json",
        "evidence": "tables/expanded_selector_generalization.md",
    },
    {
        "stage": "heldout2_expanded",
        "role": "candidate-expanded selector test",
        "seed_set": "heldout2",
        "source": "tables/portfolio_probe_selector_1200_heldout2_expanded.json",
        "evidence": "tables/expanded_selector_generalization.md",
    },
    {
        "stage": "heldout3_expanded",
        "role": "third disjoint external validation",
        "seed_set": "heldout3",
        "source": "tables/portfolio_probe_selector_1200_heldout3_expanded.json",
        "evidence": "tables/heldout3_external_validation.md",
    },
    {
        "stage": "heldout3_targeted_expanded",
        "role": "targeted diagnostic selector after heldout3 repair",
        "seed_set": "heldout3",
        "source": "tables/portfolio_probe_selector_1200_heldout3_targeted_expanded.json",
        "evidence": "tables/heldout3_targeted_selector_generalization.md",
    },
    {
        "stage": "heldout4_targeted_expanded",
        "role": "post-repair external validation",
        "seed_set": "heldout4",
        "source": "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.json",
        "evidence": "tables/heldout4_external_validation.md",
    },
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def error_type(selected_status, oracle_status):
    if selected_status == "PASS":
        return "pass"
    if oracle_status == "PASS":
        return "selector_miss"
    return "candidate_gap"


def float_or_none(value):
    if value is None:
        return None
    return float(value)


def selector_rows(root, spec):
    report = load_json(root / spec["source"])
    rows = []
    for row in report["decisions"]:
        selected_status = row["selected_full_status"]
        oracle_status = row["oracle_status"]
        rows.append(
            {
                "stage": spec["stage"],
                "role": spec["role"],
                "seed_set": spec["seed_set"],
                "seed": int(row["seed"]),
                "selected_method": row["selected_method"],
                "selected_method_key": row.get("selected_method_key"),
                "selected_status": selected_status,
                "selected_progress": float_or_none(row.get("selected_full_progress")),
                "selected_grass": float_or_none(row.get("selected_full_grass")),
                "selected_rank": row.get("selected_full_rank"),
                "oracle_method": row.get("oracle_method"),
                "oracle_status": oracle_status,
                "error_type": error_type(selected_status, oracle_status),
                "probe_score": float_or_none(row.get("probe_score")),
                "probe_progress": float_or_none(row.get("probe_progress")),
                "probe_grass": float_or_none(row.get("probe_grass")),
                "probe_rank": row.get("probe_rank"),
                "source_json": spec["source"],
                "primary_evidence": spec["evidence"],
            }
        )
    return rows


def summarize(rows):
    grouped = {}
    for row in rows:
        item = grouped.setdefault(
            row["stage"],
            {
                "stage": row["stage"],
                "role": row["role"],
                "seed_set": row["seed_set"],
                "n": 0,
                "selector_pass_count": 0,
                "oracle_pass_count": 0,
                "selector_miss_count": 0,
                "candidate_gap_count": 0,
                "strict_fail_count": 0,
                "pass_seeds": [],
                "selector_miss_seeds": [],
                "candidate_gap_seeds": [],
            },
        )
        item["n"] += 1
        if row["selected_status"] == "PASS":
            item["selector_pass_count"] += 1
            item["pass_seeds"].append(row["seed"])
        else:
            item["strict_fail_count"] += 1
        if row["oracle_status"] == "PASS":
            item["oracle_pass_count"] += 1
        if row["error_type"] == "selector_miss":
            item["selector_miss_count"] += 1
            item["selector_miss_seeds"].append(row["seed"])
        if row["error_type"] == "candidate_gap":
            item["candidate_gap_count"] += 1
            item["candidate_gap_seeds"].append(row["seed"])
    for item in grouped.values():
        for key in ["pass_seeds", "selector_miss_seeds", "candidate_gap_seeds"]:
            item[key] = sorted(item[key])
    return [grouped[key] for key in sorted(grouped)]


def build_report(root):
    rows = []
    for spec in SELECTOR_SOURCES:
        rows.extend(selector_rows(root, spec))
    summaries = summarize(rows)
    total = {
        "rows": len(rows),
        "stages": len(summaries),
        "selector_pass_count": sum(row["selected_status"] == "PASS" for row in rows),
        "oracle_pass_count": sum(row["oracle_status"] == "PASS" for row in rows),
        "selector_miss_count": sum(row["error_type"] == "selector_miss" for row in rows),
        "candidate_gap_count": sum(row["error_type"] == "candidate_gap" for row in rows),
    }
    return {
        "root": str(root),
        "source_specs": SELECTOR_SOURCES,
        "summary": total,
        "stage_summaries": summaries,
        "rows": rows,
        "interpretation": (
            "This ledger consolidates seed-level online-selector outcomes across held-out stages. "
            "It is intended for audit and reviewer navigation: selector_miss means the selected policy failed "
            "while the diagnostic oracle had a passing candidate; candidate_gap means no tested candidate passed."
        ),
    }


def write_csv(report, path):
    fields = [
        "stage",
        "role",
        "seed_set",
        "seed",
        "selected_method",
        "selected_method_key",
        "selected_status",
        "selected_progress",
        "selected_grass",
        "selected_rank",
        "oracle_method",
        "oracle_status",
        "error_type",
        "probe_score",
        "probe_progress",
        "probe_grass",
        "probe_rank",
        "source_json",
        "primary_evidence",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({key: row.get(key) for key in fields})


def write_summary_csv(report, path):
    fields = [
        "stage",
        "role",
        "seed_set",
        "n",
        "selector_pass_count",
        "oracle_pass_count",
        "selector_miss_count",
        "candidate_gap_count",
        "strict_fail_count",
        "pass_seeds",
        "selector_miss_seeds",
        "candidate_gap_seeds",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["stage_summaries"]:
            writer.writerow(
                {
                    key: (
                        ",".join(str(seed) for seed in row[key])
                        if key in {"pass_seeds", "selector_miss_seeds", "candidate_gap_seeds"}
                        else row[key]
                    )
                    for key in fields
                }
            )


def write_markdown(report, path):
    lines = [
        "# Seed Outcome Ledger",
        "",
        report["interpretation"],
        "",
        "## Overall Summary",
        "",
        f"- Rows: {report['summary']['rows']}",
        f"- Stages: {report['summary']['stages']}",
        f"- Selector PASS outcomes: {report['summary']['selector_pass_count']}",
        f"- Oracle PASS outcomes: {report['summary']['oracle_pass_count']}",
        f"- Selector misses: {report['summary']['selector_miss_count']}",
        f"- Candidate gaps: {report['summary']['candidate_gap_count']}",
        "",
        "## Stage Summary",
        "",
        "| stage | role | selector pass | oracle pass | selector misses | candidate gaps |",
        "|---|---|---:|---:|---|---|",
    ]
    for item in report["stage_summaries"]:
        lines.append(
            f"| {item['stage']} | {item['role']} | {item['selector_pass_count']}/{item['n']} | "
            f"{item['oracle_pass_count']}/{item['n']} | "
            f"{','.join(map(str, item['selector_miss_seeds'])) or 'none'} | "
            f"{','.join(map(str, item['candidate_gap_seeds'])) or 'none'} |"
        )
    lines.extend(
        [
            "",
            "## Seed-Level Rows",
            "",
            "The full ledger is available in `tables/seed_outcome_ledger.csv` and `tables/seed_outcome_ledger.json`.",
            "",
            "| stage | seed | selected | status | oracle | oracle status | error type |",
            "|---|---:|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['stage']} | {row['seed']} | {row['selected_method']} | {row['selected_status']} | "
            f"{row['oracle_method']} | {row['oracle_status']} | {row['error_type']} |"
        )
    lines.extend(
        [
            "",
            "## Reporting Boundary",
            "",
            "- Rows are copied from saved selector decision reports; this script does not rerun simulations.",
            "- Oracle columns are diagnostic upper bounds and are not online selector performance.",
            "- Heldout3-targeted rows are diagnostic because heldout3 guided the repair; heldout4 remains the post-repair external validation row group.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export seed-level online selector outcome ledger.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    table_dir = root / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = table_dir / "seed_outcome_ledger.json"
    out_md = table_dir / "seed_outcome_ledger.md"
    out_csv = table_dir / "seed_outcome_ledger.csv"
    out_summary_csv = table_dir / "seed_outcome_ledger_stage_summary.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    write_summary_csv(report, out_summary_csv)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "summary_csv": str(out_summary_csv),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
