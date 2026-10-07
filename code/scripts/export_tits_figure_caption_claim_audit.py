#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


FIGURE_MANIFEST = "outputs/tits_dynamic_graph/manuscript_english_figures/manuscript_english_figures_manifest.json"
FIGURE_LEGEND = "outputs/tits_dynamic_graph/manuscript_english_figures/materials/FIGURE_DYNAMIC_DLC_OVERTAKING_LEGEND.md"
FIGURE_QA = "outputs/tits_dynamic_graph/manuscript_english_figures/materials/FIGURE_DYNAMIC_DLC_OVERTAKING_QA.json"
FIGURE_SOURCE = "outputs/tits_dynamic_graph/manuscript_english_figures/tables/figure_dynamic_dlc_overtaking_source_data.csv"
FIGURE_VALUE_RECOMPUTE = "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/tits_figure_source_value_recompute_audit_manifest.json"
RESULTS_REPORTING = "outputs/tits_dynamic_graph/tits_results_reporting_checklist/tits_results_reporting_checklist_manifest.json"
RESULTS_NARRATIVE = "outputs/tits_dynamic_graph/tits_results_narrative_pack/tits_results_narrative_pack_manifest.json"

EXPECTED_PANELS = {"a", "b", "c", "d"}
EXPECTED_PANEL_METRICS = {
    "a": {"overtake_success_rate", "elegant_overtake_rate", "on_track_overtake_rate"},
    "b": {"overtake_start_to_complete_time", "target_grass_rate"},
    "c": {"elegant_overtake_rate"},
    "d": {
        "overtake_success_rate",
        "elegant_overtake_rate",
        "on_track_overtake_rate",
        "overtake_start_to_complete_time",
        "target_grass_rate",
    },
}
FORBIDDEN_CAPTION_PHRASES = [
    "real-world validation",
    "real road safety",
    "deployment-ready",
    "proves safety",
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


def panel_source_summary(source_rows):
    summary = []
    for panel in sorted(EXPECTED_PANELS):
        rows = [row for row in source_rows if row.get("panel") == panel]
        metrics = sorted({row.get("metric", "") for row in rows if row.get("metric")})
        algorithms = sorted({row.get("algorithm_label", "") for row in rows if row.get("algorithm_label")})
        comparisons = sorted({row.get("comparison", "") for row in rows if row.get("comparison")})
        expected = EXPECTED_PANEL_METRICS[panel]
        missing_metrics = sorted(expected - set(metrics))
        summary.append(
            {
                "panel": panel,
                "source_row_count": len(rows),
                "metrics": ";".join(metrics),
                "expected_metrics": ";".join(sorted(expected)),
                "missing_metrics": ";".join(missing_metrics),
                "algorithm_count": len(algorithms),
                "comparison_count": len(comparisons),
                "status": "pass" if rows and not missing_metrics else "review_required",
            }
        )
    return summary


def build_checks(root, legend, source_rows):
    manifest = read_json(root / FIGURE_MANIFEST)
    qa = read_json(root / FIGURE_QA)
    value_recompute = read_json(root / FIGURE_VALUE_RECOMPUTE)
    results_reporting = read_json(root / RESULTS_REPORTING)
    results_narrative = read_json(root / RESULTS_NARRATIVE)
    paths = manifest.get("paths", {})
    export_paths = [paths.get("figure_svg"), paths.get("figure_pdf"), paths.get("figure_png"), paths.get("figure_tiff")]
    export_status = all(path and (root / path).exists() and (root / path).stat().st_size > 0 for path in export_paths)
    panels_in_caption = {panel for panel in EXPECTED_PANELS if f"**{panel}," in legend or f"{panel}," in legend}
    forbidden_hits = [phrase for phrase in FORBIDDEN_CAPTION_PHRASES if phrase in legend.lower()]
    panel_rows = panel_source_summary(source_rows)
    checks = [
        {
            "check_id": "FC_exports_exist",
            "category": "export_contract",
            "status": "pass" if export_status else "review_required",
            "observed": ";".join(path for path in export_paths if path),
            "expected": "svg/pdf/png/tiff exports exist and are nonempty",
            "evidence": FIGURE_MANIFEST,
        },
        {
            "check_id": "FC_qa_export_contract",
            "category": "export_contract",
            "status": "pass"
            if qa.get("status") == "pass"
            and qa.get("checks", {}).get("editable_svg_text")
            and qa.get("checks", {}).get("pdf_fonttype") == "42"
            and qa.get("checks", {}).get("all_exports_nonempty") is True
            else "review_required",
            "observed": f"qa={qa.get('status')}; svg={qa.get('checks', {}).get('editable_svg_text')}; pdf={qa.get('checks', {}).get('pdf_fonttype')}; exports={qa.get('checks', {}).get('all_exports_nonempty')}",
            "expected": "editable SVG text, PDF fonttype 42, all exports nonempty",
            "evidence": FIGURE_QA,
        },
        {
            "check_id": "FC_caption_panel_coverage",
            "category": "caption_logic",
            "status": "pass" if panels_in_caption == EXPECTED_PANELS else "review_required",
            "observed": ";".join(sorted(panels_in_caption)),
            "expected": ";".join(sorted(EXPECTED_PANELS)),
            "evidence": FIGURE_LEGEND,
        },
        {
            "check_id": "FC_caption_source_data_pointer",
            "category": "caption_logic",
            "status": "pass" if "figure_dynamic_dlc_overtaking_source_data.csv" in legend else "review_required",
            "observed": "present" if "figure_dynamic_dlc_overtaking_source_data.csv" in legend else "missing",
            "expected": "caption points to quantitative source data",
            "evidence": FIGURE_LEGEND,
        },
        {
            "check_id": "FC_caption_boundary",
            "category": "claim_boundary",
            "status": "pass" if "frozen confirmatory evidence" in legend and not forbidden_hits else "review_required",
            "observed": f"forbidden_hits={';'.join(forbidden_hits)}",
            "expected": "caption remains scoped to frozen confirmatory simulation evidence",
            "evidence": FIGURE_LEGEND,
        },
        {
            "check_id": "FC_source_panel_metrics",
            "category": "source_data",
            "status": "pass" if all(row["status"] == "pass" for row in panel_rows) else "review_required",
            "observed": ";".join(f"{row['panel']}:{row['source_row_count']} rows" for row in panel_rows),
            "expected": "each panel has expected source metrics",
            "evidence": FIGURE_SOURCE,
        },
        {
            "check_id": "FC_value_recompute_pass",
            "category": "numeric_traceability",
            "status": "pass" if value_recompute.get("status") == "pass" else "review_required",
            "observed": value_recompute.get("status"),
            "expected": "pass",
            "evidence": FIGURE_VALUE_RECOMPUTE,
        },
        {
            "check_id": "FC_results_text_alignment",
            "category": "manuscript_alignment",
            "status": "pass" if results_reporting.get("status") == "pass" and results_narrative.get("status") == "pass" else "review_required",
            "observed": f"reporting={results_reporting.get('status')}; narrative={results_narrative.get('status')}",
            "expected": "Results reporting checklist and narrative pack pass",
            "evidence": f"{RESULTS_REPORTING};{RESULTS_NARRATIVE}",
        },
    ]
    return checks, panel_rows


def build_report(root):
    legend = read_text(root / FIGURE_LEGEND)
    source_rows = read_csv(root / FIGURE_SOURCE)
    checks, panel_rows = build_checks(root, legend, source_rows)
    issue_count = sum(1 for row in checks + panel_rows if row["status"] != "pass")
    summary = {
        "status": "pass" if issue_count == 0 else "review_required",
        "check_count": len(checks),
        "check_issue_count": sum(1 for row in checks if row["status"] != "pass"),
        "panel_count": len(panel_rows),
        "panel_issue_count": sum(1 for row in panel_rows if row["status"] != "pass"),
        "source_rows": len(source_rows),
        "figure_archetype": read_json(root / FIGURE_MANIFEST).get("figure_contract", {}).get("archetype"),
        "backend": read_json(root / FIGURE_MANIFEST).get("figure_contract", {}).get("backend"),
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "check_rows": checks,
        "panel_rows": panel_rows,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Figure Caption Claim Audit",
        "",
        "该审计面向主图和图注：检查多面板图件的 caption 声明、source data、导出格式、图件 QA、数值复算和 Results 叙述是否闭环一致。它不重新绘图，只审计现有投稿图件证据链。",
        "",
        "## Figure Contract",
        "",
        f"- core conclusion: Dynamic-neighborhood DLC world-model planning improves online overtaking quality and efficiency over original DLC.",
        f"- archetype: {summary['figure_archetype']}",
        f"- backend: {summary['backend']}",
        f"- export contract: SVG/PDF/PNG/TIFF plus source data and editable text checks.",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Panel Claim Map",
            "",
            "| Panel | Source rows | Metrics | Expected metrics | Algorithms | Comparisons | Status |",
            "|---|---:|---|---|---:|---:|---|",
        ]
    )
    for row in report["panel_rows"]:
        lines.append(
            f"| {row['panel']} | {row['source_row_count']} | {row['metrics']} | {row['expected_metrics']} | "
            f"{row['algorithm_count']} | {row['comparison_count']} | {row['status']} |"
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
    for row in report["check_rows"]:
        lines.append(
            f"| {row['check_id']} | {row['category']} | {row['status']} | {row['observed']} | {row['expected']} | `{row['evidence']}` |"
        )
    lines.extend(
        [
            "",
            "## Writing Boundary",
            "",
            "- Keep the caption scoped to simulator-based confirmatory evidence.",
            "- Do not promote GIF case studies or visual examples above the 240-run quantitative matrix.",
            "- Preserve source-data pointers in the final caption or supplementary legend.",
            "- If the figure is redrawn or resized for IEEE production, rerun this audit and the figure source-value recompute audit.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_figure_caption_claim_audit.py --out-dir outputs/tits_dynamic_graph/tits_figure_caption_claim_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit manuscript figure caption claims against source data and Results evidence.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_figure_caption_claim_audit")
    args = parser.parse_args()
    root = Path(".").resolve()
    report = build_report(root)
    out_dir = Path(args.out_dir)
    paths = {
        "report_md": write_text(out_dir / "materials" / "FIGURE_CAPTION_CLAIM_AUDIT.md", build_markdown(report)),
        "check_csv": write_csv(
            out_dir / "tables" / "figure_caption_claim_checks.csv",
            report["check_rows"],
            ["check_id", "category", "status", "observed", "expected", "evidence"],
        ),
        "panel_csv": write_csv(
            out_dir / "tables" / "figure_panel_claim_map.csv",
            report["panel_rows"],
            ["panel", "source_row_count", "metrics", "expected_metrics", "missing_metrics", "algorithm_count", "comparison_count", "status"],
        ),
        "report_json": write_json(out_dir / "materials" / "FIGURE_CAPTION_CLAIM_AUDIT.json", report),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
        "boundary": "Figure-caption audit only; it checks existing figure evidence and does not redraw figures or alter numerical results.",
    }
    manifest_path = write_json(out_dir / "tits_figure_caption_claim_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
