#!/usr/bin/env python
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_manifest(root):
    full = load_json(root / "tables" / "full_statistical_report.json")
    heldout = load_json(root / "tables" / "heldout_generalization.json")
    calibration = load_json(root / "tables" / "selector_calibration.json")
    selector_distillation = load_json(root / "tables" / "selector_distillation_report.json")
    candidate_expansion = load_json(root / "tables" / "heldout2_candidate_expansion.json")
    expanded_selector = load_json(root / "tables" / "expanded_selector_generalization.json")
    expanded_distillation = load_json(root / "tables" / "expanded_selector_distillation_report.json")
    learned_selector = load_json(root / "tables" / "learned_selector_report.json")
    heldout3 = load_json(root / "tables" / "heldout3_external_validation.json")
    heldout3_expansion = load_json(root / "tables" / "heldout3_candidate_expansion.json")
    heldout4 = load_json(root / "tables" / "heldout4_external_validation.json")
    cross_heldout = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    audit = load_json(root / "tables" / "reproducibility_audit.json")
    figure_2 = load_json(root / "figures" / "figure_2_manifest.json")
    figure_3 = load_json(root / "figures" / "figure_3_manifest.json")
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    claim_qa = load_json(root / "materials" / "MANUSCRIPT_CLAIM_QA.json")

    method_summary = {item["method"]: item for item in full["method_summaries"]}
    h1 = heldout["sets"]["heldout1"]["selector"]
    h2 = heldout["sets"]["heldout2"]["selector"]
    cal_h2 = calibration["test_heldout2"]

    return {
        "title": "Permutation-invariant safe multi-car full-lap overtaking",
        "root": str(root),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_model_dir": "outputs/torch_dlc_full_lap_seed01/seed_1/models",
        "device": "cuda:0,cuda:1,cuda:2,cuda:3",
        "scope": {
            "task": "strict non-VLM multi-car full-lap overtaking",
            "excluded": "VLM components intentionally excluded",
            "validator": "target lap completion, target rank 1, first-ahead event, target grass threshold, and global traffic quality",
        },
        "seed_sets": {
            "locked": [3, 7, 11, 17, 23, 29, 31, 37, 41, 43],
            "heldout1": heldout["sets"]["heldout1"]["seeds"],
            "heldout2": heldout["sets"]["heldout2"]["seeds"],
            "heldout3": heldout3["seeds"],
            "heldout4": heldout4["seeds"],
            "hard_smoke": [61, 71, 73, 89],
        },
        "components": {
            "baselines": [
                "telemetry_cruise",
                "telemetry_yield",
                "telemetry_lane",
                "telemetry_overtake",
                "expert_gate",
            ],
            "innovation": [
                "permutation-invariant graph/set actor behavior cloning",
                "adaptive telemetry gate",
                "graph-adaptive shield",
                "DAgger-style hard-state recovery v1/v2",
                "online portfolio probe selector",
                "cross-held-out generalization diagnostics",
            ],
            "negative_controls": [
                "expert_fast_only",
                "expert_barrier_only",
                "expert_recovery_only",
                "first DAgger recovery strict hard-smoke result",
            ],
        },
        "key_results": {
            "locked_single_methods": {
                "overtake_base_only": {
                    "pass_count": method_summary["main:overtake_base_only"]["pass_count"],
                    "n": method_summary["main:overtake_base_only"]["n"],
                },
                "graph_adaptive_shield": {
                    "pass_count": method_summary["adaptive:graph_adaptive_shield"]["pass_count"],
                    "n": method_summary["adaptive:graph_adaptive_shield"]["n"],
                },
                "graph_soft_shield": {
                    "pass_count": method_summary["main:graph_soft_shield"]["pass_count"],
                    "n": method_summary["main:graph_soft_shield"]["n"],
                },
            },
            "heldout1_five_candidate_selector": {
                "pass_count": h1["pass_count"],
                "n": h1["n"],
                "oracle_pass_count": h1["oracle_pass_count"],
                "oracle_n": h1["n"],
            },
            "heldout2_five_candidate_selector": {
                "pass_count": h2["pass_count"],
                "n": h2["n"],
                "oracle_pass_count": h2["oracle_pass_count"],
                "oracle_n": h2["n"],
            },
            "selector_calibration_heldout2": {
                "pass_count": cal_h2["pass_count"],
                "n": cal_h2["n"],
                "oracle_pass_count": cal_h2["oracle_pass_count"],
                "candidate_gap_count": cal_h2["candidate_gap_count"],
                "selector_miss_count": cal_h2["selector_miss_count"],
            },
            "selector_distillation_heldout2": {
                "train_set": selector_distillation["train_set"],
                "test_set": selector_distillation["test_set"],
                "heldout1_perfect_configs": selector_distillation["grid"]["heldout1_perfect_configs"],
                "best_heldout2_pass_count": selector_distillation["best_train_perfect"]["heldout2_pass_count"],
                "n": h2["n"],
            },
            "heldout2_candidate_expansion": {
                "original_oracle_pass_count": candidate_expansion["original_oracle"]["pass_count"],
                "expanded_oracle_pass_count": candidate_expansion["expanded_oracle"]["pass_count"],
                "n": candidate_expansion["expanded_oracle"]["n"],
                "newly_covered_seeds": candidate_expansion["expanded_oracle"]["newly_covered_seeds"],
                "remaining_candidate_gap_seeds": candidate_expansion["expanded_oracle"]["remaining_candidate_gap_seeds"],
            },
            "expanded_online_selector": {
                "heldout1_pass_count": expanded_selector["summaries"]["heldout1_expanded"]["pass_count"],
                "heldout1_n": expanded_selector["summaries"]["heldout1_expanded"]["n"],
                "heldout2_pass_count": expanded_selector["summaries"]["heldout2_expanded"]["pass_count"],
                "heldout2_n": expanded_selector["summaries"]["heldout2_expanded"]["n"],
                "heldout2_oracle_pass_count": expanded_selector["summaries"]["heldout2_expanded"]["oracle_pass_count"],
                "heldout2_selector_miss_seeds": expanded_selector["summaries"]["heldout2_expanded"]["selector_miss_seeds"],
            },
            "expanded_selector_distillation": {
                "heldout1_perfect_configs": expanded_distillation["grid"]["heldout1_perfect_configs"],
                "best_heldout2_pass_count": expanded_distillation["best_train_perfect"]["heldout2_pass_count"],
                "n": expanded_selector["summaries"]["heldout2_expanded"]["n"],
            },
            "learned_selector_exploratory": {
                "primary_variant": learned_selector["primary_variant"],
                "heldout1_pass_count": learned_selector["variants"][learned_selector["primary_variant"]]["train"]["pass_count"],
                "heldout1_n": learned_selector["variants"][learned_selector["primary_variant"]]["train"]["n"],
                "heldout2_pass_count": learned_selector["variants"][learned_selector["primary_variant"]]["test"]["pass_count"],
                "heldout2_n": learned_selector["variants"][learned_selector["primary_variant"]]["test"]["n"],
                "heldout3_pass_count": learned_selector["variants"][learned_selector["primary_variant"]]["external_heldout3"]["pass_count"],
                "heldout3_n": learned_selector["variants"][learned_selector["primary_variant"]]["external_heldout3"]["n"],
                "accepted_replacement": False,
            },
            "heldout3_external_validation": {
                "candidate_oracle_pass_count": heldout3["oracle"]["pass_count"],
                "candidate_oracle_n": heldout3["oracle"]["n"],
                "candidate_gap_seeds": heldout3["oracle"]["candidate_gap_seeds"],
                "expanded_selector_pass_count": heldout3["expanded_selector"]["pass_count"],
                "expanded_selector_n": heldout3["expanded_selector"]["n"],
                "expanded_selector_failed_seeds": heldout3["expanded_selector"]["failed_seeds"],
                "learned_selector_variant": heldout3["learned_selector_primary"]["variant"],
                "learned_selector_pass_count": heldout3["learned_selector_primary"]["pass_count"],
                "learned_selector_n": heldout3["learned_selector_primary"]["n"],
            },
            "heldout3_targeted_candidate_expansion": {
                "original_oracle_pass_count": heldout3_expansion["original_oracle"]["pass_count"],
                "expanded_oracle_pass_count": heldout3_expansion["expanded_oracle"]["pass_count"],
                "n": heldout3_expansion["expanded_oracle"]["n"],
                "newly_covered_seeds": heldout3_expansion["expanded_oracle"]["newly_covered_seeds"],
                "remaining_candidate_gap_seeds": heldout3_expansion["expanded_oracle"]["remaining_candidate_gap_seeds"],
                "reporting_boundary": "targeted repair diagnostic, not external validation or online selector performance",
            },
            "heldout4_external_after_targeted_repair": {
                "selector_pass_count": heldout4["selector"]["pass_count"],
                "selector_n": heldout4["selector"]["n"],
                "oracle_pass_count": heldout4["oracle"]["pass_count"],
                "oracle_n": heldout4["oracle"]["n"],
                "selector_miss_seeds": heldout4["selector"]["selector_miss_seeds"],
                "candidate_gap_seeds": heldout4["oracle"]["candidate_gap_seeds"],
                "reporting_boundary": "post-repair external validation with partial transfer, not robustness",
            },
            "cross_heldout_synthesis": cross_heldout["aggregate_expanded_or_later"],
        },
        "reporting_boundary": {
            "main_positive": (
                "The package demonstrates reproducible strict full-lap multi-car overtaking experiments and "
                "a promising online portfolio selector on heldout1, with an expanded-candidate improvement on heldout2."
            ),
            "main_limitation": (
                "The original second held-out selector is 5/10. Candidate expansion raises the oracle to 10/10 "
                "and the online expanded selector to 7/10, leaving selector misses on seeds 103, 109, and 113. "
                "A third disjoint heldout3 batch is negative external validation: oracle 8/10, expanded selector 4/10, "
                "and primary learned selector 4/10. Heldout4 after targeted repair shows partial transfer at 6/10 "
                "against an 8/10 oracle. This must not be reported as broad robustness evidence."
            ),
            "oracle_policy": "Oracle portfolios are diagnostic upper bounds, not online selector outputs.",
        },
        "primary_materials": {
            "publication_package_summary": "materials/PUBLICATION_PACKAGE_SUMMARY.md",
            "top_journal_readiness_checklist": "materials/TOP_JOURNAL_READINESS_CHECKLIST.md",
            "statistical_analysis_plan": "materials/STATISTICAL_ANALYSIS_PLAN.md",
            "data_code_availability": "materials/DATA_CODE_AVAILABILITY.md",
            "data_code_availability_rows": "materials/DATA_CODE_AVAILABILITY.csv",
            "data_dictionary": "materials/DATA_DICTIONARY.md",
            "experiment_registry": "materials/EXPERIMENT_REGISTRY.md",
            "transparent_reporting_checklist": "materials/TRANSPARENT_REPORTING_CHECKLIST.md",
            "submission_gap_action_plan": "materials/SUBMISSION_GAP_ACTION_PLAN.md",
            "compute_cost_report": "tables/compute_cost_report.md",
            "selector_distillation_report": "tables/selector_distillation_report.md",
            "release_archive_manifest": "materials/RELEASE_ARCHIVE_MANIFEST.md",
            "final_checksum_freeze_record": "materials/FINAL_CHECKSUM_FREEZE_RECORD.md",
            "fair_archive_metadata": "materials/FAIR_ARCHIVE_METADATA.md",
            "archive_readme": "materials/ARCHIVE_README.md",
            "citation_metadata": "materials/CITATION_METADATA.md",
            "research_risk_and_safety": "materials/RESEARCH_RISK_AND_SAFETY.md",
            "top_journal_reporting_summary": "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
            "editorial_submission_checklist": "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
            "significance_briefing": "materials/SIGNIFICANCE_BRIEFING.md",
            "editorial_narrative_package": "materials/EDITORIAL_NARRATIVE_PACKAGE.md",
            "cover_letter_draft_package": "materials/COVER_LETTER_DRAFT_PACKAGE.md",
            "submission_portal_package_map": "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
            "editorial_decision_brief": "materials/EDITORIAL_DECISION_BRIEF.md",
            "editorial_triage_and_reviewer_checklist": "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md",
            "reviewer_risk_response_dossier": "materials/REVIEWER_RISK_RESPONSE_DOSSIER.md",
            "novelty_positioning_matrix": "materials/NOVELTY_POSITIONING_MATRIX.md",
            "related_work_positioning_matrix": "materials/RELATED_WORK_POSITIONING_MATRIX.md",
            "remaining_author_blockers_matrix": "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.md",
            "confirmatory_experiment_preregistration": "materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.md",
            "target_journal_compliance_matrix": "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md",
            "author_action_freeze_plan": "materials/AUTHOR_ACTION_FREEZE_PLAN.md",
            "final_submission_file_bundle": "materials/FINAL_SUBMISSION_FILE_BUNDLE.md",
            "supplementary_materials_index": "materials/SUPPLEMENTARY_MATERIALS_INDEX.md",
            "title_abstract_highlights_package": "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
            "submission_readiness_dashboard": "materials/SUBMISSION_READINESS_DASHBOARD.md",
            "artifact_dependency_map": "materials/ARTIFACT_DEPENDENCY_MAP.md",
            "environment_reproducibility_audit": "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
            "manuscript_draft_package": "manuscript/main.md",
            "manuscript_source_package": "manuscript/main.tex",
            "manuscript_source_package_audit": "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.md",
            "manuscript_compile_preflight": "materials/MANUSCRIPT_COMPILE_PREFLIGHT.md",
            "methods": "materials/METHODS.md",
            "results_status": "materials/RESULTS_STATUS.md",
            "limitations": "materials/LIMITATIONS.md",
            "supplementary_index": "materials/SUPPLEMENTARY_INDEX.md",
            "claim_evidence_matrix": "materials/CLAIM_EVIDENCE_MATRIX.md",
            "manuscript_claim_qa": "materials/MANUSCRIPT_CLAIM_QA.md",
            "publication_package_verification": "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "manuscript_outline": "materials/MANUSCRIPT_OUTLINE.md",
            "reviewer_response_map": "materials/REVIEWER_RESPONSE_MAP.md",
            "manuscript_draft": "materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md",
            "artifact_provenance": "tables/artifact_provenance.md",
            "reproducibility_audit": "tables/reproducibility_audit.md",
            "heldout2_failure_atlas": "tables/heldout2_failure_atlas.md",
            "heldout2_candidate_expansion": "tables/heldout2_candidate_expansion.md",
            "expanded_selector_generalization": "tables/expanded_selector_generalization.md",
            "expanded_selector_distillation": "tables/expanded_selector_distillation_report.md",
            "learned_selector_report": "tables/learned_selector_report.md",
            "heldout3_external_validation": "tables/heldout3_external_validation.md",
            "heldout3_candidate_expansion": "tables/heldout3_candidate_expansion.md",
            "heldout4_external_validation": "tables/heldout4_external_validation.md",
            "heldout4_failure_atlas": "tables/heldout4_failure_atlas.md",
            "cross_heldout_validation_synthesis": "tables/cross_heldout_validation_synthesis.md",
            "seed_outcome_ledger": "tables/seed_outcome_ledger.md",
        },
        "figures": {
            "figure_1": "figures/figure_1_multicar_overtake_results.*",
            "figure_2": "figures/figure_2_portfolio_selector_summary.*",
            "figure_2_claim": figure_2["claim"],
            "figure_3": "figures/figure_3_cross_heldout_validation.*",
            "figure_3_claim": figure_3["claim"],
        },
        "artifact_status": {
            "artifact_provenance_complete": provenance["complete_count"],
            "artifact_provenance_total": len(provenance["artifacts"]),
            "reproducibility_missing_or_weak": len(audit["missing_or_weak_items"]),
            "claim_count": len(claims["claims"]),
            "manuscript_claim_qa_status": claim_qa["summary"]["status"],
            "manuscript_claim_qa_blockers": claim_qa["summary"]["blockers"],
            "manuscript_claim_qa_warnings": claim_qa["summary"]["warnings"],
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Export package-level manifest from current reports.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--out", default="manifest.json")
    args = parser.parse_args()
    root = Path(args.root)
    out = root / args.out
    out.write_text(json.dumps(build_manifest(root), indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(out)}, indent=2))


if __name__ == "__main__":
    main()
