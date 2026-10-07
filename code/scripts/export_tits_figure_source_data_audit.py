#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


FIGURE_SPECS = [
    {
        "figure_id": "main_fig_2",
        "title": "Dynamic DLC overtaking main result",
        "base": "outputs/tits_dynamic_graph/manuscript_english_figures/figures/figure_dynamic_dlc_overtaking_english",
        "source_tables": ["outputs/tits_dynamic_graph/manuscript_english_figures/tables/figure_dynamic_dlc_overtaking_source_data.csv"],
        "legend_files": ["outputs/tits_dynamic_graph/manuscript_english_figures/materials/FIGURE_DYNAMIC_DLC_OVERTAKING_LEGEND.md"],
        "qa_files": ["outputs/tits_dynamic_graph/manuscript_english_figures/materials/FIGURE_DYNAMIC_DLC_OVERTAKING_QA.json"],
        "intended_use": "Main manuscript figure",
    },
    {
        "figure_id": "fig_contribution_attribution",
        "title": "Contribution attribution",
        "base": "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/figures/figure_dynamic_dlc_contribution_attribution",
        "source_tables": [
            "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/tables/ablation_contribution_overall.csv",
            "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/tables/ablation_contribution_paired.csv",
            "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/tables/ablation_contribution_scenario.csv",
        ],
        "legend_files": ["outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/FIGURE_DYNAMIC_DLC_CONTRIBUTION_LEGEND.md"],
        "qa_files": ["outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_QA.json"],
        "intended_use": "Main or supplementary figure",
    },
    {
        "figure_id": "fig_statistical_robustness",
        "title": "Statistical robustness",
        "base": "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/figures/figure_tits_statistical_robustness",
        "source_tables": [
            "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv",
            "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_effect_sizes.csv",
            "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_exploratory_holm_all.csv",
        ],
        "legend_files": ["outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/FIGURE_TITS_STATISTICAL_ROBUSTNESS_LEGEND.md"],
        "qa_files": ["outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/STATISTICAL_ANALYSIS_QA.json"],
        "intended_use": "Supplementary figure",
    },
    {
        "figure_id": "fig_confirmatory_overtake_cn",
        "title": "Confirmatory overtaking evidence Chinese figure",
        "base": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/figures/figure_confirmatory_overtake_evidence_cn",
        "source_tables": [
            "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv",
            "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_scenario_statistics.csv",
            "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv",
        ],
        "legend_files": ["outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/materials/CONFIRMATORY_EVIDENCE_REPORT.md"],
        "qa_files": ["outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/confirmatory_evidence_pack_manifest.json"],
        "intended_use": "Chinese supplementary/report figure",
    },
    {
        "figure_id": "fig_casewise_diagnostics_cn",
        "title": "Casewise overtaking diagnostics",
        "base": "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/figures/figure_casewise_overtake_diagnostics_cn",
        "source_tables": [
            "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_pairwise_win_loss_summary.csv",
            "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_failure_mode_summary.csv",
            "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_pairwise_overtake_deltas.csv",
        ],
        "legend_files": ["outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/materials/CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md"],
        "qa_files": ["outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tits_casewise_diagnostic_pack_manifest.json"],
        "intended_use": "Supplementary diagnostic figure",
    },
    {
        "figure_id": "fig_runtime_scalability_cn",
        "title": "Runtime scalability",
        "base": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/figures/figure_runtime_scalability_cn",
        "source_tables": [
            "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_scalability_by_vehicle_count.csv",
            "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_complexity_crosswalk.csv",
            "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_latency_vehicle_count_slopes.csv",
        ],
        "legend_files": ["outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md"],
        "qa_files": ["outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tits_runtime_scalability_pack_manifest.json"],
        "intended_use": "Supplementary scalability figure",
    },
    {
        "figure_id": "fig_experimental_design_power_cn",
        "title": "Experimental design, power and stability audit",
        "base": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/figures/figure_experimental_design_power_audit_cn",
        "source_tables": [
            "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/experimental_design_coverage.csv",
            "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/primary_metric_stability.csv",
            "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/scenario_level_stability.csv",
            "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/leave_one_scenario_stability.csv",
        ],
        "legend_files": ["outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md"],
        "qa_files": ["outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_QA.json"],
        "intended_use": "Supplementary experimental-design QC figure",
    },
    {
        "figure_id": "fig_case_influence_audit_cn",
        "title": "Leave-one-case influence audit",
        "base": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/figures/figure_case_influence_audit_cn",
        "source_tables": [
            "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/leave_one_case_influence.csv",
            "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/case_influence_summary.csv",
        ],
        "legend_files": ["outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md"],
        "qa_files": ["outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_QA.json"],
        "intended_use": "Supplementary leave-one-case robustness figure",
    },
]
FORMATS = ["pdf", "svg", "png", "tiff"]


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


def csv_row_count(path):
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def svg_text_count(path):
    path = Path(path)
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"<text\b", text))


def audit_figures(root):
    rows = []
    source_rows = []
    for spec in FIGURE_SPECS:
        errors = []
        warnings = []
        sizes = {}
        for fmt in FORMATS:
            rel = f"{spec['base']}.{fmt}"
            path = root / rel
            size = path.stat().st_size if path.exists() else 0
            sizes[f"{fmt}_path"] = rel
            sizes[f"{fmt}_size_bytes"] = size
            if size <= 0:
                errors.append(f"missing_or_empty_{fmt}")
        text_count = svg_text_count(root / f"{spec['base']}.svg")
        if text_count <= 0:
            warnings.append("svg_has_no_text_elements_or_text_converted_to_paths")
        total_source_rows = 0
        for table in spec["source_tables"]:
            count = csv_row_count(root / table)
            total_source_rows += count
            if count <= 0:
                errors.append(f"missing_or_empty_source_table:{table}")
            source_rows.append(
                {
                    "figure_id": spec["figure_id"],
                    "source_table": table,
                    "row_count": count,
                    "exists": (root / table).exists(),
                    "size_bytes": (root / table).stat().st_size if (root / table).exists() else 0,
                    "status": "pass" if count > 0 else "error",
                }
            )
        for key, label in [("legend_files", "legend"), ("qa_files", "qa")]:
            for rel in spec[key]:
                path = root / rel
                if not path.exists() or path.stat().st_size <= 0:
                    errors.append(f"missing_or_empty_{label}:{rel}")
        rows.append(
            {
                "figure_id": spec["figure_id"],
                "title": spec["title"],
                "intended_use": spec["intended_use"],
                **sizes,
                "source_table_count": len(spec["source_tables"]),
                "source_total_rows": total_source_rows,
                "legend_file_count": len(spec["legend_files"]),
                "qa_file_count": len(spec["qa_files"]),
                "svg_text_element_count": text_count,
                "status": "pass" if not errors else "error",
                "errors": ";".join(errors),
                "warnings": ";".join(warnings),
            }
        )
    return rows, source_rows


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Figure Source Data and Format Audit",
        "",
        "该审计检查当前投稿/补充材料图件是否具备顶刊常要求的三类证据：多格式导出、可追溯 source data、图例/QA 或报告说明。它不重新绘图，而是验证已有正式图件产物是否完整、非空、可归档。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Figure Checks",
            "",
            "| Figure | Status | Intended use | Source tables | Source rows | SVG text | Errors | Warnings |",
            "|---|---|---|---:|---:|---:|---|---|",
        ]
    )
    for row in report["figure_rows"]:
        lines.append(
            f"| {row['figure_id']} | {row['status']} | {row['intended_use']} | {row['source_table_count']} | {row['source_total_rows']} | {row['svg_text_element_count']} | {row['errors']} | {row['warnings']} |"
        )
    blocking = [row for row in report["figure_rows"] if row["status"] != "pass"]
    lines.extend(["", "## Blocking Issues", ""])
    if not blocking:
        lines.append("No blocking figure source-data or format issues were found.")
    else:
        for row in blocking:
            lines.append(f"- `{row['figure_id']}`: {row['errors']}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- PASS requires PDF/SVG/PNG/TIFF files to exist and be non-empty.",
            "- PASS requires every registered source table to exist and contain at least one data row.",
            "- SVG text-element count is reported as an editability clue; a low count is a warning, not a blocking error, because some Matplotlib objects may be path-based.",
            "- Final IEEE upload may still require author-side checks for figure width, caption wording, color accessibility and PDF compliance.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_figure_source_data_audit.py --out-dir outputs/tits_dynamic_graph/tits_figure_source_data_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit T-ITS formal figure source-data and format coverage.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_figure_source_data_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    figure_rows, source_rows = audit_figures(root)
    blocking = [row for row in figure_rows if row["status"] != "pass"]
    warning_count = sum(1 for row in figure_rows if row["warnings"])
    summary = {
        "status": "pass" if not blocking else "review_required",
        "figure_count": len(figure_rows),
        "format_count_per_figure": len(FORMATS),
        "source_table_count": len(source_rows),
        "source_table_total_rows": sum(int(row["row_count"]) for row in source_rows),
        "blocking_figure_count": len(blocking),
        "warning_figure_count": warning_count,
    }
    report = {
        "status": summary["status"],
        "summary": summary,
        "figure_specs": FIGURE_SPECS,
        "figure_rows": figure_rows,
        "source_rows": source_rows,
        "note": "This audit validates formal figure artifact coverage. It does not replace final journal layout, caption, color, or accessibility checks.",
    }
    figure_fields = [
        "figure_id",
        "title",
        "intended_use",
        "pdf_path",
        "pdf_size_bytes",
        "svg_path",
        "svg_size_bytes",
        "png_path",
        "png_size_bytes",
        "tiff_path",
        "tiff_size_bytes",
        "source_table_count",
        "source_total_rows",
        "legend_file_count",
        "qa_file_count",
        "svg_text_element_count",
        "status",
        "errors",
        "warnings",
    ]
    source_fields = ["figure_id", "source_table", "row_count", "exists", "size_bytes", "status"]
    paths = {
        "audit_md": write_text(materials / "FIGURE_SOURCE_DATA_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "FIGURE_SOURCE_DATA_AUDIT.json", report),
        "figure_checks_csv": write_csv(tables / "figure_source_data_checks.csv", figure_rows, figure_fields),
        "source_table_checks_csv": write_csv(tables / "figure_source_table_checks.csv", source_rows, source_fields),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": summary,
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_figure_source_data_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
