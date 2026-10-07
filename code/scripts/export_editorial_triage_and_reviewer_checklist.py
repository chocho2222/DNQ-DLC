#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def checklist_row(domain, question, status, evidence, reviewer_use, boundary):
    return {
        "domain": domain,
        "question": question,
        "status": status,
        "evidence": evidence,
        "reviewer_use": reviewer_use,
        "boundary": boundary,
    }


def risk_row(risk_id, risk, severity, status, evidence, mitigation, claim_boundary, author_action):
    return {
        "id": risk_id,
        "risk": risk,
        "severity": severity,
        "status": status,
        "evidence": evidence,
        "mitigation": mitigation,
        "claim_boundary": claim_boundary,
        "author_action": author_action,
    }


def unlisted_release_output_count(dependency):
    summary = dependency["summary"]
    if "unlisted_release_outputs_after_exclusions" in summary:
        return len(summary["unlisted_release_outputs_after_exclusions"])
    return len(summary.get("missing_release_outputs_excluding_release_manifest", []))


def build_report(root):
    manifest = load_json(root / "manifest.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    decision = load_json(root / "materials" / "EDITORIAL_DECISION_BRIEF.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_PACKAGE_MAP.json")
    claim_qa = load_json(root / "materials" / "MANUSCRIPT_CLAIM_QA.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    endpoint = load_json(root / "materials" / "ENDPOINT_SENSITIVITY_AUDIT.json")
    selector = load_json(root / "materials" / "SELECTOR_DECISION_AUDIT.json")
    seeds = load_json(root / "materials" / "SEED_PARTITION_AUDIT.json")
    source = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    visual = load_json(root / "materials" / "VISUAL_EVIDENCE_AUDIT.json")
    dependency = load_json(root / "materials" / "ARTIFACT_DEPENDENCY_MAP.json")
    archive = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    references = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")
    sample = load_json(root / "materials" / "SAMPLE_SIZE_SENSITIVITY_BRIEF.json")
    fairness = load_json(root / "materials" / "BASELINE_FAIRNESS_AUDIT.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")
    validity = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    threats = load_json(root / "materials" / "THREATS_TO_VALIDITY_AUDIT.json")
    blockers = load_json(root / "materials" / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json")

    figure_source_complete = source["summary"]["incomplete_count"] == 0

    checklist = [
        checklist_row(
            "editorial_fit",
            "Is there a clear contribution beyond short qualitative rollouts?",
            "ready_with_limitations",
            "materials/EDITORIAL_NARRATIVE_PACKAGE.md; materials/SIGNIFICANCE_BRIEFING.md; figures/figure_3_cross_heldout_validation.*",
            "Use to judge whether the submission should be framed as strict simulator evaluation plus transparent generalization limits.",
            "Do not frame as real-road autonomy or broad robustness.",
        ),
        checklist_row(
            "baseline_strength",
            "Are strong baselines preserved rather than replaced by weak comparisons?",
            "ready",
            "materials/BASELINE_FAIRNESS_AUDIT.md; tables/full_statistical_report.md",
            f"Baseline audit status counts: {fairness['summary']['status_counts']}.",
            "The strongest rule baseline remains a serious comparator, not a straw baseline.",
        ),
        checklist_row(
            "statistical_consistency",
            "Do manuscript-facing numbers match saved tables and figures?",
            stats["summary"]["status"],
            "materials/STATISTICAL_CONSISTENCY_AUDIT.md; figures/figure_3_source_data.csv; tables/seed_outcome_ledger.md",
            f"{stats['summary']['check_count']} checks; failed checks: {stats['summary']['failed_checks']}.",
            "Statistics are descriptive for simulator seed batches; avoid population-level robustness claims.",
        ),
        checklist_row(
            "sample_size",
            "Are n=10 and n=50 limits disclosed with sensitivity planning?",
            "ready_with_limitations",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md; materials/SAMPLE_SIZE_SENSITIVITY_STAGE_ROWS.csv",
            f"Current expanded-or-later selector: {sample['summary']['expanded_or_later_selector']}.",
            "Small seed batches support bounded simulator claims, not broad robustness.",
        ),
        checklist_row(
            "external_validity",
            "Are heldout3, targeted repair, and heldout4 interpreted correctly?",
            "ready_with_guardrails",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md; tables/heldout3_external_validation.md; tables/heldout4_external_validation.md",
            f"Expanded-or-later oracle across external validity view: {validity['summary']['expanded_or_later_oracle']}.",
            "Heldout3 targeted repair is diagnostic; heldout4 is partial post-repair transfer.",
        ),
        checklist_row(
            "negative_results",
            "Are failed controls and candidate/selector gaps visible?",
            "ready",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; tables/heldout4_failure_atlas.md",
            f"Negative/failure rows retained: {negative['summary']['item_count']}.",
            "Do not omit negative controls from supplementary review materials.",
        ),
        checklist_row(
            "endpoint_dependence",
            "Can reviewers inspect endpoint-threshold sensitivity?",
            "ready",
            "materials/ENDPOINT_SENSITIVITY_AUDIT.md; materials/ENDPOINT_SENSITIVITY_SCENARIO_ROWS.csv",
            f"Endpoint scenarios: {endpoint['summary']['scenario_count']}; sensitive stage-method rows: {endpoint['summary']['endpoint_sensitive_stage_methods']}.",
            "Endpoint sensitivity is a limitation and transparency asset, not a weakness to hide.",
        ),
        checklist_row(
            "selector_transparency",
            "Can online selector decisions be recomputed from probe rows?",
            selector["summary"]["status"],
            "materials/SELECTOR_DECISION_AUDIT.md; materials/SELECTOR_DECISION_AUDIT_ROWS.csv",
            f"Decision rows: {selector['summary']['decision_row_count']}; mismatches: {selector['summary']['total_mismatch_count']}.",
            "Selector remains a simulator online-probe policy, not a zero-cost single controller.",
        ),
        checklist_row(
            "seed_partition",
            "Are seed splits and diagnostic reuse disclosed?",
            seeds["summary"]["status"],
            "materials/SEED_PARTITION_AUDIT.md; materials/SEED_PARTITION_SEED_SETS.csv",
            f"Primary seed sets: {seeds['summary']['primary_seed_set_count']}; unexpected overlaps: {seeds['summary']['unexpected_overlap_count']}.",
            "Diagnostic reuse must remain labeled and separate from external validation.",
        ),
        checklist_row(
            "source_data",
            "Are figure source data and export formats traceable?",
            "ready" if figure_source_complete else "review_required",
            "materials/FIGURE_SOURCE_DATA_AUDIT.md; figures/*_source_data.csv",
            f"Figure source-data audit complete: {figure_source_complete}.",
            "Figures summarize saved simulator evidence only.",
        ),
        checklist_row(
            "visual_evidence",
            "Are GIFs treated as qualitative evidence and linked to quantitative tables?",
            "ready",
            "materials/VISUAL_EVIDENCE_AUDIT.md; materials/VISUAL_EVIDENCE_AUDIT.csv",
            f"Saved GIF count: {visual['summary']['gif_count']}.",
            "GIFs cannot substitute for strict validation gates.",
        ),
        checklist_row(
            "reproducibility",
            "Can reviewers trace artifacts to commands, scripts, and release files?",
            "ready",
            "tables/artifact_provenance.md; materials/ARTIFACT_DEPENDENCY_MAP.md; materials/REPRODUCTION_GUIDE.md",
            (
                f"Artifact provenance {verification['summary']['artifact_provenance']}; "
                f"unlisted release outputs after documented exclusions: {unlisted_release_output_count(dependency)}."
            ),
            "Local reproducibility readiness is not the same as a public archive DOI.",
        ),
        checklist_row(
            "claim_safety",
            "Are overclaims blocked before manuscript upload?",
            claim_qa["summary"]["status"],
            "materials/CLAIM_EVIDENCE_MATRIX.md; materials/MANUSCRIPT_CLAIM_QA.md",
            f"Claim QA blockers: {claim_qa['summary']['blockers']}; warnings retained: {claim_qa['summary']['warnings']}.",
            "Oracle, targeted repair, VLM, real-road, perception, and safety-certification claims are prohibited unless new evidence is added.",
        ),
        checklist_row(
            "archive_readiness",
            "Is the local package ready for external archive deposition?",
            "ready_with_author_action",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/RELEASE_ARCHIVE_MANIFEST.md; materials/FAIR_ARCHIVE_METADATA.md",
            f"Archive preflight status: {archive['summary']['status']}; author-required rows: {archive['summary']['author_required_count']}.",
            "A DOI/accession is still author-required before final submission or acceptance.",
        ),
        checklist_row(
            "reference_readiness",
            "Are citations internally valid and related work gaps marked?",
            references["summary"]["status"],
            "materials/REFERENCE_READINESS_AUDIT.md; manuscript/references.bib",
            f"Topic rows needing author completion: {references['summary']['topic_needs_author_completion_count']}.",
            "Starter references are not a polished top-journal related-work section.",
        ),
        checklist_row(
            "submission_completion",
            "Which items still need author action before upload?",
            "author_action_required",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md; materials/SUBMISSION_PORTAL_AUTHOR_ACTIONS.csv",
            f"Portal author actions: {portal['summary']['author_action_count']}; status counts: {portal['summary']['status_counts']}.",
            "Author metadata, disclosures, journal formatting, and DOI fields cannot be inferred from the package.",
        ),
    ]

    status_counts = {}
    for row in checklist:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    editorial_triage = {
        "recommendation": decision["decision"]["recommendation"],
        "package_status": verification["summary"]["status"],
        "send_to_review_arguments": [row["id"] for row in decision["send_to_review_arguments"]],
        "highest_risk_items": [row["id"] for row in decision["desk_reject_risks"] if row["severity"].startswith("high")],
        "author_action_count": portal["summary"]["author_action_count"],
        "external_archive_pending": archive["summary"]["external_archive_pending"],
        "claim_guardrail": "Proceed only with simulator-only, non-VLM, non-deployment wording.",
    }

    author_blockers = {
        row["id"]: row
        for row in blockers["rows"]
        if row.get("status") == "author_required"
    }
    desk_reject_closure = [
        risk_row(
            "DR1_overclaim_scope",
            "Editor or reviewer reads the work as broad robustness, real-road readiness, VLM autonomy, or safety certification.",
            "high_if_unmitigated",
            "closed_by_guardrails",
            "materials/MANUSCRIPT_CLAIM_QA.md; materials/CLAIM_EVIDENCE_MATRIX.md; materials/SIMULATION_TO_REAL_APPLICABILITY.md; materials/RESEARCH_RISK_AND_SAFETY.md",
            "Claim QA is pass, simulation-to-real scope is explicit, and prohibited terms are tracked by manuscript/portal guardrails.",
            "Simulator-only method development; no real-road, perception-stack, VLM-autonomy, safety-certification, or broad-robustness claim.",
            "Authors must preserve conservative wording during final journal-format editing.",
        ),
        risk_row(
            "DR2_small_seed_batches",
            "Current held-out batches are too small for population-level robustness or superiority claims.",
            "medium",
            "controlled_limitation",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md; materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.md; tables/cross_heldout_statistical_supplement.md",
            "Wilson intervals, exact descriptive comparisons, and larger-N planning rows are available.",
            "Report seed-set evidence and uncertainty descriptively; do not claim population-level robustness.",
            "For stronger revision claims, preregister and run a larger fresh held-out batch.",
        ),
        risk_row(
            "DR3_targeted_repair_reuse",
            "Heldout3 targeted repair could be mistaken for independent external validation.",
            "high_if_unmitigated",
            "closed_by_partition_labels",
            "materials/SEED_PARTITION_AUDIT.md; materials/STUDY_PROTOCOL_AND_DEVIATIONS.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md; tables/seed_outcome_ledger.md",
            "Diagnostic reuse and heldout4 post-repair validation are separated in seed ledgers, protocol deviations, and external-validity audit.",
            "Heldout3 targeted repair is diagnostic reuse; heldout4 is post-repair external validation with partial transfer.",
            "Keep seed-set labels in abstract-adjacent text, Results, figure legends, and reviewer responses.",
        ),
        risk_row(
            "DR4_baseline_strawman",
            "A reviewer may suspect baseline weakness if only one hand-tuned comparator is emphasized.",
            "medium",
            "evidence_ready",
            "materials/BASELINE_FAIRNESS_AUDIT.md; tables/full_statistical_report.md; baselines/",
            "Three implemented baselines and locked-suite outcomes are preserved; the strongest baseline remains visible.",
            "Do not claim uniform dominance; frame the contribution as transparent portfolio selection and bounded generalization.",
            "Keep baseline folders and fairness audit in the supplement/archive rather than trimming them for space.",
        ),
        risk_row(
            "DR5_negative_results_omission",
            "Desk rejection or reviewer distrust if heldout3/heldout4 failures, selector misses, or candidate gaps are hidden.",
            "high_if_unmitigated",
            "closed_by_failure_register",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; tables/heldout4_failure_atlas.md; tables/cross_heldout_validation_synthesis.md",
            "Failure register, atlas tables, and cross-heldout synthesis explicitly retain negative controls and miss seeds.",
            "Claim improvement only within the saved simulator validation ladder and disclose residual failure modes.",
            "Do not compress failure discussion out of the final manuscript or supplementary upload.",
        ),
        risk_row(
            "DR6_archive_and_author_metadata",
            "Package is locally complete but not a finished submission because DOI/accession, authorship, disclosures, and journal template are author-owned.",
            "required_before_upload_or_revision",
            "author_action_required",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.md; materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/SUBMISSION_METADATA_DRAFT.md; materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
            "Author-owned items are isolated from local evidence gates so they remain visible and are not fabricated.",
            "Local readiness is not a journal receipt, public archive record, or author-certified disclosure package.",
            "; ".join(
                row["remaining_action"]
                for key, row in author_blockers.items()
                if key
                in {
                    "AF1_target_journal_template",
                    "AF2_external_archive_doi",
                    "AF3_author_identity_orcid",
                    "AF4_credit_contributions",
                    "AF5_disclosures_funding_ethics",
                }
            ),
        ),
    ]

    risk_status_counts = {}
    for row in desk_reject_closure:
        risk_status_counts[row["status"]] = risk_status_counts.get(row["status"], 0) + 1

    return {
        "root": str(root),
        "title": "Editorial triage and reviewer checklist",
        "purpose": (
            "Condense the local evidence package into reviewer-facing triage questions, direct evidence paths, "
            "claim boundaries, and remaining author actions."
        ),
        "scope": manifest["scope"],
        "editorial_triage": editorial_triage,
        "desk_reject_risk_closure": desk_reject_closure,
        "reviewer_checklist": checklist,
        "summary": {
            "checklist_count": len(checklist),
            "desk_reject_risk_count": len(desk_reject_closure),
            "desk_reject_risk_status_counts": risk_status_counts,
            "status_counts": status_counts,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
            "claim_qa_status": claim_qa["summary"]["status"],
            "statistical_consistency_status": stats["summary"]["status"],
            "threats_to_validity_status_counts": threats["summary"]["status_counts"],
            "dependency_unlisted_release_output_count": unlisted_release_output_count(dependency),
            "dependency_documented_release_exclusion_count": dependency["summary"].get("excluded_release_output_count", 0),
            "external_archive_pending": archive["summary"]["external_archive_pending"],
            "author_action_count": portal["summary"]["author_action_count"],
        },
        "interpretation": (
            "This checklist is for editorial triage and reviewer navigation. It strengthens transparency, but it does not "
            "replace final author-certified metadata, target-journal formatting, public archive deposition, or expanded related work."
        ),
    }


def write_csv(report, path):
    fields = ["section", "id", "domain", "question", "status", "evidence", "reviewer_use", "boundary"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["desk_reject_risk_closure"]:
            writer.writerow(
                {
                    "section": "desk_reject_risk_closure",
                    "id": row["id"],
                    "domain": row["severity"],
                    "question": row["risk"],
                    "status": row["status"],
                    "evidence": row["evidence"],
                    "reviewer_use": row["mitigation"],
                    "boundary": row["claim_boundary"] + " Author action: " + row["author_action"],
                }
            )
        for row in report["reviewer_checklist"]:
            writer.writerow(
                {
                    "section": "reviewer_checklist",
                    "id": row["domain"],
                    "domain": row["domain"],
                    "question": row["question"],
                    "status": row["status"],
                    "evidence": row["evidence"],
                    "reviewer_use": row["reviewer_use"],
                    "boundary": row["boundary"],
                }
            )


def write_markdown(report, path):
    lines = [
        "# Editorial Triage and Reviewer Checklist",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Triage Snapshot",
        "",
        f"- Recommendation: `{report['editorial_triage']['recommendation']}`",
        f"- Package verification: `{report['editorial_triage']['package_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- Claim QA: `{report['summary']['claim_qa_status']}`",
        f"- Statistical consistency: `{report['summary']['statistical_consistency_status']}`",
        f"- External archive pending: `{report['summary']['external_archive_pending']}`",
        f"- Author actions: {report['summary']['author_action_count']}",
        f"- Claim guardrail: {report['editorial_triage']['claim_guardrail']}",
        "",
        "## Desk-Reject Risk Closure",
        "",
        "| risk | severity | status | evidence | mitigation | boundary | author action |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report["desk_reject_risk_closure"]:
        lines.append(
            f"| {row['risk']} | {row['severity']} | {row['status']} | "
            f"`{row['evidence']}` | {row['mitigation']} | {row['claim_boundary']} | {row['author_action']} |"
        )
    lines.extend(
        [
            "",
        "## Reviewer Checklist",
        "",
        "| domain | question | status | evidence | reviewer use | boundary |",
        "|---|---|---|---|---|---|",
        ]
    )
    for row in report["reviewer_checklist"]:
        lines.append(
            f"| {row['domain']} | {row['question']} | {row['status']} | "
            f"`{row['evidence']}` | {row['reviewer_use']} | {row['boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Checklist rows: {report['summary']['checklist_count']}",
            f"- Desk-reject risk rows: {report['summary']['desk_reject_risk_count']}",
            f"- Desk-reject risk status counts: `{report['summary']['desk_reject_risk_status_counts']}`",
            f"- Status counts: `{report['summary']['status_counts']}`",
            f"- Threats-to-validity status counts: `{report['summary']['threats_to_validity_status_counts']}`",
            f"- Dependency unlisted release outputs after documented exclusions: {report['summary']['dependency_unlisted_release_output_count']}",
            f"- Dependency documented release exclusions: {report['summary']['dependency_documented_release_exclusion_count']}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export editorial triage and reviewer checklist.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    out_json = materials / "EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.json"
    out_md = materials / "EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md"
    out_csv = materials / "EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
