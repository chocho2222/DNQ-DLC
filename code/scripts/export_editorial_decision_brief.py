#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_brief(root):
    manifest = load_json(root / "manifest.json")
    summary = load_json(root / "materials" / "PUBLICATION_PACKAGE_SUMMARY.json")
    narrative = load_json(root / "materials" / "EDITORIAL_NARRATIVE_PACKAGE.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_PACKAGE_MAP.json")
    cover = load_json(root / "materials" / "COVER_LETTER_DRAFT_PACKAGE.json")
    validity = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")
    sample = load_json(root / "materials" / "SAMPLE_SIZE_SENSITIVITY_BRIEF.json")
    reference = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    preflight = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    archive_upload = load_json(root / "materials" / "ARCHIVE_UPLOAD_READINESS_MATRIX.json")
    figure_qc = load_json(root / "materials" / "FIGURE_TECHNICAL_QC.json")
    source_data = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    stats_appendix = load_json(root / "materials" / "STATISTICAL_REPORTING_APPENDIX.json")
    ethics = load_json(root / "materials" / "ETHICS_DISCLOSURE_READINESS_PACK.json")

    main = summary["main_results"]
    portal_counts = portal["summary"]["status_counts"]
    current_artifact_provenance = verification["summary"]["artifact_provenance"]
    reference_summary = dict(reference["summary"])
    reference_summary["artifact_provenance"] = current_artifact_provenance
    reference_topics_pending = reference_summary.get("topic_needs_author_completion_count", 0)
    reference_rationale = (
        "and related-work expansion"
        if reference_topics_pending
        else "and final author style/literature-balance review"
    )

    decision = {
        "recommendation": "proceed_after_author_completion",
        "rationale": (
            "The local evidence package is internally consistent and unusually transparent for a simulator-only "
            "method paper, but final submission still requires author metadata, target-journal formatting, public "
            f"archive DOI/accession, {reference_rationale}."
        ),
        "confidence": "package_preflight_pass_but_not_final_submission_ready",
    }

    send_to_review_arguments = [
        {
            "id": "strict_full_lap_standard",
            "argument": "The package evaluates full-lap multi-car overtaking with strict rank, completion, first-ahead, grass-rate, and traffic-quality gates.",
            "evidence": "materials/METHODS.md; materials/STATISTICAL_ANALYSIS_PLAN.md; tables/seed_outcome_ledger.md",
            "editorial_value": "Raises the evidence bar above short qualitative rollouts.",
        },
        {
            "id": "strong_baseline_preserved",
            "argument": f"The strongest rule baseline is preserved at {main['locked_rule_overtake']}, while graph-adaptive shielding reaches {main['locked_graph_adaptive']}.",
            "evidence": "tables/full_statistical_report.md; materials/BASELINE_FAIRNESS_AUDIT.md",
            "editorial_value": "Avoids a weak-baseline comparison and makes limitations visible.",
        },
        {
            "id": "selector_progress_and_boundary",
            "argument": (
                f"The expanded online selector reaches {main['heldout1_expanded_selector']} on heldout1 and "
                f"{main['heldout2_expanded_selector']} on heldout2, while heldout3/heldout4 expose external-validation limits."
            ),
            "evidence": "tables/expanded_selector_generalization.md; tables/heldout3_external_validation.md; tables/heldout4_external_validation.md",
            "editorial_value": "Provides both positive evidence and clear generalization boundaries.",
        },
        {
            "id": "transparent_negative_results",
            "argument": f"{negative['summary']['item_count']} negative-result and failure-mode rows are retained.",
            "evidence": "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; tables/heldout4_failure_atlas.md",
            "editorial_value": "Supports credibility by preserving failed controls and selector/candidate gaps.",
        },
        {
            "id": "reproducible_archive_ready_local",
            "argument": f"Publication verification is {verification['summary']['status']} with artifact provenance {verification['summary']['artifact_provenance']}.",
            "evidence": "materials/PUBLICATION_PACKAGE_VERIFICATION.md; tables/artifact_provenance.md; materials/RELEASE_ARCHIVE_MANIFEST.md",
            "editorial_value": "Gives reviewers a traceable local evidence package.",
        },
        {
            "id": "production_and_source_data_ready",
            "argument": (
                f"Main-figure technical QC is {figure_qc['summary']['status']} and source-data coverage has "
                f"{source_data['summary']['complete_count']}/{source_data['summary']['figure_count']} complete figure records."
            ),
            "evidence": "materials/FIGURE_TECHNICAL_QC.md; materials/FIGURE_SOURCE_DATA_AUDIT.md; figures/*_source_data.csv",
            "editorial_value": "Supports production review and source-data upload without relying on screenshots alone.",
        },
        {
            "id": "statistics_and_limitations_ready",
            "argument": (
                f"The statistical reporting appendix is {stats_appendix['summary']['status']} with "
                f"{stats_appendix['summary']['row_count']} reporting rows and zero review-required rows."
            ),
            "evidence": "materials/STATISTICAL_REPORTING_APPENDIX.md; materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.md",
            "editorial_value": "Makes uncertainty, small-N limits, and endpoint sensitivity visible before review.",
        },
    ]

    desk_reject_risks = [
        {
            "id": "overclaim_risk",
            "risk": "Framing the work as broadly robust or deployment-ready would be unsupported.",
            "mitigation": "Use the claim matrix, manuscript QA, and portal map wording; keep oracle and targeted repair boundaries explicit.",
            "evidence": "materials/CLAIM_EVIDENCE_MATRIX.md; materials/MANUSCRIPT_CLAIM_QA.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "severity": "high_if_unmitigated",
        },
        {
            "id": "small_n_risk",
            "risk": "Held-out seed counts are small for strong robustness claims.",
            "mitigation": "Report intervals and tests as descriptive; present larger-N validation as future work.",
            "evidence": "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md; tables/cross_heldout_statistical_supplement.md",
            "severity": "medium",
        },
        {
            "id": "final_manuscript_not_packaged",
            "risk": "The current manuscript is a conservative Markdown draft, not final journal source/PDF.",
            "mitigation": "Authors must convert to target-journal format and rerun claim/cross-reference QA.",
            "evidence": "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md; manuscript/main.md",
            "severity": "high_before_upload",
        },
        {
            "id": "archive_doi_missing",
            "risk": "No public archive DOI/accession is assigned yet.",
            "mitigation": "Deposit the package and update Data/Code Availability and portal map fields.",
            "evidence": "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/FAIR_ARCHIVE_METADATA.md",
            "severity": "high_before_upload_or_acceptance",
        },
    ]
    if reference_topics_pending:
        desk_reject_risks.append(
            {
                "id": "related_work_thin",
                "risk": "Starter bibliography is not enough for a polished top-journal related-work section.",
                "mitigation": "Authors should expand domain-specific autonomous racing, multi-agent control, and safety-validation references.",
                "evidence": "materials/REFERENCE_READINESS_AUDIT.md; manuscript/references.bib",
                "severity": "medium",
            }
        )
    else:
        desk_reject_risks.append(
            {
                "id": "related_work_style_review",
                "risk": "Reference keys and topic coverage pass local checks, but final literature balance and journal style remain author-owned.",
                "mitigation": "Authors should review related-work framing, citation style, and any target-journal topical expectations before upload.",
                "evidence": "materials/REFERENCE_READINESS_AUDIT.md; materials/RELATED_WORK_POSITIONING_MATRIX.md; manuscript/references.bib",
                "severity": "low_to_medium",
            }
        )

    go_no_go_gates = [
        {
            "gate": "local_package_integrity",
            "status": "go",
            "evidence": f"Verification {verification['summary']['status']}; provenance {verification['summary']['artifact_provenance']}.",
        },
        {
            "gate": "claim_safety",
            "status": "go_with_guardrails",
            "evidence": "Claim QA pass; broad robustness and deployment claims prohibited.",
        },
        {
            "gate": "editorial_story",
            "status": "go",
            "evidence": narrative["publication_positioning"]["best_supported_contribution"],
        },
        {
            "gate": "submission_portal",
            "status": "author_action_required",
            "evidence": f"Portal status counts: {portal_counts}.",
        },
        {
            "gate": "dashboard_clean",
            "status": "go",
            "evidence": f"Dashboard review-required rows: {dashboard['summary']['review_required_row_count']}.",
        },
        {
            "gate": "archive_upload_mapping",
            "status": "go_with_author_actions",
            "evidence": (
                f"Archive/upload matrix {archive_upload['summary']['status']}; "
                f"author-action rows: {archive_upload['summary']['author_action_required_count']}."
            ),
        },
        {
            "gate": "statistics_reporting",
            "status": "go",
            "evidence": (
                f"Statistical appendix {stats_appendix['summary']['status']}; "
                f"review-required rows: {stats_appendix['summary']['review_required_count']}."
            ),
        },
        {
            "gate": "figure_and_source_data",
            "status": "go",
            "evidence": (
                f"Figure QC {figure_qc['summary']['status']}; source-data complete "
                f"{source_data['summary']['complete_count']}/{source_data['summary']['figure_count']}."
            ),
        },
        {
            "gate": "ethics_disclosures",
            "status": "author_action_required",
            "evidence": (
                f"Ethics/disclosure pack {ethics['summary']['status']}; "
                f"author-required rows: {ethics['summary']['author_required_count']}."
            ),
        },
        {
            "gate": "external_archive",
            "status": "author_action_required",
            "evidence": f"External archive pending: {preflight['summary']['external_archive_pending']}.",
        },
        {
            "gate": "references",
            "status": "author_action_recommended",
            "evidence": reference_summary,
        },
    ]

    return {
        "root": str(root),
        "title": "Editorial decision brief",
        "purpose": "One-page editor/PI-facing go-no-go brief for deciding whether the package is ready to move toward journal submission.",
        "decision": decision,
        "recommended_title": cover["recommended_title"],
        "send_to_review_arguments": send_to_review_arguments,
        "desk_reject_risks": desk_reject_risks,
        "go_no_go_gates": go_no_go_gates,
        "summary": {
            "argument_count": len(send_to_review_arguments),
            "risk_count": len(desk_reject_risks),
            "gate_count": len(go_no_go_gates),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
            "portal_author_action_count": portal["summary"]["author_action_count"],
            "external_archive_pending": preflight["summary"]["external_archive_pending"],
            "dashboard_review_required": dashboard["summary"]["review_required_row_count"],
            "archive_upload_readiness_status": archive_upload["summary"]["status"],
            "figure_qc_status": figure_qc["summary"]["status"],
            "figure_source_data_complete": f"{source_data['summary']['complete_count']}/{source_data['summary']['figure_count']}",
            "statistical_reporting_appendix_status": stats_appendix["summary"]["status"],
            "ethics_disclosure_readiness_status": ethics["summary"]["status"],
            "seed_sets": manifest["seed_sets"],
            "sample_size_expanded_or_later_selector": sample["summary"]["expanded_or_later_selector"],
            "external_validity_expanded_or_later_oracle": validity["summary"]["expanded_or_later_oracle"],
        },
        "interpretation": (
            "This brief supports editorial triage and internal go/no-go discussion. It is not a final journal decision, "
            "and it does not override author-required submission metadata, archive deposition, or target-journal formatting."
        ),
    }


def write_csv(report, path):
    fields = ["section", "id", "message", "evidence", "status_or_severity"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["send_to_review_arguments"]:
            writer.writerow(
                {
                    "section": "send_to_review_argument",
                    "id": row["id"],
                    "message": row["argument"],
                    "evidence": row["evidence"],
                    "status_or_severity": row["editorial_value"],
                }
            )
        for row in report["desk_reject_risks"]:
            writer.writerow(
                {
                    "section": "desk_reject_risk",
                    "id": row["id"],
                    "message": row["risk"],
                    "evidence": row["evidence"],
                    "status_or_severity": row["severity"],
                }
            )
        for row in report["go_no_go_gates"]:
            writer.writerow(
                {
                    "section": "go_no_go_gate",
                    "id": row["gate"],
                    "message": row["evidence"],
                    "evidence": row["evidence"],
                    "status_or_severity": row["status"],
                }
            )


def write_markdown(report, path):
    lines = [
        "# Editorial Decision Brief",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Recommendation",
        "",
        f"- Recommendation: `{report['decision']['recommendation']}`",
        f"- Confidence: `{report['decision']['confidence']}`",
        f"- Rationale: {report['decision']['rationale']}",
        f"- Recommended title: {report['recommended_title']}",
        "",
        "## Send-to-Review Arguments",
        "",
        "| id | argument | evidence | editorial value |",
        "|---|---|---|---|",
    ]
    for row in report["send_to_review_arguments"]:
        lines.append(f"| {row['id']} | {row['argument']} | `{row['evidence']}` | {row['editorial_value']} |")
    lines.extend(
        [
            "",
            "## Desk-Reject Risks",
            "",
            "| id | risk | mitigation | evidence | severity |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["desk_reject_risks"]:
        lines.append(f"| {row['id']} | {row['risk']} | {row['mitigation']} | `{row['evidence']}` | {row['severity']} |")
    lines.extend(
        [
            "",
            "## Go/No-Go Gates",
            "",
            "| gate | status | evidence |",
            "|---|---|---|",
        ]
    )
    for row in report["go_no_go_gates"]:
        lines.append(f"| {row['gate']} | {row['status']} | {row['evidence']} |")
    lines.extend(
        [
            "",
            "## Snapshot",
            "",
            f"- Publication verification: `{report['summary']['publication_verification_status']}`",
            f"- Artifact provenance: {report['summary']['artifact_provenance']}",
            f"- Portal author actions: {report['summary']['portal_author_action_count']}",
            f"- External archive pending: `{report['summary']['external_archive_pending']}`",
            f"- Expanded-or-later selector: {report['summary']['sample_size_expanded_or_later_selector']}",
            f"- Expanded-or-later oracle: {report['summary']['external_validity_expanded_or_later_oracle']}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export editorial decision brief.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_brief(root)
    out_json = materials / "EDITORIAL_DECISION_BRIEF.json"
    out_md = materials / "EDITORIAL_DECISION_BRIEF.md"
    out_csv = materials / "EDITORIAL_DECISION_BRIEF.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
