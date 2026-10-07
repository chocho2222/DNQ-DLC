#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import glob
import json
from pathlib import Path


SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
MAIN_TABLE = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_main_results.md"
FIGURE_TABLE_PLAN = "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/FIGURE_TABLE_PLACEMENT_PLAN.md"

EXPECTED_METRICS = {
    "overtake_success_rate",
    "on_track_overtake_rate",
    "elegant_overtake_rate",
    "rank_gain",
    "overtake_start_to_complete_time",
    "target_grass_rate",
    "grass_recovery_time_mean",
    "compute_latency_ms",
}


def read_text(path):
    path = Path(path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
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


def source_facts(root):
    rows = read_csv(root / SOURCE_DATA)
    cases = {
        (
            row.get("_benchmark"),
            row.get("seed"),
            row.get("num_agents"),
            row.get("track_path"),
            row.get("traffic_profile"),
        )
        for row in rows
    }
    algorithms = sorted({row.get("algorithm", "") for row in rows if row.get("algorithm")})
    benchmarks = sorted({row.get("_benchmark", "") for row in rows if row.get("_benchmark")})
    vehicle_counts = sorted({int(row.get("num_agents", 0) or 0) for row in rows})
    fields = set(rows[0].keys()) if rows else set()
    return {
        "source_rows": len(rows),
        "matched_case_count": len(cases),
        "algorithm_count": len(algorithms),
        "algorithms": algorithms,
        "benchmarks": benchmarks,
        "vehicle_counts": vehicle_counts,
        "missing_expected_metrics": sorted(EXPECTED_METRICS - fields),
    }


def table_specs():
    return [
        {
            "table_id": "Main Table 1",
            "title": "Online overtaking benchmark across algorithms, scenarios and vehicle counts.",
            "placement": "Main text",
            "primary_artifact": MAIN_TABLE,
            "source_patterns": [
                SOURCE_DATA,
                "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/tables/statistical_table_recompute_rows.csv",
                "outputs/tits_dynamic_graph/tits_results_reporting_checklist/tables/primary_hypothesis_reporting_checks.csv",
            ],
            "upstream_manifest": "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/tits_statistical_table_recompute_audit_manifest.json",
            "expected_status": "pass",
            "caption_boundary": "State that values come from the frozen 240-run online simulation source data; do not present the table as real-road validation.",
        },
        {
            "table_id": "Supplementary Table S1",
            "title": "Benchmark cases, algorithms and metric definitions.",
            "placement": "Supplementary methods",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/metric_dictionary.csv",
            "source_patterns": [
                "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/benchmark_cards.csv",
                "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv",
                "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/metric_dictionary.csv",
            ],
            "upstream_manifest": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tits_benchmark_protocol_pack_manifest.json",
            "expected_status": "complete",
            "caption_boundary": "Use this table to define the simulation benchmark, traffic profile and metrics before reporting results.",
        },
        {
            "table_id": "Supplementary Table S2",
            "title": "Primary statistical tests, Holm adjustment and effect sizes.",
            "placement": "Supplementary statistics",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv",
            "source_patterns": [
                "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv",
                "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_effect_sizes.csv",
                "outputs/tits_dynamic_graph/tits_results_reporting_checklist/tables/primary_hypothesis_reporting_checks.csv",
            ],
            "upstream_manifest": "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tits_statistical_analysis_pack_manifest.json",
            "expected_status": "complete",
            "caption_boundary": "Report paired design, confidence intervals, effect sizes and Holm-adjusted p-values together.",
        },
        {
            "table_id": "Supplementary Table S3",
            "title": "Baseline fairness and frozen case-command controls.",
            "placement": "Supplementary baselines",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tables/fairness_command_checks.csv",
            "source_patterns": [
                "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tables/fairness_command_checks.csv",
                "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tables/fairness_summary_run_checks.csv",
                "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv",
            ],
            "upstream_manifest": "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tits_baseline_fairness_audit_manifest.json",
            "expected_status": "pass",
            "caption_boundary": "Make clear that all algorithms share matched case conditions; do not imply the rule expert is a weak baseline.",
        },
        {
            "table_id": "Supplementary Table S4",
            "title": "Threats to validity, claim guardrails and limitation routing.",
            "placement": "Supplementary discussion",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_threats_validity_pack/tables/threats_validity_risk_register.csv",
            "source_patterns": [
                "outputs/tits_dynamic_graph/tits_threats_validity_pack/tables/threats_validity_risk_register.csv",
                "outputs/tits_dynamic_graph/tits_threats_validity_pack/tables/claim_language_guardrails.csv",
                "outputs/tits_dynamic_graph/tits_limitations_evidence_audit/tables/limitations_evidence_map.csv",
            ],
            "upstream_manifest": "outputs/tits_dynamic_graph/tits_threats_validity_pack/tits_threats_validity_pack_manifest.json",
            "expected_status": "complete",
            "caption_boundary": "Frame this table as a boundary and rebuttal aid, not as proof that all validity threats are resolved.",
        },
        {
            "table_id": "Supplementary Table S5",
            "title": "Runtime scalability, vehicle-count boundary and complexity.",
            "placement": "Supplementary runtime",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_scalability_by_vehicle_count.csv",
            "source_patterns": [
                "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_scalability_by_vehicle_count.csv",
                "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_complexity_crosswalk.csv",
                "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/tables/compute_timing_evidence_rows.csv",
            ],
            "upstream_manifest": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tits_runtime_scalability_pack_manifest.json",
            "expected_status": "pass",
            "caption_boundary": "Limit the scalability claim to the evaluated 4/5/6/8-vehicle simulations and max-neighbor setting.",
        },
        {
            "table_id": "Supplementary Table S6",
            "title": "Reproducibility tiers, compute environment and archive checksums.",
            "placement": "Supplementary reproducibility",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_reproduction_tiers.csv",
            "source_patterns": [
                "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_cost_by_algorithm.csv",
                "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_environment_snapshot.csv",
                "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_reproduction_tiers.csv",
                "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv",
            ],
            "upstream_manifest": "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tits_compute_reproducibility_cost_pack_manifest.json",
            "expected_status": "pass",
            "caption_boundary": "Separate smoke, reporting-layer rebuild, full 240-run reproduction and GIF reconstruction costs.",
        },
    ]


def resolve_patterns(root, patterns):
    resolved = []
    for pattern in patterns:
        matches = sorted(glob.glob(str(root / pattern)))
        resolved.extend(Path(match).relative_to(root).as_posix() for match in matches if Path(match).is_file())
    return sorted(dict.fromkeys(resolved))


def build_rows(root):
    facts = source_facts(root)
    plan_text = read_text(root / FIGURE_TABLE_PLAN)
    rows = []
    checks = []
    for spec in table_specs():
        primary_exists = (root / spec["primary_artifact"]).exists() and (root / spec["primary_artifact"]).stat().st_size > 0
        source_files = resolve_patterns(root, spec["source_patterns"])
        missing_patterns = [pattern for pattern in spec["source_patterns"] if not resolve_patterns(root, [pattern])]
        manifest = read_json(root / spec["upstream_manifest"])
        upstream_status = manifest.get("status")
        mentioned_in_plan = spec["table_id"] in plan_text or spec["placement"] in plan_text
        status = "pass" if primary_exists and source_files and not missing_patterns and upstream_status == spec["expected_status"] else "review_required"
        rows.append(
            {
                "table_id": spec["table_id"],
                "status": status,
                "title": spec["title"],
                "placement": spec["placement"],
                "primary_artifact": spec["primary_artifact"],
                "primary_exists": primary_exists,
                "source_file_count": len(source_files),
                "source_files": "; ".join(source_files),
                "missing_source_patterns": "; ".join(missing_patterns),
                "upstream_manifest": spec["upstream_manifest"],
                "upstream_status": upstream_status,
                "expected_upstream_status": spec["expected_status"],
                "mentioned_in_figure_table_plan": mentioned_in_plan,
                "caption_boundary": spec["caption_boundary"],
            }
        )
    checks.extend(
        [
            {
                "check_id": "TC_source_rows",
                "category": "main_table_source_data",
                "observed": str(facts["source_rows"]),
                "expected": "240",
                "status": "pass" if facts["source_rows"] == 240 else "review_required",
                "evidence": SOURCE_DATA,
            },
            {
                "check_id": "TC_matched_cases",
                "category": "main_table_source_data",
                "observed": str(facts["matched_case_count"]),
                "expected": "30",
                "status": "pass" if facts["matched_case_count"] == 30 else "review_required",
                "evidence": SOURCE_DATA,
            },
            {
                "check_id": "TC_algorithm_count",
                "category": "main_table_source_data",
                "observed": str(facts["algorithm_count"]),
                "expected": "8",
                "status": "pass" if facts["algorithm_count"] == 8 else "review_required",
                "evidence": SOURCE_DATA,
            },
            {
                "check_id": "TC_vehicle_counts",
                "category": "main_table_source_data",
                "observed": ",".join(str(item) for item in facts["vehicle_counts"]),
                "expected": "4,5,6,8",
                "status": "pass" if facts["vehicle_counts"] == [4, 5, 6, 8] else "review_required",
                "evidence": SOURCE_DATA,
            },
            {
                "check_id": "TC_metric_fields",
                "category": "main_table_source_data",
                "observed": ";".join(facts["missing_expected_metrics"]),
                "expected": "no missing expected metrics",
                "status": "pass" if not facts["missing_expected_metrics"] else "review_required",
                "evidence": SOURCE_DATA,
            },
            {
                "check_id": "TC_table_plan_mentions_main_and_supplement",
                "category": "caption_routing",
                "observed": "present" if "Main Table 1" in plan_text and "Supplement Table S1-S6" in plan_text else "missing",
                "expected": "Main Table 1 and Supplement Table S1-S6 are listed in placement plan",
                "status": "pass" if "Main Table 1" in plan_text and "Supplement Table S1-S6" in plan_text else "review_required",
                "evidence": FIGURE_TABLE_PLAN,
            },
        ]
    )
    return rows, checks, facts


def build_markdown(summary, rows, checks):
    lines = [
        "# Table Caption and Source-Data Audit",
        "",
        "This audit checks manuscript-facing tables, captions and source-data routes for the T-ITS dynamic-neighborhood DLC world-model package. It does not rerun simulations; it verifies that the main table and supplementary tables point to formal source data, upstream statistical/protocol material and bounded caption language.",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Table Map",
            "",
            "| Table | Status | Placement | Primary artifact | Source files | Upstream | Caption boundary |",
            "|---|---|---|---|---:|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['table_id']} | {row['status']} | {row['placement']} | `{row['primary_artifact']}` | "
            f"{row['source_file_count']} | {row['upstream_status']} via `{row['upstream_manifest']}` | {row['caption_boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Source-Data Checks",
            "",
            "| Check | Category | Observed | Expected | Status | Evidence |",
            "|---|---|---:|---:|---|---|",
        ]
    )
    for check in checks:
        lines.append(
            f"| {check['check_id']} | {check['category']} | {check['observed']} | "
            f"{check['expected']} | {check['status']} | `{check['evidence']}` |"
        )
    lines.extend(
        [
            "",
            "## Caption Guidance",
            "",
            "- Main Table 1 should state that values are from the frozen 240-run online simulation matrix.",
            "- Supplementary statistical tables should report N, paired design, confidence intervals, effect sizes and Holm-adjusted p-values together.",
            "- Baseline tables should explicitly preserve rule-expert strength and matched-case fairness controls.",
            "- Runtime tables should limit scalability claims to evaluated vehicle counts and the fixed dynamic-neighborhood budget.",
            "- Reproducibility tables should separate smoke checks from full matrix reproduction and visual-evidence reconstruction.",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export a table caption/source-data audit for the T-ITS dynamic graph package.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_table_caption_source_data_audit")
    args = parser.parse_args()

    root = Path(args.root)
    out_dir = Path(args.out_dir)
    rows, checks, facts = build_rows(root)
    issue_count = sum(row["status"] != "pass" for row in rows) + sum(check["status"] != "pass" for check in checks)
    status = "pass" if issue_count == 0 else "review_required"
    summary = {
        "status": status,
        "table_count": len(rows),
        "table_issue_count": sum(row["status"] != "pass" for row in rows),
        "check_count": len(checks),
        "check_issue_count": sum(check["status"] != "pass" for check in checks),
        "source_rows": facts["source_rows"],
        "matched_case_count": facts["matched_case_count"],
        "algorithm_count": facts["algorithm_count"],
        "vehicle_counts": facts["vehicle_counts"],
    }
    paths = {
        "markdown": write_text(out_dir / "materials" / "TABLE_CAPTION_SOURCE_DATA_AUDIT.md", build_markdown(summary, rows, checks)),
        "table_map_csv": write_csv(
            out_dir / "tables" / "table_caption_source_data_map.csv",
            rows,
            [
                "table_id",
                "status",
                "title",
                "placement",
                "primary_artifact",
                "primary_exists",
                "source_file_count",
                "source_files",
                "missing_source_patterns",
                "upstream_manifest",
                "upstream_status",
                "expected_upstream_status",
                "mentioned_in_figure_table_plan",
                "caption_boundary",
            ],
        ),
        "checks_csv": write_csv(
            out_dir / "tables" / "table_source_data_checks.csv",
            checks,
            ["check_id", "category", "observed", "expected", "status", "evidence"],
        ),
    }
    manifest = {
        "status": status,
        "out_dir": str(out_dir),
        "summary": summary,
        "paths": paths,
        "source_inputs": [
            SOURCE_DATA,
            MAIN_TABLE,
            FIGURE_TABLE_PLAN,
            "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/tables/manuscript_figure_table_plan.csv",
            "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/tits_statistical_table_recompute_audit_manifest.json",
            "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tits_benchmark_protocol_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tits_statistical_analysis_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tits_baseline_fairness_audit_manifest.json",
            "outputs/tits_dynamic_graph/tits_threats_validity_pack/tits_threats_validity_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tits_runtime_scalability_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tits_compute_reproducibility_cost_pack_manifest.json",
        ],
    }
    manifest_path = write_json(out_dir / "tits_table_caption_source_data_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
