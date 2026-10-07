#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ratio(count, n):
    return f"{count}/{n}"


def method_summary(report, method):
    for row in report["method_summaries"]:
        if row["method"] == method:
            return row
    raise KeyError(method)


def build_report(root):
    manifest = load_json(root / "manifest.json")
    full = load_json(root / "tables" / "full_statistical_report.json")
    policy_card = load_json(root / "materials" / "POLICY_MODEL_CARD.json")
    protocol = load_json(root / "materials" / "STUDY_PROTOCOL_AND_DEVIATIONS.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    compute = load_json(root / "tables" / "compute_cost_report.json")

    overtake = method_summary(full, "main:overtake_base_only")
    graph_adaptive = method_summary(full, "adaptive:graph_adaptive_shield")
    lane = method_summary(full, "main:lane_base_only")
    graph_soft = method_summary(full, "main:graph_soft_shield")

    rows = [
        {
            "id": "F01_same_strict_validator",
            "dimension": "validator",
            "status": "pass",
            "evidence": "materials/STATISTICAL_ANALYSIS_PLAN.md; scripts/validate_overtake_behavior.py; tables/full_statistical_report.md",
            "assessment": "All reported pass/fail claims use the strict full-lap validator rather than cherry-picked GIF outcomes.",
            "risk_if_absent": "Methods could be compared using weaker visual or partial-lap criteria.",
            "mitigation": "Primary claims cite strict tables, seed ledgers, and claim QA rather than GIF-only evidence.",
        },
        {
            "id": "F02_same_locked_seed_set",
            "dimension": "seed_set",
            "status": "pass",
            "evidence": "manifest.json; materials/STUDY_PROTOCOL_AND_DEVIATIONS.md; tables/full_statistical_report_method_summary.csv",
            "assessment": f"Locked single-method comparisons use the same 10 seeds: {','.join(str(s) for s in manifest['seed_sets']['locked'])}.",
            "risk_if_absent": "A method could look stronger by using easier seeds.",
            "mitigation": "Locked, held-out, and targeted stages are explicitly separated in the protocol/deviation record.",
        },
        {
            "id": "F03_strong_baseline_preserved",
            "dimension": "baseline_strength",
            "status": "pass",
            "evidence": "tables/full_statistical_report.md; materials/SIGNIFICANCE_BRIEFING.md; materials/CLAIM_EVIDENCE_MATRIX.md",
            "assessment": (
                f"The strongest locked single controller is retained as a rule baseline: overtake_base_only "
                f"{ratio(overtake['pass_count'], overtake['n'])}; graph_adaptive_shield is {ratio(graph_adaptive['pass_count'], graph_adaptive['n'])}."
            ),
            "risk_if_absent": "The paper could overstate learning gains against weak baselines.",
            "mitigation": "Allowed wording states that graph-adaptive shielding narrows but does not surpass the strongest rule baseline.",
        },
        {
            "id": "F04_multiple_baseline_families",
            "dimension": "baseline_diversity",
            "status": "pass",
            "evidence": "baselines/; materials/POLICY_MODEL_CARD.md; tables/main_results.csv; tables/full_statistical_report.md",
            "assessment": (
                f"Rule-policy comparators include lane, overtake, expert-gate, mixed/telemetry baselines, and negative controls. "
                f"Locked lane_base_only is {ratio(lane['pass_count'], lane['n'])}; overtake_base_only is {ratio(overtake['pass_count'], overtake['n'])}."
            ),
            "risk_if_absent": "A single weak baseline would not make the comparison conservative.",
            "mitigation": "Policy/model card records rule baselines separately from learned policies and selectors.",
        },
        {
            "id": "F05_negative_controls_retained",
            "dimension": "negative_controls",
            "status": "pass",
            "evidence": "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; tables/heldout_expert_fast_smoke_report.md; tables/heldout_expert_barrier_smoke_report.md; tables/heldout_expert_recovery_smoke_report.md",
            "assessment": (
                f"Negative controls are retained in the package; the negative-results register contains "
                f"{negative['summary']['item_count']} items across {len(negative['summary']['categories'])} categories."
            ),
            "risk_if_absent": "Failed variants could be hidden, inflating apparent method progress.",
            "mitigation": "Negative controls and near misses are listed as evidence for method boundaries.",
        },
        {
            "id": "F06_oracle_not_counted_as_deployable",
            "dimension": "oracle_boundary",
            "status": "pass",
            "evidence": "materials/CLAIM_EVIDENCE_MATRIX.md; materials/STUDY_PROTOCOL_AND_DEVIATIONS.md; materials/POLICY_MODEL_CARD.md",
            "assessment": "Oracle portfolios are marked as diagnostic upper bounds and not online selector outputs.",
            "risk_if_absent": "Post hoc best-candidate results could be mistaken for online controller performance.",
            "mitigation": "Separate selector_result and oracle_result fields are used across protocol, seed ledger, and external-validity materials.",
        },
        {
            "id": "F07_compute_budget_reported",
            "dimension": "compute_and_rollout_budget",
            "status": "limitation",
            "evidence": "tables/compute_cost_report.md; materials/TRANSPARENT_REPORTING_CHECKLIST.md; materials/SUBMISSION_GAP_ACTION_PLAN.md",
            "assessment": (
                f"Simulated-step and device-count costs are reported ({compute['summary']['full_rollout_rows']} full-rollout rows, "
                f"{compute['summary']['selector_probe_rows']} selector probe rows), but exact wall-clock/utilization is unavailable."
            ),
            "risk_if_absent": "Selector probe cost could be underreported relative to single-controller baselines.",
            "mitigation": "Current reports state the limitation and recommend timed reruns if a venue requires elapsed-time accounting.",
        },
        {
            "id": "F08_visual_evidence_not_primary",
            "dimension": "anti_cherry_picking",
            "status": "pass",
            "evidence": "materials/RESEARCH_RISK_AND_SAFETY.md; materials/FIGURE_SOURCE_DATA_AUDIT.md; materials/DATA_DICTIONARY.md",
            "assessment": "GIFs are treated as qualitative visual checks; strict tables, source data, and seed ledgers are the primary evidence.",
            "risk_if_absent": "A visually appealing rollout could hide incomplete laps, off-track behavior, or traffic failures.",
            "mitigation": "The package includes source-data audits and a cherry-picked-visuals risk control.",
        },
        {
            "id": "F09_generalization_not_overstated",
            "dimension": "heldout_balance",
            "status": "pass",
            "evidence": "materials/STUDY_PROTOCOL_AND_DEVIATIONS.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md; materials/MANUSCRIPT_CLAIM_QA.md",
            "assessment": "Heldout1 positives, heldout2 stress limits, heldout3 negative external validation, and heldout4 partial transfer are reported together.",
            "risk_if_absent": "A positive held-out batch could be selectively emphasized.",
            "mitigation": "Claim QA warns on heldout1-only wording and protocol rows prohibit broad robustness interpretation.",
        },
        {
            "id": "F10_neural_method_limitations_explicit",
            "dimension": "method_limitations",
            "status": "pass",
            "evidence": "materials/POLICY_MODEL_CARD.md; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; tables/dagger_v2_heldout_failure_diagnosis.md",
            "assessment": (
                f"Learned/shielded components are documented as complementary or diagnostic where appropriate; graph_soft_shield is "
                f"{ratio(graph_soft['pass_count'], graph_soft['n'])} on locked seeds."
            ),
            "risk_if_absent": "A learned method could be framed as stronger than the evidence supports.",
            "mitigation": "Model cards and negative-results register state standalone limits for graph and DAgger variants.",
        },
    ]

    status_counts = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    return {
        "root": str(root),
        "title": "Baseline Fairness Audit",
        "purpose": (
            "Reviewer-facing audit of baseline preservation, fairness of method comparisons, oracle boundaries, "
            "negative controls, anti-cherry-picking controls, and compute-budget reporting."
        ),
        "summary": {
            "item_count": len(rows),
            "status_counts": status_counts,
            "locked_overtake_baseline": ratio(overtake["pass_count"], overtake["n"]),
            "locked_graph_adaptive": ratio(graph_adaptive["pass_count"], graph_adaptive["n"]),
            "policy_model_card_complete": policy_card["summary"]["complete"],
            "protocol_rows": protocol["summary"]["row_count"],
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
        },
        "items": rows,
        "interpretation": (
            "The package uses a conservative comparison: strong rule baselines are preserved, learned/shielded methods "
            "do not claim to surpass the strongest locked rule baseline, oracle results are marked as diagnostic, and "
            "negative controls remain visible. The main remaining fairness limitation is exact wall-clock/utilization "
            "cost accounting for selector probes."
        ),
    }


FIELDS = [
    "id",
    "dimension",
    "status",
    "evidence",
    "assessment",
    "risk_if_absent",
    "mitigation",
]


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in report["items"]:
            writer.writerow({key: row[key] for key in FIELDS})


def write_markdown(report, path):
    lines = [
        "# Baseline Fairness Audit",
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
            "## Audit Items",
            "",
            "| id | dimension | status | assessment | risk if absent | mitigation | evidence |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["items"]:
        lines.append(
            f"| {row['id']} | {row['dimension']} | {row['status']} | {row['assessment']} | "
            f"{row['risk_if_absent']} | {row['mitigation']} | `{row['evidence']}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export baseline fairness audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "BASELINE_FAIRNESS_AUDIT.json"
    out_md = materials / "BASELINE_FAIRNESS_AUDIT.md"
    out_csv = materials / "BASELINE_FAIRNESS_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
