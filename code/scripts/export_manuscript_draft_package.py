#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_main(root):
    manifest = load_json(root / "manifest.json")
    outline = load_json(root / "materials" / "MANUSCRIPT_OUTLINE.json")
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
    cost = load_json(root / "tables" / "compute_cost_report.json")

    locked = manifest["key_results"]["locked_single_methods"]
    h1 = heldout["sets"]["heldout1"]["selector"]
    h2 = heldout["sets"]["heldout2"]["selector"]
    cal_h2 = calibration["test_heldout2"]
    abstract = outline["abstract"]

    return "\n".join(
        [
            "# " + outline["recommended_title"],
            "",
            "> Draft status: evidence-linked local manuscript draft. This is not a final submission PDF/source package.",
            "",
            "## Abstract",
            "",
            f"**Background:** {abstract['background']}",
            "",
            f"**Methods:** {abstract['methods']}",
            "",
            f"**Results:** {abstract['results']}",
            "",
            f"**Conclusion:** {abstract['conclusion']}",
            "",
            "## Introduction",
            "",
            "Short visual demonstrations of autonomous overtaking can hide failures in lap completion, final rank, off-track behavior, and traffic-wide safety. We therefore treat strict full-lap multi-car validation as the primary object of study rather than using selected rollouts as proof of robust overtaking.",
            "",
            "This manuscript draft intentionally excludes VLM components. The goal is to establish a reproducible non-VLM baseline-plus-innovation package, preserve negative controls, and report held-out generalization conservatively.",
            "",
            "## Related Work",
            "",
            "Autonomous racing has become a compact testbed for high-performance autonomy because it stresses planning, control, learning, and evaluation under dynamic limits. Recent surveys organize this field across perception, planning, control, end-to-end learning, and racing platforms [@betz2022survey]. Scaled platforms such as F1TENTH further make racing useful for repeatable algorithm evaluation and education, but they also highlight the need for benchmark definitions and baselines that make results comparable [@okelly2020f1tenth].",
            "",
            "Classical autonomous-racing systems often formulate progress maximization, track-boundary handling, and opponent avoidance as optimization or model predictive control problems. Optimization-based 1:43-scale racing demonstrates that receding-horizon control can combine progress objectives with track and obstacle constraints in real time [@liniger2015optimization]. Learning-based racing work complements this line by using high-fidelity simulation and reinforcement learning to handle nonlinear dynamics and tactical interactions, including curriculum reinforcement learning for Gran Turismo overtaking [@song2021autonomous] and championship-level Gran Turismo agents trained with deep reinforcement learning and mixed scenarios [@wurman2022outracing].",
            "",
            "Our contribution is narrower and deliberately conservative relative to these systems. We do not claim real-road transfer, perception-stack capability, or champion-level racing performance. Instead, we focus on a strict simulator-only, telemetry/state-based full-lap multi-car overtaking protocol with preserved strong rule baselines, online portfolio probing, seed-level failure decomposition, and explicit held-out generalization limits.",
            "",
            "## Methods",
            "",
            "### Environment And Task",
            "",
            f"The task is {manifest['scope']['task']} in a Gym-style simulation interface [@brockman2016openai]. The strict validator requires {manifest['scope']['validator']}. The recorded seed sets are locked seeds `{manifest['seed_sets']['locked']}`, heldout1 `{manifest['seed_sets']['heldout1']}`, heldout2 `{manifest['seed_sets']['heldout2']}`, heldout3 `{manifest['seed_sets']['heldout3']}`, heldout4 `{manifest['seed_sets']['heldout4']}`, and hard-smoke seeds `{manifest['seed_sets']['hard_smoke']}`.",
            "",
            "### Methods Compared",
            "",
            "The package preserves telemetry/rule baselines, a permutation-invariant graph/set behavior-cloning actor motivated by relational inductive bias [@battaglia2018relational], adaptive telemetry gating, graph-adaptive shielding, DAgger-style hard-state recovery candidates [@ross2011reduction], and online portfolio probe selectors. Oracle portfolios are used only as diagnostic upper bounds because they select methods after full outcomes are known.",
            "",
            "### Statistical Analysis",
            "",
            "Pass rates are reported with Wilson confidence intervals where available [@wilson1927probable]. Paired locked-seed comparisons use bootstrap intervals and McNemar tests as descriptive statistics. Because the seed counts are small, statistical tests are treated as supporting evidence rather than definitive distributional proof.",
            "",
            "## Results",
            "",
            "### Strict Evaluation Preserves A Strong Rule Baseline",
            "",
            f"On the locked strict 10-seed protocol, the rule-based overtake baseline passes {locked['overtake_base_only']['pass_count']}/{locked['overtake_base_only']['n']} seeds. The best learned/shielded innovation, graph-adaptive shielding, passes {locked['graph_adaptive_shield']['pass_count']}/{locked['graph_adaptive_shield']['n']}, while the original graph soft-shield setting passes {locked['graph_soft_shield']['pass_count']}/{locked['graph_soft_shield']['n']}. Thus, the current learned component narrows but does not surpass the strongest rule baseline.",
            "",
            "Evidence: `tables/full_statistical_report.md`, `materials/CLAIM_EVIDENCE_MATRIX.md`.",
            "",
            "### Online Portfolio Probing Converts Complementarity Into A Heldout1 Result",
            "",
            f"A five-candidate 1200-step online probe selector reaches {h1['pass_count']}/{h1['n']} on heldout1 and matches the expanded oracle at {h1['oracle_pass_count']}/{h1['n']}, but this result must be read with the heldout2 {h2['pass_count']}/{h2['n']} stress result and later heldout3/heldout4 failures. This is an online simulator-loop selector because it uses early probe telemetry before committing to the full rollout, but it is computationally expensive and is not a real-time deployment controller.",
            "",
            "Evidence: `tables/portfolio_probe_selector_1200_heldout_dagger_v2.md`, `tables/heldout_generalization.md`.",
            "",
            "### A Second Held-out Batch Defines The Generalization Boundary",
            "",
            f"The same selector reaches {h2['pass_count']}/{h2['n']} on heldout2, whereas the candidate oracle reaches {h2['oracle_pass_count']}/{h2['n']}. This stress repeat prevents a broad robustness claim and shows that candidate coverage and selector calibration remain limiting factors.",
            "",
            "Evidence: `tables/portfolio_probe_selector_1200_heldout2_dagger_v2.md`, `tables/heldout_generalization.md`.",
            "",
            "### Failure Decomposition",
            "",
            f"Offline score calibration trained on heldout1 does not improve heldout2, which remains {cal_h2['pass_count']}/{cal_h2['n']}. The heldout2 failures decompose into {cal_h2['candidate_gap_count']} candidate-policy gaps and {cal_h2['selector_miss_count']} selector misses. Candidate-gap seeds are 97, 101, and 103; selector-miss seeds are 109 and 113.",
            "",
            f"A heldout1-trained scalar selector-distillation grid gives the same boundary: {selector_distillation['grid']['heldout1_perfect_configs']} heldout1-perfect linear/priority configurations remain at {selector_distillation['best_train_perfect']['heldout2_pass_count']}/{h2['n']} on heldout2.",
            "",
            f"Candidate expansion removes the policy-coverage gap at the oracle level: DAgger-v2 recovery-conservative and expert-more-graph candidates raise the heldout2 candidate oracle from {candidate_expansion['original_oracle']['pass_count']}/{candidate_expansion['original_oracle']['n']} to {candidate_expansion['expanded_oracle']['pass_count']}/{candidate_expansion['expanded_oracle']['n']}. This oracle result remains an upper bound, so it is reported separately from online selector performance.",
            "",
            f"After adding the expert-more-graph candidate to the online simulator-loop selector, heldout1 remains {expanded_selector['summaries']['heldout1_expanded']['pass_count']}/{expanded_selector['summaries']['heldout1_expanded']['n']} and heldout2 improves from {expanded_selector['summaries']['heldout2_original']['pass_count']}/{expanded_selector['summaries']['heldout2_original']['n']} to {expanded_selector['summaries']['heldout2_expanded']['pass_count']}/{expanded_selector['summaries']['heldout2_expanded']['n']}. The remaining heldout2 failures are selector misses on seeds {', '.join(str(seed) for seed in expanded_selector['summaries']['heldout2_expanded']['selector_miss_seeds'])}, with an expanded oracle of {expanded_selector['summaries']['heldout2_expanded']['oracle_pass_count']}/{expanded_selector['summaries']['heldout2_expanded']['n']}.",
            "",
            f"Simple expanded selector distillation does not close this residual gap: {expanded_distillation['grid']['heldout1_perfect_configs']} heldout1-perfect scalar/priority configurations peak at {expanded_distillation['best_train_perfect']['heldout2_pass_count']}/{expanded_selector['summaries']['heldout2_expanded']['n']} on heldout2. This negative result motivates richer learned selectors rather than further scalar score retuning.",
            "",
            f"An exploratory feature-only logistic learned selector supports that direction but is not yet an accepted replacement: it improves heldout2 to {learned_selector['variants'][learned_selector['primary_variant']]['test']['pass_count']}/{learned_selector['variants'][learned_selector['primary_variant']]['test']['n']}, while reducing heldout1 to {learned_selector['variants'][learned_selector['primary_variant']]['train']['pass_count']}/{learned_selector['variants'][learned_selector['primary_variant']]['train']['n']}. Method-identity variants fall to 5/10 on heldout2, indicating overfitting risk.",
            "",
            f"A third disjoint external validation batch is substantially weaker. On heldout3, the expanded six-candidate oracle reaches {heldout3['oracle']['pass_count']}/{heldout3['oracle']['n']} with candidate gaps on seeds {', '.join(str(seed) for seed in heldout3['oracle']['candidate_gap_seeds'])}, while the expanded online selector reaches {heldout3['expanded_selector']['pass_count']}/{heldout3['expanded_selector']['n']} and the primary learned selector also reaches {heldout3['learned_selector_primary']['pass_count']}/{heldout3['learned_selector_primary']['n']}. Thus, the heldout2 selector improvement and exploratory learned-selector gain do not generalize to heldout3.",
            "",
            f"Targeted heldout3 candidate repair raises the candidate oracle to a {heldout3_expansion['expanded_oracle']['pass_count']}/{heldout3_expansion['expanded_oracle']['n']} oracle result, with targeted coverage of seeds {', '.join(str(seed) for seed in heldout3_expansion['expanded_oracle']['newly_covered_seeds'])}. This remains a targeted repair diagnostic rather than external validation or online selector performance.",
            "",
            f"A fourth unused external validation batch after targeted repair shows partial transfer. On heldout4, the online targeted-expanded selector reaches {heldout4['selector']['pass_count']}/{heldout4['selector']['n']}, whereas the diagnostic oracle reaches {heldout4['oracle']['pass_count']}/{heldout4['oracle']['n']}. Selector misses remain on seeds {', '.join(str(seed) for seed in heldout4['selector']['selector_miss_seeds'])}, and candidate-policy gaps remain on seeds {', '.join(str(seed) for seed in heldout4['oracle']['candidate_gap_seeds'])}.",
            "",
            f"Across expanded-or-later held-out evidence, the online simulator-loop selector achieves {cross_heldout['aggregate_expanded_or_later']['selector_pass_count']}/{cross_heldout['aggregate_expanded_or_later']['n']} strict PASS outcomes, while the diagnostic oracle reaches {cross_heldout['aggregate_expanded_or_later']['oracle_pass_count']}/{cross_heldout['aggregate_expanded_or_later']['n']}. This descriptive synthesis leaves a {cross_heldout['aggregate_expanded_or_later']['selector_oracle_gap']}-seed selector-oracle gap and must not be interpreted as robustness.",
            "",
            "Evidence: `tables/selector_calibration.md`, `tables/selector_distillation_report.md`, `tables/heldout2_candidate_expansion.md`, `tables/expanded_selector_generalization.md`, `tables/expanded_selector_distillation_report.md`, `tables/learned_selector_report.md`, `tables/heldout2_failure_atlas.md`, `tables/heldout3_external_validation.md`, `tables/heldout3_candidate_expansion.md`, `tables/heldout4_external_validation.md`, `tables/heldout4_failure_atlas.md`, `tables/cross_heldout_validation_synthesis.md`.",
            "",
            "## Discussion",
            "",
            "The most defensible claim is that strict multi-car full-lap evaluation exposes useful controller complementarity and that online portfolio probing can convert this complementarity into a strong heldout1 result and partial transfer after candidate expansion and repair. The current evidence does not support a broad robust-overtaking claim because heldout2 remains limited by selector errors, heldout3 shows a sharper external-validation drop, and heldout4 still leaves selector and candidate gaps.",
            "",
            "The next experiments should train a richer selector that uses the targeted candidate pool to reduce heldout3 selector misses on seeds 149, 151, 163, and 181 and heldout4 selector misses on seeds 197 and 211 without losing heldout1 performance. Larger-N held-out batches, traffic-density ablations, and opponent-diversity evaluations are required before stronger top-journal robustness claims.",
            "",
            "## Data And Code Availability",
            "",
            f"All local package artifacts are stored under `{root}`. The release archive manifest in `materials/RELEASE_ARCHIVE_MANIFEST.md` records the current file count, byte size, categories, and SHA256 checksums. No external DOI or repository accession has been assigned yet.",
            "",
            "## Compute Reporting",
            "",
            f"The compute-cost report summarizes {cost['summary']['full_rollout_rows']} full-rollout rows and {cost['summary']['selector_probe_rows']} selector probe rows. It reports simulated steps and device records, not wall-clock time or utilization.",
            "",
            "## Figure And Table Callouts",
            "",
            "Representative GIFs are used only as qualitative reviewer orientation; quantitative claims rely on seed-level validator tables, source data, and the strict PASS/FAIL ledgers.",
            "",
            "- Figure 1: `figures/figure_1_multicar_overtake_results.*`",
            "- Figure 2: `figures/figure_2_portfolio_selector_summary.*`",
            "- Figure 3: `figures/figure_3_cross_heldout_validation.*`",
            "- Figure legends: `materials/FIGURE_LEGENDS.md`",
            "- Figure source data and technical QC: `materials/FIGURE_SOURCE_DATA_AUDIT.md`, `materials/FIGURE_TECHNICAL_QC.md`",
            "- Supplementary failure atlas: `tables/heldout2_failure_atlas.md`",
            "- Expanded selector report: `tables/expanded_selector_generalization.md`",
            "- Expanded selector distillation: `tables/expanded_selector_distillation_report.md`",
            "- Learned selector diagnostic: `tables/learned_selector_report.md`",
            "- Heldout3 external validation: `tables/heldout3_external_validation.md`",
            "- Heldout3 targeted candidate expansion: `tables/heldout3_candidate_expansion.md`",
            "- Heldout4 external validation: `tables/heldout4_external_validation.md`",
            "- Heldout4 failure atlas: `tables/heldout4_failure_atlas.md`",
            "- Cross-heldout synthesis: `tables/cross_heldout_validation_synthesis.md`",
            "- Transparent reporting checklist: `materials/TRANSPARENT_REPORTING_CHECKLIST.md`",
            "",
            "## Claim Guardrails",
            "",
            "- Do not claim the learned graph method surpasses the strongest rule baseline.",
            "- Do not present oracle portfolios as online selector outputs.",
            "- Do not report heldout1 10/10 without heldout2 5/10.",
            "- Do not make a broad robustness claim.",
            "- Do not imply score-only calibration solves heldout2.",
            "- Do not claim heldout2 selector improvements generalize to heldout3.",
            "- Do not present heldout3 targeted repair as external validation.",
            "- Do not present heldout4 partial transfer or cross-heldout aggregate results as robustness.",
            "- Do not use GIFs or figure panels as standalone evidence without the linked tables, source data, and QC records.",
            "",
        ]
    )


def write_package(root):
    manuscript = root / "manuscript"
    figures = manuscript / "figures"
    manuscript.mkdir(exist_ok=True)
    figures.mkdir(exist_ok=True)

    main_md = manuscript / "main.md"
    main_md.write_text(build_main(root), encoding="utf-8")

    readme = manuscript / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Manuscript Draft Package",
                "",
                "This directory contains a conservative local manuscript draft generated from the evidence package.",
                "",
                "Files:",
                "",
                "- `main.md`: evidence-linked manuscript draft.",
                "- `references.bib`: starter bibliography for cited methods and statistical intervals.",
                "- `figures/README.md`: figure source mapping.",
                "- `../materials/FIGURE_LEGENDS.md`: manuscript-facing figure legends.",
                "",
                "Status:",
                "",
                "- This is not a final journal submission package.",
                "- Claims must remain consistent with `../materials/CLAIM_EVIDENCE_MATRIX.md`.",
                "- Final external archiving and DOI assignment remain incomplete.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    refs = manuscript / "references.bib"
    refs.write_text(
        "\n".join(
            [
                "@misc{brockman2016openai,",
                "  title = {OpenAI Gym},",
                "  author = {Brockman, Greg and Cheung, Vicki and Pettersson, Ludwig and Schneider, Jonas and Schulman, John and Tang, Jie and Zaremba, Wojciech},",
                "  year = {2016},",
                "  eprint = {1606.01540},",
                "  archivePrefix = {arXiv},",
                "  primaryClass = {cs.LG}",
                "}",
                "",
                "@inproceedings{ross2011reduction,",
                "  title = {A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning},",
                "  author = {Ross, St{\\'e}phane and Gordon, Geoffrey J. and Bagnell, J. Andrew},",
                "  booktitle = {Proceedings of the Fourteenth International Conference on Artificial Intelligence and Statistics},",
                "  pages = {627--635},",
                "  year = {2011},",
                "  volume = {15},",
                "  series = {Proceedings of Machine Learning Research},",
                "  publisher = {PMLR}",
                "}",
                "",
                "@article{battaglia2018relational,",
                "  title = {Relational Inductive Biases, Deep Learning, and Graph Networks},",
                "  author = {Battaglia, Peter W. and Hamrick, Jessica B. and Bapst, Victor and Sanchez-Gonzalez, Alvaro and Zambaldi, Vinicius and Malinowski, Mateusz and Tacchetti, Andrea and Raposo, David and Santoro, Adam and Faulkner, Ryan and others},",
                "  journal = {arXiv preprint arXiv:1806.01261},",
                "  year = {2018}",
                "}",
                "",
                "@article{betz2022survey,",
                "  title = {Autonomous Vehicles on the Edge: A Survey on Autonomous Vehicle Racing},",
                "  author = {Betz, Johannes and Zheng, Hongrui and Liniger, Alexander and Rosolia, Ugo and Karle, Phillip and Behl, Madhur and Krovi, Venkat and Mangharam, Rahul},",
                "  journal = {IEEE Open Journal of Intelligent Transportation Systems},",
                "  volume = {3},",
                "  pages = {458--488},",
                "  year = {2022},",
                "  doi = {10.1109/OJITS.2022.3181510}",
                "}",
                "",
                "@inproceedings{okelly2020f1tenth,",
                "  title = {F1TENTH: An Open-source Evaluation Environment for Continuous Control and Reinforcement Learning},",
                "  author = {O'Kelly, Matthew and Zheng, Hongrui and Karthik, Dhruv and Mangharam, Rahul},",
                "  booktitle = {Proceedings of the NeurIPS 2019 Competition and Demonstration Track},",
                "  pages = {77--89},",
                "  year = {2020},",
                "  volume = {123},",
                "  series = {Proceedings of Machine Learning Research},",
                "  publisher = {PMLR}",
                "}",
                "",
                "@article{liniger2015optimization,",
                "  title = {Optimization-Based Autonomous Racing of 1:43 Scale RC Cars},",
                "  author = {Liniger, Alexander and Domahidi, Alexander and Morari, Manfred},",
                "  journal = {Optimal Control Applications and Methods},",
                "  volume = {36},",
                "  number = {5},",
                "  pages = {628--647},",
                "  year = {2015},",
                "  doi = {10.1002/oca.2123}",
                "}",
                "",
                "@inproceedings{song2021autonomous,",
                "  title = {Autonomous Overtaking in Gran Turismo Sport Using Curriculum Reinforcement Learning},",
                "  author = {Song, Yunlong and Lin, HaoChih and Kaufmann, Elia and Durr, Peter and Scaramuzza, Davide},",
                "  booktitle = {2021 IEEE International Conference on Robotics and Automation},",
                "  pages = {9403--9409},",
                "  year = {2021},",
                "  organization = {IEEE},",
                "  doi = {10.1109/ICRA48506.2021.9561049}",
                "}",
                "",
                "@article{wurman2022outracing,",
                "  title = {Outracing Champion Gran Turismo Drivers with Deep Reinforcement Learning},",
                "  author = {Wurman, Peter R. and Barrett, Samuel and Kawamoto, Kenta and MacGlashan, James and Subramanian, Kaushik and Walsh, Thomas J. and Capobianco, Roberto and Devlic, Alisa and Eckert, Franziska and Fuchs, Florian and others},",
                "  journal = {Nature},",
                "  volume = {602},",
                "  pages = {223--228},",
                "  year = {2022},",
                "  doi = {10.1038/s41586-021-04357-7}",
                "}",
                "",
                "@article{wilson1927probable,",
                "  title = {Probable Inference, the Law of Succession, and Statistical Inference},",
                "  author = {Wilson, Edwin B.},",
                "  journal = {Journal of the American Statistical Association},",
                "  volume = {22},",
                "  number = {158},",
                "  pages = {209--212},",
                "  year = {1927},",
                "  doi = {10.1080/01621459.1927.10502953}",
                "}",
                "",
                "% Evidence-linked starter bibliography. Authors should still adapt citation breadth and formatting to the selected journal.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (figures / "README.md").write_text(
        "\n".join(
            [
                "# Figure Mapping",
                "",
                "- Figure 1 source: `../../figures/figure_1_multicar_overtake_results.*`",
                "- Figure 1 source data: `../../figures/figure_1_source_data.csv`",
                "- Figure 2 source: `../../figures/figure_2_portfolio_selector_summary.*`",
                "- Figure 2 source data: `../../figures/figure_2_source_data.csv`",
                "- Figure 3 source: `../../figures/figure_3_cross_heldout_validation.*`",
                "- Figure 3 source data: `../../figures/figure_3_source_data.csv`",
                "- Figure legends: `../../materials/FIGURE_LEGENDS.md`",
                "- Supplementary failure atlas: `../../tables/heldout2_failure_atlas.md`",
                "- Heldout4 failure atlas: `../../tables/heldout4_failure_atlas.md`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    manifest = {
        "status": "draft_not_final_submission",
        "files": [
            "manuscript/README.md",
            "manuscript/main.md",
            "manuscript/references.bib",
            "manuscript/figures/README.md",
        ],
        "claim_guardrail": "Use materials/CLAIM_EVIDENCE_MATRIX.md before promoting this draft to a final manuscript.",
    }
    out_manifest = manuscript / "manuscript_manifest.json"
    out_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Export a conservative local manuscript draft package.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    manifest = write_package(root)
    print(json.dumps({"manifest": str(root / "manuscript" / "manuscript_manifest.json"), **manifest}, indent=2))


if __name__ == "__main__":
    main()
