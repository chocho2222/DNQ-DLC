#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_map(root):
    manifest = load_json(root / "manifest.json")
    heldout = load_json(root / "tables" / "heldout_generalization.json")
    calibration = load_json(root / "tables" / "selector_calibration.json")
    atlas = load_json(root / "tables" / "heldout2_failure_atlas.json")
    heldout3 = load_json(root / "tables" / "heldout3_external_validation.json")
    heldout3_expansion = load_json(root / "tables" / "heldout3_candidate_expansion.json")
    heldout4 = load_json(root / "tables" / "heldout4_external_validation.json")
    heldout4_atlas = load_json(root / "tables" / "heldout4_failure_atlas.json")
    cross_heldout = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")
    full = load_json(root / "tables" / "full_statistical_report.json")
    audit = load_json(root / "tables" / "reproducibility_audit.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    stat = load_json(root / "materials" / "STATISTICAL_ANALYSIS_PLAN.json")
    outline = load_json(root / "materials" / "MANUSCRIPT_OUTLINE.json")

    h1 = heldout["sets"]["heldout1"]["selector"]
    h2 = heldout["sets"]["heldout2"]["selector"]
    cal_h2 = calibration["test_heldout2"]
    locked = manifest["key_results"]["locked_single_methods"]

    questions = [
        {
            "id": "Q1_baseline_fairness",
            "question": "Why is the rule-based overtake baseline the right comparison point, and is the learned model being held to the same validator?",
            "short_answer": (
                "Yes. The rule baseline is the strongest locked single controller at 8/10, and the same strict validator "
                "is applied to all methods with the same completion, rank, first-ahead, and grass thresholds."
            ),
            "evidence": [
                "tables/full_statistical_report.md",
                "tables/full_statistical_report.json",
                "materials/STATISTICAL_ANALYSIS_PLAN.md",
                "materials/MANUSCRIPT_OUTLINE.md",
            ],
            "boundary": "Do not claim the learned graph method surpasses the rule baseline.",
            "follow_up": "Report the locked seed comparison and the strict PASS criteria together.",
        },
        {
            "id": "Q2_selector_positive",
            "question": "Is the online selector just an oracle in disguise?",
            "short_answer": (
                "No. It is an online simulator-loop selector because it chooses using only early probe telemetry, but it is expensive "
                "and still only validated on the recorded seed sets."
            ),
            "evidence": [
                "tables/portfolio_probe_selector_1200_heldout_dagger_v2.md",
                "tables/heldout_generalization.md",
                "materials/DATA_CODE_AVAILABILITY.md",
                "materials/REPRODUCTION_GUIDE.md",
            ],
            "boundary": "Do not present oracle portfolio results as online selector performance.",
            "follow_up": "State the 1200-step probe cost and report heldout1 and heldout2 together.",
        },
        {
            "id": "Q3_generalization_limit",
            "question": "Does the 10/10 heldout1 selector result mean the method is robust?",
            "short_answer": (
                "No. A second disjoint held-out set drops the same selector to 5/10 against a 7/10 oracle, so the result is a "
                "promising held-out batch success, not broad robustness evidence."
            ),
            "evidence": [
                "tables/heldout_generalization.md",
                "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.md",
                "tables/heldout2_failure_atlas.md",
                "materials/MANUSCRIPT_OUTLINE.md",
            ],
            "boundary": "Do not make a broad robustness claim.",
            "follow_up": "Pair the positive heldout1 result with the heldout2 stress repeat and failure atlas.",
        },
        {
            "id": "Q4_calibration_vs_pool",
            "question": "Is heldout2 mainly a selector calibration problem, or is the candidate pool itself insufficient?",
            "short_answer": (
                "Both. Offline calibration still leaves heldout2 at 5/10, with 3 candidate-policy gaps and 2 selector misses."
            ),
            "evidence": [
                "tables/selector_calibration.md",
                "tables/selector_calibration.json",
                "tables/heldout2_failure_atlas.md",
                "tables/heldout2_failure_atlas_seed_rows.csv",
            ],
            "boundary": "Do not imply that retuning the current linear score solves heldout2.",
            "follow_up": "Separate candidate-gap seeds from selector-miss seeds when describing future work.",
        },
        {
            "id": "Q5_heldout3_external_validation",
            "question": "Do the heldout2 candidate-expansion and learned-selector gains generalize to a new external batch?",
            "short_answer": (
                f"No. On heldout3, the expanded oracle is {heldout3['oracle']['pass_count']}/{heldout3['oracle']['n']}, "
                f"but both the expanded online selector and primary learned selector are "
                f"{heldout3['expanded_selector']['pass_count']}/{heldout3['expanded_selector']['n']}."
            ),
            "evidence": [
                "tables/heldout3_external_validation.md",
                "tables/portfolio_probe_selector_1200_heldout3_expanded.md",
                "tables/learned_selector_report.md",
            ],
            "boundary": "Do not claim heldout2 gains are externally validated.",
            "follow_up": "Report that targeted repair covers 173 and seed157 traffic-aware repair closes candidate coverage, leaving selector misses as the next P0 target.",
        },
        {
            "id": "Q6_heldout3_targeted_repair",
            "question": "Does the heldout3-targeted recovery candidate solve the external-validation failure?",
            "short_answer": (
                f"No. It improves candidate coverage from {heldout3_expansion['original_oracle']['pass_count']}/10 to "
                f"{heldout3_expansion['expanded_oracle']['pass_count']}/10, but it is targeted repair rather than "
                "an online selector result or external-validation result."
            ),
            "evidence": [
                "tables/heldout3_candidate_expansion.md",
                "tables/heldout3_targeted_recovery_suite_report.md",
                "tables/heldout3_targeted_recovery_conservative_traffic_suite_report.md",
                "tables/seed157_traffic_ablation.md",
            ],
            "boundary": "Do not present targeted heldout3 repair as external validation or online selector performance.",
            "follow_up": "Use it as evidence for the next candidate-policy target, not as a robustness claim.",
        },
        {
            "id": "Q7_heldout4_partial_transfer",
            "question": "Does heldout4 show that the heldout3-targeted repair generalizes robustly?",
            "short_answer": (
                f"No. Heldout4 is an unused external validation after targeted repair and shows partial transfer: "
                f"the online simulator-loop selector reaches {heldout4['selector']['pass_count']}/{heldout4['selector']['n']} "
                f"against an {heldout4['oracle']['pass_count']}/{heldout4['oracle']['n']} oracle, with selector misses "
                f"{heldout4['selector']['selector_miss_seeds']} and candidate gaps {heldout4['oracle']['candidate_gap_seeds']}."
            ),
            "evidence": [
                "tables/heldout4_external_validation.md",
                "tables/heldout4_failure_atlas.md",
                "figures/figure_3_cross_heldout_validation.*",
            ],
            "boundary": "Do not claim heldout4 proves broad generalization.",
            "follow_up": "Frame heldout4 as partial post-repair transfer and use it to motivate a fresh heldout5-style validation after the next selector/candidate changes.",
        },
        {
            "id": "Q8_cross_heldout_synthesis",
            "question": "Can the cross-heldout aggregate be used as the main robustness result?",
            "short_answer": (
                f"No. It is descriptive: across expanded-or-later evidence, the selector is "
                f"{cross_heldout['aggregate_expanded_or_later']['selector_pass_count']}/"
                f"{cross_heldout['aggregate_expanded_or_later']['n']} while the oracle is "
                f"{cross_heldout['aggregate_expanded_or_later']['oracle_pass_count']}/"
                f"{cross_heldout['aggregate_expanded_or_later']['n']}, leaving a "
                f"{cross_heldout['aggregate_expanded_or_later']['selector_oracle_gap']}-seed gap."
            ),
            "evidence": [
                "tables/cross_heldout_validation_synthesis.md",
                "figures/figure_3_cross_heldout_validation.*",
                "tables/heldout4_external_validation.md",
            ],
            "boundary": "Do not average away heldout3/heldout4 failures or present the aggregate as robustness.",
            "follow_up": "Use Figure 3 to show the selector-oracle gap and split failures into selector misses and candidate-policy gaps.",
        },
        {
            "id": "Q9_dagger_role",
            "question": "Is DAgger-v2 the main breakthrough?",
            "short_answer": (
                "No. It is complementary: it improves candidate-pool coverage and hard-smoke behavior, but it is not standalone "
                "superior on the complete held-out suite."
            ),
            "evidence": [
                "tables/heldout_graph_dagger_recovery_v2_smoke_report.md",
                "tables/heldout_graph_dagger_recovery_v2_suite_report.md",
                "tables/heldout_v2_portfolio.md",
                "materials/LIMITATIONS.md",
            ],
            "boundary": "Do not call DAgger-v2 a standalone robust controller.",
            "follow_up": "Frame it as a candidate that improves oracle coverage, not as the final method.",
        },
        {
            "id": "Q10_reproducibility",
            "question": "Can a reviewer reproduce the package from the saved artifacts alone?",
            "short_answer": (
                "Yes for the recorded package state: provenance is complete and audit finds no missing or weak items, with all "
                "scripts, logs, tables, models, and figure data saved under the package root."
            ),
            "evidence": [
                "tables/artifact_provenance.md",
                "tables/reproducibility_audit.md",
                "materials/DATA_CODE_AVAILABILITY.md",
                "materials/REPRODUCTION_GUIDE.md",
            ],
            "boundary": "Do not claim external manuscript submission packaging is complete.",
            "follow_up": "Point readers to provenance and audit first, then to the reproduction guide.",
        },
        {
            "id": "Q11_statistical_rigor",
            "question": "Are the statistics strong enough for a top-journal claim?",
            "short_answer": (
                "The package reports Wilson intervals, paired bootstrap comparisons, and McNemar tests, but the small seed counts "
                "mean the tests are descriptive and the manuscript should stay conservative."
            ),
            "evidence": [
                "tables/full_statistical_report.md",
                "materials/STATISTICAL_ANALYSIS_PLAN.md",
                "materials/MANUSCRIPT_OUTLINE.md",
            ],
            "boundary": "Do not overstate p-values or imply broad distributional proof from 10-seed sets.",
            "follow_up": "Use confidence intervals and held-out repeats as the main basis for claims.",
        },
    ]

    summary = {
        "root": str(root),
        "title": manifest["title"],
        "high_level_takeaway": (
            "The package is a reproducible baseline-plus-innovation study: strong rule baseline, promising selector on heldout1, "
            "and explicit heldout2 limits that prevent overclaiming."
            " Heldout3 is negative external validation and further prevents robustness claims."
            " Heldout4 shows partial post-repair transfer but leaves selector and candidate gaps."
        ),
        "hard_numbers": {
            "locked_rule_baseline": f"{locked['overtake_base_only']['pass_count']}/{locked['overtake_base_only']['n']}",
            "locked_graph_adaptive": f"{locked['graph_adaptive_shield']['pass_count']}/{locked['graph_adaptive_shield']['n']}",
            "heldout1_selector": f"{h1['pass_count']}/{h1['n']}",
            "heldout2_selector": f"{h2['pass_count']}/{h2['n']}",
            "heldout2_oracle": f"{h2['oracle_pass_count']}/{h2['n']}",
            "heldout2_calibration": f"{cal_h2['pass_count']}/{cal_h2['n']}",
            "heldout2_candidate_gaps": cal_h2["candidate_gap_count"],
            "heldout2_selector_misses": cal_h2["selector_miss_count"],
            "heldout3_oracle": f"{heldout3['oracle']['pass_count']}/{heldout3['oracle']['n']}",
            "heldout3_expanded_selector": (
                f"{heldout3['expanded_selector']['pass_count']}/{heldout3['expanded_selector']['n']}"
            ),
            "heldout3_learned_selector": (
                f"{heldout3['learned_selector_primary']['pass_count']}/{heldout3['learned_selector_primary']['n']}"
            ),
            "heldout3_targeted_expanded_oracle": (
                f"{heldout3_expansion['expanded_oracle']['pass_count']}/{heldout3_expansion['expanded_oracle']['n']}"
            ),
            "heldout3_candidate_gap_seeds": heldout3["oracle"]["candidate_gap_seeds"],
            "heldout3_remaining_candidate_gap_seeds": heldout3_expansion["expanded_oracle"]["remaining_candidate_gap_seeds"],
            "heldout3_failed_seeds": heldout3["expanded_selector"]["failed_seeds"],
            "heldout4_selector": f"{heldout4['selector']['pass_count']}/{heldout4['selector']['n']}",
            "heldout4_oracle": f"{heldout4['oracle']['pass_count']}/{heldout4['oracle']['n']}",
            "heldout4_selector_miss_seeds": heldout4["selector"]["selector_miss_seeds"],
            "heldout4_candidate_gap_seeds": heldout4["oracle"]["candidate_gap_seeds"],
            "cross_heldout_selector": (
                f"{cross_heldout['aggregate_expanded_or_later']['selector_pass_count']}/"
                f"{cross_heldout['aggregate_expanded_or_later']['n']}"
            ),
            "cross_heldout_oracle": (
                f"{cross_heldout['aggregate_expanded_or_later']['oracle_pass_count']}/"
                f"{cross_heldout['aggregate_expanded_or_later']['n']}"
            ),
            "cross_heldout_selector_oracle_gap": cross_heldout["aggregate_expanded_or_later"]["selector_oracle_gap"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "audit_missing_or_weak": len(audit["missing_or_weak_items"]),
        },
        "evidence_clusters": {
            "baseline": full["interpretation"],
            "generalization": heldout["overall_interpretation"],
            "calibration": calibration["interpretation"],
            "failure_atlas": atlas["summary"]["interpretation"],
            "heldout3_external_validation": heldout3["interpretation"],
            "heldout3_candidate_expansion": heldout3_expansion["interpretation"],
            "heldout4_failure_atlas": heldout4_atlas["summary"]["interpretation"],
            "cross_heldout_validation": cross_heldout["interpretation"],
            "stat_plan": stat["multiplicity_policy"],
            "outline_guardrails": outline["claim_guardrails"],
        },
    }

    return {"summary": summary, "questions": questions}


def write_markdown(report, path):
    lines = [
        "# Reviewer Response Map",
        "",
        "This map is a rebuttal-ready FAQ built from the saved evidence package. It is designed to answer the questions most likely to be raised by a careful reviewer.",
        "",
        "## Package Summary",
        "",
        report["summary"]["high_level_takeaway"],
        "",
        "### Hard Numbers",
        "",
    ]
    for key, value in report["summary"]["hard_numbers"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Reviewer Questions",
            "",
        ]
    )
    for item in report["questions"]:
        lines.extend(
            [
                f"### {item['id']}",
                "",
                f"**Question:** {item['question']}",
                "",
                f"**Short answer:** {item['short_answer']}",
                "",
                "**Evidence:**",
                "",
            ]
        )
        lines.extend(f"- `{e}`" for e in item["evidence"])
        lines.extend(
            [
                "",
                f"**Boundary:** {item['boundary']}",
                "",
                f"**Follow-up line:** {item['follow_up']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Evidence Clusters",
            "",
        ]
    )
    for key, value in report["summary"]["evidence_clusters"].items():
        if isinstance(value, list):
            lines.append(f"- `{key}`: " + "; ".join(str(v) for v in value))
        else:
            lines.append(f"- `{key}`: {value}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(report, root):
    path = root / "materials" / "REVIEWER_RESPONSE_MAP.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "question", "short_answer", "boundary", "follow_up", "evidence"],
        )
        writer.writeheader()
        for item in report["questions"]:
            writer.writerow(
                {
                    "id": item["id"],
                    "question": item["question"],
                    "short_answer": item["short_answer"],
                    "boundary": item["boundary"],
                    "follow_up": item["follow_up"],
                    "evidence": "; ".join(item["evidence"]),
                }
            )
    return path


def main():
    parser = argparse.ArgumentParser(description="Export a reviewer-ready response map from saved evidence.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_map(root)
    out_json = root / "materials" / "REVIEWER_RESPONSE_MAP.json"
    out_md = root / "materials" / "REVIEWER_RESPONSE_MAP.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    out_csv = write_csv(report, root)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
