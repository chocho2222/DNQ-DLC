#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def as_path_list(values):
    return "; ".join(values) if isinstance(values, list) else str(values)


def row(
    row_id,
    theme,
    status,
    evidence,
    action,
    boundary,
    decision_gate,
    claim_boundary,
    next_validation,
    primary_evidence,
    requires_new_experiment,
):
    return {
        "id": row_id,
        "theme": theme,
        "status": status,
        "evidence": evidence,
        "action": action,
        "boundary": boundary,
        "decision_gate": decision_gate,
        "claim_boundary": claim_boundary,
        "next_validation": next_validation,
        "primary_evidence": primary_evidence,
        "requires_new_experiment": requires_new_experiment,
    }


def claim_by_id(claims):
    return {item["id"]: item for item in claims["claims"]}


def readiness_by_id(readiness):
    return {item["id"]: item for item in readiness["rows"]}


def cross_entry(cross, heldout, stage=None):
    for item in cross["entries"]:
        if item["heldout"] == heldout and (stage is None or item["stage"] == stage):
            return item
    raise KeyError(f"{heldout}:{stage}")


def build_report(root):
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    downgrade = load_json(root / "materials" / "CLAIM_BOUNDARY_COMMUNICATION_PACK.json")
    readiness = load_json(root / "materials" / "TOP_JOURNAL_READINESS_CHECKLIST.json")
    roadmap = load_json(root / "materials" / "CONFIRMATORY_ROADMAP.json")
    cross = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")
    ledger = load_json(root / "tables" / "seed_outcome_ledger.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    external = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")

    claim_lookup = claim_by_id(claims)
    ready_lookup = readiness_by_id(readiness)
    roadmap_lookup = {item["gap_id"]: item for item in roadmap["rows"]}

    h1 = cross_entry(cross, "heldout1", "five_candidate_original")
    h2 = cross_entry(cross, "heldout2", "six_candidate_expanded")
    h3 = cross_entry(cross, "heldout3", "six_candidate_external")
    h4 = cross_entry(cross, "heldout4", "seven_candidate_external_after_targeted_repair")

    rows = [
        row(
            "DT01",
            "baseline_and_main_result",
            "claim_allowed_with_boundary",
            claim_lookup["C1_locked_baseline_strength"]["claim"],
            "State the locked strict-protocol baseline comparison and preserve all baseline rows for reviewer inspection.",
            claim_lookup["C1_locked_baseline_strength"]["do_not_claim"],
            "Allowed only when baseline fairness audit, full statistical report, and source-data tables remain present and unchanged.",
            "This supports bounded simulator comparison, not uniform dominance by the learned graph method.",
            "Use the same locked validation endpoint for any added baseline or candidate policy.",
            as_path_list(claim_lookup["C1_locked_baseline_strength"]["primary_evidence"]),
            False,
        ),
        row(
            "DT02",
            "diagnostic_oracle_boundary",
            "diagnostic_upper_bound_only",
            claim_lookup["C2_oracle_complementarity"]["claim"],
            "Use oracle rows only to decompose candidate-policy coverage versus selector misses.",
            claim_lookup["C2_oracle_complementarity"]["do_not_claim"],
            "If a result uses full-rollout outcomes, label it diagnostic upper bound and never online control.",
            "Oracle performance cannot be reported as deployed, deployable, or online-selector performance.",
            "A selector claim requires probe-only or feature-only decision fields and selector decision audit rows.",
            "tables/portfolio_oracle.md; tables/seed_outcome_ledger.md; materials/SELECTOR_DECISION_AUDIT.md",
            False,
        ),
        row(
            "DT03",
            "heldout1_positive_boundary",
            "claim_allowed_with_boundary",
            f"Heldout1 selector {h1['selector_pass_count']}/{h1['n']} against diagnostic oracle {h1['oracle_pass_count']}/{h1['n']}.",
            "Report heldout1 as a positive bounded simulator result from the online simulator-loop selector.",
            claim_lookup["C4_first_heldout_selector_positive"]["do_not_claim"],
            "Heldout1 language must be paired with heldout2, heldout3, and heldout4 boundary results.",
            "A 10/10 heldout1 result alone does not support broad robustness.",
            "Preserve cross-heldout synthesis and seed-level ledger after any selector update.",
            "tables/heldout_generalization.md; tables/cross_heldout_validation_synthesis.md; tables/seed_outcome_ledger.md",
            False,
        ),
        row(
            "DT04",
            "heldout2_selector_gap",
            "claim_must_be_downgraded",
            f"Heldout2 expanded selector {h2['selector_pass_count']}/{h2['n']} against diagnostic oracle {h2['oracle_pass_count']}/{h2['n']}.",
            "Describe heldout2 as improved but still selector-limited; name selector misses rather than smoothing them away.",
            ready_lookup["NG04_heldout2_selector_misses"]["evidence"],
            roadmap_lookup["NG04_heldout2_selector_misses"]["decision_gate"],
            roadmap_lookup["NG04_heldout2_selector_misses"]["claim_boundary"],
            roadmap_lookup["NG04_heldout2_selector_misses"]["required_future_evidence"],
            "tables/cross_heldout_validation_synthesis.md; materials/SELECTOR_DECISION_AUDIT.md; materials/CONFIRMATORY_ROADMAP.md",
            True,
        ),
        row(
            "DT05",
            "heldout3_external_validation",
            "negative_boundary_retained",
            f"Heldout3 selector {h3['selector_pass_count']}/{h3['n']} against diagnostic oracle {h3['oracle_pass_count']}/{h3['n']}.",
            "Keep heldout3 as adverse external-validation evidence before any targeted repair discussion.",
            ready_lookup["NG02_heldout3_weak"]["evidence"],
            roadmap_lookup["NG02_heldout3_weak"]["decision_gate"],
            roadmap_lookup["NG02_heldout3_weak"]["claim_boundary"],
            roadmap_lookup["NG02_heldout3_weak"]["required_future_evidence"],
            "tables/heldout3_external_validation.md; tables/heldout3_failure_atlas.md; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
            True,
        ),
        row(
            "DT06",
            "targeted_repair_boundary",
            "diagnostic_reuse_only",
            ready_lookup["NG05_heldout3_targeted_selector"]["evidence"],
            "Call targeted heldout3 repair diagnostic reuse; do not convert it into external validation.",
            "Do not claim that heldout3 targeted repair is external validation or broad generalization evidence.",
            "Any stronger claim requires a frozen selector/candidate update followed by fresh disjoint seeds.",
            "Heldout3 targeted repair is not a substitute for heldout5 or larger-N validation.",
            "Run the frozen heldout5 plan only after selector/candidate changes are fixed.",
            "tables/heldout3_candidate_expansion.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md; materials/CONFIRMATORY_FREEZE_AUDIT.md",
            True,
        ),
        row(
            "DT07",
            "heldout4_partial_transfer",
            "partial_transfer_only",
            f"Heldout4 selector {h4['selector_pass_count']}/{h4['n']} against diagnostic oracle {h4['oracle_pass_count']}/{h4['n']}.",
            "Report heldout4 as post-repair external validation with partial transfer and visible misses.",
            ready_lookup["NG03_heldout4_partial"]["evidence"],
            roadmap_lookup["NG03_heldout4_partial"]["decision_gate"],
            roadmap_lookup["NG03_heldout4_partial"]["claim_boundary"],
            roadmap_lookup["NG03_heldout4_partial"]["required_future_evidence"],
            "tables/heldout4_external_validation.md; tables/heldout4_failure_atlas.md; figures/figure_3_source_data.csv",
            True,
        ),
        row(
            "DT08",
            "broad_robustness_gate",
            "not_yet_supported",
            ready_lookup["NG01_broad_robustness"]["evidence"],
            "Use bounded simulator evidence wording; avoid broad robustness or solved-generalization phrasing.",
            "Do not claim broad robustness, cross-distribution reliability, or solved generalization.",
            roadmap_lookup["NG01_broad_robustness"]["decision_gate"],
            roadmap_lookup["NG01_broad_robustness"]["claim_boundary"],
            roadmap_lookup["NG01_broad_robustness"]["required_future_evidence"],
            "materials/TOP_JOURNAL_READINESS_CHECKLIST.md; materials/CONFIRMATORY_ROADMAP.md; tables/cross_heldout_statistical_supplement.md",
            True,
        ),
        row(
            "DT09",
            "probe_cost_gate",
            "cost_claim_not_yet_supported",
            ready_lookup["NG07_probe_cost"]["evidence"],
            "Report probe cost with accuracy; do not hide expensive five-candidate, 1200-step probing.",
            "Do not call the selector cheap or lightweight unless a no-regression cheaper selector is validated.",
            roadmap_lookup["NG07_probe_cost"]["decision_gate"],
            roadmap_lookup["NG07_probe_cost"]["claim_boundary"],
            roadmap_lookup["NG07_probe_cost"]["required_future_evidence"],
            "tables/compute_cost_report.md; materials/CONFIRMATORY_ROADMAP.md",
            True,
        ),
        row(
            "DT10",
            "real_world_and_safety_boundary",
            "prohibited_claim",
            "No real-road, public-road, perception, hardware, or safety-certification evidence is included.",
            "Frame all results as simulator-only and keep sim-to-real limitations visible.",
            "Do not claim real-road readiness, public-road deployment, VLM autonomy, perception robustness, or safety certification.",
            "Any real-world claim requires a separate preregistered real-world/perception/safety study, not this simulator package.",
            "The current package supports simulator-only method evaluation.",
            "Use external-validity and risk statements as mandatory limitation text.",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.md; materials/RESEARCH_RISK_AND_SAFETY.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            True,
        ),
    ]

    risky_missing = [item for item in downgrade["downgrade_rows"] if not item["evidence_complete"]]
    selector_miss_count = sum(1 for item in ledger["rows"] if item.get("error_type") == "selector_miss")
    candidate_gap_count = sum(1 for item in ledger["rows"] if item.get("error_type") == "candidate_gap")

    report = {
        "root": str(root),
        "title": "Claim Decision Tree and Upgrade/Downgrade Gates",
        "purpose": (
            "Translate saved simulator evidence, negative results, diagnostic-oracle boundaries, and future-experiment "
            "gates into reviewer-facing claim decisions."
        ),
        "interpretation": (
            "This is not a new experiment. It is a manuscript-control artifact that says which claims are currently "
            "allowed, which must be downgraded, and which require fresh GPU validation before stronger wording."
        ),
        "summary": {
            "status": "pass" if verification["summary"]["status"] == "pass" and not risky_missing else "review_required",
            "decision_row_count": len(rows),
            "requires_new_experiment_count": sum(1 for item in rows if item["requires_new_experiment"]),
            "claim_allowed_count": sum(1 for item in rows if item["status"] == "claim_allowed_with_boundary"),
            "downgrade_or_boundary_count": sum(1 for item in rows if item["status"] != "claim_allowed_with_boundary"),
            "selector_miss_count_in_ledger": selector_miss_count,
            "candidate_gap_count_in_ledger": candidate_gap_count,
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_status": smoke["summary"]["status"],
            "external_validity_boundary_status": external["summary"].get("status", "available"),
            "roadmap_not_executed_boundary": roadmap["summary"]["not_executed_boundary"],
        },
        "rows": rows,
        "global_policy": {
            "oracle_rows_are_diagnostic_upper_bounds": True,
            "heldout3_targeted_repair_is_diagnostic_reuse": True,
            "heldout4_is_partial_transfer_not_broad_robustness": True,
            "no_broad_robustness_without_new_validation": True,
            "no_real_world_or_safety_claims": True,
            "failed_seeds_remain_reportable_evidence": True,
        },
    }
    return report


def write_csv(report, path):
    fields = [
        "id",
        "theme",
        "status",
        "evidence",
        "action",
        "boundary",
        "decision_gate",
        "claim_boundary",
        "next_validation",
        "primary_evidence",
        "requires_new_experiment",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Claim Decision Tree and Upgrade/Downgrade Gates",
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
    lines.extend(["", "## Global Policy", ""])
    for key, value in report["global_policy"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Decision Rows",
            "",
            "| id | theme | status | evidence | action | boundary | decision gate | claim boundary | next validation | primary evidence | new experiment |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['id']} | {item['theme']} | {item['status']} | {item['evidence']} | "
            f"{item['action']} | {item['boundary']} | {item['decision_gate']} | "
            f"{item['claim_boundary']} | {item['next_validation']} | `{item['primary_evidence']}` | "
            f"{item['requires_new_experiment']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export claim decision tree and upgrade/downgrade gates.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "CLAIM_DECISION_TREE.json"
    out_md = materials / "CLAIM_DECISION_TREE.md"
    out_csv = materials / "CLAIM_DECISION_TREE.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
