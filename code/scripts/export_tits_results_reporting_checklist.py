#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


PRIMARY = "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv"
EFFECTS = "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_effect_sizes.csv"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
MAIN_RESULTS = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_main_results.md"
STAT_PLAN = "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/STATISTICAL_ANALYSIS_PLAN.md"
CLAIM_NUMERIC = "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/tits_claim_numeric_consistency_audit_manifest.json"
TABLE_RECOMPUTE = "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/tits_statistical_table_recompute_audit_manifest.json"
FIGURE_VALUE_RECOMPUTE = "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/tits_figure_source_value_recompute_audit_manifest.json"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"

PRIMARY_METRICS = {
    "overtake_success_rate",
    "elegant_overtake_rate",
    "on_track_overtake_rate",
    "overtake_start_to_complete_time",
    "target_grass_rate",
}


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


def has_number(row, key):
    value = row.get(key, "")
    if value in {"", "NA", "nan", None}:
        return False
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def source_facts(rows):
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
    return {
        "source_rows": len(rows),
        "matched_case_count": len(cases),
        "algorithm_count": len({row.get("algorithm") for row in rows if row.get("algorithm")}),
        "benchmarks": ";".join(sorted({row.get("_benchmark", "") for row in rows if row.get("_benchmark")})),
    }


def build_primary_rows(primary_rows, effect_rows):
    effect_by_metric = {
        (row.get("algorithm"), row.get("metric")): row
        for row in effect_rows
    }
    checks = []
    for row in primary_rows:
        metric = row.get("metric", "")
        effect = effect_by_metric.get((row.get("algorithm"), metric), {})
        missing = []
        for field in [
            "n_paired",
            "improvement_mean",
            "improvement_ci95_low",
            "improvement_ci95_high",
            "p_raw",
            "p_holm",
        ]:
            if not has_number(row, field):
                missing.append(field)
        if not effect:
            missing.append("effect_size_row")
        elif not has_number(effect, "paired_cohen_dz"):
            missing.append("paired_cohen_dz")
        if row.get("direction") not in {"higher is better", "lower is better"}:
            missing.append("direction")
        if row.get("p_source") == "":
            missing.append("p_source")
        checks.append(
            {
                "hypothesis_id": row.get("hypothesis_id", ""),
                "metric": metric,
                "metric_label": row.get("metric_label", ""),
                "algorithm": row.get("algorithm", ""),
                "baseline": row.get("baseline", ""),
                "direction": row.get("direction", ""),
                "n_paired": row.get("n_paired", ""),
                "improvement_mean": row.get("improvement_mean", ""),
                "ci95": f"[{row.get('improvement_ci95_low', '')}, {row.get('improvement_ci95_high', '')}]",
                "p_raw": row.get("p_raw", ""),
                "p_holm": row.get("p_holm", ""),
                "significant_holm_0_05": row.get("significant_holm_0_05", ""),
                "paired_cohen_dz": effect.get("paired_cohen_dz", ""),
                "positive_cases": effect.get("positive_cases", ""),
                "negative_cases": effect.get("negative_cases", ""),
                "zero_cases": effect.get("zero_cases", ""),
                "missing_fields": ";".join(missing),
                "status": "pass" if not missing else "review_required",
            }
        )
    return checks


def build_checklist(primary_rows, effect_rows, source_rows, root):
    facts = source_facts(source_rows)
    primary_metrics = {row.get("metric") for row in primary_rows}
    effect_metrics = {
        row.get("metric")
        for row in effect_rows
        if row.get("algorithm") == "v6_runtime_dynamic_neighborhood_safe"
    }
    inputs = [PRIMARY, EFFECTS, SOURCE_DATA, MAIN_RESULTS, STAT_PLAN, CLAIM_NUMERIC, TABLE_RECOMPUTE, FIGURE_VALUE_RECOMPUTE]
    rows = [
        {
            "check_id": "RR_inputs_exist",
            "category": "input_presence",
            "status": "pass" if all((root / path).exists() for path in inputs) else "review_required",
            "observed": ";".join(path for path in inputs if (root / path).exists()),
            "expected": "all statistical, source-data and recompute-audit inputs exist",
            "evidence": ";".join(inputs),
        },
        {
            "check_id": "RR_primary_hypothesis_count",
            "category": "primary_hypotheses",
            "status": "pass" if len(primary_rows) == 5 else "review_required",
            "observed": len(primary_rows),
            "expected": 5,
            "evidence": PRIMARY,
        },
        {
            "check_id": "RR_primary_metric_set",
            "category": "primary_hypotheses",
            "status": "pass" if primary_metrics == PRIMARY_METRICS else "review_required",
            "observed": ";".join(sorted(primary_metrics)),
            "expected": ";".join(sorted(PRIMARY_METRICS)),
            "evidence": PRIMARY,
        },
        {
            "check_id": "RR_effect_size_coverage",
            "category": "effect_size",
            "status": "pass" if PRIMARY_METRICS.issubset(effect_metrics) else "review_required",
            "observed": ";".join(sorted(effect_metrics & PRIMARY_METRICS)),
            "expected": ";".join(sorted(PRIMARY_METRICS)),
            "evidence": EFFECTS,
        },
        {
            "check_id": "RR_source_data_scale",
            "category": "source_data",
            "status": "pass" if facts["source_rows"] == 240 and facts["matched_case_count"] == 30 and facts["algorithm_count"] == 8 else "review_required",
            "observed": f"rows={facts['source_rows']}; cases={facts['matched_case_count']}; algorithms={facts['algorithm_count']}; benchmarks={facts['benchmarks']}",
            "expected": "240 rows; 30 matched cases; 8 algorithms",
            "evidence": SOURCE_DATA,
        },
        {
            "check_id": "RR_recompute_audits_pass",
            "category": "independent_recompute",
            "status": "pass"
            if read_json(root / TABLE_RECOMPUTE).get("status") == "pass"
            and read_json(root / FIGURE_VALUE_RECOMPUTE).get("status") == "pass"
            and read_json(root / CLAIM_NUMERIC).get("status") == "pass"
            else "review_required",
            "observed": (
                f"stat_table={read_json(root / TABLE_RECOMPUTE).get('status')}; "
                f"figure_values={read_json(root / FIGURE_VALUE_RECOMPUTE).get('status')}; "
                f"claim_numeric={read_json(root / CLAIM_NUMERIC).get('status')}"
            ),
            "expected": "all pass",
            "evidence": f"{TABLE_RECOMPUTE};{FIGURE_VALUE_RECOMPUTE};{CLAIM_NUMERIC}",
        },
        {
            "check_id": "RR_main_results_table_present",
            "category": "manuscript_table",
            "status": "pass" if (root / MAIN_RESULTS).exists() and "95% CI" in (root / MAIN_RESULTS).read_text(encoding="utf-8") else "review_required",
            "observed": "present_with_95ci" if (root / MAIN_RESULTS).exists() else "missing",
            "expected": "main results table exists and labels 95% CI",
            "evidence": MAIN_RESULTS,
        },
    ]
    return rows


def build_report(root):
    primary_rows = read_csv(root / PRIMARY)
    effect_rows = read_csv(root / EFFECTS)
    source_rows = read_csv(root / SOURCE_DATA)
    primary_checks = build_primary_rows(primary_rows, effect_rows)
    checklist = build_checklist(primary_rows, effect_rows, source_rows, root)
    issue_count = sum(1 for row in primary_checks + checklist if row["status"] != "pass")
    final = read_json(root / FINAL_READINESS)
    summary = {
        "status": "pass" if issue_count == 0 else "review_required",
        "primary_hypothesis_count": len(primary_rows),
        "primary_metric_count": len({row.get("metric") for row in primary_rows}),
        "primary_reporting_issue_count": sum(1 for row in primary_checks if row["status"] != "pass"),
        "checklist_issue_count": sum(1 for row in checklist if row["status"] != "pass"),
        "source_rows": len(source_rows),
        "effect_size_rows": len(effect_rows),
        "final_readiness": f"{final.get('pass_count', 'NA')}/{final.get('gate_count', 'NA')}",
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "primary_rows": primary_checks,
        "checklist_rows": checklist,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Results Reporting Checklist",
        "",
        "该审计面向 Results 写作：检查主假设是否同时具备样本规模、方向、均值差、95% CI、原始 p 值、Holm 校正 p 值、效应量和配对胜负计数，并确认这些结果可回链到 source data 与独立复算审计。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Primary Hypothesis Reporting Rows",
            "",
            "| H | Metric | N | Delta | 95% CI | Holm p | dz | + / - / 0 | Status |",
            "|---|---|---:|---:|---|---:|---:|---|---|",
        ]
    )
    for row in report["primary_rows"]:
        lines.append(
            f"| {row['hypothesis_id']} | {row['metric_label']} | {row['n_paired']} | {row['improvement_mean']} | "
            f"{row['ci95']} | {row['p_holm']} | {row['paired_cohen_dz']} | "
            f"{row['positive_cases']}/{row['negative_cases']}/{row['zero_cases']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Checklist",
            "",
            "| Check | Category | Status | Observed | Expected | Evidence |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["checklist_rows"]:
        lines.append(
            f"| {row['check_id']} | {row['category']} | {row['status']} | {row['observed']} | {row['expected']} | `{row['evidence']}` |"
        )
    lines.extend(
        [
            "",
            "## Writing Boundary",
            "",
            "- Results should report effect sizes and confidence intervals before p-value interpretation.",
            "- Holm-corrected primary hypotheses support the pre-specified v6-safe versus original DLC comparison; exploratory rows should remain labeled as exploratory.",
            "- Simulation metrics must not be written as real-road safety certification.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_results_reporting_checklist.py --out-dir outputs/tits_dynamic_graph/tits_results_reporting_checklist",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export a Results reporting checklist for T-ITS manuscript writing.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_results_reporting_checklist")
    args = parser.parse_args()
    root = Path(".").resolve()
    report = build_report(root)
    out_dir = Path(args.out_dir)
    paths = {
        "report_md": write_text(out_dir / "materials" / "RESULTS_REPORTING_CHECKLIST.md", build_markdown(report)),
        "primary_csv": write_csv(
            out_dir / "tables" / "primary_hypothesis_reporting_checks.csv",
            report["primary_rows"],
            [
                "hypothesis_id",
                "metric",
                "metric_label",
                "algorithm",
                "baseline",
                "direction",
                "n_paired",
                "improvement_mean",
                "ci95",
                "p_raw",
                "p_holm",
                "significant_holm_0_05",
                "paired_cohen_dz",
                "positive_cases",
                "negative_cases",
                "zero_cases",
                "missing_fields",
                "status",
            ],
        ),
        "checklist_csv": write_csv(
            out_dir / "tables" / "results_reporting_checklist.csv",
            report["checklist_rows"],
            ["check_id", "category", "status", "observed", "expected", "evidence"],
        ),
        "report_json": write_json(out_dir / "materials" / "RESULTS_REPORTING_CHECKLIST.json", report),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
        "boundary": "Results reporting audit only; it checks table completeness and source routes but does not rerun simulations.",
    }
    manifest_path = write_json(out_dir / "tits_results_reporting_checklist_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
