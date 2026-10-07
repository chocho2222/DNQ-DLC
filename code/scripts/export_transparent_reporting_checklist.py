#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def exists(root, rel):
    return (root / rel).exists() or Path(rel).exists()


def item(category, item_id, requirement, status, evidence, limitation="", action=""):
    return {
        "category": category,
        "id": item_id,
        "requirement": requirement,
        "status": status,
        "evidence": evidence,
        "limitation": limitation,
        "action": action,
    }


def build_checklist(root):
    manifest = load_json(root / "manifest.json")
    audit = load_json(root / "tables" / "reproducibility_audit.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    heldout = load_json(root / "tables" / "heldout_generalization.json")
    calibration = load_json(root / "tables" / "selector_calibration.json")
    atlas = load_json(root / "tables" / "heldout2_failure_atlas.json")
    candidate_expansion = load_json(root / "tables" / "heldout2_candidate_expansion.json")
    expanded_selector = load_json(root / "tables" / "expanded_selector_generalization.json")
    expanded_distillation = load_json(root / "tables" / "expanded_selector_distillation_report.json")
    learned_selector = load_json(root / "tables" / "learned_selector_report.json")
    heldout3 = load_json(root / "tables" / "heldout3_external_validation.json")
    heldout3_expansion = load_json(root / "tables" / "heldout3_candidate_expansion.json")
    heldout4 = load_json(root / "tables" / "heldout4_external_validation.json")
    heldout4_atlas = load_json(root / "tables" / "heldout4_failure_atlas.json")
    cross_heldout = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")

    items = [
        item(
            "Study scope",
            "scope_non_vlm",
            "Declare task scope and excluded components.",
            "complete",
            ["manifest.json", "materials/METHODS.md", "materials/DATA_CODE_AVAILABILITY.md"],
            "VLM components are intentionally excluded.",
        ),
        item(
            "Study design",
            "seed_sets",
            "Report locked, held-out, and hard-smoke seed sets.",
            "complete",
            ["manifest.json", "materials/STATISTICAL_ANALYSIS_PLAN.md", "tables/heldout_generalization.md"],
        ),
        item(
            "Endpoints",
            "primary_endpoint",
            "Define the primary success endpoint before interpreting results.",
            "complete",
            ["materials/STATISTICAL_ANALYSIS_PLAN.md", "scripts/validate_multicar_lap.py"],
        ),
        item(
            "Baselines",
            "baseline_preservation",
            "Preserve baseline methods and report the strongest baseline.",
            "complete",
            ["baselines/", "tables/full_statistical_report.md", "materials/PUBLICATION_PACKAGE_SUMMARY.md"],
        ),
        item(
            "Methods",
            "innovation_stack",
            "Describe learned actor, shields, DAgger recovery, selector, and negative controls.",
            "complete",
            ["materials/METHODS.md", "materials/LIMITATIONS.md", "materials/MANUSCRIPT_OUTLINE.md"],
        ),
        item(
            "Statistics",
            "intervals_tests",
            "Report confidence intervals and paired comparisons where applicable.",
            "complete",
            ["tables/full_statistical_report.md", "materials/STATISTICAL_ANALYSIS_PLAN.md"],
            "Small seed counts require descriptive rather than confirmatory interpretation.",
        ),
        item(
            "Generalization",
            "heldout_repeats",
            "Report at least one positive held-out result and a stress repeat.",
            "complete",
            ["tables/heldout_generalization.md", "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.md"],
            "Heldout2 prevents a broad robustness claim.",
        ),
        item(
            "External validation",
            "heldout3_external_validation",
            "Report a third disjoint external validation batch after selector/candidate expansion.",
            "complete",
            [
                "tables/heldout3_external_validation.md",
                "tables/portfolio_probe_selector_1200_heldout3_expanded.md",
                "tables/learned_selector_report.md",
            ],
            "Heldout3 is negative external validation: expanded selector 4/10 and learned selector 4/10 against an 8/10 oracle.",
        ),
        item(
            "Targeted repair",
            "heldout3_candidate_expansion",
            "Report heldout3-targeted candidate repair separately from external validation.",
            "complete",
            [
                "tables/heldout3_candidate_expansion.md",
                "tables/heldout3_targeted_recovery_suite_report.md",
                "tables/heldout3_targeted_recovery_conservative_traffic_suite_report.md",
            ],
            "Targeted repair improves candidate oracle to 10/10 but is not an online selector result or external-validation result.",
        ),
        item(
            "External validation",
            "heldout4_external_after_repair",
            "Report a fourth unused external validation batch after heldout3-targeted repair.",
            "complete",
            [
                "tables/heldout4_external_validation.md",
                "tables/heldout4_failure_atlas.md",
                "figures/figure_3_cross_heldout_validation.png",
                "figures/figure_3_source_data.csv",
            ],
            "Heldout4 shows partial transfer: selector 6/10 against an 8/10 oracle, not robustness.",
        ),
        item(
            "Synthesis",
            "cross_heldout_synthesis",
            "Report cross-heldout selector and oracle evidence without averaging away failures.",
            "complete",
            [
                "tables/cross_heldout_validation_synthesis.md",
                "figures/figure_3_cross_heldout_validation.png",
                "materials/CLAIM_EVIDENCE_MATRIX.md",
            ],
            "The expanded-or-later aggregate is descriptive and should not be presented as broad robustness evidence.",
        ),
        item(
            "Failure analysis",
            "failure_decomposition",
            "Separate candidate-policy gaps from selector misses.",
            "complete",
            ["tables/selector_calibration.md", "tables/heldout2_failure_atlas.md"],
        ),
        item(
            "Negative results",
            "negative_controls",
            "Preserve negative controls and failed variants.",
            "complete",
            [
                "tables/heldout_expert_fast_smoke_report.md",
                "tables/heldout_expert_barrier_smoke_report.md",
                "tables/heldout_expert_recovery_smoke_report.md",
                "materials/LIMITATIONS.md",
            ],
        ),
        item(
            "Figures",
            "figure_source_data",
            "Provide figure exports and source data.",
            "complete",
            [
                "figures/figure_1_multicar_overtake_results.png",
                "figures/figure_1_source_data.csv",
                "figures/figure_2_portfolio_selector_summary.png",
                "figures/figure_2_source_data.csv",
                "figures/figure_3_cross_heldout_validation.png",
                "figures/figure_3_source_data.csv",
                "materials/FIGURE_LEGENDS.md",
            ],
        ),
        item(
            "Data",
            "machine_readable_data",
            "Provide machine-readable tables and raw summaries.",
            "complete",
            [
                "tables/*.json",
                "tables/*_rows.csv",
                "tables/seed_outcome_ledger.csv",
                "materials/DATA_DICTIONARY.md",
                "evaluations/*/multiseed_suite_summary.json",
            ],
        ),
        item(
            "Code",
            "code_snapshots",
            "Provide scripts and policy/rollout code snapshots.",
            "complete",
            ["scripts/", "materials/scripts/", "materials/dlc/", "gym_multi_car_racing/"],
        ),
        item(
            "Study Design",
            "experiment_registry",
            "Register experiment roles, seed sets, endpoints, evidence files, and claim boundaries.",
            "complete",
            ["materials/EXPERIMENT_REGISTRY.md", "materials/EXPERIMENT_REGISTRY.json", "materials/EXPERIMENT_REGISTRY.csv"],
            "The registry distinguishes locked development, stress-repeat, external-validation, targeted-diagnostic, post-repair external-validation, and descriptive synthesis stages.",
            "Use the registry as the source of truth when drafting Methods, Results, and reviewer responses.",
        ),
        item(
            "Compute",
            "compute_record",
            "Record compute devices and environment information.",
            "complete",
            [
                "manifest.json",
                "environment.yml",
                "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
                "tables/reproducibility_audit.md",
                "tables/compute_cost_report.md",
            ],
            "Compute scale is summarized by simulated steps, probe counts, and devices; exact wall-clock and utilization are unavailable.",
            "Add timed reruns or utilization logging if a venue requires elapsed-time cost accounting.",
        ),
        item(
            "Reproduction",
            "artifact_provenance",
            "Provide artifact-level commands and audit status.",
            "complete",
            ["tables/artifact_provenance.md", "tables/reproducibility_audit.md"],
        ),
        item(
            "Reproduction",
            "artifact_dependency_map",
            "Provide a reviewer-facing dependency map linking artifacts to inputs, outputs, scripts, commands, and file edges.",
            "complete",
            [
                "materials/ARTIFACT_DEPENDENCY_MAP.md",
                "materials/ARTIFACT_DEPENDENCY_MAP.csv",
                "materials/ARTIFACT_DEPENDENCY_FILE_EDGES.csv",
                "tables/artifact_provenance.md",
            ],
            "The dependency map summarizes provenance; artifact_provenance remains the command-level source of truth.",
            "Use it for audit navigation and figure/table lineage checks.",
        ),
        item(
            "Reproduction",
            "publication_package_verification",
            "Provide a one-command local preflight gate for provenance, audit, claim QA, registry, ledger, release, and forbidden-text checks.",
            "complete",
            [
                "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
                "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
                "materials/PUBLICATION_PACKAGE_VERIFICATION.csv",
            ],
        ),
        item(
            "Claims",
            "claim_guardrails",
            "Map manuscript claims to evidence and prohibited overclaims.",
            "complete",
            ["materials/CLAIM_EVIDENCE_MATRIX.md", "materials/REVIEWER_RESPONSE_MAP.md"],
        ),
        item(
            "Claims",
            "risk_and_safety_boundaries",
            "Provide simulation-only, oracle-boundary, overclaim, reproducibility, and archive-risk controls.",
            "complete",
            [
                "materials/RESEARCH_RISK_AND_SAFETY.md",
                "materials/CLAIM_EVIDENCE_MATRIX.md",
                "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            ],
            "The statement records that no human-subject, animal, personal-data, real-vehicle, or public-road evidence is included.",
            "Use the required wording and prohibited-claim list before manuscript submission.",
        ),
        item(
            "Manuscript preparation",
            "editor_reporting_summary",
            "Provide an editor-facing reporting summary for methods, statistics, data/code, reproducibility, and safety items.",
            "complete",
            [
                "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
                "materials/STATISTICAL_ANALYSIS_PLAN.md",
                "materials/DATA_CODE_AVAILABILITY.md",
                "materials/RESEARCH_RISK_AND_SAFETY.md",
            ],
            "The reporting summary keeps sample-size, archive, and final-manuscript limitations explicit.",
            "Use this as the source for journal reporting forms or editorial checklists.",
        ),
        item(
            "Manuscript preparation",
            "editorial_submission_checklist",
            "Provide a submission-system checklist that separates evidence-package readiness from author-input metadata.",
            "complete",
            [
                "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
                "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
                "materials/RESEARCH_RISK_AND_SAFETY.md",
            ],
            "The checklist flags DOI/accession, final manuscript source, author contributions, competing interests, funding, and ORCID metadata as unresolved or author-provided where appropriate.",
            "Use this before uploading to a journal portal.",
        ),
        item(
            "Manuscript preparation",
            "significance_briefing",
            "Provide evidence-bound cover-letter and editor-facing significance material.",
            "complete",
            [
                "materials/SIGNIFICANCE_BRIEFING.md",
                "materials/CLAIM_EVIDENCE_MATRIX.md",
                "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
            ],
            "The briefing separates significance points from prohibited claims and keeps external-validation boundaries explicit.",
            "Use as source material, not as a final cover letter.",
        ),
        item(
            "Manuscript preparation",
            "manuscript_materials",
            "Provide outline, Results/Discussion scaffold, and reviewer response map.",
            "complete",
            [
                "materials/MANUSCRIPT_OUTLINE.md",
                "materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md",
                "materials/REVIEWER_RESPONSE_MAP.md",
            ],
        ),
        item(
            "External archiving",
            "doi_release",
            "Provide public DOI or repository accession for submission.",
            "limitation",
            ["materials/DATA_CODE_AVAILABILITY.md"],
            "No public DOI or repository accession number is included in the local package.",
            "Archive final code/data package in Zenodo/OSF/GitHub release before external submission.",
        ),
        item(
            "Final manuscript",
            "final_pdf_source",
            "Provide final submission-ready manuscript PDF/source outside the experimental package.",
            "limitation",
            ["tables/reproducibility_audit.md", "materials/DATA_CODE_AVAILABILITY.md", "manuscript/main.md"],
            "A local evidence-linked manuscript draft exists, but no final submission PDF/source is stored.",
            "Promote the draft to final manuscript source after finalizing claims and larger-N experiments.",
        ),
        item(
            "Robustness",
            "larger_n_stress",
            "Run larger-N and traffic/opponent diversity stress tests before broad robustness claims.",
            "limitation",
            ["materials/TOP_JOURNAL_READINESS_CHECKLIST.md", "materials/MANUSCRIPT_OUTLINE.md"],
            "Current held-out evidence includes four 10-seed batches, with heldout3 exposing a negative external-validation boundary and heldout4 showing partial post-repair transfer.",
            "Add larger held-out batches and traffic-density/opponent-diversity ablations.",
        ),
    ]

    counts = {}
    for row in items:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    missing_evidence = []
    for row in items:
        for rel in row["evidence"]:
            if "*" in rel or rel.endswith("/"):
                continue
            if not exists(root, rel):
                missing_evidence.append({"id": row["id"], "path": rel})

    return {
        "root": str(root),
        "scope": manifest["scope"],
        "summary": {
            "total_items": len(items),
            "status_counts": counts,
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "audit_missing_or_weak": len(audit["missing_or_weak_items"]),
            "heldout1_selector": f"{heldout['sets']['heldout1']['selector']['pass_count']}/{heldout['sets']['heldout1']['selector']['n']}",
            "heldout2_selector": f"{heldout['sets']['heldout2']['selector']['pass_count']}/{heldout['sets']['heldout2']['selector']['n']}",
            "heldout2_oracle": f"{heldout['sets']['heldout2']['selector']['oracle_pass_count']}/{heldout['sets']['heldout2']['selector']['n']}",
            "heldout2_expanded_candidate_oracle": (
                f"{candidate_expansion['expanded_oracle']['pass_count']}/"
                f"{candidate_expansion['expanded_oracle']['n']}"
            ),
            "candidate_gap_seeds": atlas["summary"]["candidate_gap_seeds"],
            "expanded_candidate_gap_seeds": candidate_expansion["expanded_oracle"]["remaining_candidate_gap_seeds"],
            "heldout1_expanded_selector": (
                f"{expanded_selector['summaries']['heldout1_expanded']['pass_count']}/"
                f"{expanded_selector['summaries']['heldout1_expanded']['n']}"
            ),
            "heldout2_expanded_selector": (
                f"{expanded_selector['summaries']['heldout2_expanded']['pass_count']}/"
                f"{expanded_selector['summaries']['heldout2_expanded']['n']}"
            ),
            "expanded_selector_miss_seeds": expanded_selector["summaries"]["heldout2_expanded"]["selector_miss_seeds"],
            "expanded_selector_distillation": (
                f"{expanded_distillation['best_train_perfect']['heldout2_pass_count']}/"
                f"{expanded_selector['summaries']['heldout2_expanded']['n']}"
            ),
            "expanded_selector_distillation_train_perfect": expanded_distillation["grid"]["heldout1_perfect_configs"],
            "learned_selector_h1": (
                f"{learned_selector['variants'][learned_selector['primary_variant']]['train']['pass_count']}/"
                f"{learned_selector['variants'][learned_selector['primary_variant']]['train']['n']}"
            ),
            "learned_selector_h2": (
                f"{learned_selector['variants'][learned_selector['primary_variant']]['test']['pass_count']}/"
                f"{learned_selector['variants'][learned_selector['primary_variant']]['test']['n']}"
            ),
            "learned_selector_h3": (
                f"{learned_selector['variants'][learned_selector['primary_variant']]['external_heldout3']['pass_count']}/"
                f"{learned_selector['variants'][learned_selector['primary_variant']]['external_heldout3']['n']}"
            ),
            "heldout3_oracle": f"{heldout3['oracle']['pass_count']}/{heldout3['oracle']['n']}",
            "heldout3_candidate_gap_seeds": heldout3["oracle"]["candidate_gap_seeds"],
            "heldout3_expanded_selector": (
                f"{heldout3['expanded_selector']['pass_count']}/"
                f"{heldout3['expanded_selector']['n']}"
            ),
            "heldout3_expanded_selector_failed_seeds": heldout3["expanded_selector"]["failed_seeds"],
            "heldout3_targeted_expanded_oracle": (
                f"{heldout3_expansion['expanded_oracle']['pass_count']}/"
                f"{heldout3_expansion['expanded_oracle']['n']}"
            ),
            "heldout3_targeted_newly_covered": heldout3_expansion["expanded_oracle"]["newly_covered_seeds"],
            "heldout3_targeted_remaining_gaps": heldout3_expansion["expanded_oracle"]["remaining_candidate_gap_seeds"],
            "heldout4_selector": f"{heldout4['selector']['pass_count']}/{heldout4['selector']['n']}",
            "heldout4_oracle": f"{heldout4['oracle']['pass_count']}/{heldout4['oracle']['n']}",
            "heldout4_selector_miss_seeds": heldout4["selector"]["selector_miss_seeds"],
            "heldout4_candidate_gap_seeds": heldout4["oracle"]["candidate_gap_seeds"],
            "heldout4_failure_atlas_interpretation": heldout4_atlas["summary"]["interpretation"],
            "cross_heldout_selector": (
                f"{cross_heldout['aggregate_expanded_or_later']['selector_pass_count']}/"
                f"{cross_heldout['aggregate_expanded_or_later']['n']}"
            ),
            "cross_heldout_oracle": (
                f"{cross_heldout['aggregate_expanded_or_later']['oracle_pass_count']}/"
                f"{cross_heldout['aggregate_expanded_or_later']['n']}"
            ),
            "cross_heldout_selector_oracle_gap": cross_heldout["aggregate_expanded_or_later"]["selector_oracle_gap"],
            "selector_miss_seeds": atlas["summary"]["selector_miss_seeds"],
            "calibrated_heldout2": f"{calibration['test_heldout2']['pass_count']}/{calibration['test_heldout2']['n']}",
        },
        "items": items,
        "missing_evidence": missing_evidence,
        "interpretation": (
            "The package satisfies the main local reporting and reproducibility requirements, while external archiving, "
            "final manuscript source, and broader robustness experiments remain limitations before a strong top-journal submission."
        ),
    }


def write_markdown(report, path):
    s = report["summary"]
    lines = [
        "# Transparent Reporting Checklist",
        "",
        "This checklist translates the experiment package into reviewer-facing reporting requirements.",
        "",
        "## Summary",
        "",
        f"- Total items: {s['total_items']}",
        f"- Status counts: {s['status_counts']}",
        f"- Artifact provenance: {s['artifact_provenance']}",
        f"- Reproducibility missing/weak items: {s['audit_missing_or_weak']}",
        f"- Heldout1 selector: {s['heldout1_selector']}",
        f"- Heldout2 selector: {s['heldout2_selector']}",
        f"- Heldout2 oracle: {s['heldout2_oracle']}",
        f"- Heldout2 expanded candidate oracle: {s['heldout2_expanded_candidate_oracle']}",
        f"- Heldout1 expanded selector: {s['heldout1_expanded_selector']}",
        f"- Heldout2 expanded selector: {s['heldout2_expanded_selector']}",
        f"- Expanded selector distillation best heldout2: {s['expanded_selector_distillation']}",
        f"- Expanded selector distillation heldout1-perfect configs: {s['expanded_selector_distillation_train_perfect']}",
        f"- Exploratory learned selector heldout1: {s['learned_selector_h1']}",
        f"- Exploratory learned selector heldout2: {s['learned_selector_h2']}",
        f"- Exploratory learned selector heldout3: {s['learned_selector_h3']}",
        f"- Heldout3 oracle: {s['heldout3_oracle']}",
        f"- Heldout3 expanded selector: {s['heldout3_expanded_selector']}",
        f"- Heldout3 targeted expanded oracle: {s['heldout3_targeted_expanded_oracle']}",
        f"- Heldout3 targeted newly covered seeds: {', '.join(map(str, s['heldout3_targeted_newly_covered']))}",
        f"- Heldout3 remaining candidate-gap seeds after targeted repair: {', '.join(map(str, s['heldout3_targeted_remaining_gaps'])) or 'none'}",
        f"- Heldout3 candidate-gap seeds: {', '.join(map(str, s['heldout3_candidate_gap_seeds']))}",
        f"- Heldout3 expanded-selector failed seeds: {', '.join(map(str, s['heldout3_expanded_selector_failed_seeds']))}",
        f"- Heldout4 selector: {s['heldout4_selector']}",
        f"- Heldout4 oracle: {s['heldout4_oracle']}",
        f"- Heldout4 selector-miss seeds: {', '.join(map(str, s['heldout4_selector_miss_seeds']))}",
        f"- Heldout4 candidate-gap seeds: {', '.join(map(str, s['heldout4_candidate_gap_seeds']))}",
        f"- Cross-heldout expanded-or-later selector: {s['cross_heldout_selector']}",
        f"- Cross-heldout expanded-or-later oracle: {s['cross_heldout_oracle']}",
        f"- Cross-heldout selector-oracle gap: {s['cross_heldout_selector_oracle_gap']} seeds",
        f"- Heldout2 candidate-gap seeds: {', '.join(map(str, s['candidate_gap_seeds']))}",
        f"- Heldout2 remaining candidate-gap seeds after expansion: {', '.join(map(str, s['expanded_candidate_gap_seeds']))}",
        f"- Heldout2 expanded-selector miss seeds: {', '.join(map(str, s['expanded_selector_miss_seeds']))}",
        f"- Heldout2 selector-miss seeds: {', '.join(map(str, s['selector_miss_seeds']))}",
        "",
        "## Checklist",
        "",
        "| category | id | status | requirement | evidence | limitation/action |",
        "|---|---|---|---|---|---|",
    ]
    for row in report["items"]:
        limitation_action = row["limitation"]
        if row["action"]:
            limitation_action = (limitation_action + " " if limitation_action else "") + "Action: " + row["action"]
        lines.append(
            f"| {row['category']} | {row['id']} | {row['status']} | {row['requirement']} | "
            f"{'<br>'.join(row['evidence'])} | {limitation_action} |"
        )
    lines.extend(["", "## Missing Evidence Paths", ""])
    if report["missing_evidence"]:
        for row in report["missing_evidence"]:
            lines.append(f"- {row['id']}: `{row['path']}`")
    else:
        lines.append("- None")
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(report, root):
    path = root / "materials" / "TRANSPARENT_REPORTING_CHECKLIST.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["category", "id", "requirement", "status", "evidence", "limitation", "action"],
        )
        writer.writeheader()
        for row in report["items"]:
            writer.writerow({**row, "evidence": "; ".join(row["evidence"])})
    return path


def main():
    parser = argparse.ArgumentParser(description="Export transparent reporting checklist.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_checklist(root)
    out_json = root / "materials" / "TRANSPARENT_REPORTING_CHECKLIST.json"
    out_md = root / "materials" / "TRANSPARENT_REPORTING_CHECKLIST.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    out_csv = write_csv(report, root)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
