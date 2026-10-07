#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


FORMAL_SCAN_DIRS = [
    "outputs/tits_dynamic_graph/tits_manuscript_package",
    "outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit",
    "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit",
    "outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit",
    "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator",
    "outputs/tits_dynamic_graph/tits_numbering_consistency_audit",
    "outputs/tits_dynamic_graph/tits_figure_source_data_audit",
    "outputs/tits_dynamic_graph/tits_media_upload_quality_audit",
    "outputs/tits_dynamic_graph/manuscript_english_figures",
    "outputs/tits_dynamic_graph/tits_ablation_contribution_pack",
    "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack",
    "outputs/tits_dynamic_graph/tits_baseline_fairness_audit",
    "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack",
    "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack",
    "outputs/tits_dynamic_graph/tits_statistical_analysis_pack",
    "outputs/tits_dynamic_graph/tits_experimental_design_power_audit",
    "outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit",
    "outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit",
    "outputs/tits_dynamic_graph/tits_root_readme_alignment_audit",
    "outputs/tits_dynamic_graph/tits_refresh_coverage_audit",
    "outputs/tits_dynamic_graph/tits_status_snapshot",
    "outputs/tits_dynamic_graph/tits_evidence_ledger",
    "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit",
    "outputs/tits_dynamic_graph/tits_checksum_verification_audit",
    "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit",
    "outputs/tits_dynamic_graph/tits_limitations_evidence_audit",
    "outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack",
    "outputs/tits_dynamic_graph/tits_threats_validity_pack",
    "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack",
    "outputs/tits_dynamic_graph/tits_runtime_scalability_pack",
    "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack",
    "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit",
    "outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit",
    "outputs/tits_dynamic_graph/tits_claim_language_audit",
    "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit",
    "outputs/tits_dynamic_graph/reviewer_replication_packet",
    "outputs/tits_dynamic_graph/tits_source_data_integrity_audit",
    "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack",
    "outputs/tits_dynamic_graph/tits_run_level_provenance_audit",
    "outputs/tits_dynamic_graph/tits_trace_integrity_audit",
    "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack",
    "outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit",
    "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit",
    "outputs/tits_dynamic_graph/tits_results_reporting_checklist",
    "outputs/tits_dynamic_graph/tits_results_narrative_pack",
    "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit",
    "outputs/tits_dynamic_graph/tits_figure_caption_claim_audit",
    "outputs/tits_dynamic_graph/tits_table_caption_source_data_audit",
    "outputs/tits_dynamic_graph/tits_table_value_recompute_audit",
    "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit",
    "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack",
    "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack",
    "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack",
    "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack",
    "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack",
    "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack",
    "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit",
    "outputs/tits_dynamic_graph/tits_determinism_smoke_audit",
    "outputs/tits_dynamic_graph/tits_reproducibility_capsule",
    "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit",
    "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability",
    "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit",
    "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit",
    "outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit",
    "outputs/tits_dynamic_graph/public_release_plan",
    "outputs/tits_dynamic_graph/final_readiness_dashboard",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack",
    "outputs/tits_dynamic_graph/tits_github_release_readiness_pack",
    "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit",
    "outputs/tits_dynamic_graph/tits_author_submission_closure_pack",
    "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit",
    "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit",
    "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack",
    "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack",
    "outputs/tits_dynamic_graph/tits_freshness_audit",
    "outputs/tits_dynamic_graph/tits_container_build_preflight",
    "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map",
    "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist",
    "outputs/tits_dynamic_graph/tits_submission_gap_priority_audit",
    "outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit",
    "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit",
    "outputs/tits_dynamic_graph/tits_dependency_license_audit",
    ]

SCAN_SUFFIXES = {".md", ".csv"}
SKIP_SCAN_FILES = {
    "outputs/tits_dynamic_graph/public_release_plan/public_release_file_plan.csv",
    "outputs/tits_dynamic_graph/public_release_plan/public_release_directory_plan.csv",
    "outputs/tits_dynamic_graph/tits_claim_language_audit/tables/claim_language_scan_rows.csv",
    "outputs/tits_dynamic_graph/tits_freshness_audit/materials/FRESHNESS_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_freshness_audit/tables/freshness_scan_rows.csv",
    "outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit/tables/ai_tool_use_scan_hits.csv",
    "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/materials/ANONYMIZATION_PRIVACY_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/tables/anonymization_privacy_scan_rows.csv",
}

PATH_PATTERN = re.compile(
    r"(?P<path>(?:outputs/tits_dynamic_graph|outputs/paper_multicar_overtake_20260618|configs|docs|scripts|dlc|gym_multi_car_racing|tracks)/"
    r"[\w./*\-\[\]{}?]+)"
)

BOUNDARY_MARKERS = [
    "do not cite",
    "do not upload",
    "not formal",
    "not a paper-scale result",
    "local-only",
    "exclude",
    "excluded",
    "do not present",
    "不要",
    "不应",
    "不建议",
    "只用于",
    "调参",
    "历史",
    "早期",
    "中间结果",
    "不是正式",
    "不能",
    "优先引用",
    "routed away from the minimal code repository",
    "exclude_from_public_release",
    "internal_only",
    "keep local provenance",
    "legacy_or_superseded_output",
    "needed_new_script",
    "needed_new_runner",
    "planned",
]

RISKY_SEGMENTS = [
    "outputs/tits_dynamic_graph/smoke",
    "/smoke/",
    "_smoke/",
    "optimization_checks",
    "partial_summary",
    "outputs/tits_dynamic_graph/quality_aux",
    "outputs/tits_dynamic_graph/quality_guided",
    "outputs/tits_dynamic_graph/quality_graph_bc",
    "outputs/tits_dynamic_graph/quality_metric_checks",
    "outputs/tits_dynamic_graph/elegant_dataset",
    "outputs/tits_dynamic_graph/elegant_graph_bc",
    "outputs/tits_dynamic_graph/quality_proposal_dlc_v2",
    "outputs/tits_dynamic_graph/online_evaluation_matrix_quality",
    "outputs/tits_dynamic_graph/online_evaluation_matrix",
    "outputs/tits_dynamic_graph/online_planner_patch_smoke",
    "outputs/tits_dynamic_graph/overtake_planner_ablation_smoke",
    "outputs/tits_dynamic_graph/config_driven_eval_smoke",
    "outputs/tits_dynamic_graph/v6_planner_budget",
]

FORMAL_PREFIXES = [
    "outputs/tits_dynamic_graph/models/",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix/",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/",
    "outputs/tits_dynamic_graph/v6_confirmatory_preflight/",
    "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/",
    "outputs/tits_dynamic_graph/publication_gifs/",
    "outputs/tits_dynamic_graph/reviewer_replication_packet/",
    "outputs/tits_dynamic_graph/tits_manuscript_package/",
    "outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/",
    "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/",
    "outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit/",
    "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/",
    "outputs/tits_dynamic_graph/tits_numbering_consistency_audit/",
    "outputs/tits_dynamic_graph/tits_figure_source_data_audit/",
    "outputs/tits_dynamic_graph/tits_media_upload_quality_audit/",
    "outputs/tits_dynamic_graph/manuscript_english_figures/",
    "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/",
    "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/",
    "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/",
    "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/",
    "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/",
    "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/",
    "outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit/",
    "outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit/",
    "outputs/tits_dynamic_graph/tits_root_readme_alignment_audit/",
    "outputs/tits_dynamic_graph/tits_refresh_coverage_audit/",
    "outputs/tits_dynamic_graph/tits_status_snapshot/",
    "outputs/tits_dynamic_graph/tits_evidence_ledger/",
    "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/",
    "outputs/tits_dynamic_graph/tits_checksum_verification_audit/",
    "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/",
    "outputs/tits_dynamic_graph/tits_limitations_evidence_audit/",
    "outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/",
    "outputs/tits_dynamic_graph/tits_threats_validity_pack/",
    "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/",
    "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/",
    "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/",
    "outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack/",
    "outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack/",
    "outputs/tits_dynamic_graph/tits_v7_elegance_barrier_design_pack/",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_smoke/",
    "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/",
    "outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit/",
    "outputs/tits_dynamic_graph/tits_claim_language_audit/",
    "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/",
    "outputs/tits_dynamic_graph/tits_cross_reference_audit/",
    "outputs/tits_dynamic_graph/tits_source_data_integrity_audit/",
    "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/",
    "outputs/tits_dynamic_graph/tits_run_level_provenance_audit/",
    "outputs/tits_dynamic_graph/tits_trace_integrity_audit/",
    "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/",
    "outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/",
    "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/",
    "outputs/tits_dynamic_graph/tits_results_reporting_checklist/",
    "outputs/tits_dynamic_graph/tits_results_narrative_pack/",
    "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/",
    "outputs/tits_dynamic_graph/tits_figure_caption_claim_audit/",
    "outputs/tits_dynamic_graph/tits_table_caption_source_data_audit/",
    "outputs/tits_dynamic_graph/tits_table_value_recompute_audit/",
    "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/",
    "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/",
    "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/",
    "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/",
    "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/",
    "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/",
    "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack/",
    "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/",
    "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/",
    "outputs/tits_dynamic_graph/tits_reproducibility_capsule/",
    "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/",
    "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/",
    "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/",
    "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/",
    "outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit/",
    "outputs/paper_multicar_overtake_20260618/models/",
    "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model/",
    "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/",
    "outputs/tits_dynamic_graph/public_release_plan/",
    "outputs/tits_dynamic_graph/final_readiness_dashboard/",
    "outputs/tits_dynamic_graph/ieee_tits_compliance/",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack/",
    "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/",
    "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/",
    "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/",
    "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/",
    "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/",
    "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/",
    "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/",
    "outputs/tits_dynamic_graph/tits_freshness_audit/",
    "outputs/tits_dynamic_graph/tits_container_build_preflight/",
    "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/",
    "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/",
    "outputs/tits_dynamic_graph/tits_submission_gap_priority_audit/",
    "outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit/",
    "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/",
    "outputs/tits_dynamic_graph/tits_dependency_license_audit/",
    "outputs/tits_dynamic_graph/artifact_manifest/",
    "outputs/tits_dynamic_graph_cleanup/",
    "configs/",
    "docs/",
    "scripts/",
    "dlc/",
    "gym_multi_car_racing/",
    "tracks/",
]

FORMAL_FILES = {
    "outputs/tits_dynamic_graph/tits_readiness_audit.json",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_run_summary.json",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_run_results_ledger.csv",
    "outputs/tits_dynamic_graph/train_summary.json",
}


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


def discover_scan_files(root):
    files = []
    for rel in FORMAL_SCAN_DIRS:
        base = root / rel
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            rel = path.relative_to(root).as_posix()
            if path.is_file() and path.suffix in SCAN_SUFFIXES and rel not in SKIP_SCAN_FILES:
                files.append(path)
    return files


def clean_path(raw):
    return raw.strip().rstrip("`'\".,);:")


def line_context(text, start):
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end].strip()
    return line, text.count("\n", 0, start) + 1


def is_boundary_context(line):
    lowered = line.lower()
    return any(marker in lowered for marker in BOUNDARY_MARKERS)


def is_risky_path(path):
    if path == "outputs/tits_dynamic_graph/reviewer_replication_packet/run_reviewer_smoke.sh":
        return False
    if path.startswith("outputs/tits_dynamic_graph/tits_determinism_smoke_audit/"):
        return False
    lowered = path.lower()
    return any(segment in lowered for segment in RISKY_SEGMENTS)


def is_planned_future_script(source_file, path, line):
    return (
        source_file.startswith("outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack/")
        and path.startswith("scripts/")
        and ("needed_new_script" in line or "needed_new_runner" in line)
    )


def is_formal_prefix(path):
    return path in FORMAL_FILES or any(path.startswith(prefix) or path == prefix.rstrip("/") for prefix in FORMAL_PREFIXES)


def resolve_reference(root, path):
    if "*" in path or "?" in path or "[" in path:
        matches = sorted(root.glob(path))
        return bool(matches), len(matches), "glob"
    full = root / path
    return full.exists(), 1 if full.exists() else 0, "path"


def collect_references(root):
    rows = []
    seen = set()
    for file_path in discover_scan_files(root):
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_file = file_path.relative_to(root).as_posix()
        for match in PATH_PATTERN.finditer(text):
            ref = clean_path(match.group("path"))
            line, number = line_context(text, match.start())
            key = (rel_file, number, ref)
            if key in seen:
                continue
            seen.add(key)
            exists, match_count, ref_type = resolve_reference(root, ref)
            risky = is_risky_path(ref)
            boundary = is_boundary_context(line)
            planned_future_script = is_planned_future_script(rel_file, ref, line)
            if not exists and (boundary and (risky or planned_future_script)):
                status = "boundary_reference"
            elif not exists:
                status = "missing"
            elif boundary and (risky or not is_formal_prefix(ref)):
                status = "boundary_reference"
            elif risky:
                status = "risky_formal_reference"
            elif not is_formal_prefix(ref):
                status = "unknown_prefix"
            else:
                status = "pass"
            rows.append(
                {
                    "source_file": rel_file,
                    "line": number,
                    "reference": ref,
                    "reference_type": ref_type,
                    "exists": exists,
                    "match_count": match_count,
                    "risky_path": risky,
                    "boundary_context": boundary,
                    "status": status,
                    "line_text": line[:500],
                }
            )
    return rows


def summarize(rows, source_files, upstream):
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    blocking_statuses = {"missing", "risky_formal_reference", "unknown_prefix"}
    blocking = [row for row in rows if row["status"] in blocking_statuses]
    return {
        "status": "pass" if not blocking else "review_required",
        "scanned_file_count": len(source_files),
        "reference_count": len(rows),
        "unique_reference_count": len({row["reference"] for row in rows}),
        "missing_reference_count": counts.get("missing", 0),
        "risky_formal_reference_count": counts.get("risky_formal_reference", 0),
        "boundary_reference_count": counts.get("boundary_reference", 0),
        "unknown_prefix_count": counts.get("unknown_prefix", 0),
        "status_counts": dict(sorted(counts.items())),
        "upstream_status": upstream,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Formal Cross-Reference Audit",
        "",
        "该审计扫描当前 T-ITS 正式材料中的文件路径引用，检查路径是否存在，并识别是否把 smoke、调参、partial summary 等非正式产物误写成正式证据。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `pass`: 路径存在，且属于正式证据、代码、配置或轨道文件前缀。",
            "- `boundary_reference`: 引用了高风险/非正式/发布分流产物，但上下文明确写作“不应引用、只用于 smoke、调参、历史产物或从最小代码仓库分流”，因此作为边界说明保留。",
            "- `missing`: 路径不存在，需要修正文档或补齐文件。",
            "- `risky_formal_reference`: 高风险/非正式产物被当成普通证据引用，需要改写为边界说明或移除。",
            "- `unknown_prefix`: 引用前缀不在当前正式发布规则中，需要人工确认。",
            "",
            "## Blocking Rows",
            "",
        ]
    )
    blocking = [
        row
        for row in report["rows"]
        if row["status"] in {"missing", "risky_formal_reference", "unknown_prefix"}
    ]
    if not blocking:
        lines.append("No blocking cross-reference issues were found.")
    else:
        lines.extend(["| status | source | line | reference | context |", "|---|---|---:|---|---|"])
        for row in blocking:
            lines.append(
                f"| {row['status']} | `{row['source_file']}` | {row['line']} | `{row['reference']}` | {row['line_text']} |"
            )
    lines.extend(
        [
            "",
            "## Boundary References",
            "",
        ]
    )
    boundary_rows = [row for row in report["rows"] if row["status"] == "boundary_reference"]
    if not boundary_rows:
        lines.append("No boundary-only risky references were found.")
    else:
        lines.extend(["| source | line | reference | context |", "|---|---:|---|---|"])
        for row in boundary_rows[:80]:
            lines.append(f"| `{row['source_file']}` | {row['line']} | `{row['reference']}` | {row['line_text']} |")
        if len(boundary_rows) > 80:
            lines.append(f"| ... | ... | ... | {len(boundary_rows) - 80} additional boundary rows omitted from markdown; see CSV. |")
    lines.extend(
        [
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_cross_reference_audit.py --out-dir outputs/tits_dynamic_graph/tits_cross_reference_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit formal T-ITS material cross-references and risky output references.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_cross_reference_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    source_files = [path.relative_to(root).as_posix() for path in discover_scan_files(root)]
    rows = collect_references(root)
    upstream = {
        "navigator": read_json(root / "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/NAVIGATOR_QA.json").get("status"),
        "public_release": read_json(root / "outputs/tits_dynamic_graph/public_release_plan/public_release_audit.json").get("status"),
        "final_readiness": read_json(root / "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json").get("status"),
        "artifact_manifest": read_json(root / "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json").get("status"),
    }
    report = {
        "status": "pending",
        "out_dir": args.out_dir,
        "scan_dirs": FORMAL_SCAN_DIRS,
        "scanned_files": source_files,
        "summary": {},
        "rows": rows,
        "note": "This audit checks manuscript-facing path references. It does not validate scientific correctness beyond reference integrity and formal-output boundary rules.",
    }
    report["summary"] = summarize(rows, source_files, upstream)
    report["status"] = report["summary"]["status"]
    paths = {
        "audit_md": write_text(materials / "FORMAL_CROSS_REFERENCE_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "FORMAL_CROSS_REFERENCE_AUDIT.json", report),
        "reference_rows_csv": write_csv(
            tables / "formal_cross_reference_rows.csv",
            rows,
            [
                "source_file",
                "line",
                "reference",
                "reference_type",
                "exists",
                "match_count",
                "risky_path",
                "boundary_context",
                "status",
                "line_text",
            ],
        ),
        "scanned_files_csv": write_csv(
            tables / "formal_cross_reference_scanned_files.csv",
            [{"source_file": path} for path in source_files],
            ["source_file"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_cross_reference_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
