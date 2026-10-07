#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path


CLAIM_MATRIX = "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/tables/claim_evidence_completeness_matrix.csv"
NUMERIC_TRACE = "outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/tits_manuscript_numeric_trace_audit_manifest.json"
CLAIM_LANGUAGE = "outputs/tits_dynamic_graph/tits_claim_language_audit/tits_claim_language_audit_manifest.json"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"

MANUSCRIPT_FILES = {
    "Abstract": "outputs/tits_dynamic_graph/tits_manuscript_package/materials/ABSTRACT_HIGHLIGHTS_DRAFT.md",
    "Contributions": "outputs/tits_dynamic_graph/tits_manuscript_package/materials/CONTRIBUTIONS_DRAFT.md",
    "Methods": "outputs/tits_dynamic_graph/tits_manuscript_package/materials/METHODS_DRAFT.md",
    "Results": "outputs/tits_dynamic_graph/tits_manuscript_package/materials/RESULTS_DRAFT.md",
    "Discussion": "outputs/tits_dynamic_graph/tits_manuscript_package/materials/LIMITATIONS_DRAFT.md",
    "Limitations": "outputs/tits_dynamic_graph/tits_manuscript_package/materials/LIMITATIONS_DRAFT.md",
    "Data/Code Availability": "outputs/tits_dynamic_graph/reviewer_replication_packet/DATA_CODE_AVAILABILITY_DRAFT.md",
    "Supplement": "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/MANUSCRIPT_SUPPLEMENT_NAVIGATOR.md",
    "Supplementary Results": "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/MANUSCRIPT_SUPPLEMENT_NAVIGATOR.md",
    "Supplementary Analysis": "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/MANUSCRIPT_SUPPLEMENT_NAVIGATOR.md",
    "Supplementary Reproducibility": "outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md",
    "Supplementary Videos": "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.md",
    "Ablation": "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_REPORT.md",
    "Experiments": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/materials/BENCHMARK_METRIC_PROTOCOL_CARD.md",
    "Metrics": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/metric_dictionary.csv",
}

SECTION_GROUPS = [
    {
        "section": "Abstract",
        "required_claim_areas": ["main_result", "dynamic_vehicle_count", "reproducibility"],
        "writing_role": "High-level bounded claim: problem, method family, benchmark scale, main result and reproducibility route.",
    },
    {
        "section": "Contributions",
        "required_claim_areas": ["algorithm_novelty", "dynamic_vehicle_count", "reproducibility"],
        "writing_role": "Contribution wording: DLC lineage, runtime graph construction, overtake-aware planning and reproducibility package.",
    },
    {
        "section": "Methods",
        "required_claim_areas": ["algorithm_novelty", "dynamic_vehicle_count", "statistical_validity"],
        "writing_role": "Technical description: dynamic-neighborhood graph, world-model planner, baselines, benchmark and statistical plan.",
    },
    {
        "section": "Results",
        "required_claim_areas": ["main_result", "overtake_quality", "external_track_boundary", "failure_boundary", "statistical_validity"],
        "writing_role": "Evidence-first reporting: primary metrics, paired deltas, Monza result and residual failure modes.",
    },
    {
        "section": "Discussion",
        "required_claim_areas": ["external_track_boundary", "failure_boundary", "baseline_fairness_rule_expert", "metric_sensitivity", "quality_proposal_boundary"],
        "writing_role": "Bounded interpretation: external validity, rule expert trade-offs, quality proposal and limitations.",
    },
    {
        "section": "Data/Code Availability",
        "required_claim_areas": ["reproducibility", "container_reproducibility_boundary"],
        "writing_role": "Reproducibility wording: source data, commands, artifact checksums, author-owned DOI/license boundary and container draft status.",
    },
]


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


def split_sections(section_text):
    return [item.strip() for item in section_text.split(";") if item.strip()]


def normalize_section(section):
    mapping = {
        "Supplementary Results": "Supplement",
        "Supplementary Analysis": "Supplement",
        "Supplementary Reproducibility": "Data/Code Availability",
        "Supplementary Videos": "Supplement",
        "Metrics": "Methods",
        "Experiments": "Methods",
        "Limitations": "Discussion",
    }
    return mapping.get(section, section)


def evidence_status(root, paths_text):
    paths = [item.strip() for item in paths_text.split(";") if item.strip()]
    missing = [item for item in paths if not (root / item).exists()]
    return len(paths), missing


def draft_mentions_claim(text, claim):
    haystack = text.lower()
    claim_area = claim.get("claim_area", "").replace("_", " ").lower()
    section = normalize_section(split_sections(claim.get("paper_section", ""))[0] if claim.get("paper_section") else "").lower()
    keywords = {
        "main_result": ["success", "elegant", "completion"],
        "overtake_quality": ["quality", "elegant", "grass"],
        "dynamic_vehicle_count": ["dynamic", "neighbor", "vehicle count", "8"],
        "external_track_boundary": ["monza", "external"],
        "failure_boundary": ["grass", "failure", "off-track"],
        "baseline_fairness_rule_expert": ["rule expert", "baseline"],
        "metric_sensitivity": ["sensitivity", "threshold"],
        "statistical_validity": ["paired", "holm", "confidence"],
        "case_stability": ["case", "leave-one", "heterogeneity"],
        "algorithm_novelty": ["dlc", "world model", "dynamic-neighborhood"],
        "quality_proposal_boundary": ["quality-proposal", "quality proposal"],
        "reproducibility": ["source data", "checksum", "reproducibility"],
        "compute_transparency": ["compute", "gpu", "wall-clock"],
        "visual_evidence": ["gif", "first-person", "top-down"],
        "container_reproducibility_boundary": ["docker", "apptainer", "container"],
    }.get(claim.get("claim_area"), [claim_area])
    return any(keyword in haystack for keyword in keywords) or section in haystack


def build_section_rows(root, claims):
    rows = []
    for claim in claims:
        sections = split_sections(claim.get("paper_section", ""))
        path_count, missing = evidence_status(root, claim.get("evidence_paths", ""))
        for raw_section in sections:
            section = normalize_section(raw_section)
            draft_path = MANUSCRIPT_FILES.get(raw_section) or MANUSCRIPT_FILES.get(section, "")
            draft_text = read_text(root / draft_path) if draft_path else ""
            rows.append(
                {
                    "section": section,
                    "source_section_label": raw_section,
                    "claim_id": claim.get("claim_id", ""),
                    "claim_area": claim.get("claim_area", ""),
                    "allowed_claim": claim.get("allowed_claim", ""),
                    "required_boundary": claim.get("required_boundary", ""),
                    "avoid_claim": claim.get("avoid_claim", ""),
                    "evidence_path_count": path_count,
                    "missing_evidence_count": len(missing),
                    "missing_evidence": "; ".join(missing),
                    "draft_path": draft_path,
                    "draft_exists": bool(draft_path and (root / draft_path).exists()),
                    "draft_mentions_claim": draft_mentions_claim(draft_text, claim) if draft_text else False,
                    "status": "pass" if path_count > 0 and not missing and draft_path and (root / draft_path).exists() else "review_required",
                }
            )
    return rows


def build_section_group_rows(root, claims, section_rows):
    by_area = defaultdict(list)
    for row in section_rows:
        by_area[row["claim_area"]].append(row)
    rows = []
    for group in SECTION_GROUPS:
        missing_areas = []
        weak_draft_areas = []
        evidence_missing_areas = []
        for area in group["required_claim_areas"]:
            area_rows = by_area.get(area, [])
            normalized_area_rows = [row for row in area_rows if row["section"] == group["section"]]
            usable_rows = normalized_area_rows or area_rows
            if not usable_rows:
                missing_areas.append(area)
                continue
            if not any(row["draft_mentions_claim"] for row in usable_rows):
                weak_draft_areas.append(area)
            if any(int(row["missing_evidence_count"]) > 0 for row in usable_rows):
                evidence_missing_areas.append(area)
        draft_path = MANUSCRIPT_FILES.get(group["section"], "")
        rows.append(
            {
                "section": group["section"],
                "writing_role": group["writing_role"],
                "required_claim_areas": "; ".join(group["required_claim_areas"]),
                "missing_claim_areas": "; ".join(missing_areas),
                "weak_draft_signal_areas": "; ".join(weak_draft_areas),
                "evidence_missing_areas": "; ".join(evidence_missing_areas),
                "draft_path": draft_path,
                "draft_exists": bool(draft_path and (root / draft_path).exists()),
                "status": "pass" if not missing_areas and not evidence_missing_areas and draft_path and (root / draft_path).exists() else "review_required",
            }
        )
    return rows


def build_boundary_rows(section_rows):
    out = []
    seen = set()
    for row in section_rows:
        key = (row["section"], row["claim_id"])
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "section": row["section"],
                "claim_id": row["claim_id"],
                "claim_area": row["claim_area"],
                "required_boundary": row["required_boundary"],
                "avoid_claim": row["avoid_claim"],
            }
        )
    return out


def build_markdown(report):
    lines = [
        "# T-ITS Manuscript Section Trace Audit",
        "",
        "该审计把 manuscript-facing 草稿按章节映射到 claim、证据文件、限制边界和禁止表述。它用于顶刊写作和返修时逐段核对，不新增实验结果。",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Section-Level Gates",
            "",
            "| Section | Status | Required claim areas | Missing areas | Weak draft signals | Evidence missing | Draft |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["section_group_rows"]:
        lines.append(
            f"| {row['section']} | {row['status']} | {row['required_claim_areas']} | {row['missing_claim_areas']} | "
            f"{row['weak_draft_signal_areas']} | {row['evidence_missing_areas']} | `{row['draft_path']}` |"
        )
    lines.extend(
        [
            "",
            "## Writing Rules",
            "",
            "- Abstract 只能写 simulation-bounded 主结论，不能写真实道路安全或任意泛化。",
            "- Methods 必须把当前算法明确写成 optimized DLC-style world model，而不是脱离 DLC baseline 家族的新算法。",
            "- Results 的每个数值 claim 必须可回链到 source CSV、paired/statistical table、figure source data 或 numeric trace。",
            "- Discussion 必须同时写成功、失败、rule expert trade-off、Monza 单赛道边界和后验敏感性边界。",
            "- Data/Code Availability 必须明确 DOI/license/repository release 仍是作者侧动作；容器只有草案和预检，不能写成已发布镜像。",
        ]
    )
    return "\n".join(lines)


def build_report(root):
    claims = read_csv(root / CLAIM_MATRIX)
    numeric_trace = read_json(root / NUMERIC_TRACE)
    claim_language = read_json(root / CLAIM_LANGUAGE)
    readiness = read_json(root / FINAL_READINESS)
    section_rows = build_section_rows(root, claims)
    section_group_rows = build_section_group_rows(root, claims, section_rows)
    boundary_rows = build_boundary_rows(section_rows)
    missing_evidence = sorted({item for row in section_rows for item in row["missing_evidence"].split("; ") if item})
    summary = {
        "status": "pass" if all(row["status"] == "pass" for row in section_group_rows) and not missing_evidence else "review_required",
        "claim_count": len(claims),
        "section_trace_row_count": len(section_rows),
        "section_gate_count": len(section_group_rows),
        "section_gate_pass_count": sum(1 for row in section_group_rows if row["status"] == "pass"),
        "missing_evidence_count": len(missing_evidence),
        "weak_draft_signal_count": sum(1 for row in section_rows if not row["draft_mentions_claim"]),
        "numeric_trace_status": numeric_trace.get("status"),
        "claim_language_status": claim_language.get("status"),
        "final_readiness": f"{readiness.get('pass_count', 'NA')}/{readiness.get('gate_count', 'NA')}",
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "section_rows": section_rows,
        "section_group_rows": section_group_rows,
        "boundary_rows": boundary_rows,
        "missing_evidence": missing_evidence,
        "boundary": "Section trace PASS means manuscript-facing sections have claim/evidence/boundary routes. It does not certify final IEEE formatting, author declarations, DOI deposition or journal submission.",
    }


def main():
    parser = argparse.ArgumentParser(description="Export manuscript section-to-claim trace audit for T-ITS package.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    report = build_report(root)
    paths = {
        "report_md": write_text(materials / "MANUSCRIPT_SECTION_TRACE_AUDIT.md", build_markdown(report)),
        "report_json": write_json(materials / "MANUSCRIPT_SECTION_TRACE_AUDIT.json", report),
        "section_trace_csv": write_csv(
            tables / "manuscript_section_claim_trace.csv",
            report["section_rows"],
            [
                "section",
                "source_section_label",
                "claim_id",
                "claim_area",
                "allowed_claim",
                "required_boundary",
                "avoid_claim",
                "evidence_path_count",
                "missing_evidence_count",
                "missing_evidence",
                "draft_path",
                "draft_exists",
                "draft_mentions_claim",
                "status",
            ],
        ),
        "section_gate_csv": write_csv(
            tables / "manuscript_section_gate_matrix.csv",
            report["section_group_rows"],
            [
                "section",
                "writing_role",
                "required_claim_areas",
                "missing_claim_areas",
                "weak_draft_signal_areas",
                "evidence_missing_areas",
                "draft_path",
                "draft_exists",
                "status",
            ],
        ),
        "boundary_csv": write_csv(
            tables / "manuscript_section_boundary_map.csv",
            report["boundary_rows"],
            ["section", "claim_id", "claim_area", "required_boundary", "avoid_claim"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
        "boundary": report["boundary"],
    }
    manifest_path = write_json(out_dir / "tits_manuscript_section_trace_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
