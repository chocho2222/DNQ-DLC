#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


OVERALL = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv"
PAIRED = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv"
SCENARIO = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_scenario_statistics.csv"
METRIC_SENSITIVITY = "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/robustness_summary_by_algorithm.csv"
DESIGN_MANIFEST = "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tits_experimental_design_power_audit_manifest.json"
COMPUTE_MANIFEST = "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tits_compute_reproducibility_cost_pack_manifest.json"
READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def row_by(rows, **criteria):
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    return {}


def fmt(value, digits=3):
    if value in ("", None):
        return "NA"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def evidence_status(root, evidence_paths):
    paths = [item.strip() for item in evidence_paths.split(";") if item.strip()]
    missing = [item for item in paths if not (root / item).exists()]
    return {
        "evidence_path_count": len(paths),
        "missing_evidence_count": len(missing),
        "missing_evidence": "; ".join(missing),
        "evidence_complete": len(missing) == 0,
    }


def build_facts(overall, paired, scenario, sensitivity, design, compute, readiness):
    safe = row_by(overall, algorithm="v6_runtime_dynamic_neighborhood_safe")
    dlc = row_by(overall, algorithm="dlc_world_original")
    rule = row_by(overall, algorithm="rule_expert_gate")
    quality = row_by(overall, algorithm="quality_proposal_dlc_world_v1")
    n8_safe = row_by(scenario, algorithm="v6_runtime_dynamic_neighborhood_safe", benchmark="vehicle_count_extrapolation")
    n8_dlc = row_by(scenario, algorithm="dlc_world_original", benchmark="vehicle_count_extrapolation")
    monza6_safe = row_by(scenario, algorithm="v6_runtime_dynamic_neighborhood_safe", benchmark="monza_external_track", num_agents="6")
    monza6_dlc = row_by(scenario, algorithm="dlc_world_original", benchmark="monza_external_track", num_agents="6")
    safe_success = row_by(paired, algorithm="v6_runtime_dynamic_neighborhood_safe", metric="overtake_success_rate")
    safe_elegant = row_by(paired, algorithm="v6_runtime_dynamic_neighborhood_safe", metric="elegant_overtake_rate")
    safe_time = row_by(paired, algorithm="v6_runtime_dynamic_neighborhood_safe", metric="overtake_start_to_complete_time")
    safe_sensitivity = row_by(sensitivity, algorithm="v6_runtime_dynamic_neighborhood_safe")
    rule_sensitivity = row_by(sensitivity, algorithm="rule_expert_gate")
    return {
        "safe_success": fmt(safe.get("overtake_success_rate_mean")),
        "dlc_success": fmt(dlc.get("overtake_success_rate_mean")),
        "safe_elegant": fmt(safe.get("elegant_overtake_rate_mean")),
        "dlc_elegant": fmt(dlc.get("elegant_overtake_rate_mean")),
        "safe_time": fmt(safe.get("overtake_start_to_complete_time_mean"), 1),
        "dlc_time": fmt(dlc.get("overtake_start_to_complete_time_mean"), 1),
        "safe_grass": fmt(safe.get("target_grass_rate_mean")),
        "dlc_grass": fmt(dlc.get("target_grass_rate_mean")),
        "rule_elegant": fmt(rule.get("elegant_overtake_rate_mean")),
        "quality_success": fmt(quality.get("overtake_success_rate_mean")),
        "quality_elegant": fmt(quality.get("elegant_overtake_rate_mean")),
        "paired_success_delta": fmt(safe_success.get("improvement_vs_dlc_mean")),
        "paired_elegant_delta": fmt(safe_elegant.get("improvement_vs_dlc_mean")),
        "paired_time_delta": fmt(safe_time.get("improvement_vs_dlc_mean"), 1),
        "n8_safe_elegant": fmt(n8_safe.get("elegant_overtake_rate_mean")),
        "n8_dlc_elegant": fmt(n8_dlc.get("elegant_overtake_rate_mean")),
        "monza6_safe_success": fmt(monza6_safe.get("overtake_success_rate_mean")),
        "monza6_dlc_success": fmt(monza6_dlc.get("overtake_success_rate_mean")),
        "sensitivity_positive": fmt(safe_sensitivity.get("positive_delta_fraction")),
        "sensitivity_nonnegative": fmt(safe_sensitivity.get("nonnegative_delta_fraction")),
        "rule_sensitivity_positive": fmt(rule_sensitivity.get("positive_delta_fraction")),
        "case_count": str(design.get("summary", {}).get("case_count", "NA")),
        "algorithm_count": str(compute.get("summary", {}).get("algorithm_count", "NA")),
        "source_rows": str(compute.get("summary", {}).get("source_rows", "NA")),
        "sim_steps": str(compute.get("summary", {}).get("total_simulated_steps_across_algorithm_runs", "NA")),
        "gpu_count": str(compute.get("summary", {}).get("gpu_count", "NA")),
        "readiness": f"{readiness.get('pass_count', 'NA')}/{readiness.get('gate_count', 'NA')}",
    }


def claim_rows(facts):
    return [
        {
            "claim_id": "C01",
            "claim_area": "main_result",
            "paper_section": "Abstract; Results",
            "allowed_claim": f"v6-safe improves online overtaking over original DLC in the evaluated benchmark: success {facts['safe_success']} vs {facts['dlc_success']}, elegant {facts['safe_elegant']} vs {facts['dlc_elegant']}, and completion time {facts['safe_time']} vs {facts['dlc_time']} steps.",
            "required_boundary": "Limit to evaluated simulation benchmarks; do not imply real-road safety.",
            "evidence_types": "source_data; paired_statistics; figure; numeric_trace; limitation",
            "evidence_paths": "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv; outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv; outputs/tits_dynamic_graph/manuscript_english_figures/figures/figure_dynamic_dlc_overtaking_english.pdf; outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/materials/MANUSCRIPT_NUMERIC_TRACE_AUDIT.md; outputs/tits_dynamic_graph/tits_manuscript_package/materials/LIMITATIONS_DRAFT.md",
            "rebuttal_link": "R01; R04; R05",
            "avoid_claim": "Do not say the method solves autonomous overtaking or guarantees desirable overtaking behavior in every case.",
        },
        {
            "claim_id": "C02",
            "claim_area": "overtake_quality",
            "paper_section": "Results; Metrics",
            "allowed_claim": f"The improvement is quality-related rather than speed-only: paired gains include success +{facts['paired_success_delta']}, desirable/on-track +{facts['paired_elegant_delta']}, and start-to-completion reduction of {facts['paired_time_delta']} steps.",
            "required_boundary": "Report success, desirable/on-track, grass and time metrics as a family.",
            "evidence_types": "paired_statistics; metric_dictionary; figure; failure_analysis",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv; outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/metric_dictionary.csv; outputs/tits_dynamic_graph/manuscript_english_figures/materials/FIGURE_DYNAMIC_DLC_OVERTAKING_LEGEND.md; outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/materials/FAILURE_ATLAS.md",
            "rebuttal_link": "R04; R05; R07",
            "avoid_claim": "Do not reduce the result to fastest vehicle wins.",
        },
        {
            "claim_id": "C03",
            "claim_area": "dynamic_vehicle_count",
            "paper_section": "Methods; Supplementary Results",
            "allowed_claim": f"Runtime dynamic neighborhoods support the included 4/5/6/8-car online settings with fixed max_neighbors=3; n=8 desirable overtaking behavior rate is {facts['n8_safe_elegant']} vs DLC {facts['n8_dlc_elegant']}.",
            "required_boundary": "This is bounded vehicle-count extrapolation, not arbitrary density.",
            "evidence_types": "runtime_scalability; source_data; innovation_trace",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md; outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials/INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md",
            "rebuttal_link": "R03",
            "avoid_claim": "Do not claim unlimited traffic scalability or no-retraining for every possible traffic density.",
        },
        {
            "claim_id": "C04",
            "claim_area": "external_track_boundary",
            "paper_section": "Results; Discussion",
            "allowed_claim": f"On the included Monza n=6 external-track setting, v6-safe success is {facts['monza6_safe_success']} vs DLC {facts['monza6_dlc_success']}.",
            "required_boundary": "Monza is one CSV-derived external stress test, not broad track generalization.",
            "evidence_types": "scenario_statistics; benchmark_protocol; threats_boundary",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_scenario_statistics.csv; outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/benchmark_cards.csv; outputs/tits_dynamic_graph/tits_threats_validity_pack/materials/THREATS_TO_VALIDITY_DOSSIER.md",
            "rebuttal_link": "R02",
            "avoid_claim": "Do not claim arbitrary road-geometry generalization.",
        },
        {
            "claim_id": "C05",
            "claim_area": "failure_boundary",
            "paper_section": "Results; Discussion",
            "allowed_claim": f"v6-safe reduces grass exposure relative to original DLC ({facts['safe_grass']} vs {facts['dlc_grass']}) but residual off-track/high-grass cases remain.",
            "required_boundary": "Failure atlas and casewise diagnostics must be cited beside grass/off-track claims.",
            "evidence_types": "failure_atlas; casewise_diagnostics; threats_boundary",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/materials/FAILURE_ATLAS.md; outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/materials/CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md; outputs/tits_dynamic_graph/tits_threats_validity_pack/tables/threats_validity_risk_register.csv",
            "rebuttal_link": "R04",
            "avoid_claim": "Do not claim the method always stays on track.",
        },
        {
            "claim_id": "C06",
            "claim_area": "baseline_fairness_rule_expert",
            "paper_section": "Experiments; Discussion",
            "allowed_claim": f"The rule expert is a strong hand-engineered reference, with desirable overtaking behavior rate {facts['rule_elegant']} and positive threshold-sensitivity fraction {facts['rule_sensitivity_positive']}.",
            "required_boundary": "Discuss rule expert trade-offs; do not dismiss rules.",
            "evidence_types": "overall_statistics; metric_sensitivity; baseline_fairness",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv; outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md; outputs/tits_dynamic_graph/tits_baseline_fairness_audit/materials/BASELINE_FAIRNESS_AUDIT.md",
            "rebuttal_link": "R06; R10",
            "avoid_claim": "Do not say all rule-based methods are weak.",
        },
        {
            "claim_id": "C07",
            "claim_area": "metric_sensitivity",
            "paper_section": "Supplementary Analysis; Discussion",
            "allowed_claim": f"v6-safe remains better than original DLC in {facts['sensitivity_positive']} of post-hoc quality-threshold settings and nonnegative in {facts['sensitivity_nonnegative']}.",
            "required_boundary": "This is post-hoc sensitivity analysis, not a preregistered endpoint.",
            "evidence_types": "metric_sensitivity; metric_dictionary; claim_boundary",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md; outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/robustness_summary_by_algorithm.csv; outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/metric_dictionary.csv",
            "rebuttal_link": "R07",
            "avoid_claim": "Do not claim robustness under every possible quality definition.",
        },
        {
            "claim_id": "C08",
            "claim_area": "statistical_validity",
            "paper_section": "Methods; Results",
            "allowed_claim": "Primary comparisons are reported with paired effect sizes, confidence intervals and Holm-corrected primary tests.",
            "required_boundary": "Exploratory comparisons, conditional endpoints and protocol/deviation boundaries must remain separated from the primary family.",
            "evidence_types": "statistical_plan; protocol_deviation; holm_table; effect_sizes",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/STATISTICAL_ANALYSIS_PLAN.md; outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/materials/PROTOCOL_DEVIATION_READINESS_REPORT.md; outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tables/endpoint_hierarchy.csv; outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tables/protocol_deviation_register.csv; outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv; outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_effect_sizes.csv",
            "rebuttal_link": "R08",
            "avoid_claim": "Do not treat all exploratory p values as confirmatory discoveries.",
        },
        {
            "claim_id": "C09",
            "claim_area": "case_stability",
            "paper_section": "Supplementary Analysis",
            "allowed_claim": f"The main effect is not driven by a single case under leave-one-case audit; the formal matrix covers {facts['case_count']} matched cases.",
            "required_boundary": "Report high-influence cases and scenario heterogeneity.",
            "evidence_types": "design_power; leave_one_case; casewise",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/case_influence_summary.csv; outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_pairwise_win_loss_summary.csv",
            "rebuttal_link": "R09",
            "avoid_claim": "Do not imply all cases have equal difficulty.",
        },
        {
            "claim_id": "C10",
            "claim_area": "algorithm_novelty",
            "paper_section": "Methods; Ablation",
            "allowed_claim": "The method is an optimized DLC-style graph world model with runtime dynamic neighborhoods, overtake-aware candidate planning, safety/quality scoring and a quality proposal branch.",
            "required_boundary": "Keep the relation to DLC explicit; do not present it as unrelated to the baseline family.",
            "evidence_types": "innovation_trace; ablation; model_artifacts; code",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials/INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md; outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_REPORT.md; outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/materials/MODEL_ARTIFACT_INTEGRITY_AUDIT.md; dlc/graph_world_model.py",
            "rebuttal_link": "R14",
            "avoid_claim": "Do not present the method as unrelated to DLC world-model baselines.",
        },
        {
            "claim_id": "C11",
            "claim_area": "quality_proposal_boundary",
            "paper_section": "Ablation; Discussion",
            "allowed_claim": f"Quality proposal is useful but not the final standalone solution: success {facts['quality_success']} with desirable overtaking behavior rate {facts['quality_elegant']}.",
            "required_boundary": "Describe quality proposal as a candidate source/variant, not the full final method.",
            "evidence_types": "overall_statistics; ablation; model_artifacts",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv; outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_REPORT.md; outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/tables/model_artifact_inventory.csv",
            "rebuttal_link": "R14",
            "avoid_claim": "Do not claim quality proposal alone is the optimal algorithm.",
        },
        {
            "claim_id": "C12",
            "claim_area": "reproducibility",
            "paper_section": "Data/Code Availability; Supplement",
            "allowed_claim": f"The formal evidence chain contains {facts['source_rows']} source rows, {facts['algorithm_count']} algorithms, {facts['sim_steps']} simulated steps, and readiness {facts['readiness']}.",
            "required_boundary": "DOI, license, final author statements and public upload remain author-owned.",
            "evidence_types": "reproducibility_capsule; reviewer_packet; artifact_manifest; release_plan; third_party_pack; container_preflight",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md; outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md; outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.md; outputs/tits_dynamic_graph/public_release_plan/PUBLIC_RELEASE_PLAN.md; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/THIRD_PARTY_REPRODUCTION_PACK.md; outputs/tits_dynamic_graph/tits_container_build_preflight/materials/CONTAINER_BUILD_PREFLIGHT.md",
            "rebuttal_link": "R11; R15",
            "avoid_claim": "Do not claim DOI-backed public archive exists before the author creates it.",
        },
        {
            "claim_id": "C13",
            "claim_area": "compute_transparency",
            "paper_section": "Supplementary Reproducibility",
            "allowed_claim": f"The compute pack records run scale, decision latency, CUDA availability and {facts['gpu_count']} GPUs, while full wall-clock/GPU-utilization traces are unavailable.",
            "required_boundary": "Do not equate workload proxy with measured wall-clock time.",
            "evidence_types": "compute_cost; environment_snapshot; claim_boundary",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/materials/COMPUTE_REPRODUCIBILITY_COST_REPORT.md; outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_environment_snapshot.csv; outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_claim_boundaries.csv",
            "rebuttal_link": "R12",
            "avoid_claim": "Do not claim complete wall-clock or GPU-utilization accounting.",
        },
        {
            "claim_id": "C14",
            "claim_area": "visual_evidence",
            "paper_section": "Supplementary Videos",
            "allowed_claim": "Top-down and first-person GIFs provide qualitative visual examples; aggregate claims come from the 240-run source data.",
            "required_boundary": "GIFs are representative visual evidence only.",
            "evidence_types": "gif_manifest; source_data; figure_audit",
            "evidence_paths": "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.md; outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv; outputs/tits_dynamic_graph/tits_figure_source_data_audit/materials/FIGURE_SOURCE_DATA_AUDIT.md",
            "rebuttal_link": "R13",
            "avoid_claim": "Do not infer aggregate performance from one GIF.",
        },
        {
            "claim_id": "C15",
            "claim_area": "container_reproducibility_boundary",
            "paper_section": "Data/Code Availability; Supplementary Reproducibility",
            "allowed_claim": "Docker/Apptainer reproduction drafts and a local container-build preflight are provided, while the current server lacks Docker/Apptainer runtime and no image has been built or certified.",
            "required_boundary": "Do not describe the container as published, built, tested, certified or digest-pinned until an actual image build and smoke test are completed.",
            "evidence_types": "third_party_pack; dockerfile_draft; apptainer_draft; container_preflight",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/THIRD_PARTY_REPRODUCTION_PACK.md; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/Dockerfile.draft; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/apptainer.def.draft; outputs/tits_dynamic_graph/tits_container_build_preflight/materials/CONTAINER_BUILD_PREFLIGHT.md",
            "rebuttal_link": "R15",
            "avoid_claim": "Do not claim a ready-to-run container image exists in the current artifact set.",
        },
    ]


def build_rows(root, facts):
    rows = []
    for claim in claim_rows(facts):
        status = evidence_status(root, claim["evidence_paths"])
        row = dict(claim)
        row.update(status)
        row["status"] = "pass" if row["evidence_complete"] and row["required_boundary"] and row["avoid_claim"] else "review_required"
        rows.append(row)
    return rows


def build_evidence_index(root, rows):
    index = {}
    for row in rows:
        for path in [item.strip() for item in row["evidence_paths"].split(";") if item.strip()]:
            item = index.setdefault(path, {"evidence_path": path, "exists": (root / path).exists(), "claim_ids": []})
            item["claim_ids"].append(row["claim_id"])
    out = []
    for path, item in sorted(index.items()):
        out.append({"evidence_path": path, "exists": item["exists"], "claim_ids": "; ".join(item["claim_ids"])})
    return out


def build_boundary_rows(rows):
    return [
        {
            "claim_id": row["claim_id"],
            "claim_area": row["claim_area"],
            "required_boundary": row["required_boundary"],
            "avoid_claim": row["avoid_claim"],
            "rebuttal_link": row["rebuttal_link"],
        }
        for row in rows
    ]


def build_markdown(report):
    lines = [
        "# T-ITS Claim Evidence Completeness Audit",
        "",
        "该审计把投稿可写 claim 逐条映射到正式 source data、统计证据、图表/补充材料、限制边界和 rebuttal 入口。它不新增仿真实验，只检查当前证据链能否支撑论文叙述。",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Claim Table",
            "",
            "| ID | Area | Section | Status | Allowed claim | Required boundary | Evidence paths | Avoid |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["claim_rows"]:
        lines.append(
            f"| {row['claim_id']} | {row['claim_area']} | {row['paper_section']} | {row['status']} | "
            f"{row['allowed_claim']} | {row['required_boundary']} | {row['evidence_path_count']} paths | {row['avoid_claim']} |"
        )
    lines.extend(
        [
            "",
            "## Review Rules",
            "",
            "- Results 中的主 claim 必须同时引用 source data、成对统计或图表，并与 Limitations 保持一致。",
            "- Methods/Contributions 中的创新 claim 必须回链到代码、配置、模型 artifact 和 ablation/traceability 材料。",
            "- Discussion/Rebuttal 中不能把边界审计写成风险已解决，只能写成风险已披露、证据已限定。",
            "- GIF、smoke、partial、探索性 sweep 不能替代正式 240-run source data。",
        ]
    )
    if report["missing_evidence"]:
        lines.extend(["", "## Missing Evidence", ""])
        for item in report["missing_evidence"]:
            lines.append(f"- `{item}`")
    return "\n".join(lines)


def build_report(root):
    overall = read_csv(root / OVERALL)
    paired = read_csv(root / PAIRED)
    scenario = read_csv(root / SCENARIO)
    sensitivity = read_csv(root / METRIC_SENSITIVITY)
    design = read_json(root / DESIGN_MANIFEST)
    compute = read_json(root / COMPUTE_MANIFEST)
    readiness = read_json(root / READINESS)
    facts = build_facts(overall, paired, scenario, sensitivity, design, compute, readiness)
    rows = build_rows(root, facts)
    evidence_index = build_evidence_index(root, rows)
    boundary_rows = build_boundary_rows(rows)
    missing = sorted({item for row in rows for item in row["missing_evidence"].split("; ") if item})
    summary = {
        "status": "pass" if not missing and all(row["status"] == "pass" for row in rows) else "review_required",
        "claim_count": len(rows),
        "claim_pass_count": sum(1 for row in rows if row["status"] == "pass"),
        "evidence_path_count": len(evidence_index),
        "missing_evidence_count": len(missing),
        "boundary_count": len(boundary_rows),
        "formal_source_rows": facts["source_rows"],
        "formal_algorithms": facts["algorithm_count"],
        "formal_cases": facts["case_count"],
        "final_readiness": facts["readiness"],
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "facts": facts,
        "claim_rows": rows,
        "evidence_index": evidence_index,
        "boundary_rows": boundary_rows,
        "missing_evidence": missing,
    }


def main():
    parser = argparse.ArgumentParser(description="Export a T-ITS claim evidence completeness audit.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    report = build_report(root)
    claim_fields = [
        "claim_id",
        "claim_area",
        "paper_section",
        "allowed_claim",
        "required_boundary",
        "evidence_types",
        "evidence_paths",
        "rebuttal_link",
        "avoid_claim",
        "evidence_path_count",
        "missing_evidence_count",
        "missing_evidence",
        "evidence_complete",
        "status",
    ]
    paths = {
        "audit_md": write_text(materials / "CLAIM_EVIDENCE_COMPLETENESS_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "CLAIM_EVIDENCE_COMPLETENESS_AUDIT.json", report),
        "claim_matrix_csv": write_csv(tables / "claim_evidence_completeness_matrix.csv", report["claim_rows"], claim_fields),
        "evidence_index_csv": write_csv(
            tables / "claim_evidence_path_index.csv",
            report["evidence_index"],
            ["evidence_path", "exists", "claim_ids"],
        ),
        "boundary_csv": write_csv(
            tables / "claim_boundary_requirements.csv",
            report["boundary_rows"],
            ["claim_id", "claim_area", "required_boundary", "avoid_claim", "rebuttal_link"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_claim_evidence_completeness_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
