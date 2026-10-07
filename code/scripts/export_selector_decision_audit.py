#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


SELECTOR_REPORTS = [
    ("locked_short_probe", "tables/portfolio_probe_selector.json"),
    ("locked_probe_1200", "tables/portfolio_probe_selector_1200.json"),
    ("heldout1_original", "tables/portfolio_probe_selector_1200_heldout_dagger_v2.json"),
    ("heldout2_original", "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json"),
    ("heldout1_expanded", "tables/portfolio_probe_selector_1200_heldout_expanded.json"),
    ("heldout2_expanded", "tables/portfolio_probe_selector_1200_heldout2_expanded.json"),
    ("heldout3_expanded", "tables/portfolio_probe_selector_1200_heldout3_expanded.json"),
    ("heldout3_targeted_expanded", "tables/portfolio_probe_selector_1200_heldout3_targeted_expanded.json"),
    ("heldout4_targeted_expanded", "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.json"),
]

PROBE_ONLY_FIELDS = {
    "method",
    "method_key",
    "model_path",
    "seed",
    "status",
    "summary",
    "log",
    "probe_score",
    "probe_progress",
    "probe_grass",
    "probe_rank",
    "probe_first_ahead_step",
    "probe_steps_run",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def priority(report, method):
    return report.get("tie_break_priority", {}).get(method, 0)


def decision_by_seed(report):
    return {int(row["seed"]): row for row in report.get("decisions", [])}


def candidate_rows(report, seed):
    return [
        row
        for row in report.get("probe_rows", [])
        if int(row["seed"]) == seed and row.get("status") == "PASS"
    ]


def score_tuple(report, row):
    return (float(row["probe_score"]), priority(report, row["method"]))


def margin(report, selected, candidates):
    others = [row for row in candidates if row["method"] != selected["method"]]
    if not others:
        return None
    runner_up = max(others, key=lambda row: score_tuple(report, row))
    return {
        "runner_up_method": runner_up["method"],
        "runner_up_probe_score": float(runner_up["probe_score"]),
        "runner_up_priority": priority(report, runner_up["method"]),
        "score_margin": float(selected["probe_score"]) - float(runner_up["probe_score"]),
        "priority_margin": priority(report, selected["method"]) - priority(report, runner_up["method"]),
    }


def audit_report(root, stage, rel):
    path = root / rel
    report = load_json(path)
    decisions = decision_by_seed(report)
    rows = []
    missing_candidate_seeds = []
    mismatches = []
    forbidden_probe_fields = sorted(
        {
            key
            for probe in report.get("probe_rows", [])
            for key in probe.keys()
            if key not in PROBE_ONLY_FIELDS
        }
    )
    for seed in report.get("seeds", []):
        seed = int(seed)
        candidates = candidate_rows(report, seed)
        decision = decisions.get(seed)
        if not candidates:
            missing_candidate_seeds.append(seed)
            continue
        recomputed = max(candidates, key=lambda row: score_tuple(report, row))
        margin_info = margin(report, recomputed, candidates) or {}
        selected_matches = decision is not None and recomputed["method"] == decision["selected_method"]
        score_matches = decision is not None and abs(float(recomputed["probe_score"]) - float(decision["probe_score"])) < 1e-12
        status_matches = decision is not None and recomputed.get("method_key") == decision.get("selected_method_key")
        if not (selected_matches and score_matches and status_matches):
            mismatches.append(seed)
        sorted_candidates = sorted(candidates, key=lambda row: score_tuple(report, row), reverse=True)
        top_tie_count = sum(score_tuple(report, row) == score_tuple(report, recomputed) for row in candidates)
        rows.append(
            {
                "stage": stage,
                "source": rel,
                "seed": seed,
                "candidate_count": len(candidates),
                "selected_method": decision.get("selected_method") if decision else "",
                "recomputed_method": recomputed["method"],
                "selected_method_key": decision.get("selected_method_key") if decision else "",
                "recomputed_method_key": recomputed.get("method_key", ""),
                "selected_probe_score": decision.get("probe_score") if decision else "",
                "recomputed_probe_score": recomputed["probe_score"],
                "selected_priority": priority(report, recomputed["method"]),
                "runner_up_method": margin_info.get("runner_up_method", ""),
                "runner_up_probe_score": margin_info.get("runner_up_probe_score", ""),
                "score_margin": margin_info.get("score_margin", ""),
                "priority_margin": margin_info.get("priority_margin", ""),
                "top_tie_count": top_tie_count,
                "selection_recomputed": selected_matches and score_matches and status_matches,
                "selected_full_status": decision.get("selected_full_status") if decision else "",
                "oracle_status": decision.get("oracle_status") if decision else "",
                "candidate_order": ";".join(row["method"] for row in sorted_candidates),
            }
        )
    return {
        "stage": stage,
        "source": rel,
        "probe_steps": report.get("probe_steps"),
        "method_count": len(report.get("methods", [])),
        "seed_count": len(report.get("seeds", [])),
        "probe_row_count": len(report.get("probe_rows", [])),
        "decision_count": len(report.get("decisions", [])),
        "pass_count": report.get("pass_count"),
        "oracle_pass_count": report.get("oracle_pass_count"),
        "mismatch_count": len(mismatches),
        "missing_candidate_seeds": missing_candidate_seeds,
        "mismatch_seeds": mismatches,
        "forbidden_probe_fields": forbidden_probe_fields,
        "rows": rows,
    }


def build_report(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    audits = [audit_report(root, stage, rel) for stage, rel in SELECTOR_REPORTS]
    rows = [row for audit in audits for row in audit["rows"]]
    stage_rows = []
    for audit in audits:
        stage_rows.append(
            {
                "stage": audit["stage"],
                "source": audit["source"],
                "probe_steps": audit["probe_steps"],
                "method_count": audit["method_count"],
                "seed_count": audit["seed_count"],
                "probe_row_count": audit["probe_row_count"],
                "decision_count": audit["decision_count"],
                "pass_count": audit["pass_count"],
                "oracle_pass_count": audit["oracle_pass_count"],
                "mismatch_count": audit["mismatch_count"],
                "missing_candidate_count": len(audit["missing_candidate_seeds"]),
                "forbidden_probe_field_count": len(audit["forbidden_probe_fields"]),
                "status": (
                    "pass"
                    if audit["mismatch_count"] == 0
                    and not audit["missing_candidate_seeds"]
                    and not audit["forbidden_probe_fields"]
                    else "fail"
                ),
            }
        )
    failing = [row for row in stage_rows if row["status"] != "pass"]
    margins = [float(row["score_margin"]) for row in rows if row["score_margin"] != ""]
    return {
        "root": str(root),
        "title": "Selector Decision Transparency Audit",
        "purpose": (
            "Recompute each online probe selector decision from saved probe rows using probe_score and the registered "
            "tie-break priority, and verify that selector decisions do not require full-rollout or oracle fields."
        ),
        "summary": {
            "selector_report_count": len(audits),
            "decision_row_count": len(rows),
            "failed_stage_count": len(failing),
            "total_mismatch_count": sum(row["mismatch_count"] for row in stage_rows),
            "total_missing_candidate_count": sum(row["missing_candidate_count"] for row in stage_rows),
            "total_forbidden_probe_field_count": sum(row["forbidden_probe_field_count"] for row in stage_rows),
            "minimum_score_margin": min(margins) if margins else None,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
            "status": "pass" if not failing else "fail",
        },
        "stage_rows": stage_rows,
        "decision_rows": rows,
        "interpretation": (
            "This is a static audit of saved selector reports. It verifies reproducibility of the recorded selector "
            "choice from probe telemetry and registered tie-breaks; oracle and full-rollout outcomes remain diagnostic "
            "labels used only after selection for evaluation."
        ),
    }


def write_csv(rows, path, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def write_markdown(report, path):
    lines = [
        "# Selector Decision Transparency Audit",
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
            "## Selector Reports",
            "",
            "| stage | status | seeds | methods | probe rows | decisions | mismatches | missing candidates | forbidden probe fields |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report["stage_rows"]:
        lines.append(
            f"| {row['stage']} | {row['status']} | {row['seed_count']} | {row['method_count']} | "
            f"{row['probe_row_count']} | {row['decision_count']} | {row['mismatch_count']} | "
            f"{row['missing_candidate_count']} | {row['forbidden_probe_field_count']} |"
        )
    lines.extend(
        [
            "",
            "## Decision Rows",
            "",
            "Per-seed recomputation rows are exported to `materials/SELECTOR_DECISION_AUDIT_ROWS.csv`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export selector decision transparency audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "SELECTOR_DECISION_AUDIT.json"
    out_md = materials / "SELECTOR_DECISION_AUDIT.md"
    stage_csv = materials / "SELECTOR_DECISION_AUDIT_STAGE_ROWS.csv"
    row_csv = materials / "SELECTOR_DECISION_AUDIT_ROWS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(
        report["stage_rows"],
        stage_csv,
        [
            "stage",
            "source",
            "probe_steps",
            "method_count",
            "seed_count",
            "probe_row_count",
            "decision_count",
            "pass_count",
            "oracle_pass_count",
            "mismatch_count",
            "missing_candidate_count",
            "forbidden_probe_field_count",
            "status",
        ],
    )
    write_csv(
        report["decision_rows"],
        row_csv,
        [
            "stage",
            "source",
            "seed",
            "candidate_count",
            "selected_method",
            "recomputed_method",
            "selected_method_key",
            "recomputed_method_key",
            "selected_probe_score",
            "recomputed_probe_score",
            "selected_priority",
            "runner_up_method",
            "runner_up_probe_score",
            "score_margin",
            "priority_margin",
            "top_tie_count",
            "selection_recomputed",
            "selected_full_status",
            "oracle_status",
            "candidate_order",
        ],
    )
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "stage_csv": str(stage_csv),
                "row_csv": str(row_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
