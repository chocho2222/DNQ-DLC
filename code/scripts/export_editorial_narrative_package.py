#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def as_count(row):
    return f"{row['pass_count']}/{row['n']}"


def build_package(root):
    manifest = load_json(root / "manifest.json")
    summary = load_json(root / "materials" / "PUBLICATION_PACKAGE_SUMMARY.json")
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    significance = load_json(root / "materials" / "SIGNIFICANCE_BRIEFING.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")
    validity = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    sample_size = load_json(root / "materials" / "SAMPLE_SIZE_SENSITIVITY_BRIEF.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    submission = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    current_artifact_provenance = verification["summary"]["artifact_provenance"]

    key = manifest["key_results"]
    main = summary["main_results"]
    claim_by_id = {row["id"]: row for row in claims["claims"]}
    validity_rows = validity["stages"]

    narrative_threads = [
        {
            "id": "strict_full_lap_evidence_standard",
            "editor_facing_message": (
                "The study replaces selected short visual demonstrations with strict full-lap multi-car validation "
                "using lap completion, final rank, first-ahead, grass-rate, and traffic-quality gates."
            ),
            "primary_evidence": [
                "materials/METHODS.md",
                "materials/STATISTICAL_ANALYSIS_PLAN.md",
                "figures/figure_1_multicar_overtake_results.*",
                "tables/seed_outcome_ledger.md",
            ],
            "safe_claim": "strict simulator evaluation and reproducibility package",
            "boundary": "simulation-only evidence; no real-road, perception, or safety-certification claim",
        },
        {
            "id": "strong_baseline_preservation",
            "editor_facing_message": (
                "The strongest locked single-controller comparator is preserved rather than replaced: "
                f"rule overtake baseline {main['locked_rule_overtake']} versus graph-adaptive shield "
                f"{main['locked_graph_adaptive']}."
            ),
            "primary_evidence": claim_by_id["C1_locked_baseline_strength"]["primary_evidence"],
            "safe_claim": "conservative baseline comparison",
            "boundary": claim_by_id["C1_locked_baseline_strength"]["do_not_claim"],
        },
        {
            "id": "portfolio_complementarity",
            "editor_facing_message": (
                "Controller complementarity motivates online portfolio probing, while oracle portfolios are retained "
                "only as diagnostic upper bounds."
            ),
            "primary_evidence": claim_by_id["C2_oracle_complementarity"]["primary_evidence"],
            "safe_claim": "oracle complementarity identifies candidate coverage headroom",
            "boundary": claim_by_id["C2_oracle_complementarity"]["do_not_claim"],
        },
        {
            "id": "online_selector_progress",
            "editor_facing_message": (
                f"The expanded online selector reaches {main['heldout1_expanded_selector']} on heldout1 and "
                f"{main['heldout2_expanded_selector']} on heldout2, below the heldout2 expanded oracle "
                f"of {main['heldout2_expanded_candidate_oracle']}."
            ),
            "primary_evidence": claim_by_id["C10_expanded_selector_progress"]["primary_evidence"],
            "safe_claim": "bounded in-simulator online selector progress with residual selector misses",
            "boundary": claim_by_id["C10_expanded_selector_progress"]["do_not_claim"],
        },
        {
            "id": "external_validation_boundary",
            "editor_facing_message": (
                f"Heldout3 is negative external validation ({main['heldout3_expanded_selector']} selector versus "
                f"{main['heldout3_candidate_oracle']} oracle); heldout4 after targeted repair shows partial transfer "
                f"({main['heldout4_selector']} selector versus {main['heldout4_oracle']} oracle)."
            ),
            "primary_evidence": [
                "tables/heldout3_external_validation.md",
                "tables/heldout4_external_validation.md",
                "tables/cross_heldout_validation_synthesis.md",
                "figures/figure_3_cross_heldout_validation.*",
            ],
            "safe_claim": "external-validation boundary and partial post-repair transfer",
            "boundary": "do not report heldout3-targeted repair or heldout4 partial transfer as broad robustness",
        },
        {
            "id": "negative_results_as_design_signal",
            "editor_facing_message": (
                "Negative controls, calibration failures, selector misses, and candidate gaps are preserved as design "
                "signals rather than hidden during reporting."
            ),
            "primary_evidence": [
                "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
                "tables/heldout2_failure_atlas.md",
                "tables/heldout4_failure_atlas.md",
                "materials/SUBMISSION_GAP_ACTION_PLAN.md",
            ],
            "safe_claim": "transparent failure-mode accounting",
            "boundary": "negative evidence should constrain novelty claims, not be reframed as solved generalization",
        },
    ]

    validity_rows_by_stage = {row["id"]: row for row in validity_rows}
    evidence_ladder = [
        {
            "level": "locked baseline comparison",
            "result": f"rule overtake {main['locked_rule_overtake']}; graph-adaptive {main['locked_graph_adaptive']}",
            "interpretation": "establishes a hard comparator for innovations",
            "claim_strength": "moderate",
        },
        {
            "level": "heldout1 online simulator-loop selector",
            "result": main["heldout1_expanded_selector"],
            "interpretation": validity_rows_by_stage["heldout1_expanded"]["allowed_interpretation"],
            "claim_strength": "positive but seed-bounded",
        },
        {
            "level": "heldout2 online simulator-loop selector",
            "result": main["heldout2_expanded_selector"],
            "interpretation": validity_rows_by_stage["heldout2_expanded"]["allowed_interpretation"],
            "claim_strength": "progress with limitation",
        },
        {
            "level": "heldout3 external validation",
            "result": main["heldout3_expanded_selector"],
            "interpretation": validity_rows_by_stage["heldout3_external"]["allowed_interpretation"],
            "claim_strength": "negative external validation",
        },
        {
            "level": "heldout4 post-repair validation",
            "result": main["heldout4_selector"],
            "interpretation": validity_rows_by_stage["heldout4_post_repair"]["allowed_interpretation"],
            "claim_strength": "partial transfer",
        },
    ]

    reviewer_risks = [
        {
            "risk": "Baseline stronger than graph-only innovation",
            "answer": "State this explicitly and frame graph/DAgger components as complementary candidates.",
            "evidence": "tables/full_statistical_report.md; materials/BASELINE_FAIRNESS_AUDIT.md",
        },
        {
            "risk": "Oracle portfolios mistaken for deployment-ready policies",
            "answer": "Use oracle only as diagnostic upper bound; report the online simulator-loop selector separately.",
            "evidence": "materials/CLAIM_EVIDENCE_MATRIX.md; materials/SELECTOR_DECISION_AUDIT.md",
        },
        {
            "risk": "Heldout3-targeted repair interpreted as external validation",
            "answer": "Label targeted repair as diagnostic and use heldout4 as the post-repair external check.",
            "evidence": "materials/SEED_PARTITION_AUDIT.md; materials/STUDY_PROTOCOL_AND_DEVIATIONS.md",
        },
        {
            "risk": "Small n overinterpreted",
            "answer": "Keep statistical claims descriptive and cite Wilson intervals and larger-N planning thresholds.",
            "evidence": "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md; tables/cross_heldout_statistical_supplement.md",
        },
        {
            "risk": "Reproducibility without public DOI",
            "answer": "Report complete local provenance and mark external archive DOI/accession as pending author action.",
            "evidence": "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/SUBMISSION_METADATA_DRAFT.md",
        },
    ]

    author_actions = [
        {
            "item": "Select target journal and formatting rules",
            "why": "The package is journal-agnostic and does not generate a final submission PDF.",
            "status": "author_required",
        },
        {
            "item": "Complete ORCID, affiliation, funding, conflicts, and corresponding-author metadata",
            "why": f"{submission['summary']['author_required_count']} submission metadata fields are intentionally not fabricated.",
            "status": "author_required",
        },
        {
            "item": "Deposit archive and add DOI/accession",
            "why": "Local release manifest and Zenodo-style metadata are ready, but external DOI is pending.",
            "status": "author_required",
        },
        {
            "item": "Expand domain-specific related work",
            "why": "Starter bibliography exists; domain-positioning references still need author curation.",
            "status": "author_required",
        },
    ]

    sample_size_snapshot = dict(sample_size["summary"])
    sample_size_snapshot["artifact_provenance"] = current_artifact_provenance

    return {
        "root": str(root),
        "title": "Editorial narrative package",
        "purpose": (
            "Consolidate a claim-safe publication narrative for the current evidence package: innovation framing, "
            "evidence ladder, reviewer risks, and author-required submission actions."
        ),
        "recommended_title": significance["recommended_title"],
        "one_sentence_pitch": significance["cover_letter_material"]["one_sentence_pitch"],
        "narrative_threads": narrative_threads,
        "evidence_ladder": evidence_ladder,
        "reviewer_risks": reviewer_risks,
        "author_actions": author_actions,
        "negative_result_count": len(negative["items"]),
        "sample_size_snapshot": sample_size_snapshot,
        "verification_snapshot": verification["summary"],
        "publication_positioning": {
            "best_supported_contribution": (
                "A strict, reproducible, simulator-only full-lap multi-car overtaking evaluation package with "
                "preserved strong baselines, portfolio-selector diagnostics, transparent negative results, and "
                "bounded held-out validation."
            ),
            "not_yet_supported": [
                "broad robustness",
                "real-world deployment readiness",
                "perception or VLM autonomy",
                "oracle-as-controller performance",
                "safety certification",
            ],
            "current_best_numeric_summary": {
                "locked_overtake_baseline": key["locked_single_methods"]["overtake_base_only"],
                "locked_graph_adaptive": key["locked_single_methods"]["graph_adaptive_shield"],
                "heldout1_expanded_selector": {
                    "pass_count": key["expanded_online_selector"]["heldout1_pass_count"],
                    "n": key["expanded_online_selector"]["heldout1_n"],
                },
                "heldout2_expanded_selector": {
                    "pass_count": key["expanded_online_selector"]["heldout2_pass_count"],
                    "n": key["expanded_online_selector"]["heldout2_n"],
                },
                "heldout3_expanded_selector": {
                    "pass_count": key["heldout3_external_validation"]["expanded_selector_pass_count"],
                    "n": key["heldout3_external_validation"]["expanded_selector_n"],
                },
                "heldout4_selector": {
                    "pass_count": key["heldout4_external_after_targeted_repair"]["selector_pass_count"],
                    "n": key["heldout4_external_after_targeted_repair"]["selector_n"],
                },
            },
        },
        "interpretation": (
            "Use this file as a writing scaffold for the manuscript, cover letter, and internal submission review. "
            "It summarizes saved evidence only and deliberately preserves limitations."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["section", "id", "message", "evidence", "boundary_or_action", "status"],
        )
        writer.writeheader()
        for row in report["narrative_threads"]:
            writer.writerow(
                {
                    "section": "narrative_thread",
                    "id": row["id"],
                    "message": row["editor_facing_message"],
                    "evidence": "; ".join(row["primary_evidence"]),
                    "boundary_or_action": row["boundary"],
                    "status": row["safe_claim"],
                }
            )
        for row in report["evidence_ladder"]:
            writer.writerow(
                {
                    "section": "evidence_ladder",
                    "id": row["level"],
                    "message": row["result"],
                    "evidence": row["interpretation"],
                    "boundary_or_action": row["claim_strength"],
                    "status": "",
                }
            )
        for row in report["reviewer_risks"]:
            writer.writerow(
                {
                    "section": "reviewer_risk",
                    "id": row["risk"],
                    "message": row["answer"],
                    "evidence": row["evidence"],
                    "boundary_or_action": "",
                    "status": "",
                }
            )
        for row in report["author_actions"]:
            writer.writerow(
                {
                    "section": "author_action",
                    "id": row["item"],
                    "message": row["why"],
                    "evidence": "",
                    "boundary_or_action": row["status"],
                    "status": row["status"],
                }
            )


def write_markdown(report, path):
    lines = [
        "# Editorial Narrative Package",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Positioning",
        "",
        f"- Recommended title: {report['recommended_title']}",
        f"- One-sentence pitch: {report['one_sentence_pitch']}",
        f"- Best-supported contribution: {report['publication_positioning']['best_supported_contribution']}",
        "",
        "Not yet supported:",
        "",
    ]
    lines.extend(f"- {item}" for item in report["publication_positioning"]["not_yet_supported"])
    lines.extend(
        [
            "",
            "## Narrative Threads",
            "",
            "| id | editor-facing message | safe claim | evidence | boundary |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["narrative_threads"]:
        evidence = "; ".join(f"`{item}`" for item in row["primary_evidence"])
        lines.append(
            f"| {row['id']} | {row['editor_facing_message']} | {row['safe_claim']} | {evidence} | {row['boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Evidence Ladder",
            "",
            "| level | result | interpretation | claim strength |",
            "|---|---|---|---|",
        ]
    )
    for row in report["evidence_ladder"]:
        lines.append(f"| {row['level']} | {row['result']} | {row['interpretation']} | {row['claim_strength']} |")
    lines.extend(
        [
            "",
            "## Reviewer Risks",
            "",
            "| risk | answer | evidence |",
            "|---|---|---|",
        ]
    )
    for row in report["reviewer_risks"]:
        lines.append(f"| {row['risk']} | {row['answer']} | `{row['evidence']}` |")
    lines.extend(
        [
            "",
            "## Author Actions",
            "",
            "| item | why | status |",
            "|---|---|---|",
        ]
    )
    for row in report["author_actions"]:
        lines.append(f"| {row['item']} | {row['why']} | {row['status']} |")
    lines.extend(
        [
            "",
            "## Verification Snapshot",
            "",
            f"- Publication verification: `{report['verification_snapshot']['status']}`",
            f"- Artifact provenance: {report['verification_snapshot']['artifact_provenance']}",
            f"- Negative-result rows retained: {report['negative_result_count']}",
            f"- Sample-size stage count: {report['sample_size_snapshot']['stage_count']}",
            f"- Expanded-or-later selector summary: {report['sample_size_snapshot']['expanded_or_later_selector']}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export claim-safe editorial narrative package.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_package(root)
    out_json = materials / "EDITORIAL_NARRATIVE_PACKAGE.json"
    out_md = materials / "EDITORIAL_NARRATIVE_PACKAGE.md"
    out_csv = materials / "EDITORIAL_NARRATIVE_PACKAGE.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
