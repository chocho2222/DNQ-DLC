#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


README = "README.md"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"

REQUIRED_COMMANDS = [
    "make tits-smoke",
    "make tits-refresh-gates",
    "make tits-status",
    "make tits-status-snapshot",
    "make tits-evidence-ledger",
    "make tits-claim-numeric-audit",
    "make tits-manuscript-section-trace",
    "make tits-abstract-highlights-audit",
    "make tits-checksum-audit",
    "make tits-external-validity-audit",
    "make tits-limitations-evidence-audit",
    "make tits-threats-validity",
    "make tits-protocol-deviation",
    "make tits-author-owned-audit",
    "make tits-reproduction-time-budget",
    "make tits-run-level-provenance",
    "make tits-trace-integrity",
    "make tits-trace-schema",
    "make tits-overtake-event-consistency",
    "make tits-statistical-table-recompute",
    "make tits-results-reporting-checklist",
    "make tits-results-narrative-pack",
    "make tits-figure-source-value-recompute",
    "make tits-figure-caption-claim-audit",
    "make tits-table-caption-source-data-audit",
    "make tits-table-value-recompute",
    "make tits-publication-gif-provenance",
    "make tits-supplementary-video-index",
    "make tits-supplementary-submission-index",
    "make tits-online-decision-case-study",
    "make tits-safety-proxy-audit",
    "make tits-source-data-schema",
    "make tits-algorithm-config-freeze",
    "make tits-compute-timing-boundary",
    "make tits-ai-tool-use-disclosure",
    "make tits-open-source-minimal-repo",
    "make tits-submission-gap-priority",
    "make tits-refresh-coverage",
    "make tits-audit-route",
    "make tits-audit-readme",
    "make tits-dashboard",
]

REQUIRED_PATHS = [
    "outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md",
    "outputs/tits_dynamic_graph/tits_status_snapshot/TITS_STATUS_SNAPSHOT.md",
    "outputs/tits_dynamic_graph/tits_evidence_ledger/materials/EVIDENCE_LEDGER.md",
    "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/materials/CLAIM_NUMERIC_CONSISTENCY_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/materials/MANUSCRIPT_SECTION_TRACE_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit/materials/ABSTRACT_HIGHLIGHTS_EVIDENCE_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_checksum_verification_audit/materials/CHECKSUM_VERIFICATION_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_limitations_evidence_audit/materials/LIMITATIONS_EVIDENCE_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_threats_validity_pack/materials/THREATS_TO_VALIDITY_DOSSIER.md",
    "outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/materials/PROTOCOL_DEVIATION_READINESS_REPORT.md",
    "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/materials/REVIEWER_REPRODUCTION_TIME_BUDGET_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_run_level_provenance_audit/materials/RUN_LEVEL_PROVENANCE_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_trace_integrity_audit/materials/TRACE_INTEGRITY_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/materials/TRACE_SCHEMA_DICTIONARY.md",
    "outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/materials/OVERTAKE_EVENT_CONSISTENCY_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/materials/STATISTICAL_TABLE_RECOMPUTE_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_results_reporting_checklist/materials/RESULTS_REPORTING_CHECKLIST.md",
    "outputs/tits_dynamic_graph/tits_results_narrative_pack/materials/RESULTS_NARRATIVE_PACK.md",
    "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/materials/FIGURE_SOURCE_VALUE_RECOMPUTE_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_figure_caption_claim_audit/materials/FIGURE_CAPTION_CLAIM_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_table_caption_source_data_audit/materials/TABLE_CAPTION_SOURCE_DATA_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_table_value_recompute_audit/materials/TABLE_VALUE_RECOMPUTE_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/materials/PUBLICATION_GIF_PROVENANCE_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/materials/SUPPLEMENTARY_VIDEO_INDEX.md",
    "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/materials/SUPPLEMENTARY_SUBMISSION_INDEX.md",
    "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/materials/ONLINE_DECISION_CASE_STUDY_PACK.md",
    "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/materials/SAFETY_PROXY_AUDIT_PACK.md",
    "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/materials/SOURCE_DATA_SCHEMA_DICTIONARY.md",
    "outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit/materials/ALGORITHM_CONFIG_FREEZE_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/materials/COMPUTE_TIMING_BOUNDARY_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit/materials/AI_TOOL_USE_DISCLOSURE_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/materials/OPEN_SOURCE_MINIMAL_REPO_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_submission_gap_priority_audit/materials/SUBMISSION_GAP_PRIORITY_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_refresh_coverage_audit/materials/TITS_REFRESH_COVERAGE_AUDIT.md",
    "outputs/tits_dynamic_graph/final_readiness_dashboard/FINAL_READINESS_DASHBOARD.md",
    "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv",
    "outputs/tits_dynamic_graph/public_release_plan/PUBLIC_RELEASE_PLAN.md",
    "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv",
]

REQUIRED_PHRASES = [
    ("primary_title", "# Dynamic-Neighborhood World Models for Online Multi-Car Overtaking"),
    ("section_title", "Dynamic-Neighborhood T-ITS Study"),
    ("method_position", "optimized DLC-style world-model controller"),
    ("dynamic_graph", "runtime dynamic-neighborhood graph construction"),
    ("overtake_planning", "overtake-aware candidate"),
    ("safety_scoring", "safety-oriented scoring"),
    ("comparison_family", "DLC world-model variants"),
    ("rule_baseline", "rule-based expert"),
    ("abstract_highlights", "Abstract/highlights evidence audit"),
    ("limitations_evidence", "Limitations evidence audit"),
    ("results_reporting", "Results reporting checklist"),
    ("results_narrative", "Results narrative pack"),
    ("figure_caption_claim", "Figure caption-claim audit"),
    ("table_caption_source_data", "Table caption/source-data audit"),
    ("table_value_recompute", "Table value recompute audit"),
    ("open_source_minimal_repo", "Open-source minimal repository audit"),
    ("submission_gap_priority", "Submission gap priority audit"),
    ("refresh_coverage", "Refresh coverage audit"),
    ("simulation_boundary", "simulation-only results"),
    ("threats_validity", "Threats-to-validity dossier"),
    ("protocol_deviation_boundary", "protocol/deviation register"),
    ("smoke_boundary", "smoke runs must not be cited as paper-scale"),
    ("legacy_boundary", "not the current T-ITS confirmatory evidence"),
]

FORBIDDEN_PHRASES = [
    ("old_inactive_warning", "Warning: This project is not under active maintenance"),
    ("old_clone_command", "git clone https://github.com/igilitschenski/multi_car_racing.git"),
]


def read_text(path):
    path = Path(path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


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


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def source_facts(root):
    path = root / SOURCE_DATA
    if not path.exists():
        return {
            "source_rows": 0,
            "algorithm_count": 0,
            "matched_case_count": 0,
            "max_vehicle_count": 0,
            "has_monza_external_track": False,
            "benchmarks": [],
            "status": "missing_source_data",
        }
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    algorithms = {row.get("algorithm") for row in rows}
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
    vehicle_counts = [int(row.get("num_agents", 0) or 0) for row in rows]
    tracks = {row.get("track_path", "") for row in rows}
    benchmarks = sorted({row.get("_benchmark", "") for row in rows})
    return {
        "source_rows": len(rows),
        "algorithm_count": len(algorithms),
        "matched_case_count": len(cases),
        "max_vehicle_count": max(vehicle_counts) if vehicle_counts else 0,
        "has_monza_external_track": "tracks/monza_scaled.npz" in tracks,
        "benchmarks": benchmarks,
        "status": "pass",
    }


def check_contains(text, check_id, expected_text, note=""):
    present = expected_text in text
    return {
        "check_id": check_id,
        "expected": expected_text,
        "observed": expected_text if present else "",
        "status": "pass" if present else "missing",
        "note": note,
    }


def style_guard_rows(text):
    rows = []
    for check_id, phrase in FORBIDDEN_PHRASES:
        present = phrase in text
        rows.append(
            {
                "check_id": check_id,
                "rule": f"must_not_contain: {phrase}",
                "observed": phrase if present else "",
                "status": "forbidden_present" if present else "pass",
            }
        )
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    expected_title = "# Dynamic-Neighborhood World Models for Online Multi-Car Overtaking"
    rows.append(
        {
            "check_id": "first_heading_current_project",
            "rule": f"first_line_equals: {expected_title}",
            "observed": first_line,
            "status": "pass" if first_line == expected_title else "wrong_first_heading",
        }
    )
    section_count = text.count("## Dynamic-Neighborhood T-ITS Study")
    rows.append(
        {
            "check_id": "single_tits_section",
            "rule": "exactly_one_dynamic_neighborhood_tits_section",
            "observed": section_count,
            "status": "pass" if section_count == 1 else "wrong_section_count",
        }
    )
    return rows


def build_report(root):
    readme_path = root / README
    text = read_text(readme_path)
    facts = source_facts(root)
    final = read_json(root / FINAL_READINESS)
    final_text = f"{final.get('pass_count', 'NA')}/{final.get('gate_count', 'NA')}"

    phrase_rows = [check_contains(text, cid, phrase) for cid, phrase in REQUIRED_PHRASES]
    guard_rows = style_guard_rows(text)
    command_rows = [check_contains(text, f"command_{idx:02d}", command) for idx, command in enumerate(REQUIRED_COMMANDS, start=1)]
    path_rows = []
    for idx, rel in enumerate(REQUIRED_PATHS, start=1):
        mentioned = rel in text
        exists = (root / rel).exists()
        status = "pass" if mentioned and exists else "missing_or_unresolved"
        path_rows.append(
            {
                "check_id": f"path_{idx:02d}",
                "path": rel,
                "mentioned": mentioned,
                "exists": exists,
                "status": status,
            }
        )

    numeric_specs = [
        ("algorithm_runs", facts["source_rows"], r"\b240\s+algorithm-runs?\b"),
        ("matched_cases", facts["matched_case_count"], r"\b30\s+matched\s+cases?\b"),
        ("algorithm_count", facts["algorithm_count"], r"\b8\s+algorithms?\b"),
        ("max_vehicle_count", facts["max_vehicle_count"], r"\bup\s+to\s+8\s+vehicles?\b"),
    ]
    numeric_rows = []
    for check_id, expected, pattern in numeric_specs:
        present = bool(re.search(pattern, text, flags=re.IGNORECASE))
        numeric_rows.append(
            {
                "check_id": check_id,
                "expected": expected,
                "pattern": pattern,
                "status": "pass" if present else "missing",
            }
        )
    monza_row = {
        "check_id": "monza_external_track",
        "expected": facts["has_monza_external_track"],
        "pattern": "Monza",
        "status": "pass" if facts["has_monza_external_track"] and re.search(r"Monza", text, flags=re.IGNORECASE) else "missing",
    }
    numeric_rows.append(monza_row)

    errors = (
        [row for row in phrase_rows if row["status"] != "pass"]
        + [row for row in guard_rows if row["status"] != "pass"]
        + [row for row in command_rows if row["status"] != "pass"]
        + [row for row in path_rows if row["status"] != "pass"]
        + [row for row in numeric_rows if row["status"] != "pass"]
    )
    summary = {
        "status": "pass" if readme_path.exists() and not errors and facts["status"] == "pass" else "review_required",
        "readme": README,
        "source_rows": facts["source_rows"],
        "algorithm_count": facts["algorithm_count"],
        "matched_case_count": facts["matched_case_count"],
        "max_vehicle_count": facts["max_vehicle_count"],
        "has_monza_external_track": facts["has_monza_external_track"],
        "phrase_check_count": len(phrase_rows),
        "style_guard_count": len(guard_rows),
        "command_check_count": len(command_rows),
        "path_check_count": len(path_rows),
        "numeric_check_count": len(numeric_rows),
        "error_count": len(errors),
        "final_readiness": final_text,
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "phrase_rows": phrase_rows,
        "guard_rows": guard_rows,
        "command_rows": command_rows,
        "path_rows": path_rows,
        "numeric_rows": numeric_rows,
        "facts": facts,
    }


def markdown_table(rows, fields):
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join(["---"] * len(fields)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return lines


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Root README Alignment Audit",
        "",
        "该审计检查根目录 `README.md` 这个第三方第一入口是否与当前 T-ITS 证据链一致。它聚焦开源读者最容易复制或引用的信息：算法定位、正式矩阵规模、Monza 外部赛道、8 车外推边界、smoke 与正式结果边界、Makefile 快捷入口和关键证据路径。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Phrase Checks", ""])
    lines.extend(markdown_table(report["phrase_rows"], ["check_id", "expected", "status"]))
    lines.extend(["", "## First-Screen and Legacy Guard Checks", ""])
    lines.extend(markdown_table(report["guard_rows"], ["check_id", "rule", "observed", "status"]))
    lines.extend(["", "## Command Checks", ""])
    lines.extend(markdown_table(report["command_rows"], ["check_id", "expected", "status"]))
    lines.extend(["", "## Path Checks", ""])
    lines.extend(markdown_table(report["path_rows"], ["check_id", "path", "mentioned", "exists", "status"]))
    lines.extend(["", "## Numeric/Factual Checks", ""])
    lines.extend(markdown_table(report["numeric_rows"], ["check_id", "expected", "pattern", "status"]))
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- PASS 表示根 README 的 T-ITS 入口与当前正式 source data、final readiness、Makefile 和关键证据路径一致。",
            "- 该审计不检查论文正文质量，也不替代作者对 DOI、license、匿名审稿策略和最终仓库 URL 的人工确认。",
            "- 修改 README、Makefile、source data 或 final dashboard 后需要重新运行该审计。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_root_readme_alignment_audit.py --out-dir outputs/tits_dynamic_graph/tits_root_readme_alignment_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit root README alignment with the formal T-ITS evidence chain.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_root_readme_alignment_audit")
    args = parser.parse_args()

    root = Path(".").resolve()
    out_dir = Path(args.out_dir)
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    report = build_report(root)
    paths = {
        "report_md": write_text(materials / "ROOT_README_ALIGNMENT_AUDIT.md", build_markdown(report)),
        "phrase_checks_csv": write_csv(tables / "root_readme_phrase_checks.csv", report["phrase_rows"], ["check_id", "expected", "observed", "status", "note"]),
        "style_guard_checks_csv": write_csv(tables / "root_readme_style_guard_checks.csv", report["guard_rows"], ["check_id", "rule", "observed", "status"]),
        "command_checks_csv": write_csv(tables / "root_readme_command_checks.csv", report["command_rows"], ["check_id", "expected", "observed", "status", "note"]),
        "path_checks_csv": write_csv(tables / "root_readme_path_checks.csv", report["path_rows"], ["check_id", "path", "mentioned", "exists", "status"]),
        "numeric_checks_csv": write_csv(tables / "root_readme_numeric_checks.csv", report["numeric_rows"], ["check_id", "expected", "pattern", "status"]),
        "facts_json": write_json(materials / "root_readme_alignment_facts.json", report["facts"]),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
        "boundary": "Root README alignment audit only; does not certify legal release readiness, DOI/accession completion, or real-world deployment safety.",
    }
    manifest_path = write_json(out_dir / "tits_root_readme_alignment_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
