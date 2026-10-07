#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def row(
    row_id,
    domain,
    severity,
    status,
    threat,
    evidence,
    current_control,
    residual_risk,
    prohibited_claim,
    recommended_action,
    reviewer_likelihood,
    local_action_possible=False,
    blocks_submission=False,
):
    return {
        "id": row_id,
        "domain": domain,
        "severity": severity,
        "status": status,
        "threat": threat,
        "evidence": evidence,
        "current_control": current_control,
        "residual_risk": residual_risk,
        "prohibited_claim": prohibited_claim,
        "recommended_action": recommended_action,
        "reviewer_likelihood": reviewer_likelihood,
        "local_action_possible": local_action_possible,
        "blocks_submission": blocks_submission,
    }


def build_audit(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    external = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    seed_partition = load_json(root / "materials" / "SEED_PARTITION_AUDIT.json")
    sample = load_json(root / "materials" / "SAMPLE_SIZE_SENSITIVITY_BRIEF.json")
    selector = load_json(root / "materials" / "SELECTOR_DECISION_AUDIT.json")
    endpoint = load_json(root / "materials" / "ENDPOINT_SENSITIVITY_AUDIT.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")
    visual = load_json(root / "materials" / "VISUAL_EVIDENCE_AUDIT.json")
    sim2real = load_json(root / "materials" / "SIMULATION_TO_REAL_APPLICABILITY.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    fig_qc = load_json(root / "materials" / "FIGURE_TECHNICAL_QC.json")
    bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")

    external_summary = external["summary"]
    sample_summary = sample["summary"]
    rows = [
        row(
            "TV1_external_generalization",
            "external_validity",
            "high",
            "controlled_limitation",
            "Held-out performance varies across disjoint seed batches, with heldout3 negative validation and heldout4 partial transfer after targeted repair.",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md; tables/cross_heldout_validation_synthesis.md; tables/heldout4_external_validation.md",
            (
                f"External-validity audit reports expanded-or-later selector {external_summary['expanded_or_later_selector']} "
                f"and oracle {external_summary['expanded_or_later_oracle']} with explicit heldout3/heldout4 boundaries."
            ),
            "The current evidence supports simulator method development and bounded validation, not broad robustness.",
            "broad robustness or solved generalization",
            "Freeze the next selector/candidate design and run a larger fresh held-out batch before stronger claims.",
            "high",
        ),
        row(
            "TV2_seed_reuse_and_targeted_repair",
            "internal_validity",
            "high",
            "controlled_boundary",
            "Heldout3-targeted repair reuses diagnostic failures and must not be treated as independent external validation.",
            "materials/SEED_PARTITION_AUDIT.md; materials/STUDY_PROTOCOL_AND_DEVIATIONS.md; tables/heldout3_candidate_expansion.md",
            (
                f"Seed partition audit has {seed_partition['summary']['unexpected_overlap_count']} unexpected overlaps "
                f"and {seed_partition['summary']['documented_diagnostic_overlap_count']} documented diagnostic overlap."
            ),
            "Targeted repair remains useful as a mechanism diagnostic, but independent validation begins again only on heldout4 or later.",
            "heldout3 targeted repair as external validation",
            "Keep seed-set labels visible in Methods, Results, figure legends, and reviewer responses.",
            "high",
        ),
        row(
            "TV3_small_n_precision",
            "statistical_conclusion_validity",
            "high",
            "controlled_limitation",
            "Per-stage held-out batches are n=10, so interval widths remain too wide for population-level robustness claims.",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md; tables/cross_heldout_statistical_supplement.md",
            (
                f"Sample-size audit reports expanded-or-later selector {sample_summary['expanded_or_later_selector']} "
                f"across {sample_summary['expanded_or_later_n']} seeds, with planning thresholds for larger-N validation."
            ),
            "Descriptive seed-set statistics are appropriate; confirmatory performance estimation requires larger frozen batches.",
            "population-level robustness or superiority",
            "Use Wilson intervals and exact tests descriptively; preregister larger-N validation before broad claims.",
            "high",
        ),
        row(
            "TV4_selector_decision_transparency",
            "construct_validity",
            "medium",
            "controlled",
            "Online portfolio probing could hide decision leakage or unsupported oracle-like information if not audited.",
            "materials/SELECTOR_DECISION_AUDIT.md; tables/seed_outcome_ledger.md",
            (
                f"Selector decision audit covers {selector['summary']['decision_row_count']} decisions with "
                f"{selector['summary']['total_mismatch_count']} recomputation mismatches and "
                f"{selector['summary']['total_forbidden_probe_field_count']} forbidden probe fields."
            ),
            "The audit supports saved selector transparency, not selector optimality or out-of-distribution safety.",
            "selector optimality or oracle-equivalent online selection",
            "Retain probe-only decision audits and source CSVs with any selector-performance figure.",
            "medium",
        ),
        row(
            "TV5_endpoint_definition_sensitivity",
            "construct_validity",
            "medium",
            "controlled_limitation",
            "Strict PASS/FAIL outcomes may depend on endpoint thresholds such as grass rate, rank, lap completion, and first-ahead timing.",
            "materials/ENDPOINT_SENSITIVITY_AUDIT.md; materials/STATISTICAL_CONSISTENCY_AUDIT.md",
            (
                f"Endpoint sensitivity audit evaluates {endpoint['summary']['scenario_count']} scenarios and "
                f"flags {endpoint['summary']['endpoint_sensitive_stage_methods']} sensitive stage-method rows."
            ),
            "Sensitivity is characterized for nearby saved-threshold scenarios but does not replace new validation.",
            "threshold-invariant performance",
            "Report strict endpoint definitions before sensitivity tables and avoid selecting thresholds post hoc.",
            "medium",
        ),
        row(
            "TV6_negative_result_visibility",
            "reporting_validity",
            "high",
            "controlled",
            "Selective reporting would overstate the method if failed variants, selector misses, or candidate gaps were omitted.",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; tables/heldout4_failure_atlas.md",
            f"Negative-results register retains {negative['summary']['item_count']} negative or limitation rows.",
            "Negative results are visible locally, but final manuscript drafting must preserve them rather than compress them away.",
            "unqualified improvement or solved failure modes",
            "Keep failure atlases and negative-control rows in supplementary material and Discussion.",
            "high",
        ),
        row(
            "TV7_visual_evidence_overread",
            "reporting_validity",
            "medium",
            "controlled",
            "Qualitative GIFs can be overread as proof of success if disconnected from strict seed-level tables.",
            "materials/VISUAL_EVIDENCE_AUDIT.md; figures/*_source_data.csv",
            (
                f"Visual evidence audit catalogs {visual['summary']['gif_count']} GIFs and marks them as qualitative support only."
            ),
            "GIFs are useful for reviewer orientation, but quantitative claims must cite validator tables.",
            "GIF-based success rates or robustness",
            "Use representative GIFs only alongside seed-level PASS/FAIL tables and source data.",
            "medium",
        ),
        row(
            "TV8_simulation_to_real_scope",
            "external_validity",
            "high",
            "controlled_guardrail",
            "Simulator-only state/telemetry evidence does not establish real-road deployment, perception robustness, or safety certification.",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.md; materials/RESEARCH_RISK_AND_SAFETY.md",
            (
                f"Simulation-to-real boundary and risk register are present; research-risk rows: {len(risk['risk_items'])}."
            ),
            "The package supports simulator evidence only; real-world transfer would require new perception, dynamics, and safety evidence.",
            "real-road deployment readiness, perception-stack support, VLM autonomy, or safety certification",
            "Copy simulator-only wording into manuscript, cover letter, ethics/safety forms, and archive README.",
            "high",
        ),
        row(
            "TV9_figure_and_source_data_integrity",
            "reproducibility_validity",
            "medium",
            "controlled",
            "Figure exports or source-data files could become inconsistent during journal-specific resizing or format conversion.",
            "materials/FIGURE_SOURCE_DATA_AUDIT.md; materials/FIGURE_TECHNICAL_QC.md",
            (
                f"Figure technical QC passes {fig_qc['summary']['pass_count']}/{fig_qc['summary']['figure_count']} figures; "
                f"final bundle missing required files: {bundle['summary']['missing_required_count']}."
            ),
            "Current files are internally consistent, but journal production edits require rerunning QC.",
            "figure-only evidence without source-data traceability",
            "Rerun figure source-data and technical QC after final journal layout/export changes.",
            "medium",
            local_action_possible=True,
        ),
        row(
            "TV10_archive_and_author_metadata",
            "reproducibility_validity",
            "high",
            "author_action_required",
            "Local package checks cannot substitute for public DOI/accession, author identity, disclosures, funding, or final journal source.",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.md; materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/SUBMISSION_METADATA_DRAFT.md",
            "Local verification passes, but archive DOI/accession and author-certified metadata remain outside automation.",
            "The package is locally reproducible but not a completed journal submission record.",
            "final submission readiness or public archive completion",
            "Authors must deposit the archive, add DOI/URL/accession, certify metadata, and rerun final freeze checks.",
            "high",
            local_action_possible=False,
            blocks_submission=True,
        ),
    ]

    status_counts = {}
    severity_counts = {}
    for item in rows:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
        severity_counts[item["severity"]] = severity_counts.get(item["severity"], 0) + 1
    return {
        "root": str(root),
        "title": "Threats-to-validity audit",
        "purpose": (
            "Provide a reviewer-facing threats-to-validity map for simulator-only multi-car overtaking claims, "
            "linking each validity threat to evidence, current controls, residual risk, prohibited claims, and next actions."
        ),
        "summary": {
            "row_count": len(rows),
            "high_severity_count": severity_counts.get("high", 0),
            "author_action_required_count": status_counts.get("author_action_required", 0),
            "blocks_submission_count": sum(1 for item in rows if item["blocks_submission"]),
            "status_counts": status_counts,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
        },
        "threats": rows,
        "interpretation": (
            "This audit is a claim-control and reviewer-preparation artifact. It does not add new empirical evidence; "
            "it makes the current evidence boundaries explicit so manuscript claims remain conservative."
        ),
    }


def write_csv(report, path):
    fields = [
        "id",
        "domain",
        "severity",
        "status",
        "threat",
        "evidence",
        "current_control",
        "residual_risk",
        "prohibited_claim",
        "recommended_action",
        "reviewer_likelihood",
        "local_action_possible",
        "blocks_submission",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["threats"])


def write_markdown(report, path):
    lines = [
        "# Threats-to-validity Audit",
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
            "## Threats",
            "",
            "| id | domain | severity | status | threat | evidence | residual risk | prohibited claim | action |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["threats"]:
        lines.append(
            f"| {item['id']} | {item['domain']} | {item['severity']} | {item['status']} | "
            f"{item['threat']} | `{item['evidence']}` | {item['residual_risk']} | "
            f"{item['prohibited_claim']} | {item['recommended_action']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export threats-to-validity audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_audit(root)
    out_json = materials / "THREATS_TO_VALIDITY_AUDIT.json"
    out_md = materials / "THREATS_TO_VALIDITY_AUDIT.md"
    out_csv = materials / "THREATS_TO_VALIDITY_AUDIT.csv"
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
