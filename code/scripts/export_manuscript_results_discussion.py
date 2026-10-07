#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_claim(claims, claim_id):
    for claim in claims:
        if claim["id"] == claim_id:
            return claim
    raise KeyError(claim_id)


def evidence_list(items):
    return "\n".join(f"- `{item}`" for item in items)


def build_document(root):
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")["claims"]
    full = load_json(root / "tables" / "full_statistical_report.json")
    heldout = load_json(root / "tables" / "heldout_generalization.json")
    calibration = load_json(root / "tables" / "selector_calibration.json")
    heldout3 = load_json(root / "tables" / "heldout3_external_validation.json")
    heldout3_expansion = load_json(root / "tables" / "heldout3_candidate_expansion.json")
    heldout4 = load_json(root / "tables" / "heldout4_external_validation.json")
    cross_heldout = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")
    fig1 = load_json(root / "figures" / "figure_manifest.json")
    fig2 = load_json(root / "figures" / "figure_2_manifest.json")
    fig3 = load_json(root / "figures" / "figure_3_manifest.json")

    h1 = heldout["sets"]["heldout1"]["selector"]
    h2 = heldout["sets"]["heldout2"]["selector"]
    cal_h2 = calibration["test_heldout2"]

    sections = [
        {
            "title": "Results Paragraph 1: Strict Evaluation Reveals A Strong Rule Baseline",
            "claim_id": "C1_locked_baseline_strength",
            "draft": (
                "Under the strict multi-car full-lap validator, the strongest single controller was the "
                "rule-based overtake baseline, which passed 8/10 locked seeds. The best innovation variant, "
                "graph-adaptive shielding, reached 7/10, whereas the original graph behavior-cloning actor "
                "with soft shielding reached 2/10. These results indicate that the learned graph actor is "
                "not yet a standalone replacement for a strong rule baseline, but that adaptive shielding "
                "substantially narrows the gap."
            ),
            "figure_callout": "Figure 1 and Figure 2a",
        },
        {
            "title": "Results Paragraph 2: Portfolio Analysis Shows Seed-level Complementarity",
            "claim_id": "C2_oracle_complementarity",
            "draft": (
                "The full-rollout oracle analysis revealed substantial seed-level complementarity among "
                "controllers. Portfolio upper bounds improved coverage relative to the best single method, "
                "supporting online method selection as a research direction. Because these oracle portfolios "
                "select methods after observing full outcomes, they are interpreted only as diagnostic upper "
                "bounds rather than online selector outputs."
            ),
            "figure_callout": "Figure 2b and Figure 2d",
        },
        {
            "title": "Results Paragraph 3: DAgger-v2 Improves Complementarity But Is Not Standalone Robust",
            "claim_id": "C3_dagger_v2_complementary_not_standalone",
            "draft": (
                "Hard-state DAgger recovery improved several difficult held-out cases when paired with "
                "expert-gate shielding, including a 3/4 hard-smoke result in the second DAgger iteration. "
                "However, complete held-out validation showed that DAgger-v2 remained complementary rather "
                "than standalone superior. Its value was clearest when added to the candidate pool, where it "
                "expanded oracle coverage on the first held-out batch."
            ),
            "figure_callout": "Supplementary DAgger tables and Figure 2 source data",
        },
        {
            "title": "Results Paragraph 4: Online Probe Selection Converts Complementarity Into A Heldout1 Simulator-loop Result",
            "claim_id": "C4_first_heldout_selector_positive",
            "draft": (
                f"A five-candidate 1200-step online probe selector was then evaluated using only early "
                f"rollout telemetry before committing to a full run. On the first disjoint held-out set, "
                f"the selector passed {h1['pass_count']}/{h1['n']} seeds and matched the expanded oracle, "
                f"but this heldout1 result is bounded by the heldout2 {h2['pass_count']}/{h2['n']} stress result and later heldout3/heldout4 failures. "
                "This result demonstrates that portfolio complementarity can be converted into an online "
                "simulator-loop decision rule on this held-out batch, but not a real-time deployment controller."
            ),
            "figure_callout": "Figure 2c",
        },
        {
            "title": "Results Paragraph 5: A Second Held-out Batch Exposes The Generalization Boundary",
            "claim_id": "C5_second_heldout_generalization_boundary",
            "draft": (
                f"The same selector did not retain this performance on a second disjoint held-out batch. "
                f"It passed {h2['pass_count']}/{h2['n']} seeds, while the oracle over the same candidate "
                f"pool passed {h2['oracle_pass_count']}/{h2['n']}. This stress repeat shows that the "
                "first held-out success should not be interpreted as broad robustness evidence; the current "
                "candidate pool and selector both remain sensitive to seed variation."
            ),
            "figure_callout": "Figure 2c and Held-out Generalization table",
        },
        {
            "title": "Results Paragraph 6: Calibration Separates Candidate Gaps From Selector Misses",
            "claim_id": "C6_selector_calibration_negative",
            "draft": (
                "To determine whether the heldout2 failure was merely a score-tuning problem, the selector "
                "score was calibrated offline on heldout1 and then evaluated on heldout2. Calibration did "
                f"not improve heldout2, which remained {cal_h2['pass_count']}/{cal_h2['n']}. Error "
                f"decomposition identified {cal_h2['candidate_gap_count']} candidate-policy gaps and "
                f"{cal_h2['selector_miss_count']} selector misses. Thus, future work must both expand the "
                "candidate policy pool and replace the current hand-scored selector with richer learned or "
                "feature-based selection."
            ),
            "figure_callout": "Selector Calibration table and Figure 2 source data",
        },
        {
            "title": "Results Paragraph 7: Heldout3 External Validation Exposes A Sharper Boundary",
            "claim_id": "C13_reproducible_package",
            "draft": (
                "A third disjoint external validation batch further constrained the claims. After candidate expansion, "
                f"the heldout3 oracle reached {heldout3['oracle']['pass_count']}/{heldout3['oracle']['n']}, but the "
                f"expanded online selector reached only {heldout3['expanded_selector']['pass_count']}/"
                f"{heldout3['expanded_selector']['n']}; the primary learned selector also reached "
                f"{heldout3['learned_selector_primary']['pass_count']}/{heldout3['learned_selector_primary']['n']}. "
                f"Candidate gaps remained on seeds {heldout3['oracle']['candidate_gap_seeds']}, and selector failures "
                f"included seeds {heldout3['expanded_selector']['failed_seeds']}. This result shows that the heldout2 "
                "selector improvement and exploratory learned-selector gain do not generalize externally."
            ),
            "figure_callout": "Heldout3 External Validation table",
        },
        {
            "title": "Results Paragraph 8: Targeted Repair Improves Candidate Coverage But Leaves One Gap",
            "claim_id": "C14_reproducible_package",
            "draft": (
                f"Because heldout3 exposed candidate gaps, we trained a targeted recovery candidate on heldout3 hard seeds. "
                f"This targeted repair raised the heldout3 candidate oracle from "
                f"{heldout3_expansion['original_oracle']['pass_count']}/{heldout3_expansion['original_oracle']['n']} to "
                f"a {heldout3_expansion['expanded_oracle']['pass_count']}/{heldout3_expansion['expanded_oracle']['n']} oracle result, "
                f"with targeted coverage of seeds {heldout3_expansion['expanded_oracle']['newly_covered_seeds']}. "
                "This is candidate-policy progress rather than external validation or online selector performance."
            ),
            "figure_callout": "Heldout3 Candidate Expansion table",
        },
        {
            "title": "Results Paragraph 9: Heldout4 Shows Partial Post-repair Transfer",
            "claim_id": "C15_reproducible_package",
            "draft": (
                "Heldout4 was then used as a new external validation batch after the heldout3-targeted repair. "
                f"The online targeted-expanded selector reached {heldout4['selector']['pass_count']}/"
                f"{heldout4['selector']['n']}, whereas the diagnostic oracle reached "
                f"{heldout4['oracle']['pass_count']}/{heldout4['oracle']['n']}. Selector misses occurred on "
                f"seeds {heldout4['selector']['selector_miss_seeds']}, while candidate-policy gaps remained on "
                f"seeds {heldout4['oracle']['candidate_gap_seeds']}. This is partial transfer after repair, not "
                "evidence for a broad robustness claim."
            ),
            "figure_callout": "Figure 3 and Heldout4 Failure Atlas",
        },
        {
            "title": "Results Paragraph 10: Cross-heldout Synthesis Preserves The Failure Boundary",
            "claim_id": "C16_reproducible_package",
            "draft": (
                "A cross-heldout synthesis summarizes the saved validation stages without averaging away the "
                "external failures. Across expanded-or-later evidence, the online simulator-loop selector achieved "
                f"{cross_heldout['aggregate_expanded_or_later']['selector_pass_count']}/"
                f"{cross_heldout['aggregate_expanded_or_later']['n']} strict PASS outcomes, while the corresponding "
                f"diagnostic oracle achieved {cross_heldout['aggregate_expanded_or_later']['oracle_pass_count']}/"
                f"{cross_heldout['aggregate_expanded_or_later']['n']}. The "
                f"{cross_heldout['aggregate_expanded_or_later']['selector_oracle_gap']}-seed selector-oracle gap "
                "is therefore reported as a limitation and a guide for the next selector/candidate experiments."
            ),
            "figure_callout": "Figure 3 and Cross-heldout Validation Synthesis table",
        },
        {
            "title": "Discussion Paragraph 1: Main Interpretation",
            "claim_id": "C16_reproducible_package",
            "draft": (
                "Overall, the study supports a cautious interpretation. Adaptive gating and hard-state "
                "recovery improve the experimental package and expose useful complementarity, but the current "
                "system is not yet a robust autonomous overtaking solution. The most defensible claim is that "
                "online portfolio probing is a promising bridge between specialized controllers, provided that "
                "candidate coverage and selector calibration are improved and externally validated beyond heldout4."
            ),
            "figure_callout": "Figure 3 and Claim Evidence Matrix",
        },
        {
            "title": "Discussion Paragraph 2: Limitations And Next Experiments",
            "claim_id": "C6_selector_calibration_negative",
            "draft": (
                "The next experiments should target the two failure modes separately. Candidate-gap seeds "
                "now have a targeted repair diagnostic, but selector-miss seeds require richer early-rollout features or a learned selector, especially heldout3 "
                "selector failures on 149, 151, 163, and 181 and heldout4 selector misses on 197 and 211. Larger held-out seed sets and traffic-density ablations "
                "are required before making stronger top-journal generalization claims."
            ),
            "figure_callout": "Limitations and Selector Calibration report",
        },
    ]

    lines = [
        "# Manuscript Results and Discussion Draft",
        "",
        "This file is a manuscript-facing writing scaffold generated from the saved evidence package. "
        "It is intentionally conservative: oracle results are separated from online simulator-loop selector results, "
        "and heldout2/calibration plus heldout3 external-validation failures are preserved as limitations.",
        "",
        "## Figure Claims",
        "",
        f"- Figure 1 claim: {fig1['claim']}",
        f"- Figure 2 claim: {fig2['claim']}",
        f"- Figure 3 claim: {fig3['claim']}",
        "",
        "## Results and Discussion Skeleton",
        "",
    ]
    for section in sections:
        claim = get_claim(claims, section["claim_id"])
        lines.extend(
            [
                f"### {section['title']}",
                "",
                section["draft"],
                "",
                f"Figure/table callout: {section['figure_callout']}",
                "",
                "Evidence:",
                "",
                evidence_list(claim["primary_evidence"]),
                "",
                "Guardrail:",
                "",
                f"- {claim['do_not_claim']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Suggested Abstract Result Sentence",
            "",
            (
                "In strict multi-car full-lap overtaking, adaptive shielding and hard-state recovery improve "
                "method complementarity, and a five-candidate online probe selector reaches 10/10 on one "
                "held-out batch while a second held-out batch drops to 5/10 against a 7/10 oracle, "
                "and a third external-validation batch reaches only 4/10 against an 8/10 oracle after expansion, "
                "with targeted repair improving candidate coverage to 9/10 but not solving the remaining gap; "
                "a fourth post-repair external batch reaches 6/10 against an 8/10 oracle, "
                "revealing that candidate coverage and selector calibration remain the dominant barriers to "
                "broad generalization."
            ),
            "",
            "## Prohibited Shortcuts",
            "",
            "- Do not describe oracle portfolios as online selector outputs.",
            "- Do not describe DAgger-v2 as a standalone robust controller.",
            "- Do not report heldout1 10/10 without the heldout2 5/10 stress result.",
            "- Do not claim heldout2 selector improvements generalize to heldout3.",
            "- Do not present heldout3 targeted repair as external validation.",
            "- Do not present heldout4 partial transfer as robustness.",
            "- Do not imply that linear score calibration solves the selector failure.",
            "",
            "## Source Summaries",
            "",
            f"- Full statistical interpretation: {full['interpretation']}",
            f"- Held-out generalization interpretation: {heldout['overall_interpretation']}",
            f"- Selector calibration interpretation: {calibration['interpretation']}",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export manuscript-facing Results/Discussion scaffold.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--out", default="materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md")
    args = parser.parse_args()
    root = Path(args.root)
    out_path = root / args.out
    out_path.write_text(build_document(root), encoding="utf-8")
    print(json.dumps({"markdown": str(out_path)}, indent=2))


if __name__ == "__main__":
    main()
