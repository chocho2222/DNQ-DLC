#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


PRIMARY = "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv"
EFFECTS = "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_effect_sizes.csv"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
RESULTS_REPORTING = "outputs/tits_dynamic_graph/tits_results_reporting_checklist/tits_results_reporting_checklist_manifest.json"
TABLE_RECOMPUTE = "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/tits_statistical_table_recompute_audit_manifest.json"
CLAIM_NUMERIC = "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/tits_claim_numeric_consistency_audit_manifest.json"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"

PRIMARY_ALGORITHM = "v6_runtime_dynamic_neighborhood_safe"
BASELINE_ALGORITHM = "dlc_world_original"


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


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt_num(value, digits=2):
    value = as_float(value)
    if value is None:
        return "NA"
    if abs(value) < 0.001 and value != 0:
        return f"{value:.2e}"
    return f"{value:.{digits}f}"


def fmt_p(value):
    value = as_float(value)
    if value is None:
        return "NA"
    if value < 0.001:
        return "p < 0.001"
    return f"p = {value:.3f}"


def fmt_ci(low, high, unit):
    if unit == "percentage points":
        return f"{fmt_num(100 * as_float(low), 1)} to {fmt_num(100 * as_float(high), 1)} percentage points"
    return f"{fmt_num(low, 1)} to {fmt_num(high, 1)} simulation steps"


def fmt_ci_cn(low, high, unit):
    if unit == "percentage points":
        return f"{fmt_num(100 * as_float(low), 1)} 到 {fmt_num(100 * as_float(high), 1)} 个百分点"
    return f"{fmt_num(low, 1)} 到 {fmt_num(high, 1)} 个仿真步"


def metric_unit(metric):
    if metric in {"overtake_success_rate", "elegant_overtake_rate", "on_track_overtake_rate", "target_grass_rate"}:
        return "percentage points"
    return "simulation steps"


def effect_label(dz):
    dz = abs(as_float(dz) or 0.0)
    if dz >= 0.8:
        return "large"
    if dz >= 0.5:
        return "medium"
    if dz >= 0.2:
        return "small"
    return "negligible"


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
        "benchmarks": ", ".join(sorted({row.get("_benchmark", "") for row in rows if row.get("_benchmark")})),
        "vehicle_counts": ", ".join(sorted({row.get("num_agents", "") for row in rows if row.get("num_agents")}, key=lambda x: int(x))),
    }


def build_sentence(row, effect):
    metric = row.get("metric", "")
    unit = metric_unit(metric)
    delta = as_float(row.get("improvement_mean"))
    if unit == "percentage points":
        delta_text = f"{fmt_num(100 * delta, 1)} percentage points"
    else:
        delta_text = f"{fmt_num(delta, 1)} simulation steps"
    action = "increased" if row.get("direction") == "higher is better" else "reduced"
    if metric == "overtake_start_to_complete_time":
        object_text = "the start-to-completion time of successful overtakes"
    elif metric == "target_grass_rate":
        object_text = "target-vehicle grass exposure"
    elif metric == "overtake_success_rate":
        object_text = "overtake success"
    elif metric == "elegant_overtake_rate":
        object_text = "desirable overtaking behavior rate"
    elif metric == "on_track_overtake_rate":
        object_text = "on-track overtake rate"
    else:
        object_text = row.get("metric_label", metric)
    return (
        f"Against {row.get('baseline_label')} over {row.get('n_paired')} matched cases, "
        f"{row.get('algorithm_label')} {action} {object_text} by {delta_text} "
        f"(95% CI {fmt_ci(row.get('improvement_ci95_low'), row.get('improvement_ci95_high'), unit)}; "
        f"Holm-adjusted {fmt_p(row.get('p_holm'))}; paired Cohen's dz = {fmt_num(effect.get('paired_cohen_dz'), 2)}; "
        f"paired + / - / 0 = {effect.get('positive_cases')}/{effect.get('negative_cases')}/{effect.get('zero_cases')})."
    )


def build_cn_interpretation(row, effect):
    metric = row.get("metric", "")
    unit = metric_unit(metric)
    delta = as_float(row.get("improvement_mean"))
    if unit == "percentage points":
        delta_text = f"{fmt_num(100 * delta, 1)} 个百分点"
    else:
        delta_text = f"{fmt_num(delta, 1)} 个仿真步"
    direction = "提升" if row.get("direction") == "higher is better" else "降低"
    return (
        f"{row.get('hypothesis_id')} 表明，相比原始 DLC world model，当前优化后的 Dynamic DLC-safe 在 "
        f"{row.get('metric_label')} 指标上{direction} {delta_text}，95% CI 为 "
        f"{fmt_ci_cn(row.get('improvement_ci95_low'), row.get('improvement_ci95_high'), unit)}，"
        f"Holm 校正后 {fmt_p(row.get('p_holm'))}，配对效应量 dz={fmt_num(effect.get('paired_cohen_dz'), 2)} "
        f"({effect_label(effect.get('paired_cohen_dz'))})，配对胜/负/平为 "
        f"{effect.get('positive_cases')}/{effect.get('negative_cases')}/{effect.get('zero_cases')}。"
    )


def build_rows(primary_rows, effect_rows):
    effects = {
        (row.get("algorithm"), row.get("metric")): row
        for row in effect_rows
    }
    rows = []
    for row in primary_rows:
        if row.get("algorithm") != PRIMARY_ALGORITHM or row.get("baseline") != BASELINE_ALGORITHM:
            continue
        effect = effects.get((row.get("algorithm"), row.get("metric")), {})
        missing = []
        for field in ["n_paired", "improvement_mean", "improvement_ci95_low", "improvement_ci95_high", "p_holm"]:
            if as_float(row.get(field)) is None:
                missing.append(field)
        if not effect:
            missing.append("effect_size_row")
        elif as_float(effect.get("paired_cohen_dz")) is None:
            missing.append("paired_cohen_dz")
        status = "pass" if not missing else "review_required"
        rows.append(
            {
                "hypothesis_id": row.get("hypothesis_id", ""),
                "metric": row.get("metric", ""),
                "metric_label": row.get("metric_label", ""),
                "n_paired": row.get("n_paired", ""),
                "delta": row.get("improvement_mean", ""),
                "ci95_low": row.get("improvement_ci95_low", ""),
                "ci95_high": row.get("improvement_ci95_high", ""),
                "p_holm": row.get("p_holm", ""),
                "paired_cohen_dz": effect.get("paired_cohen_dz", ""),
                "effect_magnitude": effect_label(effect.get("paired_cohen_dz")),
                "positive_cases": effect.get("positive_cases", ""),
                "negative_cases": effect.get("negative_cases", ""),
                "zero_cases": effect.get("zero_cases", ""),
                "manuscript_sentence": build_sentence(row, effect) if status == "pass" else "",
                "chinese_interpretation": build_cn_interpretation(row, effect) if status == "pass" else "",
                "missing_fields": ";".join(missing),
                "status": status,
            }
        )
    return rows


def build_checklist(root, narrative_rows, source_rows):
    reporting = read_json(root / RESULTS_REPORTING)
    table_recompute = read_json(root / TABLE_RECOMPUTE)
    claim_numeric = read_json(root / CLAIM_NUMERIC)
    facts = source_facts(source_rows)
    input_paths = [PRIMARY, EFFECTS, SOURCE_DATA, RESULTS_REPORTING, TABLE_RECOMPUTE, CLAIM_NUMERIC]
    checks = [
        {
            "check_id": "RN_inputs_exist",
            "category": "input_presence",
            "status": "pass" if all((root / path).exists() for path in input_paths) else "review_required",
            "observed": ";".join(path for path in input_paths if (root / path).exists()),
            "expected": "all narrative inputs exist",
            "evidence": ";".join(input_paths),
        },
        {
            "check_id": "RN_primary_sentence_count",
            "category": "narrative_coverage",
            "status": "pass" if len(narrative_rows) == 5 else "review_required",
            "observed": len(narrative_rows),
            "expected": 5,
            "evidence": PRIMARY,
        },
        {
            "check_id": "RN_sentence_fields_complete",
            "category": "narrative_coverage",
            "status": "pass" if all(row["status"] == "pass" for row in narrative_rows) else "review_required",
            "observed": sum(1 for row in narrative_rows if row["status"] == "pass"),
            "expected": len(narrative_rows),
            "evidence": EFFECTS,
        },
        {
            "check_id": "RN_reporting_checklist_pass",
            "category": "upstream_audit",
            "status": "pass" if reporting.get("status") == "pass" else "review_required",
            "observed": reporting.get("status"),
            "expected": "pass",
            "evidence": RESULTS_REPORTING,
        },
        {
            "check_id": "RN_recompute_and_numeric_pass",
            "category": "upstream_audit",
            "status": "pass" if table_recompute.get("status") == "pass" and claim_numeric.get("status") == "pass" else "review_required",
            "observed": f"table={table_recompute.get('status')}; claim_numeric={claim_numeric.get('status')}",
            "expected": "both pass",
            "evidence": f"{TABLE_RECOMPUTE};{CLAIM_NUMERIC}",
        },
        {
            "check_id": "RN_source_scale_bound",
            "category": "claim_boundary",
            "status": "pass" if facts["source_rows"] == 240 and facts["matched_case_count"] == 30 and facts["algorithm_count"] == 8 else "review_required",
            "observed": f"rows={facts['source_rows']}; cases={facts['matched_case_count']}; algorithms={facts['algorithm_count']}; vehicles={facts['vehicle_counts']}",
            "expected": "240 rows; 30 matched cases; 8 algorithms; vehicles 4,5,6,8",
            "evidence": SOURCE_DATA,
        },
    ]
    return checks


def build_report(root):
    primary_rows = read_csv(root / PRIMARY)
    effect_rows = read_csv(root / EFFECTS)
    source_rows = read_csv(root / SOURCE_DATA)
    narrative_rows = build_rows(primary_rows, effect_rows)
    checklist_rows = build_checklist(root, narrative_rows, source_rows)
    final = read_json(root / FINAL_READINESS)
    issue_count = sum(1 for row in narrative_rows + checklist_rows if row["status"] != "pass")
    facts = source_facts(source_rows)
    summary = {
        "status": "pass" if issue_count == 0 else "review_required",
        "primary_sentence_count": len(narrative_rows),
        "primary_sentence_pass_count": sum(1 for row in narrative_rows if row["status"] == "pass"),
        "checklist_issue_count": sum(1 for row in checklist_rows if row["status"] != "pass"),
        "source_rows": facts["source_rows"],
        "matched_case_count": facts["matched_case_count"],
        "algorithm_count": facts["algorithm_count"],
        "vehicle_counts": facts["vehicle_counts"],
        "final_readiness": f"{final.get('pass_count', 'NA')}/{final.get('gate_count', 'NA')}",
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "narrative_rows": narrative_rows,
        "checklist_rows": checklist_rows,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Results Narrative Pack",
        "",
        "该材料把正式统计表转换为可直接用于 Results 初稿的句子模板，并保留中文解释、效应量、配对胜负和平局计数与写作边界。它不是新的实验结果，而是对现有 240-run confirmatory evidence 的写作层封装。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Manuscript-Ready Primary Result Sentences",
            "",
        ]
    )
    for row in report["narrative_rows"]:
        lines.append(f"- **{row['hypothesis_id']} ({row['metric_label']})**: {row['manuscript_sentence']}")
    lines.extend(
        [
            "",
            "## 中文解释",
            "",
        ]
    )
    for row in report["narrative_rows"]:
        lines.append(f"- **{row['hypothesis_id']}**: {row['chinese_interpretation']}")
    lines.extend(
        [
            "",
            "## Narrative Table",
            "",
            "| H | Metric | N | Delta | Holm p | dz | Effect | + / - / 0 | Status |",
            "|---|---|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for row in report["narrative_rows"]:
        lines.append(
            f"| {row['hypothesis_id']} | {row['metric_label']} | {row['n_paired']} | {row['delta']} | "
            f"{row['p_holm']} | {row['paired_cohen_dz']} | {row['effect_magnitude']} | "
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
            "- These sentences should be edited for flow, but the numeric values, direction, p-values and effect sizes should not be changed by hand.",
            "- Report confidence intervals and effect sizes before interpreting p-values.",
            "- Keep the claim scoped to simulation, 240 formal runs, 30 matched cases, 8 algorithms and vehicle counts 4/5/6/8.",
            "- Do not describe these metrics as real-road safety certification or real-world deployment validation.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_results_narrative_pack.py --out-dir outputs/tits_dynamic_graph/tits_results_narrative_pack",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export manuscript-ready Results narrative text from formal T-ITS statistical evidence.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_results_narrative_pack")
    args = parser.parse_args()
    root = Path(".").resolve()
    report = build_report(root)
    out_dir = Path(args.out_dir)
    paths = {
        "report_md": write_text(out_dir / "materials" / "RESULTS_NARRATIVE_PACK.md", build_markdown(report)),
        "narrative_csv": write_csv(
            out_dir / "tables" / "results_narrative_sentences.csv",
            report["narrative_rows"],
            [
                "hypothesis_id",
                "metric",
                "metric_label",
                "n_paired",
                "delta",
                "ci95_low",
                "ci95_high",
                "p_holm",
                "paired_cohen_dz",
                "effect_magnitude",
                "positive_cases",
                "negative_cases",
                "zero_cases",
                "manuscript_sentence",
                "chinese_interpretation",
                "missing_fields",
                "status",
            ],
        ),
        "checklist_csv": write_csv(
            out_dir / "tables" / "results_narrative_checklist.csv",
            report["checklist_rows"],
            ["check_id", "category", "status", "observed", "expected", "evidence"],
        ),
        "report_json": write_json(out_dir / "materials" / "RESULTS_NARRATIVE_PACK.json", report),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
        "boundary": "Manuscript-writing narrative pack only; it formats existing formal statistics and does not rerun simulations or alter results.",
    }
    manifest_path = write_json(out_dir / "tits_results_narrative_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
