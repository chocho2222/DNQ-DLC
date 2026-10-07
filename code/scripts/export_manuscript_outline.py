#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_outline(root):
    manifest = load_json(root / "manifest.json")
    full = load_json(root / "tables" / "full_statistical_report.json")
    heldout = load_json(root / "tables" / "heldout_generalization.json")
    calibration = load_json(root / "tables" / "selector_calibration.json")
    atlas = load_json(root / "tables" / "heldout2_failure_atlas.json")
    heldout3 = load_json(root / "tables" / "heldout3_external_validation.json")
    heldout3_expansion = load_json(root / "tables" / "heldout3_candidate_expansion.json")
    heldout4 = load_json(root / "tables" / "heldout4_external_validation.json")
    cross_heldout = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")

    h1 = heldout["sets"]["heldout1"]["selector"]
    h2 = heldout["sets"]["heldout2"]["selector"]
    cal_h2 = calibration["test_heldout2"]
    locked = manifest["key_results"]["locked_single_methods"]

    return {
        "root": str(root),
        "title_options": [
            "Strict Full-lap Evaluation Reveals Complementarity and Generalization Limits in Multi-car Overtaking",
            "Online Portfolio Probing for Strict Multi-car Overtaking Under Held-out Track Variation",
            "Reproducible Multi-car Overtaking Benchmarks with Conservative Online Controller Selection",
        ],
        "recommended_title": (
            "Strict Full-lap Evaluation Reveals Complementarity and Generalization Limits in Multi-car Overtaking"
        ),
        "abstract": {
            "background": (
                "Autonomous overtaking policies are often demonstrated through short visual rollouts, but "
                "strict simulator full-lap multi-car evaluation exposes additional completion, ranking, and safety failures."
            ),
            "methods": (
                "We construct a strict non-VLM simulator multi-car full-lap benchmark with preserved rule baselines, "
                "a permutation-invariant graph actor, adaptive shielding, hard-state DAgger recovery, and "
                "a five-candidate 1200-step online probe selector."
            ),
            "results": (
                f"On locked seeds, the strongest rule overtake baseline passes "
                f"{locked['overtake_base_only']['pass_count']}/{locked['overtake_base_only']['n']} runs, "
                f"while the best learned/shielded innovation passes "
                f"{locked['graph_adaptive_shield']['pass_count']}/{locked['graph_adaptive_shield']['n']}. "
                f"The online selector reaches {h1['pass_count']}/{h1['n']} on the first held-out set, "
                f"but drops to {h2['pass_count']}/{h2['n']} on a second held-out set against a "
                f"{h2['oracle_pass_count']}/{h2['n']} oracle; after candidate expansion, heldout3 remains a diagnostic "
                f"stress boundary with only {heldout3['expanded_selector']['pass_count']}/{heldout3['expanded_selector']['n']} "
                f"for the expanded selector against an {heldout3['oracle']['pass_count']}/{heldout3['oracle']['n']} oracle. "
                f"After targeted repair, heldout4 reaches {heldout4['selector']['pass_count']}/{heldout4['selector']['n']} "
                f"against an {heldout4['oracle']['pass_count']}/{heldout4['oracle']['n']} oracle."
            ),
            "conclusion": (
                f"Failure decomposition identifies {cal_h2['candidate_gap_count']} candidate-policy gaps "
                f"and {cal_h2['selector_miss_count']} selector misses on heldout2, while heldout3 identifies "
                f"candidate-gap seeds {heldout3['oracle']['candidate_gap_seeds']}; targeted repair closes candidate coverage in "
                f"a seed-targeted diagnostic. Heldout3 selector failures remain "
                f"{heldout3['expanded_selector']['failed_seeds']}, and heldout4 leaves selector misses "
                f"{heldout4['selector']['selector_miss_seeds']} plus candidate gaps {heldout4['oracle']['candidate_gap_seeds']}. "
                f"Across expanded-or-later evidence, the selector-oracle gap is "
                f"{cross_heldout['aggregate_expanded_or_later']['selector_oracle_gap']} seeds. Online portfolio probing is promising but not yet "
                "broadly robust."
            ),
        },
        "contributions": [
            "A strict non-VLM multi-car full-lap overtaking package with preserved baselines, logs, models, GIFs, figures, and machine-readable tables.",
            "A conservative comparison showing that adaptive graph shielding narrows but does not surpass the strongest rule baseline on locked seeds.",
            "A portfolio and online-probe analysis that converts method complementarity into an online simulator-loop heldout1 result.",
            "A second held-out stress test and seed-level failure atlas that prevent overclaiming and identify separate candidate-policy and selector failure modes.",
            "A third disjoint diagnostic stress batch that shows heldout2 gains do not yet generalize.",
            "A fourth unused post-repair external validation batch and cross-heldout synthesis that show partial transfer but preserve the remaining selector-oracle gap.",
            "A reproducibility package with claim guardrails, statistical analysis plan, data/code availability statement, and artifact-level provenance.",
        ],
        "paper_structure": [
            {
                "section": "Introduction",
                "purpose": "Motivate strict full-lap evaluation and explain why visual overtaking demos are insufficient.",
                "must_include": [
                    "multi-car traffic setting",
                    "full-lap completion and rank as primary endpoint",
                    "non-VLM scope",
                    "need for conservative held-out reporting",
                ],
            },
            {
                "section": "Methods",
                "purpose": "Define environment, baselines, graph actor, adaptive shield, DAgger-v2 candidate, online selector, and validation protocol.",
                "must_include": [
                    "locked, heldout1, heldout2, heldout3, heldout4 seed sets",
                    "strict PASS criterion",
                    "oracle portfolios as diagnostic upper bounds",
                    "1200-step probe selector as online simulator-loop but expensive",
                ],
            },
            {
                "section": "Results",
                "purpose": "Report locked single-method results, complementarity, heldout1 positive selector result, heldout2 stress failure, heldout3 diagnostic stress boundary, heldout4 post-repair validation, cross-heldout synthesis, and failure decomposition.",
                "must_include": [
                    "locked overtake baseline 8/10",
                    "graph-adaptive shield 7/10",
                    "heldout1 selector 10/10 reported together with heldout2 5/10 and heldout3/heldout4 boundaries",
                    "heldout2 selector 5/10 against 7/10 oracle",
                    "heldout3 expanded selector 4/10 against 8/10 oracle",
                    "heldout4 targeted-expanded selector 6/10 against 8/10 oracle",
                    "cross-heldout expanded-or-later selector 31/50 against 45/50 oracle",
                    "candidate gaps 97, 101, 103 and selector misses 109, 113",
                    "heldout3 targeted candidate 10/10 oracle result as a seed-targeted diagnostic, not external validation",
                    "heldout3 selector failures 149, 151, 157, 163, 173, 181",
                ],
            },
            {
                "section": "Discussion",
                "purpose": "Frame the method as promising but not robust, and turn failures into next experiments.",
                "must_include": [
                    "do not make a broad robustness claim",
                    "candidate-gap seeds require new constrained/recovery candidates",
                    "selector-miss seeds require learned or richer selection",
                    "heldout3 candidate/selector failures must be addressed before larger-N claims",
                    "heldout4 selector misses and candidate gaps remain after targeted repair",
                    "larger-N and traffic-density evaluations are needed",
                ],
            },
        ],
        "figure_plan": [
            {
                "figure": "Figure 1",
                "file": "figures/figure_1_multicar_overtake_results.*",
                "role": "Main strict evaluation and visual evidence summary.",
                "claim": "Strict evaluation is harder than selected visual rollouts and exposes safety/robustness limits.",
            },
            {
                "figure": "Figure 2",
                "file": "figures/figure_2_portfolio_selector_summary.*",
                "role": "Portfolio, selector, held-out generalization, and calibration summary.",
                "claim": "Complementarity can be exploited by online probing on heldout1, but heldout2 and heldout3 expose generalization limits.",
            },
            {
                "figure": "Figure 3",
                "file": "figures/figure_3_cross_heldout_validation.*",
                "role": "Cross-heldout selector-oracle synthesis after targeted repair.",
                "claim": "Heldout4 shows partial transfer after targeted repair, while the cross-heldout aggregate remains useful but not robust.",
            },
            {
                "figure": "Supplementary External Validation Table",
                "file": "tables/heldout3_external_validation.*",
                "role": "Third disjoint held-out diagnostic stress analysis after candidate expansion.",
                "claim": "Heldout3 is a diagnostic stress boundary: oracle 8/10, expanded selector 4/10, learned selector 4/10.",
            },
            {
                "figure": "Supplementary Targeted Repair Table",
                "file": "tables/heldout3_candidate_expansion.*",
                "role": "Heldout3-targeted candidate repair after diagnostic stress analysis.",
                "claim": "Targeted repair raises heldout3 to a 10/10 oracle result, but this is a seed-targeted diagnostic rather than external validation.",
            },
            {
                "figure": "Supplementary Table/Figure",
                "file": "tables/heldout2_failure_atlas.*",
                "role": "Seed-level failure decomposition for the second held-out stress test.",
                "claim": "Heldout2 failures split into candidate-policy gaps and selector misses.",
            },
        ],
        "result_paragraph_order": [
            "Strict validator reveals that a strong rule overtake baseline remains the best single controller.",
            "Adaptive graph shielding narrows the locked-seed gap but does not surpass the rule baseline.",
            "Oracle portfolios reveal seed-level complementarity, but are not online selector outputs.",
            "DAgger-v2 is complementary and useful in the candidate pool, not standalone robust.",
            "A five-candidate online probe selector reaches heldout1 10/10, reported together with heldout2 5/10 and heldout3/heldout4 failures.",
            "The same selector reaches heldout2 5/10 against a 7/10 oracle.",
            "Expanded-candidate heldout3 diagnostic stress evaluation reaches only 4/10 against an 8/10 oracle.",
            "Heldout3-targeted candidate repair plus seed157 ablation raises the targeted repair to a 10/10 oracle result as diagnostic reuse, not external validation.",
            "Heldout4 post-repair validation reaches 6/10 against an 8/10 oracle.",
            "Cross-heldout expanded-or-later synthesis reaches 31/50 for the selector against 45/50 for the diagnostic oracle.",
            "Heldout2 failure atlas separates candidate gaps from selector misses and defines the next experiments.",
            "Heldout3 and heldout4 selector/candidate gaps define the highest-priority follow-up experiments.",
        ],
        "claim_guardrails": [
            "Report heldout1, heldout2, and heldout3 together.",
            "Describe oracle portfolios only as upper bounds.",
            "Describe DAgger-v2 as complementary, not standalone robust.",
            "Do not make a broad robustness claim.",
            "Do not imply score-only calibration solves heldout2.",
            "Do not claim heldout2 selector gains generalize to heldout3.",
            "Do not present heldout4 partial transfer as robustness.",
            "Do not average away heldout3/heldout4 failures in the cross-heldout synthesis.",
        ],
        "next_experiments": [
            {
                "target": "heldout3 targeted candidate selector integration",
                "seeds": heldout3_expansion["expanded_oracle"]["remaining_candidate_gap_seeds"],
                "action": "Integrate the targeted candidate pool into selector training/evaluation without treating it as external validation.",
            },
            {
                "target": "heldout3 selector failures",
                "seeds": heldout3["expanded_selector"]["failed_seeds"],
                "action": "Train selector features that reduce heldout3 failures while preserving heldout1 10/10 and heldout2 7/10, then validate on a fresh heldout batch.",
            },
            {
                "target": "candidate-policy gaps",
                "seeds": atlas["summary"]["candidate_gap_seeds"],
                "action": "Add boundary-constrained or recovery-specialized candidates and rerun heldout2 oracle/selector.",
            },
            {
                "target": "selector misses",
                "seeds": atlas["summary"]["selector_miss_seeds"],
                "action": "Train or distill a richer selector from early telemetry and track/traffic features.",
            },
            {
                "target": "heldout4 selector misses and candidate gaps",
                "seeds": heldout4["selector"]["selector_miss_seeds"] + heldout4["oracle"]["candidate_gap_seeds"],
                "action": "Use heldout4 only as post-repair external evidence; design the next selector/candidate changes before a fresh heldout5 validation.",
            },
            {
                "target": "top-journal robustness",
                "seeds": "larger held-out batches",
                "action": "Run larger-N seed, traffic-density, and opponent-diversity evaluations with the same strict validator.",
            },
        ],
        "evidence_entry_points": [
            "materials/CLAIM_EVIDENCE_MATRIX.md",
            "materials/STATISTICAL_ANALYSIS_PLAN.md",
            "materials/DATA_CODE_AVAILABILITY.md",
            "tables/full_statistical_report.md",
            "tables/heldout_generalization.md",
            "tables/selector_calibration.md",
            "tables/heldout2_failure_atlas.md",
            "tables/heldout3_external_validation.md",
            "tables/heldout3_candidate_expansion.md",
            "tables/heldout4_external_validation.md",
            "tables/heldout4_failure_atlas.md",
            "tables/cross_heldout_validation_synthesis.md",
            "figures/figure_3_cross_heldout_validation.*",
            "materials/FIGURE_LEGENDS.md",
            "tables/artifact_provenance.md",
            "tables/reproducibility_audit.md",
        ],
        "source_interpretations": {
            "full_statistical_report": full["interpretation"],
            "heldout_generalization": heldout["overall_interpretation"],
            "selector_calibration": calibration["interpretation"],
            "heldout2_failure_atlas": atlas["summary"]["interpretation"],
            "heldout3_external_validation": heldout3["interpretation"],
            "heldout3_candidate_expansion": heldout3_expansion["interpretation"],
            "heldout4_external_validation": heldout4["interpretation"],
            "cross_heldout_validation_synthesis": cross_heldout["interpretation"],
        },
    }


def write_markdown(report, path):
    abstract = report["abstract"]
    lines = [
        "# Manuscript Outline",
        "",
        "This outline is generated from the saved evidence package. It is intentionally conservative and should be used with the claim evidence matrix.",
        "",
        "## Recommended Title",
        "",
        report["recommended_title"],
        "",
        "## Alternative Titles",
        "",
    ]
    lines.extend(f"- {title}" for title in report["title_options"])
    lines.extend(
        [
            "",
            "## Structured Abstract Draft",
            "",
            f"**Background:** {abstract['background']}",
            "",
            f"**Methods:** {abstract['methods']}",
            "",
            f"**Results:** {abstract['results']}",
            "",
            f"**Conclusion:** {abstract['conclusion']}",
            "",
            "## Contributions",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["contributions"])
    lines.extend(["", "## Paper Structure", ""])
    for item in report["paper_structure"]:
        lines.extend(
            [
                f"### {item['section']}",
                "",
                item["purpose"],
                "",
                "Must include:",
                "",
            ]
        )
        lines.extend(f"- {entry}" for entry in item["must_include"])
        lines.append("")
    lines.extend(["## Figure And Table Plan", ""])
    for item in report["figure_plan"]:
        lines.extend(
            [
                f"### {item['figure']}",
                "",
                f"- File: `{item['file']}`",
                f"- Role: {item['role']}",
                f"- Claim: {item['claim']}",
                "",
            ]
        )
    lines.extend(["## Results Paragraph Order", ""])
    lines.extend(f"{idx}. {item}" for idx, item in enumerate(report["result_paragraph_order"], start=1))
    lines.extend(["", "## Claim Guardrails", ""])
    lines.extend(f"- {item}" for item in report["claim_guardrails"])
    lines.extend(["", "## Next Experiments", ""])
    for item in report["next_experiments"]:
        lines.extend(
            [
                f"### {item['target']}",
                "",
                f"- Seeds/scope: `{item['seeds']}`",
                f"- Action: {item['action']}",
                "",
            ]
        )
    lines.extend(["## Evidence Entry Points", ""])
    lines.extend(f"- `{item}`" for item in report["evidence_entry_points"])
    lines.extend(["", "## Source Interpretations", ""])
    for key, value in report["source_interpretations"].items():
        value = value.replace("candidate oracle of 10/10", "10/10 oracle result")
        value = value.replace("oracle of 10/10", "10/10 oracle result")
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export a conservative manuscript outline from saved evidence.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_outline(root)
    out_json = root / "materials" / "MANUSCRIPT_OUTLINE.json"
    out_md = root / "materials" / "MANUSCRIPT_OUTLINE.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md)}, indent=2))


if __name__ == "__main__":
    main()
