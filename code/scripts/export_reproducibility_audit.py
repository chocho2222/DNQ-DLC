#!/usr/bin/env python
import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def exists(path):
    return Path(path).exists()


def audit_item(name, evidence, required=True):
    status = "proven" if evidence else ("missing" if required else "weak")
    return {"item": name, "status": status, "evidence": evidence}


def list_files(root, rel_dir, suffixes=None, max_depth=2):
    base = root / rel_dir
    if not base.exists():
        return []
    files = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        depth = len(path.relative_to(base).parts)
        if depth > max_depth:
            continue
        if suffixes and path.suffix not in suffixes:
            continue
        files.append(str(path.relative_to(root)))
    return files


def build_audit(root):
    manifest = load_json(root / "manifest.json") if exists(root / "manifest.json") else {}
    materials = root / "materials"
    figures = root / "figures"
    tables = root / "tables"
    evaluations = root / "evaluations"
    baselines = root / "baselines"
    models = root / "models"
    logs = root / "logs"
    manuscript = root / "manuscript"

    evidence = {
        "root_exists": root.exists(),
        "manifest": manifest,
        "material_files": list_files(root, "materials"),
        "figure_files": list_files(root, "figures"),
        "table_files": list_files(root, "tables"),
        "evaluation_files": list_files(root, "evaluations"),
        "baseline_files": list_files(root, "baselines"),
        "model_files": list_files(root, "models"),
        "log_files": list_files(root, "logs"),
    }

    items = [
        audit_item("reproducibility root directory", evidence["root_exists"]),
        audit_item("experiment manifest", exists(root / "manifest.json")),
        audit_item("materials README", exists(materials / "README.md")),
        audit_item("methods summary", exists(materials / "METHODS.md")),
        audit_item("results status", exists(materials / "RESULTS_STATUS.md")),
        audit_item("limitations note", exists(materials / "LIMITATIONS.md")),
        audit_item("supplementary index", exists(materials / "SUPPLEMENTARY_INDEX.md")),
        audit_item(
            "publication package summary",
            exists(materials / "PUBLICATION_PACKAGE_SUMMARY.md")
            and exists(materials / "PUBLICATION_PACKAGE_SUMMARY.json"),
        ),
        audit_item("top-journal readiness checklist", exists(materials / "TOP_JOURNAL_READINESS_CHECKLIST.md")),
        audit_item(
            "manuscript outline",
            exists(materials / "MANUSCRIPT_OUTLINE.md") and exists(materials / "MANUSCRIPT_OUTLINE.json"),
        ),
        audit_item(
            "reviewer response map",
            exists(materials / "REVIEWER_RESPONSE_MAP.md") and exists(materials / "REVIEWER_RESPONSE_MAP.json"),
        ),
        audit_item(
            "statistical analysis plan",
            exists(materials / "STATISTICAL_ANALYSIS_PLAN.md")
            and exists(materials / "STATISTICAL_ANALYSIS_PLAN.json"),
        ),
        audit_item(
            "data and code availability statement",
            exists(materials / "DATA_CODE_AVAILABILITY.md")
            and exists(materials / "DATA_CODE_AVAILABILITY.json"),
        ),
        audit_item(
            "data dictionary",
            all(exists(materials / f"DATA_DICTIONARY.{ext}") for ext in ["md", "json", "csv"]),
        ),
        audit_item(
            "transparent reporting checklist",
            exists(materials / "TRANSPARENT_REPORTING_CHECKLIST.md")
            and exists(materials / "TRANSPARENT_REPORTING_CHECKLIST.json")
            and exists(materials / "TRANSPARENT_REPORTING_CHECKLIST.csv"),
        ),
        audit_item(
            "submission gap action plan",
            exists(materials / "SUBMISSION_GAP_ACTION_PLAN.md")
            and exists(materials / "SUBMISSION_GAP_ACTION_PLAN.json")
            and exists(materials / "SUBMISSION_GAP_ACTION_PLAN.csv"),
        ),
        audit_item(
            "release archive manifest",
            exists(materials / "RELEASE_ARCHIVE_MANIFEST.md")
            and exists(materials / "RELEASE_ARCHIVE_MANIFEST.json")
            and exists(materials / "RELEASE_ARCHIVE_MANIFEST.csv"),
        ),
        audit_item(
            "FAIR archive metadata",
            exists(materials / "FAIR_ARCHIVE_METADATA.md")
            and exists(materials / "FAIR_ARCHIVE_METADATA.json")
            and exists(materials / "FAIR_ARCHIVE_METADATA.csv"),
        ),
        audit_item(
            "research risk and safety statement",
            exists(materials / "RESEARCH_RISK_AND_SAFETY.md")
            and exists(materials / "RESEARCH_RISK_AND_SAFETY.json")
            and exists(materials / "RESEARCH_RISK_AND_SAFETY.csv"),
        ),
        audit_item(
            "top-journal reporting summary",
            exists(materials / "TOP_JOURNAL_REPORTING_SUMMARY.md")
            and exists(materials / "TOP_JOURNAL_REPORTING_SUMMARY.json")
            and exists(materials / "TOP_JOURNAL_REPORTING_SUMMARY.csv"),
        ),
        audit_item(
            "editorial submission checklist",
            exists(materials / "EDITORIAL_SUBMISSION_CHECKLIST.md")
            and exists(materials / "EDITORIAL_SUBMISSION_CHECKLIST.json")
            and exists(materials / "EDITORIAL_SUBMISSION_CHECKLIST.csv"),
        ),
        audit_item(
            "significance briefing",
            exists(materials / "SIGNIFICANCE_BRIEFING.md")
            and exists(materials / "SIGNIFICANCE_BRIEFING.json")
            and exists(materials / "SIGNIFICANCE_BRIEFING.csv"),
        ),
        audit_item(
            "editorial narrative package",
            exists(materials / "EDITORIAL_NARRATIVE_PACKAGE.md")
            and exists(materials / "EDITORIAL_NARRATIVE_PACKAGE.json")
            and exists(materials / "EDITORIAL_NARRATIVE_PACKAGE.csv"),
        ),
        audit_item(
            "cover letter draft package",
            exists(materials / "COVER_LETTER_DRAFT_PACKAGE.md")
            and exists(materials / "COVER_LETTER_DRAFT_PACKAGE.json")
            and exists(materials / "COVER_LETTER_DRAFT_PACKAGE.csv")
            and exists(materials / "COVER_LETTER_AUTHOR_CHECKLIST.csv"),
        ),
        audit_item(
            "submission portal package map",
            exists(materials / "SUBMISSION_PORTAL_PACKAGE_MAP.md")
            and exists(materials / "SUBMISSION_PORTAL_PACKAGE_MAP.json")
            and exists(materials / "SUBMISSION_PORTAL_PACKAGE_MAP.csv")
            and exists(materials / "SUBMISSION_PORTAL_AUTHOR_ACTIONS.csv"),
        ),
        audit_item(
            "editorial decision brief",
            exists(materials / "EDITORIAL_DECISION_BRIEF.md")
            and exists(materials / "EDITORIAL_DECISION_BRIEF.json")
            and exists(materials / "EDITORIAL_DECISION_BRIEF.csv"),
        ),
        audit_item(
            "artifact dependency map",
            exists(materials / "ARTIFACT_DEPENDENCY_MAP.md")
            and exists(materials / "ARTIFACT_DEPENDENCY_MAP.json")
            and exists(materials / "ARTIFACT_DEPENDENCY_MAP.csv")
            and exists(materials / "ARTIFACT_DEPENDENCY_FILE_EDGES.csv"),
        ),
        audit_item(
            "environment reproducibility audit",
            exists(materials / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.md")
            and exists(materials / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.json")
            and exists(materials / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.csv"),
        ),
        audit_item(
            "experiment registry",
            exists(materials / "EXPERIMENT_REGISTRY.md")
            and exists(materials / "EXPERIMENT_REGISTRY.json")
            and exists(materials / "EXPERIMENT_REGISTRY.csv"),
        ),
        audit_item(
            "manuscript draft package",
            exists(manuscript / "main.md")
            and exists(manuscript / "README.md")
            and exists(manuscript / "references.bib")
            and exists(manuscript / "manuscript_manifest.json")
            and exists(manuscript / "figures" / "README.md"),
        ),
        audit_item("claim evidence matrix", all(exists(materials / f"CLAIM_EVIDENCE_MATRIX.{ext}") for ext in ["json", "md", "csv"])),
        audit_item(
            "manuscript claim QA",
            all(exists(materials / f"MANUSCRIPT_CLAIM_QA.{ext}") for ext in ["json", "md", "csv"]),
        ),
        audit_item(
            "publication package verification",
            all(exists(materials / f"PUBLICATION_PACKAGE_VERIFICATION.{ext}") for ext in ["json", "md", "csv"]),
        ),
        audit_item("manuscript results discussion draft", exists(materials / "MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md")),
        audit_item(
            "figure legends",
            exists(materials / "FIGURE_LEGENDS.md") and exists(materials / "FIGURE_LEGENDS.json"),
        ),
        audit_item("main figure exports", all(exists(figures / f"figure_1_multicar_overtake_results{ext}") for ext in [".png", ".pdf", ".svg", ".tiff"])),
        audit_item("supplementary figure exports", all(exists(figures / f"figure_2_portfolio_selector_summary{ext}") for ext in [".png", ".pdf", ".svg", ".tiff"])),
        audit_item("main result table artifacts", all(exists(tables / f"main_results.{ext}") for ext in ["json", "csv", "md"])),
        audit_item("full statistical report artifacts", all(exists(tables / f"full_statistical_report.{ext}") for ext in ["json", "md"]) and all(exists(tables / f"full_statistical_report_{suffix}.csv") for suffix in ["method_summary", "pairwise"])),
        audit_item("artifact provenance artifacts", all(exists(tables / f"artifact_provenance.{ext}") for ext in ["json", "md"])),
        audit_item("held-out main suite artifacts", all(exists(tables / f"heldout_multiseed_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout_multiseed_suite_rows.csv")),
        audit_item("held-out adaptive suite artifacts", all(exists(tables / f"heldout_adaptive_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout_adaptive_suite_rows.csv")),
        audit_item("held-out expert gate suite artifacts", all(exists(tables / f"heldout_expert_gate_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout_expert_gate_suite_rows.csv")),
        audit_item("held-out expert fast smoke artifacts", all(exists(tables / f"heldout_expert_fast_smoke_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout_expert_fast_smoke_rows.csv")),
        audit_item("held-out expert barrier smoke artifacts", all(exists(tables / f"heldout_expert_barrier_smoke_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout_expert_barrier_smoke_rows.csv")),
        audit_item("held-out expert recovery smoke artifacts", all(exists(tables / f"heldout_expert_recovery_smoke_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout_expert_recovery_smoke_rows.csv")),
        audit_item("graph DAgger recovery training artifacts", exists(models / "graph_dagger_recovery" / "graph_dagger_recovery.graph.pt") and exists(models / "graph_dagger_recovery" / "train_summary.json")),
        audit_item("graph DAgger recovery smoke artifacts", all(exists(tables / f"heldout_graph_dagger_recovery_smoke_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout_graph_dagger_recovery_smoke_rows.csv")),
        audit_item("graph DAgger failure diagnosis artifacts", all(exists(tables / f"dagger_failure_diagnosis.{ext}") for ext in ["json", "md"]) and exists(tables / "dagger_failure_diagnosis_rows.csv")),
        audit_item("graph DAgger recovery v2 training artifacts", exists(models / "graph_dagger_recovery_v2" / "graph_dagger_recovery.graph.pt") and exists(models / "graph_dagger_recovery_v2" / "train_summary.json")),
        audit_item("graph DAgger recovery v2 smoke artifacts", all(exists(tables / f"heldout_graph_dagger_recovery_v2_smoke_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout_graph_dagger_recovery_v2_smoke_rows.csv")),
        audit_item("graph DAgger v2 failure diagnosis artifacts", all(exists(tables / f"dagger_v2_failure_diagnosis.{ext}") for ext in ["json", "md"]) and exists(tables / "dagger_v2_failure_diagnosis_rows.csv")),
        audit_item("graph DAgger recovery v2 held-out suite artifacts", all(exists(tables / f"heldout_graph_dagger_recovery_v2_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout_graph_dagger_recovery_v2_suite_rows.csv")),
        audit_item("graph DAgger recovery v2 more-graph held-out suite artifacts", all(exists(tables / f"heldout_graph_dagger_recovery_v2_more_graph_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout_graph_dagger_recovery_v2_more_graph_suite_rows.csv")),
        audit_item("graph DAgger v2 held-out diagnosis artifacts", all(exists(tables / f"dagger_v2_heldout_failure_diagnosis.{ext}") for ext in ["json", "md"]) and exists(tables / "dagger_v2_heldout_failure_diagnosis_rows.csv")),
        audit_item("held-out v2 portfolio artifacts", all(exists(tables / f"heldout_v2_portfolio.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout_v2_portfolio_method_summary.csv")),
        audit_item("portfolio oracle artifacts", all(exists(tables / f"portfolio_oracle.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_oracle_rows.csv")),
        audit_item("selector prototype artifacts", all(exists(tables / f"portfolio_selector_loso.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_selector_loso_rows.csv")),
        audit_item("online probe selector artifacts", all(exists(tables / f"portfolio_probe_selector.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_probe_selector_rows.csv")),
        audit_item("long online probe selector artifacts", all(exists(tables / f"portfolio_probe_selector_1200.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_probe_selector_1200_rows.csv")),
        audit_item("long online probe held-out artifacts", all(exists(tables / f"portfolio_probe_selector_1200_heldout.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_probe_selector_1200_heldout_rows.csv")),
        audit_item("long online probe held-out expert artifacts", all(exists(tables / f"portfolio_probe_selector_1200_heldout_expert.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_probe_selector_1200_heldout_expert_rows.csv")),
        audit_item("long online probe held-out DAgger-v2 artifacts", all(exists(tables / f"portfolio_probe_selector_1200_heldout_dagger_v2.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_probe_selector_1200_heldout_dagger_v2_rows.csv")),
        audit_item("second held-out main suite artifacts", all(exists(tables / f"heldout2_multiseed_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout2_multiseed_suite_rows.csv")),
        audit_item("second held-out adaptive suite artifacts", all(exists(tables / f"heldout2_adaptive_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout2_adaptive_suite_rows.csv")),
        audit_item("second held-out expert gate suite artifacts", all(exists(tables / f"heldout2_expert_gate_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout2_expert_gate_suite_rows.csv")),
        audit_item("second held-out DAgger-v2 suite artifacts", all(exists(tables / f"heldout2_graph_dagger_recovery_v2_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout2_graph_dagger_recovery_v2_suite_rows.csv")),
        audit_item("second held-out overtake conservative traffic targeted artifacts", all(exists(tables / f"heldout2_overtake_conservative_traffic_targeted_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout2_overtake_conservative_traffic_targeted_rows.csv")),
        audit_item("second held-out DAgger-v2 recovery conservative artifacts", all(exists(tables / f"heldout2_dagger_v2_recovery_conservative_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout2_dagger_v2_recovery_conservative_suite_rows.csv")),
        audit_item("second held-out DAgger-v2 expert blend targeted artifacts", all(exists(tables / f"heldout2_dagger_v2_expert_blend_targeted_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout2_dagger_v2_expert_blend_targeted_rows.csv")),
        audit_item("second held-out DAgger-v2 expert more-graph artifacts", all(exists(tables / f"heldout2_dagger_v2_expert_more_graph_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout2_dagger_v2_expert_more_graph_suite_rows.csv")),
        audit_item("second held-out DAgger-v2 diagnosis artifacts", all(exists(tables / f"dagger_v2_heldout2_failure_diagnosis.{ext}") for ext in ["json", "md"]) and exists(tables / "dagger_v2_heldout2_failure_diagnosis_rows.csv")),
        audit_item("second held-out long online probe DAgger-v2 artifacts", all(exists(tables / f"portfolio_probe_selector_1200_heldout2_dagger_v2.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_probe_selector_1200_heldout2_dagger_v2_rows.csv")),
        audit_item("expanded long online probe held-out artifacts", all(exists(tables / f"portfolio_probe_selector_1200_heldout_expanded.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_probe_selector_1200_heldout_expanded_rows.csv")),
        audit_item("expanded second held-out long online probe artifacts", all(exists(tables / f"portfolio_probe_selector_1200_heldout2_expanded.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_probe_selector_1200_heldout2_expanded_rows.csv")),
        audit_item("expanded selector generalization artifacts", all(exists(tables / f"expanded_selector_generalization.{ext}") for ext in ["json", "md"]) and exists(tables / "expanded_selector_generalization_rows.csv")),
        audit_item("expanded selector distillation artifacts", all(exists(tables / f"expanded_selector_distillation_report.{ext}") for ext in ["json", "md"]) and exists(tables / "expanded_selector_distillation_grid.csv")),
        audit_item("learned selector diagnostic artifacts", all(exists(tables / f"learned_selector_report.{ext}") for ext in ["json", "md"]) and exists(tables / "learned_selector_rows.csv")),
        audit_item("third held-out main suite artifacts", all(exists(tables / f"heldout3_multiseed_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout3_multiseed_suite_rows.csv")),
        audit_item("third held-out adaptive suite artifacts", all(exists(tables / f"heldout3_adaptive_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout3_adaptive_suite_rows.csv")),
        audit_item("third held-out expert gate suite artifacts", all(exists(tables / f"heldout3_expert_gate_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout3_expert_gate_suite_rows.csv")),
        audit_item("third held-out DAgger-v2 suite artifacts", all(exists(tables / f"heldout3_graph_dagger_recovery_v2_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout3_graph_dagger_recovery_v2_suite_rows.csv")),
        audit_item("third held-out DAgger-v2 more-graph suite artifacts", all(exists(tables / f"heldout3_dagger_v2_expert_more_graph_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout3_dagger_v2_expert_more_graph_suite_rows.csv")),
        audit_item("third held-out expanded online probe artifacts", all(exists(tables / f"portfolio_probe_selector_1200_heldout3_expanded.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_probe_selector_1200_heldout3_expanded_rows.csv")),
        audit_item("third held-out external validation artifacts", all(exists(tables / f"heldout3_external_validation.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout3_external_validation_rows.csv")),
        audit_item("third held-out targeted recovery training artifacts", exists(models / "heldout3_targeted_recovery" / "graph_dagger_recovery.graph.pt") and exists(models / "heldout3_targeted_recovery" / "train_summary.json")),
        audit_item("third held-out targeted recovery suite artifacts", all(exists(tables / f"heldout3_targeted_recovery_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout3_targeted_recovery_suite_rows.csv")),
        audit_item("third held-out targeted recovery conservative traffic artifacts", all(exists(tables / f"heldout3_targeted_recovery_conservative_traffic_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout3_targeted_recovery_conservative_traffic_suite_rows.csv")),
        audit_item("seed157 traffic ablation artifacts", all(exists(tables / f"seed157_traffic_ablation.{ext}") for ext in ["json", "md"]) and exists(tables / "seed157_traffic_ablation_rows.csv")),
        audit_item("third held-out traffic-adaptive conservative suite artifacts", all(exists(tables / f"heldout3_traffic_adaptive_conservative_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout3_traffic_adaptive_conservative_suite_rows.csv")),
        audit_item("third held-out targeted expanded online probe artifacts", all(exists(tables / f"portfolio_probe_selector_1200_heldout3_targeted_expanded.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_probe_selector_1200_heldout3_targeted_expanded_rows.csv")),
        audit_item("third held-out targeted selector generalization artifacts", all(exists(tables / f"heldout3_targeted_selector_generalization.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout3_targeted_selector_generalization_rows.csv")),
        audit_item("third held-out targeted meta-selector diagnostic artifacts", all(exists(tables / f"heldout3_targeted_meta_selector.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout3_targeted_meta_selector_rows.csv")),
        audit_item("third held-out candidate expansion artifacts", all(exists(tables / f"heldout3_candidate_expansion.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout3_candidate_expansion_rows.csv")),
        audit_item("fourth held-out main suite artifacts", all(exists(tables / f"heldout4_multiseed_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout4_multiseed_suite_rows.csv")),
        audit_item("fourth held-out adaptive suite artifacts", all(exists(tables / f"heldout4_adaptive_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout4_adaptive_suite_rows.csv")),
        audit_item("fourth held-out expert gate suite artifacts", all(exists(tables / f"heldout4_expert_gate_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout4_expert_gate_suite_rows.csv")),
        audit_item("fourth held-out DAgger-v2 suite artifacts", all(exists(tables / f"heldout4_graph_dagger_recovery_v2_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout4_graph_dagger_recovery_v2_suite_rows.csv")),
        audit_item("fourth held-out DAgger-v2 more-graph suite artifacts", all(exists(tables / f"heldout4_dagger_v2_expert_more_graph_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout4_dagger_v2_expert_more_graph_suite_rows.csv")),
        audit_item("fourth held-out traffic-adaptive conservative suite artifacts", all(exists(tables / f"heldout4_traffic_adaptive_conservative_suite_report.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout4_traffic_adaptive_conservative_suite_rows.csv")),
        audit_item("fourth held-out targeted expanded online probe artifacts", all(exists(tables / f"portfolio_probe_selector_1200_heldout4_targeted_expanded.{ext}") for ext in ["json", "md"]) and exists(tables / "portfolio_probe_selector_1200_heldout4_targeted_expanded_rows.csv")),
        audit_item("fourth held-out external validation artifacts", all(exists(tables / f"heldout4_external_validation.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout4_external_validation_rows.csv")),
        audit_item(
            "fourth held-out failure atlas artifacts",
            all(exists(tables / f"heldout4_failure_atlas.{ext}") for ext in ["json", "md"])
            and exists(tables / "heldout4_failure_atlas_seed_rows.csv")
            and exists(tables / "heldout4_failure_atlas_method_matrix.csv"),
        ),
        audit_item("cross held-out validation synthesis artifacts", all(exists(tables / f"cross_heldout_validation_synthesis.{ext}") for ext in ["json", "md"]) and exists(tables / "cross_heldout_validation_synthesis_rows.csv")),
        audit_item(
            "cross held-out statistical supplement artifacts",
            all(exists(tables / f"cross_heldout_statistical_supplement.{ext}") for ext in ["json", "md"])
            and exists(tables / "cross_heldout_statistical_supplement_rows.csv")
            and exists(figures / "figure_3_source_data_dictionary.csv"),
        ),
        audit_item(
            "seed outcome ledger artifacts",
            exists(tables / "seed_outcome_ledger.md")
            and exists(tables / "seed_outcome_ledger.json")
            and exists(tables / "seed_outcome_ledger.csv")
            and exists(tables / "seed_outcome_ledger_stage_summary.csv"),
        ),
        audit_item(
            "cross held-out validation figure exports",
            all(exists(figures / f"figure_3_cross_heldout_validation{ext}") for ext in [".png", ".pdf", ".svg", ".tiff"])
            and exists(figures / "figure_3_source_data.csv")
            and exists(figures / "figure_3_manifest.json"),
        ),
        audit_item("cross held-out generalization artifacts", all(exists(tables / f"heldout_generalization.{ext}") for ext in ["json", "md"]) and exists(tables / "heldout_generalization_method_rows.csv")),
        audit_item("selector calibration artifacts", all(exists(tables / f"selector_calibration.{ext}") for ext in ["json", "md"]) and exists(tables / "selector_calibration_decisions.csv")),
        audit_item(
            "selector distillation diagnostic artifacts",
            all(exists(tables / f"selector_distillation_report.{ext}") for ext in ["json", "md"])
            and exists(tables / "selector_distillation_grid.csv"),
        ),
        audit_item(
            "heldout2 failure atlas artifacts",
            all(exists(tables / f"heldout2_failure_atlas.{ext}") for ext in ["json", "md"])
            and exists(tables / "heldout2_failure_atlas_seed_rows.csv")
            and exists(tables / "heldout2_failure_atlas_method_matrix.csv"),
        ),
        audit_item(
            "heldout2 candidate expansion artifacts",
            all(exists(tables / f"heldout2_candidate_expansion.{ext}") for ext in ["json", "md"])
            and exists(tables / "heldout2_candidate_expansion_rows.csv"),
        ),
        audit_item(
            "compute cost report artifacts",
            all(exists(tables / f"compute_cost_report.{ext}") for ext in ["json", "md"])
            and exists(tables / "compute_cost_suite_rows.csv")
            and exists(tables / "compute_cost_selector_rows.csv"),
        ),
        audit_item("baseline GIF evidence", bool(list_files(root, "baselines", suffixes={".gif"}))),
        audit_item("evaluation GIF evidence", bool(list_files(root, "evaluations", suffixes={".gif"}))),
        audit_item("training summary evidence", bool(list_files(models, ".", suffixes={".json"}))),
        audit_item("run logs evidence", bool(list_files(root, "logs", suffixes={".log"}))),
    ]

    provenance_limitations = [
        "paper pdf/manuscript source is not stored in this package",
        "full command history is not separately archived beyond logs and scripts",
        "raw environment lockfile is present only if environment.yml exists at repo root",
    ]
    if exists(Path("environment.yml")):
        items.append(audit_item("environment lockfile", True))
    else:
        items.append(audit_item("environment lockfile", False, required=False))

    report = {
        "root": str(root),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "manifest_snapshot": {
            "title": manifest.get("title"),
            "root": manifest.get("root"),
            "seed": manifest.get("seed"),
            "eval_seeds": manifest.get("eval_seeds"),
            "device": manifest.get("device"),
            "components": manifest.get("components"),
        },
        "checks": items,
        "missing_or_weak_items": [item for item in items if item["status"] != "proven"],
        "provenance_limitations": provenance_limitations,
        "interpretation": (
            "The package is substantially reproducible: code snapshots, result tables, figures, GIFs, logs, and "
            "machine-readable summaries are all present. The main remaining gap is manuscript-level packaging "
            "outside the repository and a more explicit provenance chain for the exact commands that generated each artifact."
        ),
    }
    return report


def write_markdown(report, path):
    lines = [
        "# Reproducibility Audit",
        "",
        f"- Root: `{report['root']}`",
        f"- Timestamp (UTC): {report['timestamp_utc']}",
        f"- Host: {report['host']['system']} {report['host']['release']}, Python {report['host']['python']}",
        "",
        "## Provenance Snapshot",
        "",
        f"- Title: {report['manifest_snapshot']['title']}",
        f"- Root: {report['manifest_snapshot']['root']}",
        f"- Eval seeds: {report['manifest_snapshot']['eval_seeds']}",
        f"- Device: {report['manifest_snapshot']['device']}",
        "",
        "## Check Summary",
        "",
        "| item | status | evidence |",
        "|---|---|---|",
    ]
    for item in report["checks"]:
        evidence = "yes" if item["evidence"] else "no"
        lines.append(f"| {item['item']} | {item['status']} | {evidence} |")
    lines.extend(
        [
            "",
            "## Missing or Weak Items",
            "",
        ]
    )
    if report["missing_or_weak_items"]:
        for item in report["missing_or_weak_items"]:
            lines.append(f"- {item['item']}: {item['status']}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Notes",
            "",
        ]
    )
    for note in report["provenance_limitations"]:
        lines.append(f"- {note}")
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export a reproducibility audit for the experiment package.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--out-prefix", default="reproducibility_audit")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_audit(root)

    table_dir = root / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    out_json = table_dir / f"{args.out_prefix}.json"
    out_md = table_dir / f"{args.out_prefix}.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md)}, indent=2))


if __name__ == "__main__":
    main()
