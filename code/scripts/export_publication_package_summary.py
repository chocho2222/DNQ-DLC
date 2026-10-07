#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pct(count, n):
    return f"{count}/{n}"


def load_locked_results(root, manifest, full):
    key_results = manifest.get("key_results")
    if key_results and "locked_single_methods" in key_results:
        return key_results["locked_single_methods"]

    archive_readme = root / "materials" / "ARCHIVE_README.json"
    if archive_readme.exists():
        archive = load_json(archive_readme)
        if "key_results" in archive:
            return {
                "overtake_base_only": archive["key_results"]["locked_overtake_baseline"],
                "graph_adaptive_shield": archive["key_results"]["locked_graph_adaptive"],
                "graph_soft_shield": archive["key_results"].get("locked_graph_soft_shield", archive["key_results"]["locked_graph_adaptive"]),
            }

    method_summary = {item["method"]: item for item in full["method_summaries"]}
    return {
        "overtake_base_only": {
            "pass_count": method_summary["main:overtake_base_only"]["pass_count"],
            "n": method_summary["main:overtake_base_only"]["n"],
        },
        "graph_adaptive_shield": {
            "pass_count": method_summary["adaptive:graph_adaptive_shield"]["pass_count"],
            "n": method_summary["adaptive:graph_adaptive_shield"]["n"],
        },
        "graph_soft_shield": {
            "pass_count": method_summary["adaptive:graph_soft_shield"]["pass_count"],
            "n": method_summary["adaptive:graph_soft_shield"]["n"],
        },
    }


def load_scope(root, manifest):
    scope = manifest.get("scope")
    if scope:
        return scope
    archive_readme = root / "materials" / "ARCHIVE_README.json"
    if archive_readme.exists():
        archive = load_json(archive_readme)
        if "scope" in archive:
            return {
                "task": archive["scope"].get("task", "strict non-VLM multi-car full-lap overtaking"),
                "excluded": archive["scope"].get("excluded", "VLM components intentionally excluded"),
                "validator": (
                    "target lap completion, target rank 1, first-ahead event, target grass threshold, "
                    "and global traffic quality"
                ),
            }
    return {
        "task": "strict non-VLM multi-car full-lap overtaking",
        "excluded": "VLM components intentionally excluded",
        "validator": "target lap completion, target rank 1, first-ahead event, target grass threshold, and global traffic quality",
    }


def load_seed_sets(root, manifest):
    seed_sets = manifest.get("seed_sets")
    if seed_sets:
        return seed_sets
    registry = root / "materials" / "EXPERIMENT_REGISTRY.json"
    if registry.exists():
        data = load_json(registry)
        if "seed_sets" in data:
            return data["seed_sets"]
    plan = root / "materials" / "STATISTICAL_ANALYSIS_PLAN.json"
    if plan.exists():
        data = load_json(plan)
        if "seed_sets" in data:
            return data["seed_sets"]
    return {
        "locked": [],
        "heldout1": [],
        "heldout2": [],
        "heldout3": [],
        "heldout4": [],
        "hard_smoke": [],
    }


def normalize_items(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value)]


def checklist_row(section, item_id, status, text, category, evidence, action, boundary, requires_new_experiment):
    return {
        "section": section,
        "id": item_id,
        "status": status,
        "text": text,
        "category": category,
        "evidence": evidence,
        "action": action,
        "claim_boundary": boundary,
        "requires_new_experiment": requires_new_experiment,
    }


def build_summary(root):
    manifest = load_json(root / "manifest.json")
    full = load_json(root / "tables" / "full_statistical_report.json")
    main_results = load_json(root / "tables" / "main_results.json")
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
    cross_stats = load_json(root / "tables" / "cross_heldout_statistical_supplement.json")
    audit = load_json(root / "tables" / "reproducibility_audit.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    claim_qa = load_json(root / "materials" / "MANUSCRIPT_CLAIM_QA.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    data_dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")

    method_summary = {item["method"]: item for item in full["method_summaries"]}
    h1 = heldout["sets"]["heldout1"]["selector"]
    h2 = heldout["sets"]["heldout2"]["selector"]
    cal_h2 = calibration["test_heldout2"]
    locked = load_locked_results(root, manifest, full)

    graph_bc_pass_rate = main_results.get("graph_bc_pass_rate")
    dlc_pass_rate = main_results.get("dlc_pass_rate")

    return {
        "root": str(root),
        "title": manifest["title"],
        "scope": load_scope(root, manifest),
        "seed_sets": load_seed_sets(root, manifest),
        "baseline_archive": {
            "status": "saved",
            "methods": normalize_items(manifest["components"]["baselines"]),
            "locked_overtake_base_only": locked["overtake_base_only"],
            "locked_graph_adaptive_shield": locked["graph_adaptive_shield"],
            "locked_graph_soft_shield": locked["graph_soft_shield"],
        },
        "innovation_stack": normalize_items(manifest["components"]["innovation"]),
        "comparison_algorithms": manifest["components"].get("comparison", ""),
        "main_results": {
            "locked_rule_overtake": pct(
                method_summary["main:overtake_base_only"]["pass_count"],
                method_summary["main:overtake_base_only"]["n"],
            ),
            "locked_graph_adaptive": pct(
                method_summary["adaptive:graph_adaptive_shield"]["pass_count"],
                method_summary["adaptive:graph_adaptive_shield"]["n"],
            ),
            "heldout1_selector": pct(h1["pass_count"], h1["n"]),
            "heldout1_oracle": pct(h1["oracle_pass_count"], h1["n"]),
            "heldout2_selector": pct(h2["pass_count"], h2["n"]),
            "heldout2_oracle": pct(h2["oracle_pass_count"], h2["n"]),
            "heldout2_calibrated_selector": pct(cal_h2["pass_count"], cal_h2["n"]),
            "heldout2_best_heldout1_perfect_distilled_selector": pct(
                selector_distillation["best_train_perfect"]["heldout2_pass_count"],
                h2["n"],
            ),
            "heldout1_perfect_distillation_configs": selector_distillation["grid"]["heldout1_perfect_configs"],
            "heldout2_expanded_candidate_oracle": pct(
                candidate_expansion["expanded_oracle"]["pass_count"],
                candidate_expansion["expanded_oracle"]["n"],
            ),
            "heldout1_expanded_selector": pct(
                expanded_selector["summaries"]["heldout1_expanded"]["pass_count"],
                expanded_selector["summaries"]["heldout1_expanded"]["n"],
            ),
            "heldout2_expanded_selector": pct(
                expanded_selector["summaries"]["heldout2_expanded"]["pass_count"],
                expanded_selector["summaries"]["heldout2_expanded"]["n"],
            ),
            "heldout2_expanded_selector_misses": expanded_selector["summaries"]["heldout2_expanded"]["selector_miss_seeds"],
            "expanded_selector_best_distilled_heldout2": pct(
                expanded_distillation["best_train_perfect"]["heldout2_pass_count"],
                expanded_selector["summaries"]["heldout2_expanded"]["n"],
            ),
            "expanded_selector_heldout1_perfect_configs": expanded_distillation["grid"]["heldout1_perfect_configs"],
            "learned_selector_h1": pct(
                learned_selector["variants"][learned_selector["primary_variant"]]["train"]["pass_count"],
                learned_selector["variants"][learned_selector["primary_variant"]]["train"]["n"],
            ),
            "learned_selector_h2": pct(
                learned_selector["variants"][learned_selector["primary_variant"]]["test"]["pass_count"],
                learned_selector["variants"][learned_selector["primary_variant"]]["test"]["n"],
            ),
            "learned_selector_h3": pct(
                learned_selector["variants"][learned_selector["primary_variant"]]["external_heldout3"]["pass_count"],
                learned_selector["variants"][learned_selector["primary_variant"]]["external_heldout3"]["n"],
            ),
            "heldout3_candidate_oracle": pct(heldout3["oracle"]["pass_count"], heldout3["oracle"]["n"]),
            "heldout3_candidate_gap_seeds": heldout3["oracle"]["candidate_gap_seeds"],
            "heldout3_expanded_selector": pct(
                heldout3["expanded_selector"]["pass_count"],
                heldout3["expanded_selector"]["n"],
            ),
            "heldout3_expanded_selector_failed_seeds": heldout3["expanded_selector"]["failed_seeds"],
            "heldout3_learned_selector": pct(
                heldout3["learned_selector_primary"]["pass_count"],
                heldout3["learned_selector_primary"]["n"],
            ),
            "heldout3_targeted_expanded_oracle": pct(
                heldout3_expansion["expanded_oracle"]["pass_count"],
                heldout3_expansion["expanded_oracle"]["n"],
            ),
            "heldout3_targeted_newly_covered": heldout3_expansion["expanded_oracle"]["newly_covered_seeds"],
            "heldout3_targeted_remaining_gaps": heldout3_expansion["expanded_oracle"]["remaining_candidate_gap_seeds"],
            "heldout4_selector": pct(heldout4["selector"]["pass_count"], heldout4["selector"]["n"]),
            "heldout4_oracle": pct(heldout4["oracle"]["pass_count"], heldout4["oracle"]["n"]),
            "heldout4_selector_misses": heldout4["selector"]["selector_miss_seeds"],
            "heldout4_candidate_gaps": heldout4["oracle"]["candidate_gap_seeds"],
            "cross_heldout_selector": pct(
                cross_heldout["aggregate_expanded_or_later"]["selector_pass_count"],
                cross_heldout["aggregate_expanded_or_later"]["n"],
            ),
            "cross_heldout_oracle": pct(
                cross_heldout["aggregate_expanded_or_later"]["oracle_pass_count"],
                cross_heldout["aggregate_expanded_or_later"]["n"],
            ),
            "cross_heldout_selector_oracle_gap": cross_heldout["aggregate_expanded_or_later"]["selector_oracle_gap"],
            "cross_heldout_selector_ci95": [
                cross_stats["aggregate_expanded_or_later"]["selector_ci95_low"],
                cross_stats["aggregate_expanded_or_later"]["selector_ci95_high"],
            ],
            "cross_heldout_oracle_ci95": [
                cross_stats["aggregate_expanded_or_later"]["oracle_ci95_low"],
                cross_stats["aggregate_expanded_or_later"]["oracle_ci95_high"],
            ],
            "heldout2_newly_covered_candidate_seeds": candidate_expansion["expanded_oracle"]["newly_covered_seeds"],
            "heldout2_remaining_candidate_gap_seeds": candidate_expansion["expanded_oracle"]["remaining_candidate_gap_seeds"],
            "heldout2_candidate_gaps": cal_h2["candidate_gap_count"],
            "heldout2_selector_misses": cal_h2["selector_miss_count"],
            "graph_bc_pass_rate": "NA" if graph_bc_pass_rate is None else f"{graph_bc_pass_rate:.3f}",
            "dlc_pass_rate": "NA" if dlc_pass_rate is None else f"{dlc_pass_rate:.3f}",
        },
        "top_journal_readiness": build_top_journal_readiness(),
        "artifact_status": {
            "artifact_provenance_complete": provenance["complete_count"],
            "artifact_provenance_total": len(provenance["artifacts"]),
            "reproducibility_missing_or_weak": len(audit["missing_or_weak_items"]),
            "manuscript_claim_qa_status": claim_qa["summary"]["status"],
            "manuscript_claim_qa_blockers": claim_qa["summary"]["blockers"],
            "manuscript_claim_qa_warnings": claim_qa["summary"]["warnings"],
            "publication_package_verification_status": verification["summary"]["status"],
            "publication_package_verification_failed_gates": verification["summary"]["failed_gates"],
            "data_dictionary_complete": data_dictionary["summary"]["complete"],
            "data_dictionary_field_count": data_dictionary["summary"]["field_count"],
        },
    }


def build_top_journal_readiness():
    ready = [
        checklist_row("complete", "TJ01_locked_baselines", "complete", "Locked baselines are preserved for later comparison.", "baseline_integrity", "manifest.json; tables/full_statistical_report.md", "Keep baseline artifacts frozen for future comparisons.", "Do not replace negative baseline comparisons with only improved methods.", False),
        checklist_row("complete", "TJ02_strict_full_lap", "complete", "Strict full-lap multi-car validation is used rather than short-horizon visual demos.", "endpoint_validity", "materials/METHODS.md; materials/STUDY_PROTOCOL_AND_DEVIATIONS.md", "Preserve strict endpoint definitions in any new experiment.", "GIFs remain qualitative illustrations only.", False),
        checklist_row("complete", "TJ03_figure_source_data", "complete", "Figures are exported as PNG, SVG, PDF, and TIFF with source data.", "figure_reproducibility", "materials/FIGURE_SOURCE_DATA_AUDIT.md; materials/FIGURE_TECHNICAL_QC.md", "Rerun figure QC after journal-specific resizing.", "Figure technical QC does not add scientific evidence.", False),
        checklist_row("complete", "TJ04_package_together", "complete", "Machine-readable tables, Markdown summaries, logs, scripts, models, and GIF evidence are stored together.", "artifact_package", "materials/RELEASE_ARCHIVE_MANIFEST.md; tables/artifact_provenance.md", "Keep release manifest synchronized after edits.", "Local package readiness is not a public DOI/accession.", False),
        checklist_row("complete", "TJ05_claim_matrix", "complete", "Claim wording is constrained by a claim-to-evidence matrix.", "claim_control", "materials/CLAIM_EVIDENCE_MATRIX.md", "Use the matrix before editing manuscript or portal copy.", "Do not promote oracle rows to online selector outputs.", False),
        checklist_row("complete", "TJ06_claim_qa", "complete", "Manuscript-facing text has an automated overclaim QA gate with zero current blockers.", "claim_control", "materials/MANUSCRIPT_CLAIM_QA.md", "Rerun claim QA after final author edits.", "QA pass does not certify author-owned metadata.", False),
        checklist_row("complete", "TJ07_selector_distillation_negative", "complete", "Selector distillation diagnostics retain a negative heldout1-to-heldout2 result.", "negative_result", "tables/selector_distillation_report.md", "Keep the negative result visible in Results and limitations.", "Do not imply score-only calibration solves heldout2.", False),
        checklist_row("complete", "TJ08_heldout2_candidate_expansion", "complete", "A candidate-expansion diagnostic raises the heldout2 oracle from 7/10 to a 10/10 oracle result while preserving the selector/oracle boundary.", "candidate_coverage", "tables/heldout2_candidate_expansion.md", "Report as candidate coverage, not online selector performance.", "Oracle rows are diagnostic upper bounds.", False),
        checklist_row("complete", "TJ09_expanded_selector_boundary", "complete", "The expanded online selector improves heldout2 from 5/10 to 7/10 while preserving heldout1 at 10/10; this must still be read with heldout3 and heldout4 failures.", "selector_validation", "tables/expanded_selector_generalization.md", "Pair heldout1/heldout2 reporting with heldout3/heldout4 boundaries.", "Do not claim broad robustness.", False),
        checklist_row("complete", "TJ10_expanded_distillation_negative", "complete", "Expanded selector distillation preserves a negative result: heldout1-perfect scalar retuning remains capped at 7/10 on heldout2.", "negative_result", "tables/expanded_selector_distillation_report.md", "Use as evidence that cheap scalar retuning is insufficient.", "Do not hide negative calibration outcomes.", False),
        checklist_row("complete", "TJ11_learned_selector_diagnostic", "complete", "A feature-only learned selector reaches 8/10 on heldout2 as an exploratory diagnostic, but it reduces heldout1 to 9/10.", "selector_diagnostic", "tables/learned_selector_report.md", "Keep exploratory status explicit.", "Do not present as accepted replacement selector.", False),
        checklist_row("complete", "TJ12_heldout3_negative", "complete", "Heldout3 is retained as negative external validation: candidate oracle 8/10, expanded selector 4/10, learned selector 4/10.", "external_validation", "tables/heldout3_external_validation.md", "Preserve this as a generalization boundary.", "Do not retune on heldout3 and call it external validation.", False),
        checklist_row("complete", "TJ13_heldout3_targeted_repair_boundary", "complete", "Heldout3-targeted repair plus seed157 traffic-aware ablation raises targeted candidate oracle coverage to a 10/10 oracle result, but this is not external validation.", "targeted_diagnostic", "tables/heldout3_candidate_expansion.md", "Use only as diagnostic reuse.", "Do not merge targeted repair with external-validation claims.", False),
        checklist_row("complete", "TJ14_heldout4_partial_transfer", "complete", "Heldout4 is retained as post-repair external validation with partial transfer: selector 6/10 against an 8/10 oracle.", "external_validation", "tables/heldout4_external_validation.md", "Report partial transfer and remaining failures.", "Do not call heldout4 solved generalization.", False),
        checklist_row("complete", "TJ15_cross_heldout_synthesis", "complete", "Cross-heldout synthesis separates selector misses from candidate-policy gaps and keeps oracle results as diagnostic upper bounds.", "synthesis", "tables/cross_heldout_validation_synthesis.md", "Use synthesis descriptively.", "Do not average away heldout3/heldout4 failures.", False),
        checklist_row("complete", "TJ16_figure3_statistics", "complete", "Figure 3 now includes a source-data dictionary and cross-heldout statistical supplement with Wilson intervals and exact selector-oracle gap tests.", "statistics", "tables/cross_heldout_statistical_supplement.md; figures/figure_3_source_data_dictionary.csv", "Keep intervals and exact tests linked to figure claims.", "Small-N intervals remain descriptive.", False),
        checklist_row("complete", "TJ17_environment_audit", "complete", "Environment reproducibility audit records Python, conda, package, CUDA, GPU, and lockfile information.", "reproducibility", "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md", "Use GPU rerun readiness before expensive reruns.", "Hardware record does not guarantee deterministic reruns elsewhere.", False),
        checklist_row("complete", "TJ18_experiment_registry", "complete", "Experiment registry records experiment roles, seed sets, endpoints, evidence files, and claim boundaries.", "reproducibility", "materials/EXPERIMENT_REGISTRY.md", "Keep registry synchronized with new experiments.", "Registry is descriptive, not new empirical evidence.", False),
        checklist_row("complete", "TJ19_seed_ledger", "complete", "Seed outcome ledger exposes per-seed selector/oracle outcomes and separates selector misses from candidate gaps.", "source_data", "tables/seed_outcome_ledger.md", "Use ledger as source data for failure decomposition.", "Oracle choices use full rollout outcomes.", False),
        checklist_row("complete", "TJ20_data_dictionary", "complete", "Package-level data dictionary documents key machine-readable tables, fields, units, sources, and purposes.", "source_data", "materials/DATA_DICTIONARY.md", "Update after adding new tables.", "Dictionary completeness does not replace journal-specific formatting.", False),
        checklist_row("complete", "TJ21_publication_preflight", "complete", "Publication package verification provides a one-command preflight gate for provenance, audit, claim QA, registry, ledger, release, and forbidden-text checks.", "quality_gate", "materials/PUBLICATION_PACKAGE_VERIFICATION.md", "Run before every package handoff.", "Preflight pass is local package readiness, not journal acceptance.", False),
        checklist_row("complete", "TJ22_negative_results_visible", "complete", "Negative heldout2 and calibration results are explicitly retained.", "negative_result", "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md", "Keep negative controls in supplement/reviewer materials.", "Do not report only successful seeds or methods.", False),
    ]
    not_ready = [
        checklist_row("not_yet_complete", "NG01_broad_robustness", "not_yet_complete", "The current system lacks broad robustness evidence: expanded heldout2 selector performance is 7/10.", "scientific_gap", "tables/expanded_selector_generalization.md", "Run frozen larger-N validation before broad robustness language.", "Current evidence supports bounded simulator claims only.", True),
        checklist_row("not_yet_complete", "NG02_heldout3_weak", "not_yet_complete", "Heldout3 external validation is substantially weaker: expanded selector 4/10 and learned selector 4/10 against an 8/10 oracle.", "scientific_gap", "tables/heldout3_external_validation.md", "Improve selector/candidates and evaluate on fresh seeds.", "Heldout3 targeted repair is diagnostic reuse.", True),
        checklist_row("not_yet_complete", "NG03_heldout4_partial", "not_yet_complete", "Heldout4 after targeted repair is only partial transfer: selector 6/10 against an 8/10 oracle.", "scientific_gap", "tables/heldout4_external_validation.md", "Prioritize selector misses 197/211 and candidate gaps 233/239 before stronger claims.", "Partial transfer is not solved generalization.", True),
        checklist_row("not_yet_complete", "NG04_heldout2_selector_misses", "not_yet_complete", "The expanded heldout2 candidate oracle is a 10/10 oracle result, but the online selector still misses seeds 103, 109, and 113.", "selector_gap", "tables/expanded_selector_generalization.md; tables/heldout2_failure_atlas.md", "Train or audit a selector that reduces these misses without full-rollout labels.", "Do not use oracle labels at decision time.", True),
        checklist_row("not_yet_complete", "NG05_heldout3_targeted_selector", "not_yet_complete", "After targeted repair, heldout3 candidate coverage is closed only as a seed-targeted diagnostic; selector misses remain unresolved.", "selector_gap", "tables/heldout3_candidate_expansion.md", "Test the repaired candidate set with a frozen selector on fresh heldout4/heldout5-style seeds.", "Do not reclassify targeted repair as external validation.", True),
        checklist_row("not_yet_complete", "NG06_learned_selector_not_accepted", "not_yet_complete", "The exploratory learned selector is not an accepted replacement because it does not preserve the heldout1 10/10 result while improving heldout2.", "selector_gap", "tables/learned_selector_report.md", "Require no-regression on heldout1 plus improvement on heldout2 before acceptance.", "Exploratory selector results remain diagnostic.", True),
        checklist_row("not_yet_complete", "NG07_probe_cost", "not_yet_complete", "The online selector is expensive because it probes five candidates for 1200 steps.", "compute_gap", "tables/compute_cost_report.md; materials/GPU_RERUN_READINESS.md", "Distill probe behavior into cheaper track/traffic features and report cost.", "Cost reduction cannot change endpoint definitions.", True),
        checklist_row("not_yet_complete", "NG08_final_manuscript_source", "not_yet_complete", "A local manuscript draft is included, but a final submission PDF/source package is not included.", "author_or_journal_action", "manuscript/main.md; materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.md", "After target-journal choice, convert to official source/PDF and rerun audits.", "Do not invent target journal or author metadata.", False),
        checklist_row("not_yet_complete", "NG09_broader_stress_grid", "not_yet_complete", "Broader traffic-density, opponent-diversity, and larger-N evaluations are still needed for strong top-journal claims.", "scientific_gap", "materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.md", "Run preregistered stress grid with frozen selector and all failures reported.", "Future stress results are not implied by the current package.", True),
    ]
    next_experiments = [
        checklist_row("next_experiment", "NX01_selector_for_targeted_candidates", "planned", "Train and validate a selector that can use the targeted heldout3 candidates without losing heldout1 or heldout2.", "selector_development", "materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.md", "Freeze the selector before fresh heldout5 evaluation.", "Do not tune on heldout5 after seeing failures.", True),
        checklist_row("next_experiment", "NX02_larger_n_heldout", "planned", "Run larger-N held-out evaluation with confidence intervals after candidate and selector improvements.", "confirmatory_validation", "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md; materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.md", "Use n=75 minimum and n=100 preferred planning target when feasible.", "Do not strengthen robustness claims before these data exist.", True),
        checklist_row("next_experiment", "NX03_selector_distillation", "planned", "Distill the five-probe selector into cheaper track/traffic features for online simulator-loop selection.", "compute_gap", "tables/expanded_selector_distillation_report.md; materials/GPU_RERUN_READINESS.md", "Report heldout1 no-regression, heldout2 improvement, and compute cost.", "Do not use full-rollout labels as online features.", True),
    ]
    return {
        "ready": [row["text"] for row in ready],
        "not_ready": [row["text"] for row in not_ready],
        "next_experiments": [row["text"] for row in next_experiments],
        "rows": ready + not_ready + next_experiments,
        "summary": {
            "complete_count": len(ready),
            "not_yet_complete_count": len(not_ready),
            "planned_next_experiment_count": len(next_experiments),
            "requires_new_experiment_count": sum(row["requires_new_experiment"] for row in not_ready + next_experiments),
            "author_or_journal_action_count": sum(row["category"] == "author_or_journal_action" for row in not_ready),
        },
    }


def write_markdown(report, root):
    out = root / "materials" / "PUBLICATION_PACKAGE_SUMMARY.md"
    results = report["main_results"]
    readiness = report["top_journal_readiness"]
    artifacts = report["artifact_status"]

    lines = [
        "# Publication Package Summary",
        "",
        "This is the reviewer-facing entry point for the strict non-VLM multi-car full-lap overtaking package.",
        "",
        "## Scope",
        "",
        f"- Task: {report['scope']['task']}",
        f"- Excluded: {report['scope']['excluded']}",
        f"- Validator: {report['scope']['validator']}",
        "",
        "## Baselines Preserved",
        "",
        "- Saved baseline methods: " + ", ".join(report["baseline_archive"]["methods"]),
        f"- Locked rule overtake baseline: {results['locked_rule_overtake']}",
        f"- Locked graph-adaptive shield: {results['locked_graph_adaptive']}",
        "",
        "## Innovation Stack",
        "",
    ]
    lines.extend(f"- {item}" for item in report["innovation_stack"])
    if report["comparison_algorithms"]:
        lines.extend(
            [
                "",
                "## Comparison Algorithms",
                "",
                f"- {report['comparison_algorithms']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Main Experimental Results",
            "",
            "| evaluation | result | interpretation |",
            "|---|---:|---|",
            f"| locked overtake baseline | {results['locked_rule_overtake']} | strongest single locked controller |",
            f"| locked graph-adaptive shield | {results['locked_graph_adaptive']} | best learned/shielded single innovation on locked seeds |",
            f"| graph BC safety shield pass rate | {results['graph_bc_pass_rate']} | current graph-based comparison line |",
            f"| DLC/world-model pass rate | {results['dlc_pass_rate']} | telemetry-state world-model comparison line |",
            f"| heldout1 five-candidate selector | {results['heldout1_selector']} with heldout2 boundary | online simulator-loop selector matches oracle on one held-out batch, report with heldout2/heldout3/heldout4 boundaries |",
            f"| heldout1 oracle | {results['heldout1_oracle']} oracle with heldout2 boundary | diagnostic upper bound, not an online selector output, report with heldout2/heldout3/heldout4 boundaries |",
            f"| heldout2 five-candidate selector | {results['heldout2_selector']} | generalization stress test exposes failure boundary |",
            f"| heldout2 oracle | {results['heldout2_oracle']} | candidate pool itself is incomplete |",
            f"| heldout2 expanded candidate oracle | {results['heldout2_expanded_candidate_oracle']} | new candidates cover seeds {', '.join(str(seed) for seed in results['heldout2_newly_covered_candidate_seeds'])} |",
            f"| heldout1 expanded six-candidate selector | {results['heldout1_expanded_selector']} with heldout2 boundary | added candidate does not degrade the first held-out batch, report with later heldout3/heldout4 failures |",
            f"| heldout2 expanded six-candidate selector | {results['heldout2_expanded_selector']} | online simulator-loop selector improves but remains below the 10/10 oracle boundary |",
            f"| heldout1-perfect expanded selector distillation, heldout2 test | {results['expanded_selector_best_distilled_heldout2']} | {results['expanded_selector_heldout1_perfect_configs']} train-perfect scalar selectors do not improve heldout2 |",
            f"| exploratory feature-only learned selector | heldout1 {results['learned_selector_h1']}; heldout2 {results['learned_selector_h2']} | improves heldout2 but is not an accepted replacement because heldout1 drops |",
            f"| heldout3 expanded candidate oracle | {results['heldout3_candidate_oracle']} | external validation upper bound; candidate gaps remain on {', '.join(str(seed) for seed in results['heldout3_candidate_gap_seeds'])} |",
            f"| heldout3 expanded six-candidate selector | {results['heldout3_expanded_selector']} | negative external validation; heldout2 selector gains do not generalize |",
            f"| heldout3 learned selector | {results['heldout3_learned_selector']} | exploratory learned selector also fails to generalize externally |",
            f"| heldout3 targeted expanded candidate oracle | {results['heldout3_targeted_expanded_oracle']} oracle | targeted repair covers {', '.join(str(seed) for seed in results['heldout3_targeted_newly_covered'])}, not external validation |",
            f"| heldout4 post-repair external selector | {results['heldout4_selector']} | partial transfer after targeted repair; selector misses remain |",
            f"| heldout4 post-repair oracle | {results['heldout4_oracle']} | diagnostic upper bound; candidate gaps remain |",
            f"| cross-heldout expanded-or-later selector | {results['cross_heldout_selector']} | descriptive synthesis, not robustness |",
            f"| cross-heldout expanded-or-later oracle | {results['cross_heldout_oracle']} | diagnostic upper bound with a {results['cross_heldout_selector_oracle_gap']}-seed selector-oracle gap |",
            f"| cross-heldout selector Wilson 95% CI | [{results['cross_heldout_selector_ci95'][0]:.3f}, {results['cross_heldout_selector_ci95'][1]:.3f}] | descriptive uncertainty interval for Figure 3 |",
            f"| cross-heldout oracle Wilson 95% CI | [{results['cross_heldout_oracle_ci95'][0]:.3f}, {results['cross_heldout_oracle_ci95'][1]:.3f}] | diagnostic upper-bound uncertainty interval |",
            f"| calibrated heldout2 selector | {results['heldout2_calibrated_selector']} | score-only calibration is insufficient |",
            f"| heldout1-perfect distilled selector grid, heldout2 test | {results['heldout2_best_heldout1_perfect_distilled_selector']} | {results['heldout1_perfect_distillation_configs']} train-perfect scalar selectors do not improve heldout2 |",
            "",
            "## Failure Decomposition",
            "",
            f"- Heldout2 candidate-policy gaps: {results['heldout2_candidate_gaps']}",
            f"- Heldout2 selector misses: {results['heldout2_selector_misses']}",
            f"- Remaining heldout2 candidate-gap seeds after expansion: {results['heldout2_remaining_candidate_gap_seeds']}",
            f"- Remaining heldout2 expanded-selector miss seeds: {results['heldout2_expanded_selector_misses']}",
            f"- Heldout3 candidate-gap seeds: {results['heldout3_candidate_gap_seeds']}",
            f"- Heldout3 remaining candidate-gap seeds after targeted repair: {results['heldout3_targeted_remaining_gaps']}",
            f"- Heldout3 expanded-selector failed seeds: {results['heldout3_expanded_selector_failed_seeds']}",
            f"- Heldout4 selector-miss seeds: {results['heldout4_selector_misses']}",
            f"- Heldout4 candidate-gap seeds: {results['heldout4_candidate_gaps']}",
            f"- Cross-heldout expanded-or-later selector-oracle gap: {results['cross_heldout_selector_oracle_gap']} seeds",
            "",
            "## What Is Ready",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in readiness["ready"])
    lines.extend(["", "## What Is Not Yet Ready", ""])
    lines.extend(f"- {item}" for item in readiness["not_ready"])
    lines.extend(["", "## Next Experiments", ""])
    lines.extend(f"- {item}" for item in readiness["next_experiments"])
    lines.extend(
        [
            "",
            "## Artifact Integrity",
            "",
            f"- Artifact provenance: {artifacts['artifact_provenance_complete']}/{artifacts['artifact_provenance_total']}",
            f"- Reproducibility missing/weak items: {artifacts['reproducibility_missing_or_weak']}",
            f"- Manuscript claim QA: {artifacts['manuscript_claim_qa_status']} "
            f"({artifacts['manuscript_claim_qa_blockers']} blockers, "
            f"{artifacts['manuscript_claim_qa_warnings']} warnings)",
            f"- Publication package verification: {artifacts['publication_package_verification_status']} "
            f"({artifacts['publication_package_verification_failed_gates']} failed gates)",
            f"- Data dictionary: complete={artifacts['data_dictionary_complete']} "
            f"({artifacts['data_dictionary_field_count']} fields)",
            "",
            "## Primary Entry Points",
            "",
            "- `manifest.json`",
            "- `materials/CLAIM_EVIDENCE_MATRIX.md`",
            "- `materials/MANUSCRIPT_CLAIM_QA.md`",
            "- `materials/PUBLICATION_PACKAGE_VERIFICATION.md`",
            "- `materials/DATA_DICTIONARY.md`",
            "- `tables/selector_distillation_report.md`",
            "- `tables/main_results.md`",
            "- `tables/heldout2_candidate_expansion.md`",
            "- `tables/expanded_selector_generalization.md`",
            "- `tables/expanded_selector_distillation_report.md`",
            "- `tables/learned_selector_report.md`",
            "- `tables/heldout3_external_validation.md`",
            "- `tables/heldout3_candidate_expansion.md`",
            "- `tables/heldout4_external_validation.md`",
            "- `tables/heldout4_failure_atlas.md`",
            "- `tables/cross_heldout_validation_synthesis.md`",
            "- `tables/cross_heldout_statistical_supplement.md`",
            "- `tables/seed_outcome_ledger.md`",
            "- `figures/figure_3_cross_heldout_validation.*`",
            "- `figures/figure_3_source_data_dictionary.csv`",
            "- `materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md`",
            "- `materials/REPRODUCTION_GUIDE.md`",
            "- `materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md`",
            "- `materials/EXPERIMENT_REGISTRY.md`",
            "- `tables/heldout_generalization.md`",
            "- `tables/selector_calibration.md`",
            "- `tables/artifact_provenance.md`",
            "- `tables/reproducibility_audit.md`",
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_checklist(report, root):
    out = root / "materials" / "TOP_JOURNAL_READINESS_CHECKLIST.md"
    readiness = report["top_journal_readiness"]
    lines = [
        "# Top-Journal Readiness Checklist",
        "",
        "## Complete",
        "",
    ]
    lines.extend(f"- [x] {item}" for item in readiness["ready"])
    lines.extend(["", "## Not Yet Complete", ""])
    lines.extend(f"- [ ] {item}" for item in readiness["not_ready"])
    lines.extend(["", "## Actionable Next Experiments", ""])
    lines.extend(f"- [ ] {item}" for item in readiness["next_experiments"])
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_checklist_json_csv(report, root):
    readiness = report["top_journal_readiness"]
    json_out = root / "materials" / "TOP_JOURNAL_READINESS_CHECKLIST.json"
    csv_out = root / "materials" / "TOP_JOURNAL_READINESS_CHECKLIST.csv"
    payload = {
        "root": report["root"],
        "title": "Top-Journal Readiness Checklist",
        "purpose": (
            "Machine-readable companion to the Markdown checklist. Rows separate completed local evidence, "
            "remaining scientific gaps, author/journal actions, and planned confirmatory experiments."
        ),
        "summary": readiness["summary"],
        "rows": readiness["rows"],
    }
    json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    fields = [
        "section",
        "id",
        "status",
        "text",
        "category",
        "evidence",
        "action",
        "claim_boundary",
        "requires_new_experiment",
    ]
    with csv_out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(readiness["rows"])
    return json_out, csv_out


def main():
    parser = argparse.ArgumentParser(description="Export publication-facing package summary and readiness checklist.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_summary(root)
    json_path = root / "materials" / "PUBLICATION_PACKAGE_SUMMARY.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_path = write_markdown(report, root)
    checklist_path = write_checklist(report, root)
    checklist_json, checklist_csv = write_checklist_json_csv(report, root)
    print(
        json.dumps(
            {
                "json": str(json_path),
                "summary": str(summary_path),
                "checklist": str(checklist_path),
                "checklist_json": str(checklist_json),
                "checklist_csv": str(checklist_csv),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
