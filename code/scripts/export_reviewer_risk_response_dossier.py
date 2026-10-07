#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def row(row_id, theme, likely_question, status, evidence, response, boundary, follow_up, priority):
    return {
        "id": row_id,
        "theme": theme,
        "likely_question": likely_question,
        "status": status,
        "evidence": evidence,
        "recommended_response": response,
        "claim_boundary": boundary,
        "follow_up": follow_up,
        "priority": priority,
    }


def build_dossier(root):
    manifest = load_json(root / "manifest.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    external = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")
    sample = load_json(root / "materials" / "SAMPLE_SIZE_SENSITIVITY_BRIEF.json")
    selector = load_json(root / "materials" / "SELECTOR_DECISION_AUDIT.json")
    seeds = load_json(root / "materials" / "SEED_PARTITION_AUDIT.json")
    fairness = load_json(root / "materials" / "BASELINE_FAIRNESS_AUDIT.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    sim2real = load_json(root / "materials" / "SIMULATION_TO_REAL_APPLICABILITY.json")
    references = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")
    visual = load_json(root / "materials" / "VISUAL_EVIDENCE_AUDIT.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")

    key = manifest["key_results"]
    locked = key["locked_single_methods"]
    heldout4 = key["heldout4_external_after_targeted_repair"]
    cross = key["cross_heldout_synthesis"]

    rows = [
        row(
            "RR1_baseline_strength",
            "baseline_fairness",
            "Could the observed gains be explained by weak or unfair baselines?",
            "evidence_ready",
            "materials/BASELINE_FAIRNESS_AUDIT.md; tables/full_statistical_report.md",
            (
                "Report the preserved strong telemetry/rule baselines, shared seed sets, shared strict validator, "
                f"and locked-suite counts: overtake baseline {locked['overtake_base_only']['pass_count']}/"
                f"{locked['overtake_base_only']['n']} versus graph-adaptive shield "
                f"{locked['graph_adaptive_shield']['pass_count']}/{locked['graph_adaptive_shield']['n']}."
            ),
            "Do not frame the innovation as uniformly superior to all baselines; present complementarity and selector evidence.",
            "Keep baseline audit with the submission supplement and avoid removing negative controls.",
            "high",
        ),
        row(
            "RR2_generalization_limit",
            "external_validity",
            "Does the method generalize beyond the tuned seed sets?",
            "limitation_explicit",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md; tables/cross_heldout_validation_synthesis.md",
            (
                "State the held-out ladder explicitly: heldout1 is positive, heldout2 and heldout3 expose stress failures, "
                f"and heldout4 after targeted repair gives partial transfer at {heldout4['selector_pass_count']}/"
                f"{heldout4['selector_n']} against an oracle of {heldout4['oracle_pass_count']}/{heldout4['oracle_n']}."
            ),
            "Do not claim broad robustness; describe saved held-out evidence and its limits.",
            "For a stronger journal revision, run a larger pre-registered held-out seed batch before broad claims.",
            "high",
        ),
        row(
            "RR3_oracle_boundary",
            "selector_boundary",
            "Are oracle portfolio results being used as if they were online selector outputs?",
            "guardrail_ready",
            "materials/CLAIM_EVIDENCE_MATRIX.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "Separate online simulator-loop selector rows from diagnostic oracle upper bounds in every table, figure, and response.",
            "Oracle portfolios are diagnostic upper bounds only and must not be described as controllers.",
            "Keep oracle wording in legends and cover-letter language constrained by the claim matrix.",
            "high",
        ),
        row(
            "RR4_selector_transparency",
            "selector_boundary",
            "Can the online selector decision rule be audited?",
            selector["summary"]["status"],
            "materials/SELECTOR_DECISION_AUDIT.md; tables/seed_outcome_ledger.md",
            (
                "Point reviewers to the decision audit, which recomputes selector choices from probe-only fields, "
                f"covering {selector['summary']['decision_row_count']} decisions with "
                f"{selector['summary']['total_mismatch_count']} mismatches."
            ),
            "Selector audit supports transparency of saved decisions, not optimality or broad out-of-distribution safety.",
            "Retain selector decision CSVs as source data for any selector-performance figure.",
            "high",
        ),
        row(
            "RR5_seed_leakage",
            "experimental_design",
            "Was there seed leakage between tuning, diagnostics, and external validation?",
            seeds["summary"]["status"],
            "materials/SEED_PARTITION_AUDIT.md; materials/STUDY_PROTOCOL_AND_DEVIATIONS.md",
            (
                "Use the seed-partition audit to distinguish locked, heldout1, heldout2, heldout3, heldout4, "
                "and diagnostic hard-smoke uses."
            ),
            "Heldout3 targeted repair is diagnostic reuse, not external validation; heldout4 is post-repair external validation.",
            "Keep seed-set labels visible in manuscript methods and supplementary tables.",
            "high",
        ),
        row(
            "RR6_sample_size",
            "statistics",
            "Are n=10 held-out batches sufficient for strong claims?",
            "limitation_explicit",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md; materials/STATISTICAL_ANALYSIS_PLAN.md",
            (
                f"Report exact seed counts, Wilson intervals, and the current cross-held-out aggregate "
                f"({cross.get('selector_pass_count', 'NA')}/{cross.get('n', 'NA')} selector where applicable) as descriptive evidence."
            ),
            "Current seed counts support method development and stress testing, not population-level robustness.",
            "Use the planning grid to size a larger confirmatory validation batch.",
            "high",
        ),
        row(
            "RR7_negative_results",
            "selective_reporting",
            "Were failed variants or negative controls omitted?",
            "evidence_ready",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; tables/heldout2_failure_atlas.md; tables/heldout4_failure_atlas.md",
            (
                f"Report that {negative['summary'].get('register_row_count', negative['summary']['item_count'])} "
                "negative or limitation rows are retained, "
                "including failed expert controls, selector misses, candidate gaps, and targeted-repair boundaries."
            ),
            "Negative results are part of the evidence package and should not be hidden in final drafting.",
            "Keep failure atlas tables in supplementary material.",
            "high",
        ),
        row(
            "RR8_endpoint_sensitivity",
            "metrics",
            "Could the result change under nearby endpoint definitions?",
            "evidence_ready",
            "materials/ENDPOINT_SENSITIVITY_AUDIT.md; materials/STATISTICAL_CONSISTENCY_AUDIT.md",
            "Point to the endpoint-threshold and gate-ablation sensitivity audit computed from saved rollout summaries.",
            "Sensitivity analysis is local to predefined nearby thresholds and does not replace new validation rollouts.",
            "Mention strict validator definition before presenting sensitivity rows.",
            "medium",
        ),
        row(
            "RR9_visual_evidence",
            "qualitative_evidence",
            "Do GIFs prove the quantitative claims?",
            "guardrail_ready",
            "materials/VISUAL_EVIDENCE_AUDIT.md; figures/*_source_data.csv",
            (
                f"Use the {visual['summary']['gif_count']} GIFs only as qualitative illustrations and direct reviewers "
                "to strict validation tables for quantitative claims."
            ),
            "GIFs cannot substitute for seed-level PASS/FAIL tables.",
            "Select representative GIFs only after checking they correspond to documented result rows.",
            "medium",
        ),
        row(
            "RR10_sim_to_real",
            "scope_boundary",
            "Does simulator success imply real-road deployment readiness?",
            "guardrail_ready",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.md; materials/RESEARCH_RISK_AND_SAFETY.md",
            "State that the package is simulator-only and excludes perception stacks, real vehicles, public roads, and certification.",
            "No real-road, safety-certification, or deployment-readiness claim is supported.",
            "Copy simulator-only wording into manuscript, cover letter, and journal ethics/safety forms.",
            "high",
        ),
        row(
            "RR11_references",
            "related_work",
            "Is the related-work context complete enough for a top-journal submission?",
            "author_action_required" if references["summary"]["topic_needs_author_completion_count"] else references["summary"]["status"],
            "materials/REFERENCE_READINESS_AUDIT.md; manuscript/references.bib",
            "Use the current bibliography as a starter set and expand the domain-specific related work before final submission.",
            "Reference readiness is not a polished literature review.",
            "Add recent multi-agent RL, autonomous racing, safe learning, and sim-to-real citations.",
            "high",
        ),
        row(
            "RR12_archive_reproducibility",
            "reproducibility",
            "Can reviewers reproduce and audit the package?",
            verification["summary"]["status"],
            "materials/REPRODUCTION_GUIDE.md; materials/RELEASE_ARCHIVE_MANIFEST.md; tables/artifact_provenance.md",
            (
                f"Report local preflight status: verification {verification['summary']['status']}, "
                f"statistical consistency {stats['summary']['status']}, and release manifest "
                f"{release['summary']['file_count']} files."
            ),
            "Local reproducibility is not a public archive until DOI/accession is assigned.",
            "Deposit the package and update DOI/URL fields before submission.",
            "high",
        ),
        row(
            "RR13_ethics_safety",
            "ethics_and_safety",
            "Are there unresolved safety or ethics claims?",
            "ready_with_author_certification",
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/SUBMISSION_METADATA_DRAFT.md",
            f"Use the risk register with {len(risk['risk_items'])} items to fill journal safety and ethics fields.",
            "Local draft text is not author-certified disclosure.",
            "Authors must confirm funding, competing interests, approvals, and institution-specific declarations.",
            "high",
        ),
    ]

    status_counts = {}
    for item in rows:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1

    return {
        "root": str(root),
        "title": "Reviewer risk-response dossier",
        "purpose": (
            "Map likely reviewer and editor critiques to exact evidence files, conservative response wording, "
            "claim boundaries, and follow-up actions for a top-journal-style submission package."
        ),
        "rows": rows,
        "summary": {
            "row_count": len(rows),
            "high_priority_count": sum(1 for item in rows if item["priority"] == "high"),
            "author_action_count": sum(1 for item in rows if "author_action" in item["status"]),
            "status_counts": status_counts,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "statistical_consistency_status": stats["summary"]["status"],
            "external_archive_pending": True,
        },
        "interpretation": (
            "This dossier is a response-preparation aid, not a substitute for final author-certified responses. "
            "It intentionally preserves limitations and negative results."
        ),
    }


def write_csv(report, path):
    fields = [
        "id",
        "theme",
        "likely_question",
        "status",
        "evidence",
        "recommended_response",
        "claim_boundary",
        "follow_up",
        "priority",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow(item)


def write_markdown(report, path):
    lines = [
        "# Reviewer Risk-Response Dossier",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Rows: {report['summary']['row_count']}",
        f"- High-priority rows: {report['summary']['high_priority_count']}",
        f"- Author-action rows: {report['summary']['author_action_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- Statistical consistency: `{report['summary']['statistical_consistency_status']}`",
        "",
        "## Risk-Response Map",
        "",
        "| id | theme | priority | status | likely question | evidence | recommended response | claim boundary | follow-up |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in report["rows"]:
        lines.append(
            f"| {item['id']} | {item['theme']} | {item['priority']} | {item['status']} | "
            f"{item['likely_question']} | `{item['evidence']}` | {item['recommended_response']} | "
            f"{item['claim_boundary']} | {item['follow_up']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export reviewer risk-response dossier.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_dossier(root)
    out_json = materials / "REVIEWER_RISK_RESPONSE_DOSSIER.json"
    out_md = materials / "REVIEWER_RISK_RESPONSE_DOSSIER.md"
    out_csv = materials / "REVIEWER_RISK_RESPONSE_DOSSIER.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
