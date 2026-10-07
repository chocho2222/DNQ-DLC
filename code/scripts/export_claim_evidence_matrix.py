#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def method_pass(report, method):
    for item in report["method_summaries"]:
        if item["method"] == method:
            return f"{item['pass_count']}/{item['n']}"
    raise KeyError(method)


def build_claims(root):
    full = load_json(root / "tables" / "full_statistical_report.json")
    heldout_gen = load_json(root / "tables" / "heldout_generalization.json")
    calibration = load_json(root / "tables" / "selector_calibration.json")
    v2_portfolio = load_json(root / "tables" / "heldout_v2_portfolio.json")
    expanded_selector = load_json(root / "tables" / "expanded_selector_generalization.json")
    expanded_distillation = load_json(root / "tables" / "expanded_selector_distillation_report.json")
    learned_selector = load_json(root / "tables" / "learned_selector_report.json")
    heldout3 = load_json(root / "tables" / "heldout3_external_validation.json")
    heldout3_expansion = load_json(root / "tables" / "heldout3_candidate_expansion.json")
    heldout3_targeted_selector = load_json(root / "tables" / "heldout3_targeted_selector_generalization.json")
    heldout3_meta_selector = load_json(root / "tables" / "heldout3_targeted_meta_selector.json")
    heldout4 = load_json(root / "tables" / "heldout4_external_validation.json")
    cross_heldout = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")
    audit = load_json(root / "tables" / "reproducibility_audit.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")

    h1 = heldout_gen["sets"]["heldout1"]["selector"]
    h2 = heldout_gen["sets"]["heldout2"]["selector"]
    cal_h2 = calibration["test_heldout2"]

    claims = [
        {
            "id": "C1_locked_baseline_strength",
            "claim": (
                "Under the locked strict 10-seed protocol, the strongest single method is the "
                f"rule-based overtake baseline ({method_pass(full, 'main:overtake_base_only')}), "
                f"while graph-adaptive shield reaches {method_pass(full, 'adaptive:graph_adaptive_shield')}."
            ),
            "claim_type": "main_result",
            "allowed_wording": "single-method locked-seed comparison",
            "do_not_claim": "Do not claim the learned graph method surpasses the strongest rule baseline.",
            "primary_evidence": [
                "tables/full_statistical_report.md",
                "tables/full_statistical_report.json",
                "figures/figure_2_portfolio_selector_summary.*",
            ],
            "limitations": [
                "materials/LIMITATIONS.md",
                "materials/RESULTS_STATUS.md",
            ],
        },
        {
            "id": "C2_oracle_complementarity",
            "claim": (
                "Full-suite methods are complementary: oracle portfolios improve coverage, but oracle "
                "results are upper bounds because they use full-rollout outcomes."
            ),
            "claim_type": "oracle_upper_bound",
            "allowed_wording": "oracle complementarity / upper bound",
            "do_not_claim": "Do not present oracle portfolios as online selector outputs.",
            "primary_evidence": [
                "tables/portfolio_oracle.md",
                "tables/heldout_v2_portfolio.md",
                "figures/figure_2_source_data.csv",
            ],
            "limitations": ["materials/LIMITATIONS.md", "materials/METHODS.md"],
        },
        {
            "id": "C3_dagger_v2_complementary_not_standalone",
            "claim": (
                "DAgger-v2 hard-state recovery is complementary rather than standalone superior: "
                "it improves hard-smoke behavior and portfolio coverage, but its complete held-out "
                "single-candidate result is limited."
            ),
            "claim_type": "innovation_with_limitation",
            "allowed_wording": "complementary recovery candidate",
            "do_not_claim": "Do not call DAgger-v2 a standalone breakthrough or robust controller.",
            "primary_evidence": [
                "tables/heldout_graph_dagger_recovery_v2_smoke_report.md",
                "tables/heldout_graph_dagger_recovery_v2_suite_report.md",
                "tables/heldout_v2_portfolio.md",
                "models/graph_dagger_recovery_v2/train_summary.json",
            ],
            "limitations": ["materials/LIMITATIONS.md", "tables/dagger_v2_heldout_failure_diagnosis.md"],
        },
        {
            "id": "C4_first_heldout_selector_positive",
            "claim": (
                f"The five-candidate 1200-step online selector reaches {h1['pass_count']}/{h1['n']} "
                "on the first disjoint held-out set and matches the expanded oracle."
            ),
            "claim_type": "online_simulator_loop_selector_positive",
            "allowed_wording": "online simulator-loop selector on heldout1",
            "do_not_claim": "Do not generalize this 10/10 result beyond the heldout2 5/10 stress result and later external failures.",
            "primary_evidence": [
                "tables/portfolio_probe_selector_1200_heldout_dagger_v2.md",
                "tables/heldout_generalization.md",
                "figures/figure_2_portfolio_selector_summary.*",
            ],
            "limitations": ["materials/LIMITATIONS.md", "tables/selector_calibration.md"],
        },
        {
            "id": "C5_second_heldout_generalization_boundary",
            "claim": (
                f"On the second disjoint held-out set, the same selector reaches {h2['pass_count']}/{h2['n']} "
                f"against a {h2['oracle_pass_count']}/{h2['n']} candidate oracle, exposing a generalization boundary."
            ),
            "claim_type": "negative_generalization_result",
            "allowed_wording": "generalization boundary / stress repeat",
            "do_not_claim": "Do not claim broad robustness evidence.",
            "primary_evidence": [
                "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.md",
                "tables/heldout_generalization.md",
                "figures/figure_2_source_data.csv",
            ],
            "limitations": ["materials/LIMITATIONS.md", "materials/RESULTS_STATUS.md"],
        },
        {
            "id": "C6_selector_calibration_negative",
            "claim": (
                "Offline score calibration does not close the heldout2 gap: calibrated heldout2 remains "
                f"{cal_h2['pass_count']}/{cal_h2['n']}, with {cal_h2['candidate_gap_count']} candidate gaps "
                f"and {cal_h2['selector_miss_count']} selector misses."
            ),
            "claim_type": "diagnostic_negative_result",
            "allowed_wording": "score-only calibration is insufficient",
            "do_not_claim": "Do not imply that retuning the current linear score solves heldout2.",
            "primary_evidence": [
                "tables/selector_calibration.md",
                "tables/selector_calibration.json",
                "figures/figure_2_source_data.csv",
            ],
            "limitations": ["materials/LIMITATIONS.md", "materials/METHODS.md"],
        },
        {
            "id": "C7_negative_controls",
            "claim": (
                "Faster, barrier, and conservative recovery expert variants fail on the hard held-out "
                "smoke seeds, arguing against simple speed/offset hand tuning as the main path forward."
            ),
            "claim_type": "negative_control",
            "allowed_wording": "negative controls against simple hand tuning",
            "do_not_claim": "Do not use these failed experts as successful baselines.",
            "primary_evidence": [
                "tables/heldout_expert_fast_smoke_report.md",
                "tables/heldout_expert_barrier_smoke_report.md",
                "tables/heldout_expert_recovery_smoke_report.md",
                "figures/figure_2_source_data.csv",
            ],
            "limitations": ["materials/LIMITATIONS.md"],
        },
        {
            "id": "C8_selector_distillation_negative",
            "claim": (
                "Heldout1-trained linear probe-score distillation does not improve heldout2: "
                "all heldout1-perfect grid configurations remain at 5/10 on heldout2."
            ),
            "claim_type": "diagnostic_negative_result",
            "allowed_wording": "simple selector distillation / scalar probe retuning is insufficient",
            "do_not_claim": "Do not claim that the selector miss problem is solved by linear probe-score distillation.",
            "primary_evidence": [
                "tables/selector_distillation_report.md",
                "tables/selector_distillation_report.json",
                "tables/selector_distillation_grid.csv",
                "tables/heldout2_failure_atlas.md",
            ],
            "limitations": ["materials/LIMITATIONS.md", "materials/SUBMISSION_GAP_ACTION_PLAN.md"],
        },
        {
            "id": "C9_candidate_expansion_progress",
            "claim": (
                "DAgger-v2 recovery-conservative and expert-more-graph candidates raise the "
                "heldout2 candidate oracle from 7/10 to 10/10; this is candidate-policy coverage, "
                "not an online selector result."
            ),
            "claim_type": "candidate_policy_progress",
            "allowed_wording": "candidate oracle expansion / policy coverage progress",
            "do_not_claim": "Do not present the expanded oracle as an online selector result or as broad robustness evidence.",
            "primary_evidence": [
                "tables/heldout2_candidate_expansion.md",
                "tables/heldout2_candidate_expansion.json",
                "tables/heldout2_dagger_v2_recovery_conservative_suite_report.md",
                "tables/heldout2_overtake_conservative_traffic_targeted_report.md",
                "tables/heldout2_dagger_v2_expert_more_graph_suite_report.md",
            ],
            "limitations": ["tables/heldout2_candidate_expansion.md", "materials/LIMITATIONS.md"],
        },
        {
            "id": "C10_expanded_selector_progress",
            "claim": (
                "With the expanded six-candidate pool, the 1200-step online simulator-loop selector preserves "
                f"heldout1 at {expanded_selector['summaries']['heldout1_expanded']['pass_count']}/"
                f"{expanded_selector['summaries']['heldout1_expanded']['n']} and improves heldout2 from "
                f"{expanded_selector['summaries']['heldout2_original']['pass_count']}/"
                f"{expanded_selector['summaries']['heldout2_original']['n']} to "
                f"{expanded_selector['summaries']['heldout2_expanded']['pass_count']}/"
                f"{expanded_selector['summaries']['heldout2_expanded']['n']}, while the expanded oracle is "
                f"{expanded_selector['summaries']['heldout2_expanded']['oracle_pass_count']}/"
                f"{expanded_selector['summaries']['heldout2_expanded']['n']}."
            ),
            "claim_type": "online_simulator_loop_selector_progress_with_limitation",
            "allowed_wording": "expanded online selector improves heldout2 but remains below oracle",
            "do_not_claim": "Do not claim the selector problem is solved or that the result is broadly robust.",
            "primary_evidence": [
                "tables/expanded_selector_generalization.md",
                "tables/portfolio_probe_selector_1200_heldout_expanded.md",
                "tables/portfolio_probe_selector_1200_heldout2_expanded.md",
            ],
            "limitations": ["tables/expanded_selector_generalization.md", "materials/LIMITATIONS.md"],
        },
        {
            "id": "C11_expanded_selector_distillation_negative",
            "claim": (
                "Heldout1-only scalar/priority distillation does not improve the expanded selector: "
                f"{expanded_distillation['grid']['heldout1_perfect_configs']} heldout1-perfect configurations "
                f"still peak at {expanded_distillation['best_train_perfect']['heldout2_pass_count']}/"
                f"{expanded_selector['summaries']['heldout2_expanded']['n']} on heldout2."
            ),
            "claim_type": "diagnostic_negative_result",
            "allowed_wording": "simple expanded selector retuning is insufficient",
            "do_not_claim": "Do not claim scalar probe-score retuning solves the residual selector misses.",
            "primary_evidence": [
                "tables/expanded_selector_distillation_report.md",
                "tables/expanded_selector_distillation_report.json",
                "tables/expanded_selector_distillation_grid.csv",
            ],
            "limitations": ["tables/expanded_selector_distillation_report.md", "materials/SUBMISSION_GAP_ACTION_PLAN.md"],
        },
        {
            "id": "C12_learned_selector_exploratory",
            "claim": (
                "A feature-only logistic learned selector is exploratory: it improves heldout2 to "
                f"{learned_selector['variants']['feature_only_logreg']['test']['pass_count']}/"
                f"{learned_selector['variants']['feature_only_logreg']['test']['n']} but reduces heldout1 to "
                f"{learned_selector['variants']['feature_only_logreg']['train']['pass_count']}/"
                f"{learned_selector['variants']['feature_only_logreg']['train']['n']}, so it is not an accepted replacement selector."
            ),
            "claim_type": "exploratory_selector_diagnostic",
            "allowed_wording": "exploratory learned selector reveals a tradeoff",
            "do_not_claim": "Do not present the learned selector as final, robust, or superior overall.",
            "primary_evidence": [
                "tables/learned_selector_report.md",
                "tables/learned_selector_report.json",
                "tables/learned_selector_rows.csv",
            ],
            "limitations": ["tables/learned_selector_report.md", "materials/SUBMISSION_GAP_ACTION_PLAN.md"],
        },
        {
            "id": "C13_reproducible_package",
            "claim": (
                "A third disjoint external validation batch exposes the current generalization boundary: "
                f"the expanded candidate oracle reaches {heldout3['oracle']['pass_count']}/{heldout3['oracle']['n']}, "
                f"but the expanded online selector and primary learned selector each reach only "
                f"{heldout3['expanded_selector']['pass_count']}/{heldout3['expanded_selector']['n']}."
            ),
            "claim_type": "external_validation_negative_result",
            "allowed_wording": "heldout3 negative external validation / generalization boundary",
            "do_not_claim": "Do not claim the heldout2 selector improvement generalizes to heldout3 or is broadly robust.",
            "primary_evidence": [
                "tables/heldout3_external_validation.md",
                "tables/portfolio_probe_selector_1200_heldout3_expanded.md",
                "tables/learned_selector_report.md",
            ],
            "limitations": ["tables/heldout3_external_validation.md", "materials/SUBMISSION_GAP_ACTION_PLAN.md"],
        },
        {
            "id": "C14_reproducible_package",
            "claim": (
                "Heldout3-targeted candidate repair improves candidate-policy coverage but does not solve heldout3: "
                f"the targeted expanded oracle rises from {heldout3_expansion['original_oracle']['pass_count']}/"
                f"{heldout3_expansion['original_oracle']['n']} to {heldout3_expansion['expanded_oracle']['pass_count']}/"
                f"{heldout3_expansion['expanded_oracle']['n']}, with targeted coverage of seeds "
                f"{heldout3_expansion['expanded_oracle']['newly_covered_seeds']}; when the targeted traffic candidate "
                "is added to the 1200-step online selector pool, the locked heldout3 selector remains "
                f"{heldout3_targeted_selector['targeted_selector']['pass_count']}/"
                f"{heldout3_targeted_selector['targeted_selector']['n']} while its oracle rises to "
                f"{heldout3_targeted_selector['targeted_selector']['oracle_pass_count']}/"
                f"{heldout3_targeted_selector['targeted_selector']['n']}. A within-heldout3 LOSO "
                f"meta-selector reaches {heldout3_meta_selector['best_summary']['pass_count']}/"
                f"{heldout3_meta_selector['best_summary']['n']}, indicating limited but insufficient "
                "probe-feature signal."
            ),
            "claim_type": "targeted_candidate_repair_with_limitation",
            "allowed_wording": "targeted candidate-policy coverage progress on heldout3",
            "do_not_claim": "Do not present targeted heldout3 repair as external validation or online selector performance.",
            "primary_evidence": [
                "tables/heldout3_candidate_expansion.md",
                "tables/heldout3_targeted_recovery_suite_report.md",
                "tables/heldout3_targeted_recovery_conservative_traffic_suite_report.md",
                "tables/seed157_traffic_ablation.md",
                "tables/heldout3_traffic_adaptive_conservative_suite_report.md",
                "tables/heldout3_targeted_selector_generalization.md",
                "tables/heldout3_targeted_meta_selector.md",
            ],
            "limitations": [
                "tables/heldout3_candidate_expansion.md",
                "tables/heldout3_targeted_selector_generalization.md",
                "tables/heldout3_targeted_meta_selector.md",
                "materials/SUBMISSION_GAP_ACTION_PLAN.md",
            ],
        },
        {
            "id": "C15_reproducible_package",
            "claim": (
                "A fourth unused external validation batch after heldout3-targeted repair shows partial transfer "
                "but not broad robustness evidence: the targeted seven-candidate online selector reaches "
                f"{heldout4['selector']['pass_count']}/{heldout4['selector']['n']} against an oracle of "
                f"{heldout4['oracle']['pass_count']}/{heldout4['oracle']['n']}, leaving selector misses "
                f"{heldout4['selector']['selector_miss_seeds']} and candidate-gap seeds "
                f"{heldout4['oracle']['candidate_gap_seeds']}."
            ),
            "claim_type": "external_validation_after_targeted_repair",
            "allowed_wording": "heldout4 partial-transfer external validation with remaining gaps",
            "do_not_claim": "Do not claim the targeted repair generalizes robustly or solves the selector/candidate gaps.",
            "primary_evidence": [
                "tables/heldout4_external_validation.md",
                "tables/heldout4_failure_atlas.md",
                "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.md",
                "figures/figure_3_cross_heldout_validation.*",
                "tables/heldout4_adaptive_suite_report.md",
                "tables/heldout4_traffic_adaptive_conservative_suite_report.md",
            ],
            "limitations": ["tables/heldout4_external_validation.md", "materials/SUBMISSION_GAP_ACTION_PLAN.md"],
        },
        {
            "id": "C16_reproducible_package",
            "claim": (
                "Across expanded-or-later held-out evidence, the online selector achieves "
                f"{cross_heldout['aggregate_expanded_or_later']['selector_pass_count']}/"
                f"{cross_heldout['aggregate_expanded_or_later']['n']} strict PASS while the corresponding oracle reaches "
                f"{cross_heldout['aggregate_expanded_or_later']['oracle_pass_count']}/"
                f"{cross_heldout['aggregate_expanded_or_later']['n']}; the resulting "
                f"{cross_heldout['aggregate_expanded_or_later']['selector_oracle_gap']}-seed gap separates "
                "selector errors from remaining candidate-policy gaps."
            ),
            "claim_type": "cross_heldout_synthesis_with_limitation",
            "allowed_wording": "useful but not robust cross-heldout online portfolio",
            "do_not_claim": "Do not average away heldout3/heldout4 failures or present aggregate performance as broad robustness evidence.",
            "primary_evidence": [
                "tables/cross_heldout_validation_synthesis.md",
                "tables/cross_heldout_statistical_supplement.md",
                "tables/seed_outcome_ledger.md",
                "figures/figure_3_cross_heldout_validation.*",
                "figures/figure_3_source_data_dictionary.csv",
                "tables/heldout3_external_validation.md",
                "tables/heldout4_external_validation.md",
            ],
            "limitations": [
                "tables/cross_heldout_validation_synthesis.md",
                "materials/SUBMISSION_GAP_ACTION_PLAN.md",
            ],
        },
        {
            "id": "C17_reproducible_package",
            "claim": (
                f"The package has complete artifact provenance ({provenance['complete_count']}/{len(provenance['artifacts'])}), "
                f"no missing/weak reproducibility-audit items ({len(audit['missing_or_weak_items'])}), "
                "a dedicated environment audit, and an experiment registry."
            ),
            "claim_type": "reproducibility",
            "allowed_wording": "substantially reproducible artifact package",
            "do_not_claim": "Do not claim manuscript submission packaging is complete outside this repository.",
            "primary_evidence": [
                "tables/artifact_provenance.md",
                "tables/reproducibility_audit.md",
                "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
                "materials/EXPERIMENT_REGISTRY.md",
                "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
                "materials/SUPPLEMENTARY_INDEX.md",
            ],
            "limitations": [
                "tables/reproducibility_audit.md",
                "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
                "materials/EXPERIMENT_REGISTRY.md",
                "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            ],
        },
    ]
    return {
        "root": str(root),
        "claims": claims,
        "interpretation": (
            "This matrix is intended to keep manuscript claims aligned with the saved evidence. "
            "It separates online simulator-loop selector results from oracle upper bounds and records the negative "
            "heldout2/calibration and heldout3 external-validation evidence that limits broad robustness claims."
        ),
    }


def write_outputs(report, root, prefix):
    out_json = root / "materials" / f"{prefix}.json"
    out_md = root / "materials" / f"{prefix}.md"
    out_csv = root / "materials" / f"{prefix}.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "id",
            "claim_type",
            "claim",
            "allowed_wording",
            "do_not_claim",
            "primary_evidence",
            "limitations",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for claim in report["claims"]:
            writer.writerow(
                {
                    **{key: claim[key] for key in fieldnames if key not in {"primary_evidence", "limitations"}},
                    "primary_evidence": "; ".join(claim["primary_evidence"]),
                    "limitations": "; ".join(claim["limitations"]),
                }
            )
    lines = [
        "# Claim Evidence Matrix",
        "",
        report["interpretation"],
        "",
        "| id | type | allowed claim | do not claim | primary evidence | limitations |",
        "|---|---|---|---|---|---|",
    ]
    for claim in report["claims"]:
        lines.append(
            f"| {claim['id']} | {claim['claim_type']} | {claim['claim']} | "
            f"{claim['do_not_claim']} | {'<br>'.join(claim['primary_evidence'])} | "
            f"{'<br>'.join(claim['limitations'])} |"
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}


def main():
    parser = argparse.ArgumentParser(description="Export a manuscript claim-to-evidence matrix.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--prefix", default="CLAIM_EVIDENCE_MATRIX")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_claims(root)
    print(json.dumps(write_outputs(report, root, args.prefix), indent=2))


if __name__ == "__main__":
    main()
