#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
CASE_COMMANDS = "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv"
COMPUTE_REPORT = "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/materials/COMPUTE_REPRODUCIBILITY_COST_REPORT.json"
COMPUTE_TIERS = "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_reproduction_tiers.csv"
THIRD_PARTY_TIERS = "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/tables/third_party_reproduction_tiers.csv"
REPRO_COMMANDS = "outputs/tits_dynamic_graph/tits_reproducibility_capsule/tables/reproducibility_command_index.csv"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
REVIEWER_README = "outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md"


TIER_REQUIREMENTS = {
    "T0": {
        "input": "reviewer smoke script; installed environment; trained model artifacts",
        "expected_cost": "short smoke run; expected to be lightweight; not a paper-scale performance result",
        "acceptance": "summary JSON files are written under /tmp/tits_dynamic_graph_reviewer_smoke, reviewer smoke execution audit records 2/2 summaries with 0 issues, and the reviewer smoke route audit remains PASS",
        "risk_boundary": "Do not cite T0 numeric outcomes in Results.",
    },
    "T1": {
        "input": "frozen 240-run source CSV, evidence tables, figure source data and audit scripts",
        "expected_cost": "reporting-layer rebuild only; 0 new simulator runs; CPU/GPU cost is dominated by plotting/audit scripts",
        "acceptance": "claim/evidence, freshness, cross-reference, manuscript section trace and final dashboard audits return PASS",
        "risk_boundary": "T1 verifies reporting from frozen data, not independent simulator reruns.",
    },
    "T2": {
        "input": "30 frozen case commands, 8 algorithms, declared environment and model artifacts",
        "expected_cost": "paper-scale rerun: 30 case commands / 240 algorithm-runs / 528000 simulated finish steps; workload proxy is available but full wall-clock/GPU-utilization trace is not",
        "acceptance": "240 summary JSONs regenerate, source data has 240 rows, 30 matched cases and 8 algorithms, and all source-data/reproducibility audits pass",
        "risk_boundary": "Rerun differences require regenerating all downstream audits; do not mix old and new matrices.",
    },
    "T3": {
        "input": "representative case configs, model artifacts and GIF rendering scripts",
        "expected_cost": "representative visual rebuild only; cost depends on selected GIF cases and frame rate",
        "acceptance": "publication GIF manifest is regenerated and top-down/first-person visual files are present",
        "risk_boundary": "GIFs are qualitative evidence only and do not replace aggregate 240-run metrics.",
    },
}


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


def tier_command_map(compute_tiers, third_party_tiers):
    commands = {}
    for row in compute_tiers:
        commands.setdefault(row.get("tier"), row.get("primary_command", ""))
    for row in third_party_tiers:
        commands.setdefault(row.get("tier"), row.get("command", ""))
    return commands


def tier_name_map(compute_tiers, third_party_tiers):
    names = {}
    for row in third_party_tiers:
        names[row.get("tier")] = row.get("name", "")
    for row in compute_tiers:
        names.setdefault(row.get("tier"), row.get("name_cn", ""))
    return names


def build_tier_rows(root, source_rows, case_commands, compute, compute_tiers, third_party_tiers):
    commands = tier_command_map(compute_tiers, third_party_tiers)
    names = tier_name_map(compute_tiers, third_party_tiers)
    total_steps = compute.get("summary", {}).get("total_simulated_steps_across_algorithm_runs", "")
    approx_proxy = compute.get("summary", {}).get("approx_planner_time_proxy_s", "")
    rows = []
    for tier in ["T0", "T1", "T2", "T3"]:
        req = TIER_REQUIREMENTS[tier]
        command = commands.get(tier, "")
        if tier == "T2":
            expected_runs = f"{len(case_commands)} case commands / {len(source_rows)} source rows / {total_steps} simulated finish steps"
            cost_boundary = f"{req['expected_cost']}; derived planner workload proxy={approx_proxy}s"
        elif tier == "T1":
            expected_runs = "0 new simulator runs"
            cost_boundary = req["expected_cost"]
        else:
            expected_runs = "smoke or representative cases only"
            cost_boundary = req["expected_cost"]
        expected_output = {
            "T0": "/tmp/tits_dynamic_graph_reviewer_smoke/summaries/*.summary.json",
            "T1": "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json and outputs/tits_dynamic_graph/tits_status_snapshot/tits_status_snapshot_manifest.json",
            "T2": "outputs/tits_dynamic_graph/v6_confirmatory_matrix/**/*.summary.json plus regenerated source CSV",
            "T3": "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.json",
        }[tier]
        rows.append(
            {
                "tier": tier,
                "name": names.get(tier, ""),
                "input": req["input"],
                "command": command,
                "expected_output": expected_output,
                "expected_cases_or_runs": expected_runs,
                "estimated_cost_boundary": cost_boundary,
                "acceptance_criteria": req["acceptance"],
                "risk_boundary": req["risk_boundary"],
                "paper_result_scope": {
                    "T0": "no",
                    "T1": "yes, reporting layer only",
                    "T2": "yes, if full matrix is rerun and all audits are regenerated",
                    "T3": "qualitative visual evidence only",
                }[tier],
                "status": "pass" if command else "missing_command",
            }
        )
    return rows


def build_check_rows(root, tier_rows, source_rows, case_commands, compute, repro_commands, reviewer_readme):
    checks = []
    expected_paths = [
        SOURCE_DATA,
        CASE_COMMANDS,
        COMPUTE_REPORT,
        COMPUTE_TIERS,
        THIRD_PARTY_TIERS,
        REPRO_COMMANDS,
        REVIEWER_README,
    ]
    missing_paths = [path for path in expected_paths if not (root / path).exists()]
    checks.append(
        {
            "check_id": "RTB_inputs_exist",
            "status": "pass" if not missing_paths else "fail",
            "expected": "all source tier and command files exist",
            "observed": missing_paths if missing_paths else "all present",
            "note": "The time-budget audit should be reproducible from existing reviewer-facing evidence.",
        }
    )
    checks.append(
        {
            "check_id": "RTB_formal_matrix_scale",
            "status": "pass" if len(source_rows) == 240 and len(case_commands) == 30 else "fail",
            "expected": "240 source rows and 30 case commands",
            "observed": {"source_rows": len(source_rows), "case_commands": len(case_commands)},
            "note": "T2 budget must describe the actual formal matrix scale.",
        }
    )
    checks.append(
        {
            "check_id": "RTB_all_tiers_present",
            "status": "pass" if {row["tier"] for row in tier_rows} == {"T0", "T1", "T2", "T3"} else "fail",
            "expected": "T0,T1,T2,T3",
            "observed": sorted({row["tier"] for row in tier_rows}),
            "note": "Reviewers should be able to choose a reproduction depth.",
        }
    )
    checks.append(
        {
            "check_id": "RTB_wall_clock_boundary",
            "status": "pass" if compute.get("summary", {}).get("wall_clock_time_recorded") is False else "fail",
            "expected": "wall_clock_time_recorded false",
            "observed": compute.get("summary", {}).get("wall_clock_time_recorded"),
            "note": "The report must not claim complete wall-clock or GPU-utilization accounting.",
        }
    )
    readme_has_tiers = all(tier in reviewer_readme for tier in ["T0", "T1", "T2", "T3"])
    checks.append(
        {
            "check_id": "RTB_reviewer_readme_mentions_tiers",
            "status": "pass" if readme_has_tiers else "advisory",
            "expected": "reviewer README mentions T0-T3",
            "observed": readme_has_tiers,
            "note": "Advisory only: detailed tier table lives in this audit even if reviewer README is concise.",
        }
    )
    return checks


def build_markdown(report):
    lines = [
        "# T-ITS Reviewer Reproduction Time-Budget Audit",
        "",
        "该审计面向审稿人复现：把 T0-T3 复现层级整理成输入、命令、预期输出、成本边界和验收标准。它只复核现有证据，不新增实验，也不声称完整 wall-clock/GPU-utilization 历史已经记录。",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## T0-T3 Reproduction Budget",
            "",
            "| Tier | Scope | Paper result? | Expected cases/runs | Cost boundary | Acceptance criteria |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["tier_rows"]:
        lines.append(
            f"| {row['tier']} | {row['name']} | {row['paper_result_scope']} | {row['expected_cases_or_runs']} | {row['estimated_cost_boundary']} | {row['acceptance_criteria']} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- T0 smoke 只验证代码路径，不能作为性能结果。",
            "- T1 只重建冻结 source data 的报告层，不是独立仿真复现。",
            "- T2 是完整正式矩阵重跑，若重跑结果不同，必须重新生成 source data、统计、图件、claim 和 checksum 审计。",
            "- T3 GIF 是视觉证据，只能辅助解释行为，不能替代 240-run aggregate metrics。",
            "- 当前证据链有控制延迟和 workload proxy，但没有完整历史 wall-clock/GPU-utilization trace。",
        ]
    )
    return "\n".join(lines)


def build_report(root):
    source_rows = read_csv(root / SOURCE_DATA)
    case_commands = read_csv(root / CASE_COMMANDS)
    compute = read_json(root / COMPUTE_REPORT)
    compute_tiers = read_csv(root / COMPUTE_TIERS)
    third_party_tiers = read_csv(root / THIRD_PARTY_TIERS)
    repro_commands = read_csv(root / REPRO_COMMANDS)
    final = read_json(root / FINAL_READINESS)
    reviewer_readme = read_text(root / REVIEWER_README)
    tier_rows = build_tier_rows(root, source_rows, case_commands, compute, compute_tiers, third_party_tiers)
    check_rows = build_check_rows(root, tier_rows, source_rows, case_commands, compute, repro_commands, reviewer_readme)
    failures = [row for row in check_rows if row["status"] == "fail"] + [row for row in tier_rows if row["status"] != "pass"]
    summary = {
        "status": "pass" if not failures else "review_required",
        "tier_count": len(tier_rows),
        "check_count": len(check_rows),
        "failed_check_count": len(failures),
        "source_rows": len(source_rows),
        "case_command_count": len(case_commands),
        "algorithm_count": len({row.get("algorithm") for row in source_rows}),
        "matched_case_count": len({(row.get("_benchmark"), row.get("num_agents"), row.get("seed"), row.get("track_path"), row.get("traffic_profile")) for row in source_rows}),
        "total_simulated_steps": compute.get("summary", {}).get("total_simulated_steps_across_algorithm_runs"),
        "approx_planner_time_proxy_s": compute.get("summary", {}).get("approx_planner_time_proxy_s"),
        "wall_clock_time_recorded": compute.get("summary", {}).get("wall_clock_time_recorded"),
        "final_readiness": f"{final.get('pass_count', 'NA')}/{final.get('gate_count', 'NA')}",
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "tier_rows": tier_rows,
        "check_rows": check_rows,
        "repro_command_rows": repro_commands,
        "boundary": "This audit provides reviewer-facing time-budget and acceptance criteria. It does not certify actual rerun wall-clock time, container build digest, or cross-hardware bitwise determinism.",
    }


def main():
    parser = argparse.ArgumentParser(description="Export reviewer reproduction time-budget audit for T-ITS package.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    report = build_report(root)
    paths = {
        "report_md": write_text(materials / "REVIEWER_REPRODUCTION_TIME_BUDGET_AUDIT.md", build_markdown(report)),
        "report_json": write_json(materials / "REVIEWER_REPRODUCTION_TIME_BUDGET_AUDIT.json", report),
        "tier_budget_csv": write_csv(
            tables / "reviewer_reproduction_time_budget_tiers.csv",
            report["tier_rows"],
            [
                "tier",
                "name",
                "input",
                "command",
                "expected_output",
                "expected_cases_or_runs",
                "estimated_cost_boundary",
                "acceptance_criteria",
                "risk_boundary",
                "paper_result_scope",
                "status",
            ],
        ),
        "checks_csv": write_csv(
            tables / "reviewer_reproduction_time_budget_checks.csv",
            report["check_rows"],
            ["check_id", "status", "expected", "observed", "note"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
        "boundary": report["boundary"],
    }
    manifest_path = write_json(out_dir / "tits_reviewer_reproduction_time_budget_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
