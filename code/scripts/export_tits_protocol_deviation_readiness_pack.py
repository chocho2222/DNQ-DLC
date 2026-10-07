#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"

REQUIRED_EVIDENCE = {
    "benchmark_protocol": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/materials/BENCHMARK_METRIC_PROTOCOL_CARD.md",
    "statistical_analysis": "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/STATISTICAL_ANALYSIS_PLAN.md",
    "experimental_design": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md",
    "data_leakage": "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/materials/DATA_LEAKAGE_AND_TUNING_PROVENANCE_AUDIT.md",
    "baseline_fairness": "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/materials/BASELINE_FAIRNESS_AUDIT.md",
    "metric_sensitivity": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md",
    "external_validity": "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
    "gif_provenance": "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/materials/PUBLICATION_GIF_PROVENANCE_AUDIT.md",
    "casewise_worst_cards": "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_worst_case_cards.csv",
    "container_boundary": "outputs/tits_dynamic_graph/tits_container_build_preflight/materials/CONTAINER_BUILD_PREFLIGHT.md",
    "reviewer_rebuttal": "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/materials/REVIEWER_REBUTTAL_READINESS_PACK.md",
}

PRIMARY_METRICS = [
    ("overtake_success_rate", "Overtake success", "higher"),
    ("elegant_overtake_rate", "Desirable overtaking behavior", "higher"),
    ("on_track_overtake_rate", "On-track overtaking", "higher"),
    ("overtake_start_to_complete_time", "Overtake start-to-completion time", "lower"),
    ("target_grass_rate", "Target grass exposure", "lower"),
]


def read_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def case_key(row):
    return (
        row.get("_benchmark", ""),
        row.get("num_agents", ""),
        row.get("seed", ""),
        row.get("track_path", ""),
        row.get("traffic_profile", ""),
    )


def source_summary(rows):
    cases = {case_key(row) for row in rows}
    algorithms = sorted({row.get("algorithm", "") for row in rows if row.get("algorithm", "")})
    benchmarks = sorted({row.get("_benchmark", "") for row in rows if row.get("_benchmark", "")})
    vehicles = sorted({row.get("num_agents", "") for row in rows if row.get("num_agents", "")}, key=lambda item: int(item))
    scenario_cells = sorted({(row.get("_benchmark", ""), row.get("num_agents", "")) for row in rows})
    return {
        "source_rows": len(rows),
        "matched_case_count": len(cases),
        "algorithm_count": len(algorithms),
        "algorithms": algorithms,
        "benchmarks": benchmarks,
        "vehicle_counts": vehicles,
        "scenario_cell_count": len(scenario_cells),
    }


def evidence_role(key):
    roles = {
        "benchmark_protocol": "Defines frozen benchmarks, algorithms, fairness controls and metric dictionary.",
        "statistical_analysis": "Defines primary hypotheses, Holm correction, exploratory comparisons and effect-size reporting.",
        "experimental_design": "Audits matched-case coverage, conditional sample sizes and stability boundaries.",
        "data_leakage": "Separates formal confirmatory evidence from exploratory tuning and smoke outputs.",
        "baseline_fairness": "Checks matched seeds, tracks, traffic, target start order and algorithm coverage.",
        "metric_sensitivity": "Audits post-hoc quality-threshold sensitivity and claim boundaries.",
        "external_validity": "Constrains simulation, Monza and vehicle-count generalization claims.",
        "gif_provenance": "Separates representative visual evidence from statistical performance claims.",
        "casewise_worst_cards": "Makes residual failures and tail cases visible for Discussion/Supplement.",
        "container_boundary": "States that container files are drafts unless an image digest is recorded.",
        "reviewer_rebuttal": "Maps likely reviewer questions to evidence paths and conservative writing actions.",
    }
    return roles.get(key, "")


def evidence_rows(root):
    rows = []
    for key, path in REQUIRED_EVIDENCE.items():
        full = root / path
        rows.append(
            {
                "evidence_key": key,
                "path": path,
                "exists": full.exists(),
                "nonempty": full.exists() and full.stat().st_size > 0,
                "role": evidence_role(key),
            }
        )
    return rows


def protocol_summary_rows(summary):
    return [
        {
            "item": "formal_matrix",
            "value": f"{summary['source_rows']} rows, {summary['matched_case_count']} matched cases, {summary['algorithm_count']} algorithms",
            "evidence": SOURCE_DATA,
            "interpretation": "All confirmatory claims should be traced to this frozen online benchmark matrix.",
        },
        {
            "item": "benchmark_scope",
            "value": ";".join(summary["benchmarks"]),
            "evidence": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/materials/BENCHMARK_METRIC_PROTOCOL_CARD.md",
            "interpretation": "Evidence covers procedural, Monza external-track and vehicle-count extrapolation simulator settings.",
        },
        {
            "item": "vehicle_scope",
            "value": ";".join(summary["vehicle_counts"]),
            "evidence": "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "interpretation": "Dynamic-neighborhood scalability claims should be bounded by the evaluated vehicle counts.",
        },
        {
            "item": "algorithm_scope",
            "value": ";".join(summary["algorithms"]),
            "evidence": "outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit/materials/ALGORITHM_CONFIG_FREEZE_AUDIT.md",
            "interpretation": "The proposed method is evaluated against DLC world-model variants and the rule baseline in the same matched cases.",
        },
    ]


def endpoint_rows():
    rows = []
    for idx, (metric, label, direction) in enumerate(PRIMARY_METRICS, start=1):
        rows.append(
            {
                "endpoint_id": f"P{idx}",
                "tier": "primary_confirmatory",
                "metric": metric,
                "display_name": label,
                "comparison": "v6_runtime_dynamic_neighborhood_safe vs dlc_world_original",
                "direction": direction,
                "analysis_rule": "matched-case paired contrast with bootstrap 95% CI and Holm-adjusted primary family where available",
                "claim_boundary": "Supports simulator benchmark claim only; do not convert to real-road safety or universal driving claim.",
            }
        )
    rows.extend(
        [
            {
                "endpoint_id": "S1",
                "tier": "secondary_confirmatory",
                "metric": "scenario-level primary metrics",
                "display_name": "Scenario heterogeneity",
                "comparison": "primary method vs original DLC within benchmark/vehicle-count cells",
                "direction": "metric-specific",
                "analysis_rule": "report scenario means and paired signs rather than relying only on pooled means",
                "claim_boundary": "Use for robustness and heterogeneity discussion, not as independent extra powering.",
            },
            {
                "endpoint_id": "S2",
                "tier": "secondary_confirmatory",
                "metric": "rank_gain; target_completed_lap; compute_latency_ms",
                "display_name": "Race outcome and runtime support",
                "comparison": "all formal algorithms",
                "direction": "metric-specific",
                "analysis_rule": "supporting descriptive statistics with source-data provenance",
                "claim_boundary": "Support feasibility and race-outcome interpretation; not the main safety endpoint.",
            },
            {
                "endpoint_id": "E1",
                "tier": "exploratory_explanatory",
                "metric": "GIF/case-study timelines and worst-case cards",
                "display_name": "Online behavior explanation",
                "comparison": "representative matched cases",
                "direction": "not applicable",
                "analysis_rule": "qualitative/provenance-backed explanation of decision behavior and failure cases",
                "claim_boundary": "Use for interpretation only; formal performance claims must cite the 240-run source data.",
            },
        ]
    )
    return rows


def population_rule_rows():
    return [
        {
            "rule_id": "A1",
            "rule": "analysis_population",
            "definition": "All rows in the frozen source CSV are included in formal aggregate statistics.",
            "evidence": SOURCE_DATA,
            "exclusion_policy": "No row-level exclusion after source-data freeze unless a provenance audit marks the run invalid.",
        },
        {
            "rule_id": "A2",
            "rule": "matched_case_unit",
            "definition": "The matched case is benchmark, vehicle count, seed, track path and traffic profile.",
            "evidence": "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/materials/BASELINE_FAIRNESS_AUDIT.md",
            "exclusion_policy": "A case should not be used for paired claims unless both compared algorithms are present.",
        },
        {
            "rule_id": "A3",
            "rule": "conditional_completion_time",
            "definition": "Overtake start-to-completion time is analyzed only when the relevant overtake window and completion event exist.",
            "evidence": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/sample_size_and_power_wording_boundary.csv",
            "exclusion_policy": "Report conditional n explicitly; do not treat it as all 30 matched cases.",
        },
        {
            "rule_id": "A4",
            "rule": "visual_evidence_population",
            "definition": "Publication GIFs and case-study windows are representative visual/provenance evidence.",
            "evidence": "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/materials/PUBLICATION_GIF_PROVENANCE_AUDIT.md",
            "exclusion_policy": "Do not use GIF-only outcomes as aggregate performance evidence.",
        },
    ]


def deviation_rows():
    return [
        {
            "deviation_id": "D0",
            "classification": "transparent_boundary",
            "item": "No prospective preregistration claim",
            "risk_if_unstated": "Reviewers may misread the audit as an a priori power analysis or preregistration.",
            "mitigation": "State that the design/power audit is descriptive and source-data-locked, not a prospective MDE analysis.",
            "evidence": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/sample_size_and_power_wording_boundary.csv",
            "blocking": False,
        },
        {
            "deviation_id": "D1",
            "classification": "controlled_boundary",
            "item": "Exploratory tuning outputs exist outside the formal matrix",
            "risk_if_unstated": "Exploratory or smoke outputs could be confused with confirmatory results.",
            "mitigation": "Use data-leakage/tuning audit and cross-reference guardrails to separate formal and exploratory artifacts.",
            "evidence": "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/materials/DATA_LEAKAGE_AND_TUNING_PROVENANCE_AUDIT.md",
            "blocking": False,
        },
        {
            "deviation_id": "D2",
            "classification": "controlled_boundary",
            "item": "Quality thresholds and desirable-overtaking-behavior thresholds require sensitivity wording",
            "risk_if_unstated": "A single threshold could look like post-hoc metric cherry-picking.",
            "mitigation": "Report threshold sensitivity and use conservative language around desirable/on-track quality claims.",
            "evidence": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md",
            "blocking": False,
        },
        {
            "deviation_id": "D3",
            "classification": "controlled_boundary",
            "item": "Residual grass/off-track and passes that do not satisfy desirable overtaking behavior criteria remain",
            "risk_if_unstated": "The method could be overstated as always safe or always elegant.",
            "mitigation": "Use worst-case cards, failure atlas and safety proxy audit to report tail failures transparently.",
            "evidence": "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_worst_case_cards.csv",
            "blocking": False,
        },
        {
            "deviation_id": "D4",
            "classification": "controlled_boundary",
            "item": "Representative GIFs are not statistical samples",
            "risk_if_unstated": "Visual examples could be mistaken for performance estimates.",
            "mitigation": "GIF provenance explicitly links examples to formal rows while keeping statistics in source data.",
            "evidence": "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/materials/PUBLICATION_GIF_PROVENANCE_AUDIT.md",
            "blocking": False,
        },
        {
            "deviation_id": "D5",
            "classification": "controlled_boundary",
            "item": "Container material is a draft without recorded image digest",
            "risk_if_unstated": "A reviewer could assume the container image was built and certified.",
            "mitigation": "Container preflight and data/code availability draft state the build-digest boundary.",
            "evidence": "outputs/tits_dynamic_graph/tits_container_build_preflight/materials/CONTAINER_BUILD_PREFLIGHT.md",
            "blocking": False,
        },
        {
            "deviation_id": "D6",
            "classification": "claim_boundary",
            "item": "External validity is bounded by simulator tracks and evaluated traffic density",
            "risk_if_unstated": "The paper could overclaim real-world deployment or arbitrary traffic generalization.",
            "mitigation": "External-validity audit and claim-language audit enforce simulator-only, Monza-only and max-vehicle wording.",
            "evidence": "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "blocking": False,
        },
    ]


def guardrail_rows():
    return [
        {
            "claim_area": "algorithm_novelty",
            "allowed_wording": "optimized DLC world-model framework with runtime dynamic-neighborhood graph construction and overtaking-aware safety/quality scoring",
            "avoid_wording": "entirely unrelated to DLC, universally optimal, or guaranteed safe",
            "evidence": "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials/INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md",
        },
        {
            "claim_area": "multi_vehicle_generalization",
            "allowed_wording": "vehicle-count flexible within the evaluated 4/5/6/8-vehicle simulator settings",
            "avoid_wording": "arbitrary number of vehicles without any density or compute boundary",
            "evidence": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md",
        },
        {
            "claim_area": "overtaking_quality",
            "allowed_wording": "improves success, on-track/desirable overtaking and grass-exposure metrics on the frozen matrix while retaining transparent failures",
            "avoid_wording": "always overtakes with desirable behavior or never leaves the track",
            "evidence": "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/materials/CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md",
        },
        {
            "claim_area": "reproducibility",
            "allowed_wording": "provides tiered smoke, report rebuild, full 240-run rerun and GIF regeneration routes with artifact checksums",
            "avoid_wording": "container-certified or one-command full reproduction unless a built image digest and runtime log are recorded",
            "evidence": "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/materials/REVIEWER_REPRODUCTION_TIME_BUDGET_AUDIT.md",
        },
    ]


def build_markdown(summary, endpoints, populations, deviations, guardrails, evidence, paths):
    lines = [
        "# Confirmatory Protocol and Deviation Readiness Pack",
        "",
        "This pack consolidates the source-data-locked experimental protocol, endpoint hierarchy, analysis population, controlled deviations and claim guardrails for IEEE T-ITS-style review. It does not create new simulation results; it links existing formal evidence into a reviewer-readable protocol boundary.",
        "",
        "## Formal Matrix",
        "",
        f"- Source rows: {summary['source_rows']}",
        f"- Matched cases: {summary['matched_case_count']}",
        f"- Algorithms: {summary['algorithm_count']}",
        f"- Benchmarks: {', '.join(summary['benchmarks'])}",
        f"- Vehicle counts: {', '.join(summary['vehicle_counts'])}",
        "",
        "## Endpoint Hierarchy",
        "",
        "| ID | Tier | Metric | Comparison | Direction | Boundary |",
        "|---|---|---|---|---|---|",
    ]
    for row in endpoints:
        lines.append(f"| {row['endpoint_id']} | {row['tier']} | `{row['metric']}` | {row['comparison']} | {row['direction']} | {row['claim_boundary']} |")
    lines.extend(["", "## Analysis Population Rules", "", "| Rule | Definition | Exclusion policy | Evidence |", "|---|---|---|---|"])
    for row in populations:
        lines.append(f"| {row['rule_id']} | {row['definition']} | {row['exclusion_policy']} | `{row['evidence']}` |")
    lines.extend(["", "## Controlled Deviations and Boundaries", "", "| ID | Classification | Item | Mitigation | Blocking | Evidence |", "|---|---|---|---|---|---|"])
    for row in deviations:
        lines.append(f"| {row['deviation_id']} | {row['classification']} | {row['item']} | {row['mitigation']} | {row['blocking']} | `{row['evidence']}` |")
    lines.extend(["", "## Claim Guardrails", "", "| Claim area | Allowed wording | Avoid wording | Evidence |", "|---|---|---|---|"])
    for row in guardrails:
        lines.append(f"| {row['claim_area']} | {row['allowed_wording']} | {row['avoid_wording']} | `{row['evidence']}` |")
    lines.extend(["", "## Evidence Availability", "", "| Evidence key | Exists | Nonempty | Role | Path |", "|---|---|---|---|---|"])
    for row in evidence:
        lines.append(f"| {row['evidence_key']} | {row['exists']} | {row['nonempty']} | {row['role']} | `{row['path']}` |")
    lines.extend(["", "## Generated Files", ""])
    for key, path in paths.items():
        lines.append(f"- {key}: `{path}`")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export a protocol/deviation readiness pack for the T-ITS dynamic DLC evidence chain.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack")
    parser.add_argument("--source-csv", default=SOURCE_DATA)
    args = parser.parse_args()

    root = Path(".")
    out_dir = Path(args.out_dir)
    tables_dir = out_dir / "tables"
    materials_dir = out_dir / "materials"
    tables_dir.mkdir(parents=True, exist_ok=True)
    materials_dir.mkdir(parents=True, exist_ok=True)

    source_rows = read_csv(args.source_csv)
    summary = source_summary(source_rows)
    endpoints = endpoint_rows()
    populations = population_rule_rows()
    deviations = deviation_rows()
    guardrails = guardrail_rows()
    evidence = evidence_rows(root)

    paths = {}
    paths["protocol_summary_csv"] = write_csv(tables_dir / "confirmatory_protocol_summary.csv", protocol_summary_rows(summary), ["item", "value", "evidence", "interpretation"])
    paths["endpoint_hierarchy_csv"] = write_csv(tables_dir / "endpoint_hierarchy.csv", endpoints, ["endpoint_id", "tier", "metric", "display_name", "comparison", "direction", "analysis_rule", "claim_boundary"])
    paths["analysis_population_rules_csv"] = write_csv(tables_dir / "analysis_population_rules.csv", populations, ["rule_id", "rule", "definition", "evidence", "exclusion_policy"])
    paths["protocol_deviation_register_csv"] = write_csv(tables_dir / "protocol_deviation_register.csv", deviations, ["deviation_id", "classification", "item", "risk_if_unstated", "mitigation", "evidence", "blocking"])
    paths["claim_guardrails_csv"] = write_csv(tables_dir / "protocol_claim_guardrails.csv", guardrails, ["claim_area", "allowed_wording", "avoid_wording", "evidence"])
    paths["evidence_availability_csv"] = write_csv(tables_dir / "protocol_evidence_availability.csv", evidence, ["evidence_key", "path", "exists", "nonempty", "role"])
    paths["report_md"] = write_text(materials_dir / "PROTOCOL_DEVIATION_READINESS_REPORT.md", build_markdown(summary, endpoints, populations, deviations, guardrails, evidence, paths))

    missing = [row for row in evidence if not row["exists"] or not row["nonempty"]]
    blocking = [row for row in deviations if row["blocking"]]
    ok = (
        summary["source_rows"] == summary["matched_case_count"] * summary["algorithm_count"]
        and summary["source_rows"] == 240
        and summary["matched_case_count"] == 30
        and summary["algorithm_count"] == 8
        and not missing
        and not blocking
    )
    manifest = {
        "status": "pass" if ok else "check",
        "out_dir": str(out_dir),
        "paths": paths,
        "summary": {
            **summary,
            "primary_endpoint_count": len(PRIMARY_METRICS),
            "endpoint_count": len(endpoints),
            "population_rule_count": len(populations),
            "protocol_boundary_count": len(deviations),
            "blocking_deviation_count": len(blocking),
            "evidence_path_count": len(evidence),
            "missing_evidence_count": len(missing),
        },
        "boundary": "This is a source-data-locked protocol/deviation readiness pack, not a prospective preregistration.",
    }
    manifest_path = write_json(out_dir / "tits_protocol_deviation_readiness_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
