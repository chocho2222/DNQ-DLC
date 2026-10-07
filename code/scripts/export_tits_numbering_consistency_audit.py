#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


FIGURE_TABLE_PLAN = "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/tables/manuscript_figure_table_plan.csv"
SUPPLEMENT_INDEX = "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/tables/supplementary_materials_index.csv"
SOURCE_CROSSWALK = "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/tables/source_data_crosswalk.csv"
UPLOAD_BUNDLE = "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/tables/submission_upload_slots.csv"
GIF_MANIFEST = "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.json"

PLACEMENT_PATTERNS = [
    ("main_figure", re.compile(r"^Main Fig\. \d+(?: or Supplement Fig\. S\d+[a-z]?)?$")),
    ("main_table", re.compile(r"^Main Table \d+$")),
    ("supplement_figure", re.compile(r"^Supplement Fig\. S\d+[a-z]?(?: / [A-Za-z ]+)?$")),
    ("supplement_table_range", re.compile(r"^Supplement Table S\d+-S\d+$")),
    ("supplement_video_range", re.compile(r"^Supplement Videos V\d+-V\d+$")),
    ("supplementary_table", re.compile(r"^Supplementary [A-Za-z ]+$")),
    ("qc_or_release", re.compile(r"^(Reviewer Response Preparation|Submission Metadata|Open-source Release|Submission Closure|Data Archive Metadata|Third-party Reproduction|Supplementary QC(?: / [A-Za-z ]+)?|Supplementary Reproducibility Table)$")),
]
ALLOW_DUPLICATE_PLACEMENT_KINDS = {"supplementary_table", "qc_or_release"}
SUPPLEMENT_ID_PATTERNS = [
    ("supplementary_note", re.compile(r"^Supplementary Note \d+[a-z]?$")),
    ("supplementary_data", re.compile(r"^Supplementary Data \d+$")),
    ("supplementary_videos", re.compile(r"^Supplementary Videos \d+-\d+$")),
    ("named_reviewer_or_release", re.compile(r"^(Reviewer Package|Submission Metadata|Open-source Release|FAIR Archive Metadata|Third-party Reproduction)$")),
]
CLAIM_PATTERN = re.compile(r"^C\d+[a-z]?$")


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


def split_refs(value):
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def matches_any(value, patterns):
    for kind, pattern in patterns:
        if pattern.match(value):
            return True, kind
    return False, "unrecognized"


def resolve_ref(root, ref):
    if any(char in ref for char in "*?["):
        matches = sorted(root.glob(ref))
        return bool(matches), len(matches), "glob"
    path = root / ref
    return path.exists(), 1 if path.exists() else 0, "path"


def audit_figure_table_plan(root, rows):
    placement_counts = {}
    audit_rows = []
    ref_rows = []
    for row in rows:
        placement = row.get("placement", "").strip()
        placement_counts[placement] = placement_counts.get(placement, 0) + 1
        ok_pattern, placement_kind = matches_any(placement, PLACEMENT_PATTERNS)
        refs = [row.get("primary_artifact", "").strip()] + split_refs(row.get("source_data", ""))
        missing_refs = []
        matched_ref_count = 0
        for ref in refs:
            if not ref:
                continue
            exists, match_count, mode = resolve_ref(root, ref)
            matched_ref_count += match_count
            if not exists:
                missing_refs.append(ref)
            ref_rows.append(
                {
                    "table": "manuscript_figure_table_plan",
                    "entry_id": placement,
                    "reference": ref,
                    "resolution_mode": mode,
                    "match_count": match_count,
                    "exists": exists,
                    "status": "pass" if exists else "missing",
                }
            )
        duplicate = placement_counts[placement] > 1
        duplicate_ok = (not duplicate) or placement_kind in ALLOW_DUPLICATE_PLACEMENT_KINDS
        status = "pass" if ok_pattern and duplicate_ok and not missing_refs else "error"
        audit_rows.append(
            {
                "entry_table": "manuscript_figure_table_plan",
                "entry_id": placement,
                "entry_kind": placement_kind,
                "title_cn": row.get("title_cn", ""),
                "status": status,
                "pattern_ok": ok_pattern,
                "duplicate": duplicate,
                "checked_reference_count": len([ref for ref in refs if ref]),
                "matched_reference_count": matched_ref_count,
                "missing_references": "; ".join(missing_refs),
                "boundary": row.get("boundary", ""),
            }
        )
    return audit_rows, ref_rows


def audit_supplement_index(root, rows):
    id_counts = {}
    audit_rows = []
    ref_rows = []
    for row in rows:
        supplement_id = row.get("supplement_id", "").strip()
        id_counts[supplement_id] = id_counts.get(supplement_id, 0) + 1
        ok_pattern, entry_kind = matches_any(supplement_id, SUPPLEMENT_ID_PATTERNS)
        refs = [row.get("entry_file", "").strip()] + split_refs(row.get("include_files", ""))
        missing_refs = []
        matched_ref_count = 0
        for ref in refs:
            if not ref:
                continue
            exists, match_count, mode = resolve_ref(root, ref)
            matched_ref_count += match_count
            if not exists:
                missing_refs.append(ref)
            ref_rows.append(
                {
                    "table": "supplementary_materials_index",
                    "entry_id": supplement_id,
                    "reference": ref,
                    "resolution_mode": mode,
                    "match_count": match_count,
                    "exists": exists,
                    "status": "pass" if exists else "missing",
                }
            )
        duplicate = id_counts[supplement_id] > 1
        status = "pass" if ok_pattern and not duplicate and not missing_refs else "error"
        audit_rows.append(
            {
                "entry_table": "supplementary_materials_index",
                "entry_id": supplement_id,
                "entry_kind": entry_kind,
                "title_cn": row.get("title_cn", ""),
                "status": status,
                "pattern_ok": ok_pattern,
                "duplicate": duplicate,
                "checked_reference_count": len([ref for ref in refs if ref]),
                "matched_reference_count": matched_ref_count,
                "missing_references": "; ".join(missing_refs),
                "boundary": row.get("purpose", ""),
            }
        )
    return audit_rows, ref_rows


def audit_claim_crosswalk(root, rows):
    id_counts = {}
    audit_rows = []
    ref_rows = []
    for row in rows:
        claim_id = row.get("claim_id", "").strip()
        id_counts[claim_id] = id_counts.get(claim_id, 0) + 1
        refs = [row.get("primary_source", "").strip()] + split_refs(row.get("secondary_source", ""))
        missing_refs = []
        matched_ref_count = 0
        for ref in refs:
            if not ref:
                continue
            exists, match_count, mode = resolve_ref(root, ref)
            matched_ref_count += match_count
            if not exists:
                missing_refs.append(ref)
            ref_rows.append(
                {
                    "table": "source_data_crosswalk",
                    "entry_id": claim_id,
                    "reference": ref,
                    "resolution_mode": mode,
                    "match_count": match_count,
                    "exists": exists,
                    "status": "pass" if exists else "missing",
                }
            )
        duplicate = id_counts[claim_id] > 1
        pattern_ok = bool(CLAIM_PATTERN.match(claim_id))
        status = "pass" if pattern_ok and not duplicate and not missing_refs else "error"
        audit_rows.append(
            {
                "entry_table": "source_data_crosswalk",
                "entry_id": claim_id,
                "entry_kind": "claim",
                "title_cn": row.get("claim_cn", ""),
                "status": status,
                "pattern_ok": pattern_ok,
                "duplicate": duplicate,
                "checked_reference_count": len([ref for ref in refs if ref]),
                "matched_reference_count": matched_ref_count,
                "missing_references": "; ".join(missing_refs),
                "boundary": row.get("boundary", ""),
            }
        )
    return audit_rows, ref_rows


def audit_upload_alignment(root, upload_rows, figure_rows, supplement_rows):
    nav_text = " ".join(
        [row.get("placement", "") for row in figure_rows]
        + [row.get("supplement_id", "") for row in supplement_rows]
        + [row.get("title_cn", "") for row in figure_rows]
        + [row.get("title_cn", "") for row in supplement_rows]
    )
    expected_slots = {
        "S02_main_figures": "Main Fig. 2",
        "S03_source_data": "Supplementary Data 1",
        "S04_supplementary_information": "Supplementary Note",
        "S09_visual_supplement": "Supplementary Videos",
    }
    slot_ids = {row.get("slot_id", "") for row in upload_rows}
    rows = []
    for slot_id, expected_phrase in expected_slots.items():
        rows.append(
            {
                "slot_id": slot_id,
                "expected_navigation_phrase": expected_phrase,
                "slot_exists": slot_id in slot_ids,
                "navigator_mentions_phrase": expected_phrase in nav_text,
                "status": "pass" if slot_id in slot_ids and expected_phrase in nav_text else "error",
            }
        )
    return rows


def audit_gifs(root):
    manifest = read_json(root / GIF_MANIFEST)
    rows = []
    for item in manifest.get("rows", []):
        refs = [
            item.get("topdown_gif", ""),
            item.get("first_person_gif", ""),
            item.get("summary_path", ""),
            item.get("trace_path", ""),
        ]
        missing = [ref for ref in refs if ref and not (root / ref).exists()]
        rows.append(
            {
                "scene": item.get("scene", ""),
                "algorithm": item.get("algorithm", ""),
                "num_agents": item.get("num_agents", ""),
                "seed": item.get("seed", ""),
                "has_topdown": bool(item.get("topdown_gif")) and (root / item.get("topdown_gif", "")).exists(),
                "has_first_person": bool(item.get("first_person_gif")) and (root / item.get("first_person_gif", "")).exists(),
                "has_summary": bool(item.get("summary_path")) and (root / item.get("summary_path", "")).exists(),
                "has_trace": bool(item.get("trace_path")) and (root / item.get("trace_path", "")).exists(),
                "missing_references": "; ".join(missing),
                "status": "pass" if not missing else "error",
            }
        )
    manifest_ok = manifest.get("row_count") == len(rows) and manifest.get("row_count", 0) >= 4
    return rows, manifest_ok


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Numbering and Cross-Material Consistency Audit",
        "",
        "该审计面向最终投稿排版前的图号、表号、补充材料编号和视觉材料编号一致性。它不新增实验结果，而是检查 navigator、source-data crosswalk、upload bundle 和 GIF manifest 是否共同指向同一批正式证据。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Entry Checks",
            "",
            "| Table | Entry | Kind | Status | Pattern OK | Duplicate | Checked refs | Matched refs | Missing refs |",
            "|---|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in report["entry_rows"]:
        lines.append(
            f"| {row['entry_table']} | {row['entry_id']} | {row['entry_kind']} | {row['status']} | {row['pattern_ok']} | {row['duplicate']} | {row['checked_reference_count']} | {row['matched_reference_count']} | {row['missing_references']} |"
        )
    lines.extend(
        [
            "",
            "## Upload Alignment",
            "",
            "| Slot | Expected navigator phrase | Slot exists | Navigator mentions phrase | Status |",
            "|---|---|---:|---:|---|",
        ]
    )
    for row in report["upload_alignment_rows"]:
        lines.append(
            f"| {row['slot_id']} | {row['expected_navigation_phrase']} | {row['slot_exists']} | {row['navigator_mentions_phrase']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Visual Supplement Checks",
            "",
            "| Scene | Algorithm | Top-down | First-person | Summary | Trace | Status |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in report["gif_rows"]:
        lines.append(
            f"| {row['scene']} | {row['algorithm']} | {row['has_topdown']} | {row['has_first_person']} | {row['has_summary']} | {row['has_trace']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- PASS 表示当前编号规划、补充材料索引、source-data claim crosswalk、上传槽位和 GIF manifest 在文件存在性与基本编号格式上自洽。",
            "- 该审计仍不替代最终 IEEE 模板里的 Word/LaTeX 交叉引用自动更新；作者在排版后仍需人工检查 Fig./Table/Supplementary 编号。",
            "- 如果新增、删除或重排任一主图/补充图/补充视频，应先更新 manuscript supplement navigator，再重新运行本审计和 final readiness dashboard。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_numbering_consistency_audit.py --out-dir outputs/tits_dynamic_graph/tits_numbering_consistency_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def build_report(root):
    figure_rows = read_csv(root / FIGURE_TABLE_PLAN)
    supplement_rows = read_csv(root / SUPPLEMENT_INDEX)
    claim_rows = read_csv(root / SOURCE_CROSSWALK)
    upload_rows = read_csv(root / UPLOAD_BUNDLE)

    ft_entries, ft_refs = audit_figure_table_plan(root, figure_rows)
    supp_entries, supp_refs = audit_supplement_index(root, supplement_rows)
    claim_entries, claim_refs = audit_claim_crosswalk(root, claim_rows)
    upload_alignment = audit_upload_alignment(root, upload_rows, figure_rows, supplement_rows)
    gif_rows, gif_manifest_ok = audit_gifs(root)

    entry_rows = ft_entries + supp_entries + claim_entries
    reference_rows = ft_refs + supp_refs + claim_refs
    error_entries = [row for row in entry_rows if row["status"] != "pass"]
    missing_refs = [row for row in reference_rows if row["status"] != "pass"]
    upload_errors = [row for row in upload_alignment if row["status"] != "pass"]
    gif_errors = [row for row in gif_rows if row["status"] != "pass"]
    status = "pass" if not error_entries and not missing_refs and not upload_errors and not gif_errors and gif_manifest_ok else "review_required"
    summary = {
        "status": status,
        "figure_table_entries": len(ft_entries),
        "supplement_entries": len(supp_entries),
        "claim_crosswalk_entries": len(claim_entries),
        "entry_count": len(entry_rows),
        "reference_count": len(reference_rows),
        "entry_error_count": len(error_entries),
        "missing_reference_count": len(missing_refs),
        "upload_alignment_error_count": len(upload_errors),
        "gif_rows": len(gif_rows),
        "gif_manifest_row_count_ok": gif_manifest_ok,
        "gif_error_count": len(gif_errors),
    }
    return {
        "status": status,
        "summary": summary,
        "entry_rows": entry_rows,
        "reference_rows": reference_rows,
        "upload_alignment_rows": upload_alignment,
        "gif_rows": gif_rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Audit T-ITS figure/table/supplement numbering consistency.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_numbering_consistency_audit")
    args = parser.parse_args()

    root = Path(".").resolve()
    out_dir = Path(args.out_dir)
    report = build_report(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "report_md": write_text(out_dir / "materials" / "NUMBERING_CONSISTENCY_AUDIT.md", build_markdown(report)),
        "entry_checks_csv": write_csv(
            out_dir / "tables" / "numbering_entry_checks.csv",
            report["entry_rows"],
            [
                "entry_table",
                "entry_id",
                "entry_kind",
                "title_cn",
                "status",
                "pattern_ok",
                "duplicate",
                "checked_reference_count",
                "matched_reference_count",
                "missing_references",
                "boundary",
            ],
        ),
        "reference_checks_csv": write_csv(
            out_dir / "tables" / "numbering_reference_checks.csv",
            report["reference_rows"],
            ["table", "entry_id", "reference", "resolution_mode", "match_count", "exists", "status"],
        ),
        "upload_alignment_csv": write_csv(
            out_dir / "tables" / "numbering_upload_alignment.csv",
            report["upload_alignment_rows"],
            ["slot_id", "expected_navigation_phrase", "slot_exists", "navigator_mentions_phrase", "status"],
        ),
        "visual_supplement_csv": write_csv(
            out_dir / "tables" / "numbering_visual_supplement_checks.csv",
            report["gif_rows"],
            [
                "scene",
                "algorithm",
                "num_agents",
                "seed",
                "has_topdown",
                "has_first_person",
                "has_summary",
                "has_trace",
                "missing_references",
                "status",
            ],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_numbering_consistency_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
