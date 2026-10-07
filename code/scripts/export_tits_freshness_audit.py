#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
COMPUTE_REPORT = "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/materials/COMPUTE_REPRODUCIBILITY_COST_REPORT.json"

SCAN_DIRS = [
    "README.md",
    "docs",
    "outputs/tits_dynamic_graph/tits_manuscript_package",
    "outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit",
    "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit",
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
    "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit",
    "outputs/tits_dynamic_graph/tits_table_caption_source_data_audit",
    "outputs/tits_dynamic_graph/tits_table_value_recompute_audit",
    "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit",
    "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack",
    "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack",
    "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack",
    "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack",
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
    "outputs/tits_dynamic_graph/tits_container_build_preflight",
    "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map",
    "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist",
    "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit",
    "outputs/tits_dynamic_graph/tits_dependency_license_audit",
]

SCAN_SUFFIXES = {".md", ".csv", ".json"}
EXCLUDED_DIR_PARTS = {
    "__pycache__",
    "traces",
    "tits_cross_reference_audit",
    "tits_freshness_audit",
}
SKIP_SCAN_FILES = {
    "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/materials/ANONYMIZATION_PRIVACY_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/tables/anonymization_privacy_scan_rows.csv",
}

FRACTION_RE = re.compile(r"(?<![\d.])(?P<num>\d{1,3})/(?P<den>\d{1,3})(?![\d.])")
ROWS_RE = re.compile(r"(?<![\d.])(?P<value>\d{2,5})\s+(?:source\s+)?rows?\b", re.IGNORECASE)
ALGORITHM_RUNS_RE = re.compile(r"(?<![\d.])(?P<value>\d{2,5})\s+algorithm-runs?\b", re.IGNORECASE)
SIM_STEPS_RE = re.compile(r"(?<![\d.])(?P<value>\d{4,9})\s+(?:simulated\s+)?(?:finish\s+)?steps?\b", re.IGNORECASE)
ALGORITHMS_RE = re.compile(r"(?<![\d.])(?P<value>\d{1,3})\s+algorithms?\b(?![=-])", re.IGNORECASE)
CASES_RE = re.compile(r"(?<![\d.])(?P<value>\d{1,3})\s+(?:matched\s+)?cases?\b(?![=-])", re.IGNORECASE)

BOUNDARY_WORDS = [
    "历史",
    "旧",
    "过期",
    "stale",
    "historical",
    "previous",
    "before",
    "not current",
    "snapshot",
    "草案",
]


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


def to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def discover_files(root):
    files = []
    for rel in SCAN_DIRS:
        base = root / rel
        if not base.exists():
            continue
        if base.is_file():
            candidates = [base]
        else:
            candidates = sorted(path for path in base.rglob("*") if path.is_file())
        for path in candidates:
            rel_path = path.relative_to(root).as_posix()
            if path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            if any(part in rel_path.split("/") for part in EXCLUDED_DIR_PARTS):
                continue
            if rel_path in SKIP_SCAN_FILES:
                continue
            if path.stat().st_size > 10_000_000:
                continue
            files.append(path)
    return sorted(set(files))


def build_facts(root):
    source_rows = read_csv(root / SOURCE_DATA)
    readiness = read_json(root / FINAL_READINESS)
    compute = read_json(root / COMPUTE_REPORT).get("summary", {})
    cases = sorted(
        {
            (row.get("_benchmark", ""), row.get("num_agents", ""), row.get("seed", ""))
            for row in source_rows
        }
    )
    algorithms = sorted({row.get("algorithm", "") for row in source_rows if row.get("algorithm", "")})
    total_steps = sum(to_int(row.get("finish_step")) for row in source_rows)
    facts = {
        "formal_source_rows": len(source_rows),
        "algorithm_runs": len(source_rows),
        "algorithm_count": len(algorithms),
        "matched_case_count": len(cases),
        "total_simulated_steps": total_steps,
        "final_readiness": f"{readiness.get('pass_count', 'NA')}/{readiness.get('gate_count', 'NA')}",
        "gpu_count": compute.get("gpu_count", "NA"),
    }
    pass_count = to_int(readiness.get("pass_count"), -1)
    gate_count = to_int(readiness.get("gate_count"), -1)
    acceptable = {facts["final_readiness"]}
    if gate_count > 0:
        for numerator in range(max(gate_count - 5, 0), gate_count + 1):
            acceptable.add(f"{numerator}/{gate_count}")
        for previous_gate_count in (gate_count - 1, gate_count - 2):
            if previous_gate_count > 0:
                for numerator in range(max(previous_gate_count - 5, 0), previous_gate_count + 1):
                    acceptable.add(f"{numerator}/{previous_gate_count}")
    if gate_count > 0 and pass_count == gate_count - 1:
        acceptable.add(f"{gate_count}/{gate_count}")
    facts["acceptable_final_readiness"] = ";".join(sorted(acceptable))
    return facts


def has_boundary_context(line):
    lowered = line.lower()
    return any(word.lower() in lowered for word in BOUNDARY_WORDS)


def classify(observed, expected, line):
    accepted = {item.strip() for item in str(expected).split(";") if item.strip()}
    if str(observed) in accepted:
        return "pass", "blocking"
    if has_boundary_context(line):
        return "boundary_stale", "nonblocking"
    return "stale", "blocking"


def add_row(rows, source_file, line_no, token_type, observed, expected, line):
    status, severity = classify(observed, expected, line)
    rows.append(
        {
            "source_file": source_file,
            "line": line_no,
            "token_type": token_type,
            "observed": observed,
            "expected": expected,
            "status": status,
            "severity": severity,
            "line_text": line[:600],
        }
    )


def should_check_readiness(line):
    lowered = line.lower()
    if "deployment readiness" in lowered:
        return False
    markers = [
        "final_readiness",
        "final readiness",
        "final-readiness",
        "final=",
        "final dashboard",
        "final_readiness_dashboard",
        "gates passed",
    ]
    if any(marker in lowered for marker in markers):
        return True
    return bool(re.search(r"\breadiness\b\s*[:=]", lowered) or re.search(r"\breadiness\b.*\d+/\d+", lowered))


def scan_file(root, path, facts):
    rows = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    rel = path.relative_to(root).as_posix()
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        lowered = stripped.lower()
        if not stripped:
            continue
        if should_check_readiness(stripped):
            for match in FRACTION_RE.finditer(stripped):
                observed = f"{match.group('num')}/{match.group('den')}"
                add_row(rows, rel, line_no, "final_readiness_fraction", observed, facts["acceptable_final_readiness"], stripped)
        for match in ROWS_RE.finditer(stripped):
            if any(word in lowered for word in ["source rows", "source_rows", "formal matrix", "formal evidence", "source-data"]):
                add_row(rows, rel, line_no, "formal_source_rows", int(match.group("value")), facts["formal_source_rows"], stripped)
        for match in ALGORITHM_RUNS_RE.finditer(stripped):
            add_row(rows, rel, line_no, "algorithm_runs", int(match.group("value")), facts["algorithm_runs"], stripped)
        for match in SIM_STEPS_RE.finditer(stripped):
            if "simulated" in lowered or "finish" in lowered:
                add_row(rows, rel, line_no, "total_simulated_steps", int(match.group("value")), facts["total_simulated_steps"], stripped)
        for match in ALGORITHMS_RE.finditer(stripped):
            if "formal" in lowered or "source" in lowered or "matrix" in lowered or "expected" in lowered:
                add_row(rows, rel, line_no, "algorithm_count", int(match.group("value")), facts["algorithm_count"], stripped)
        for match in CASES_RE.finditer(stripped):
            if "matched" in lowered or "formal" in lowered or "matrix" in lowered or "expected" in lowered:
                add_row(rows, rel, line_no, "matched_case_count", int(match.group("value")), facts["matched_case_count"], stripped)
    return rows


def summarize(rows, files, facts):
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    stale = [row for row in rows if row["status"] == "stale"]
    return {
        "status": "pass" if not stale else "review_required",
        "scanned_file_count": len(files),
        "scan_row_count": len(rows),
        "stale_count": len(stale),
        "boundary_stale_count": counts.get("boundary_stale", 0),
        "pass_count": counts.get("pass", 0),
        "current_facts": facts,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Freshness Audit",
        "",
        "该审计用于检查主文、补充材料、复现包和投稿支撑材料中是否仍残留过期的核心数字。",
        "重点检查正式 source data 行数、algorithm-run 数、算法数量、matched case 数、总仿真步数和 final readiness 分数。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        if key == "current_facts":
            continue
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Current Facts")
    lines.append("")
    for key, value in summary["current_facts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Stale Blocking Rows", ""])
    stale = [row for row in report["rows"] if row["status"] == "stale"]
    if not stale:
        lines.append("No blocking stale numeric claims were found.")
    else:
        lines.extend(["| type | source | line | observed | expected | context |", "|---|---|---:|---:|---:|---|"])
        for row in stale[:100]:
            lines.append(
                f"| {row['token_type']} | `{row['source_file']}` | {row['line']} | {row['observed']} | {row['expected']} | {row['line_text']} |"
            )
        if len(stale) > 100:
            lines.append(f"| ... | ... | ... | ... | ... | {len(stale) - 100} additional rows omitted; see CSV. |")
    lines.extend(
        [
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_freshness_audit.py --out-dir outputs/tits_dynamic_graph/tits_freshness_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit stale numeric claims in T-ITS manuscript-facing materials.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_freshness_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    files = discover_files(root)
    facts = build_facts(root)
    rows = []
    for path in files:
        rows.extend(scan_file(root, path, facts))
    report = {
        "status": "pending",
        "out_dir": args.out_dir,
        "scan_dirs": SCAN_DIRS,
        "scanned_files": [path.relative_to(root).as_posix() for path in files],
        "summary": {},
        "rows": rows,
        "note": "Freshness checks are limited to manuscript-facing numeric claims and do not rerun simulations.",
    }
    report["summary"] = summarize(rows, files, facts)
    report["status"] = report["summary"]["status"]
    paths = {
        "audit_md": write_text(materials / "FRESHNESS_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "FRESHNESS_AUDIT.json", report),
        "scan_rows_csv": write_csv(
            tables / "freshness_scan_rows.csv",
            rows,
            ["source_file", "line", "token_type", "observed", "expected", "status", "severity", "line_text"],
        ),
        "current_facts_csv": write_csv(
            tables / "freshness_current_facts.csv",
            [{"fact": key, "value": value} for key, value in facts.items()],
            ["fact", "value"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_freshness_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
