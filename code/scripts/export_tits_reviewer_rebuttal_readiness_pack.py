#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


OVERALL = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv"
PAIRED = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv"
RISK_REGISTER = "outputs/tits_dynamic_graph/tits_threats_validity_pack/tables/threats_validity_risk_register.csv"
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


def as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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


def evidence_exists(root, evidence):
    paths = [item.strip() for item in evidence.split(";") if item.strip()]
    existing = []
    missing = []
    for item in paths:
        path = root / item
        if path.exists():
            existing.append(item)
        else:
            missing.append(item)
    return existing, missing


def build_facts(overall, paired, sensitivity, design, compute, readiness):
    safe = row_by(overall, algorithm="v6_runtime_dynamic_neighborhood_safe")
    dlc = row_by(overall, algorithm="dlc_world_original")
    rule = row_by(overall, algorithm="rule_expert_gate")
    safe_success = row_by(paired, algorithm="v6_runtime_dynamic_neighborhood_safe", metric="overtake_success_rate")
    safe_elegant = row_by(paired, algorithm="v6_runtime_dynamic_neighborhood_safe", metric="elegant_overtake_rate")
    safe_time = row_by(paired, algorithm="v6_runtime_dynamic_neighborhood_safe", metric="overtake_start_to_complete_time")
    safe_sens = row_by(sensitivity, algorithm="v6_runtime_dynamic_neighborhood_safe")
    rule_sens = row_by(sensitivity, algorithm="rule_expert_gate")
    design_summary = design.get("summary", {})
    compute_summary = compute.get("summary", {})
    return {
        "safe_success": fmt(safe.get("overtake_success_rate_mean")),
        "dlc_success": fmt(dlc.get("overtake_success_rate_mean")),
        "safe_elegant": fmt(safe.get("elegant_overtake_rate_mean")),
        "dlc_elegant": fmt(dlc.get("elegant_overtake_rate_mean")),
        "safe_grass": fmt(safe.get("target_grass_rate_mean")),
        "dlc_grass": fmt(dlc.get("target_grass_rate_mean")),
        "safe_time": fmt(safe.get("overtake_start_to_complete_time_mean")),
        "dlc_time": fmt(dlc.get("overtake_start_to_complete_time_mean")),
        "rule_elegant": fmt(rule.get("elegant_overtake_rate_mean")),
        "success_delta": fmt(safe_success.get("improvement_vs_dlc_mean")),
        "elegant_delta": fmt(safe_elegant.get("improvement_vs_dlc_mean")),
        "time_delta": fmt(safe_time.get("improvement_vs_dlc_mean")),
        "threshold_positive_fraction": fmt(safe_sens.get("positive_delta_fraction")),
        "threshold_nonnegative_fraction": fmt(safe_sens.get("nonnegative_delta_fraction")),
        "rule_threshold_positive_fraction": fmt(rule_sens.get("positive_delta_fraction")),
        "case_count": str(design_summary.get("case_count", "NA")),
        "source_rows": str(compute_summary.get("source_rows", "NA")),
        "algorithm_count": str(compute_summary.get("algorithm_count", "NA")),
        "sim_steps": str(compute_summary.get("total_simulated_steps_across_algorithm_runs", "NA")),
        "gpu_count": str(compute_summary.get("gpu_count", "NA")),
        "readiness": f"{readiness.get('pass_count', 'NA')}/{readiness.get('gate_count', 'NA')}",
        "max_case_relative_abs_influence": fmt(design_summary.get("max_case_relative_abs_influence")),
    }


def build_rebuttal_rows(facts):
    return [
        {
            "id": "R01",
            "reviewer_concern": "Does the paper claim real-world autonomous overtaking safety?",
            "response_stance": "Concede scope and constrain the claim to simulation.",
            "evidence_summary": "The benchmark is simulation-only, with procedural tracks, n=8 extrapolation and one Monza CSV-derived external track.",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/materials/BENCHMARK_METRIC_PROTOCOL_CARD.md; outputs/tits_dynamic_graph/tits_threats_validity_pack/materials/THREATS_TO_VALIDITY_DOSSIER.md",
            "manuscript_action": "Keep the limitation in Discussion and avoid deployment-level safety wording in Abstract/Conclusion.",
            "avoid_in_response": "Do not claim certified safety, legal compliance or real-road readiness.",
        },
        {
            "id": "R02",
            "reviewer_concern": "Is one external Monza track enough for broad generalization?",
            "response_stance": "Treat Monza as an external-track stress test, not a broad generalization proof.",
            "evidence_summary": "The formal matrix includes 30 matched cases and keeps Monza as a bounded external setting.",
            "evidence_paths": "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md",
            "manuscript_action": "Use 'external-track evidence' instead of 'generalizes to arbitrary tracks'.",
            "avoid_in_response": "Do not imply arbitrary road-geometry robustness.",
        },
        {
            "id": "R03",
            "reviewer_concern": "Does the dynamic graph support arbitrary vehicle counts without retraining?",
            "response_stance": "State the tested range and explain runtime neighbor construction.",
            "evidence_summary": "Runtime dynamic neighborhoods are evaluated at 4/5/6/8 vehicles with max_neighbors=3; this is bounded extrapolation evidence.",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials/INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/method_algorithm_box.csv; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/method_complexity_boundary.csv",
            "manuscript_action": "Report the mechanism as vehicle-count flexible within the evaluated settings, not unbounded scalability.",
            "avoid_in_response": "Do not claim unlimited traffic density.",
        },
        {
            "id": "R04",
            "reviewer_concern": "The proposed method still has off-track/grass behavior.",
            "response_stance": "Acknowledge residual failures and use quality metrics rather than success-only claims.",
            "evidence_summary": f"v6-safe success={facts['safe_success']} vs DLC={facts['dlc_success']}; elegant={facts['safe_elegant']} vs {facts['dlc_elegant']}; grass={facts['safe_grass']} vs {facts['dlc_grass']}.",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/materials/FAILURE_ATLAS.md; outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/materials/CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md; outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_worst_case_cards.csv",
            "manuscript_action": "Keep failure atlas, casewise diagnostics and worst-case cards in Results/Supplement/Discussion.",
            "avoid_in_response": "Do not say the method always stays on track.",
        },
        {
            "id": "R05",
            "reviewer_concern": "Are the improvements actually about overtaking quality, not just speed?",
            "response_stance": "Emphasize start-to-completion time together with desirable/on-track and grass metrics.",
            "evidence_summary": f"Paired improvements vs DLC: success +{facts['success_delta']}, elegant +{facts['elegant_delta']}, completion-time improvement {facts['time_delta']} steps.",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv; outputs/tits_dynamic_graph/manuscript_english_figures/materials/FIGURE_DYNAMIC_DLC_OVERTAKING_LEGEND.md",
            "manuscript_action": "Present success, desirable/on-track rate, grass exposure and overtake completion time as a metric family.",
            "avoid_in_response": "Do not reduce the claim to fastest vehicle wins.",
        },
        {
            "id": "R06",
            "reviewer_concern": "Why is the rule expert competitive or stronger under some quality definitions?",
            "response_stance": "Frame the rule expert as a strong hand-engineered reference and discuss trade-offs.",
            "evidence_summary": f"Rule expert desirable overtaking behavior rate is {facts['rule_elegant']}; in threshold sensitivity its positive-delta fraction is {facts['rule_threshold_positive_fraction']}, so it should not be dismissed.",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md; outputs/tits_dynamic_graph/tits_baseline_fairness_audit/materials/BASELINE_FAIRNESS_AUDIT.md",
            "manuscript_action": "Discuss rule expert as a strong baseline and focus the novelty claim on world-model dynamic-neighborhood learning/planning.",
            "avoid_in_response": "Do not state that all rule-based methods are weak.",
        },
        {
            "id": "R07",
            "reviewer_concern": "Are the quality/desirable behavior metrics arbitrary threshold choices?",
            "response_stance": "Report predefined metrics and post-hoc threshold sensitivity separately.",
            "evidence_summary": f"v6-safe is positive over DLC in {facts['threshold_positive_fraction']} of sensitivity settings and nonnegative in {facts['threshold_nonnegative_fraction']}.",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md; outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/metric_dictionary.csv",
            "manuscript_action": "Use sensitivity analysis as robustness evidence and state that it is not preregistered.",
            "avoid_in_response": "Do not claim metric-threshold independence under every possible definition.",
        },
        {
            "id": "R08",
            "reviewer_concern": "Are p values and multiple endpoints handled properly?",
            "response_stance": "Lead with paired effect sizes and confidence intervals, then Holm-corrected primary tests.",
            "evidence_summary": "The statistical pack separates primary and exploratory families and reports effect sizes.",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/STATISTICAL_ANALYSIS_PLAN.md; outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv",
            "manuscript_action": "Keep the primary hypothesis family explicit in Methods and avoid cherry-picking exploratory rows.",
            "avoid_in_response": "Do not treat every exploratory p value as a confirmatory discovery.",
        },
        {
            "id": "R09",
            "reviewer_concern": "Could the main result be driven by one seed or case?",
            "response_stance": "Use the leave-one-case influence audit and disclose high-influence cases.",
            "evidence_summary": f"Leave-one-case audit preserves main-effect direction; maximum relative influence is {facts['max_case_relative_abs_influence']}.",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/case_influence_summary.csv",
            "manuscript_action": "Report high-influence cases as robustness boundaries in Supplement.",
            "avoid_in_response": "Do not imply uniform difficulty across all seeds/scenarios.",
        },
        {
            "id": "R10",
            "reviewer_concern": "Are baselines evaluated fairly under identical conditions?",
            "response_stance": "Point to matched-case source data and baseline fairness audit.",
            "evidence_summary": f"The formal matrix has {facts['source_rows']} source rows, {facts['algorithm_count']} algorithms and {facts['case_count']} matched cases.",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/materials/BASELINE_FAIRNESS_AUDIT.md; outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv",
            "manuscript_action": "Keep case/seed/traffic/termination controls explicit in Experiments.",
            "avoid_in_response": "Do not compare runs from different matrices as if they were matched.",
        },
        {
            "id": "R11",
            "reviewer_concern": "How can reviewers reproduce the results and know which outputs are formal?",
            "response_stance": "Use the reviewer packet, reproducibility capsule and public release plan as the response spine.",
            "evidence_summary": f"Final readiness is {facts['readiness']} PASS; formal matrix contains {facts['source_rows']} rows and {facts['sim_steps']} simulated steps.",
            "evidence_paths": "outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md; outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md; outputs/tits_dynamic_graph/public_release_plan/PUBLIC_RELEASE_PLAN.md; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/THIRD_PARTY_REPRODUCTION_PACK.md",
            "manuscript_action": "Add Data/Code Availability wording that separates smoke, reporting-layer checks, full matrix rerun, GIF generation and container-draft boundaries.",
            "avoid_in_response": "Do not call smoke, GIF-only outputs or unbuilt container drafts formal statistical evidence.",
        },
        {
            "id": "R12",
            "reviewer_concern": "Is compute cost transparent enough for reproduction?",
            "response_stance": "Report what is recorded and explicitly disclose what is not recorded.",
            "evidence_summary": f"Compute pack records {facts['sim_steps']} simulated steps, CUDA availability and {facts['gpu_count']} GPUs; wall-clock timing is marked unavailable.",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/materials/COMPUTE_REPRODUCIBILITY_COST_REPORT.md; outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_environment_snapshot.csv",
            "manuscript_action": "Include a reproducibility-cost table and limitation about missing wall-clock/GPU-utilization traces.",
            "avoid_in_response": "Do not claim complete historical wall-clock or utilization accounting.",
        },
        {
            "id": "R13",
            "reviewer_concern": "Are the GIFs representative evidence or statistical evidence?",
            "response_stance": "Use GIFs as qualitative visual evidence only.",
            "evidence_summary": "Publication GIFs include representative top-down and first-person runs, while statistics come from the 240-run source data.",
            "evidence_paths": "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.md; outputs/tits_dynamic_graph/tits_figure_source_data_audit/materials/FIGURE_SOURCE_DATA_AUDIT.md",
            "manuscript_action": "Label GIFs as Supplementary Videos or qualitative examples.",
            "avoid_in_response": "Do not infer aggregate success from a single GIF.",
        },
        {
            "id": "R14",
            "reviewer_concern": "What is the algorithmic novelty beyond tuning DLC?",
            "response_stance": "Tie each novelty claim to code, configuration and formal evidence.",
            "evidence_summary": "Innovation traceability maps dynamic neighborhood graph construction, DLC-style graph world model, overtake-aware planner, safety/quality scoring and quality proposal branch.",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials/INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/method_algorithm_box.csv; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/method_notation_table.csv; outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_REPORT.md",
            "manuscript_action": "Write the method as an optimized DLC world-model framework with explicit modules, Algorithm box, notation table and ablations.",
            "avoid_in_response": "Do not present the method as unrelated to the DLC world-model baseline.",
        },
        {
            "id": "R15",
            "reviewer_concern": "Is a built and tested container image available for third-party reproduction?",
            "response_stance": "State exactly what is available: Docker/Apptainer drafts and a local build preflight, not a certified image.",
            "evidence_summary": "Container preflight records that Docker/Apptainer/Singularity are not installed on the current server, nvidia-smi is available, draft files pass integrity checks, and no image was built.",
            "evidence_paths": "outputs/tits_dynamic_graph/tits_container_build_preflight/materials/CONTAINER_BUILD_PREFLIGHT.md; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/Dockerfile.draft; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/apptainer.def.draft; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/THIRD_PARTY_REPRODUCTION_PACK.md",
            "manuscript_action": "In Data/Code Availability, say container definitions are draft/preflight artifacts unless a future image build, GPU smoke test and digest are produced.",
            "avoid_in_response": "Do not claim a ready-to-run, digest-pinned, tested or certified container image exists.",
        },
    ]


def build_revision_actions(rows):
    return [
        {
            "section": "Abstract/Conclusion",
            "action": "Keep the headline claim bounded to evaluated multi-car simulation benchmarks.",
            "linked_rebuttal_ids": "R01; R02; R03",
            "priority": "high",
        },
        {
            "section": "Methods",
            "action": "Describe runtime dynamic-neighborhood construction, max-neighbor boundary, Algorithm box, notation table and complexity boundary.",
            "linked_rebuttal_ids": "R03; R14",
            "priority": "high",
        },
        {
            "section": "Experiments",
            "action": "State matched-case design, eight algorithms, seed/vehicle/track controls and baseline fairness checks.",
            "linked_rebuttal_ids": "R10",
            "priority": "high",
        },
        {
            "section": "Results",
            "action": "Report success, desirable/on-track rate, grass exposure and start-to-completion time together.",
            "linked_rebuttal_ids": "R04; R05; R07",
            "priority": "high",
        },
        {
            "section": "Statistics",
            "action": "Lead with paired effect sizes and confidence intervals; keep Holm-corrected primary family separate.",
            "linked_rebuttal_ids": "R08; R09",
            "priority": "high",
        },
        {
            "section": "Supplement",
            "action": "Include failure atlas, worst-case cards, metric sensitivity, leave-one-case, compute-cost and reproducibility tables.",
            "linked_rebuttal_ids": "R04; R07; R09; R11; R12",
            "priority": "high",
        },
        {
            "section": "Discussion",
            "action": "Discuss rule expert strength, residual off-track behavior, limited Monza external validity and no real-road certification.",
            "linked_rebuttal_ids": "R01; R02; R04; R06",
            "priority": "high",
        },
        {
            "section": "Data/Code Availability",
            "action": "Separate smoke tests, reporting-layer reproduction, full online matrix rerun, qualitative GIF generation and unbuilt container drafts/preflight.",
            "linked_rebuttal_ids": "R11; R12; R13; R15",
            "priority": "medium",
        },
        {
            "section": "Supplementary Reproducibility",
            "action": "Include container build preflight and explicitly state Docker/Apptainer runtime availability, GPU probe result, build_attempted=False and image_built=False.",
            "linked_rebuttal_ids": "R11; R15",
            "priority": "medium",
        },
    ]


def build_evidence_index(root, rows):
    seen = {}
    for row in rows:
        for item in [p.strip() for p in row["evidence_paths"].split(";") if p.strip()]:
            existing, missing = evidence_exists(root, item)
            seen[item] = {
                "evidence_path": item,
                "exists": bool(existing) and not missing,
                "used_by_rebuttal_ids": "",
            }
    for item in seen:
        ids = [row["id"] for row in rows if item in [p.strip() for p in row["evidence_paths"].split(";")]]
        seen[item]["used_by_rebuttal_ids"] = "; ".join(ids)
    return [seen[key] for key in sorted(seen)]


def build_markdown(report):
    lines = [
        "# T-ITS Reviewer Rebuttal Readiness Pack",
        "",
        "该材料面向 IEEE T-ITS 审稿意见准备，把可能出现的关键质疑映射到可引用证据、建议答复框架、主文修改动作和禁止夸大的边界。它不新增仿真实验结果。",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Rebuttal Matrix",
            "",
            "| ID | Reviewer concern | Response stance | Evidence summary | Manuscript action | Avoid |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["rebuttal_rows"]:
        lines.append(
            f"| {row['id']} | {row['reviewer_concern']} | {row['response_stance']} | {row['evidence_summary']} | {row['manuscript_action']} | {row['avoid_in_response']} |"
        )
    lines.extend(
        [
            "",
            "## High-Priority Manuscript Actions",
            "",
            "| Section | Action | Linked IDs | Priority |",
            "|---|---|---|---|",
        ]
    )
    for row in report["revision_actions"]:
        lines.append(f"| {row['section']} | {row['action']} | {row['linked_rebuttal_ids']} | {row['priority']} |")
    lines.extend(
        [
            "",
            "## Use Rules",
            "",
            "- 只把该材料作为 rebuttal 和 manuscript revision 的索引，不把它写成新增实验。",
            "- 若重跑确认性矩阵、修改指标阈值、增删 baseline 或更新图表，需要重新生成该包。",
            "- 证据路径必须优先指向正式 source data、审计包和补充材料，不引用 smoke 或 exploratory sweep 作为主证据。",
        ]
    )
    return "\n".join(lines)


def build_report(root):
    overall = read_csv(root / OVERALL)
    paired = read_csv(root / PAIRED)
    sensitivity = read_csv(root / METRIC_SENSITIVITY)
    design = read_json(root / DESIGN_MANIFEST)
    compute = read_json(root / COMPUTE_MANIFEST)
    readiness = read_json(root / READINESS)
    facts = build_facts(overall, paired, sensitivity, design, compute, readiness)
    rebuttal_rows = build_rebuttal_rows(facts)
    revision_actions = build_revision_actions(rebuttal_rows)
    evidence_index = build_evidence_index(root, rebuttal_rows)
    missing = [row["evidence_path"] for row in evidence_index if not row["exists"]]
    summary = {
        "status": "pass" if not missing and len(rebuttal_rows) >= 12 else "review_required",
        "rebuttal_question_count": len(rebuttal_rows),
        "revision_action_count": len(revision_actions),
        "evidence_path_count": len(evidence_index),
        "missing_evidence_count": len(missing),
        "formal_source_rows": facts["source_rows"],
        "formal_algorithm_count": facts["algorithm_count"],
        "formal_case_count": facts["case_count"],
        "final_readiness": facts["readiness"],
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "facts": facts,
        "rebuttal_rows": rebuttal_rows,
        "revision_actions": revision_actions,
        "evidence_index": evidence_index,
        "missing_evidence": missing,
    }


def main():
    parser = argparse.ArgumentParser(description="Export a reviewer rebuttal readiness pack for the T-ITS dynamic graph study.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    report = build_report(root)
    paths = {
        "pack_md": write_text(materials / "REVIEWER_REBUTTAL_READINESS_PACK.md", build_markdown(report)),
        "pack_json": write_json(materials / "REVIEWER_REBUTTAL_READINESS_PACK.json", report),
        "rebuttal_matrix_csv": write_csv(
            tables / "reviewer_rebuttal_matrix.csv",
            report["rebuttal_rows"],
            [
                "id",
                "reviewer_concern",
                "response_stance",
                "evidence_summary",
                "evidence_paths",
                "manuscript_action",
                "avoid_in_response",
            ],
        ),
        "revision_actions_csv": write_csv(
            tables / "manuscript_revision_action_items.csv",
            report["revision_actions"],
            ["section", "action", "linked_rebuttal_ids", "priority"],
        ),
        "evidence_index_csv": write_csv(
            tables / "reviewer_rebuttal_evidence_index.csv",
            report["evidence_index"],
            ["evidence_path", "exists", "used_by_rebuttal_ids"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_reviewer_rebuttal_readiness_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
