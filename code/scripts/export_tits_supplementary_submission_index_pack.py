#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


NAVIGATOR_QA = "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/NAVIGATOR_QA.json"
SUPPLEMENT_INDEX = "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/tables/supplementary_materials_index.csv"
FIGURE_TABLE_PLAN = "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/tables/manuscript_figure_table_plan.csv"
SOURCE_CROSSWALK = "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/tables/source_data_crosswalk.csv"
UPLOAD_SLOTS = "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/tables/submission_upload_slots.csv"
VIDEO_INDEX = "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/tables/supplementary_video_index.csv"
NUMBERING_MANIFEST = "outputs/tits_dynamic_graph/tits_numbering_consistency_audit/tits_numbering_consistency_audit_manifest.json"
UPLOAD_MANIFEST = "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/tits_submission_upload_bundle_map_manifest.json"
VIDEO_MANIFEST = "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/tits_supplementary_video_index_pack_manifest.json"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"


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


def split_paths(value):
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def exists_nonempty(root, rel_path):
    path = root / rel_path
    return path.exists() and path.stat().st_size > 0


def reference_exists(root, rel_path):
    if "*" in rel_path:
        matches = [path for path in root.glob(rel_path) if path.is_file() and path.stat().st_size > 0]
        return bool(matches), len(matches)
    return exists_nonempty(root, rel_path), 1 if exists_nonempty(root, rel_path) else 0


def count_source_facts(root):
    rows = read_csv(root / SOURCE_DATA)
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
        "algorithm_count": len({row.get("algorithm") for row in rows}),
    }


def classify_supplement_upload_slot(supplement_id):
    if supplement_id.startswith("Supplementary Note"):
        return "S04_supplementary_information"
    if supplement_id.startswith("Supplementary Data"):
        return "S03_source_data"
    if supplement_id.startswith("Supplementary Video"):
        return "S09_visual_supplement"
    if "Reproducibility" in supplement_id or "QC" in supplement_id:
        return "S05_reproducibility_packet"
    return "S04_supplementary_information"


def build_supplement_rows(root, supplement_rows, upload_slots):
    upload_by_id = {row.get("slot_id"): row for row in upload_slots}
    rows = []
    issues = []
    for row in supplement_rows:
        files = [row.get("entry_file", "")] + split_paths(row.get("include_files", ""))
        checked = [item for item in files if item]
        matched_file_count = 0
        missing = []
        for item in checked:
            ok, count = reference_exists(root, item)
            matched_file_count += count
            if not ok:
                missing.append(item)
        slot_id = classify_supplement_upload_slot(row.get("supplement_id", ""))
        upload = upload_by_id.get(slot_id, {})
        status = "pass" if not missing and upload.get("status") == "pass" else "review_required"
        out = {
            "supplement_id": row.get("supplement_id", ""),
            "title_cn": row.get("title_cn", ""),
            "submission_slot": slot_id,
            "slot_destination": upload.get("destination", ""),
            "entry_file": row.get("entry_file", ""),
            "include_file_count": len(split_paths(row.get("include_files", ""))),
            "checked_file_count": len(checked),
            "matched_file_count": matched_file_count,
            "missing_file_count": len(missing),
            "missing_files": "; ".join(missing),
            "purpose": row.get("purpose", ""),
            "reviewer_route": row.get("reviewer_route", ""),
            "status": status,
            "boundary": upload.get("boundary", "Supplementary material routing only; formal statistics come from the frozen source data."),
        }
        rows.append(out)
        if missing:
            issues.append(
                {
                    "item_type": "supplement",
                    "item_id": out["supplement_id"],
                    "severity": "error",
                    "issue": "missing_or_empty_referenced_file",
                    "details": out["missing_files"],
                }
            )
        if upload and upload.get("status") != "pass":
            issues.append(
                {
                    "item_type": "supplement",
                    "item_id": out["supplement_id"],
                    "severity": "warning",
                    "issue": "upload_slot_review_required",
                    "details": slot_id,
                }
            )
    return rows, issues


def build_figure_rows(root, figure_rows):
    rows = []
    issues = []
    for row in figure_rows:
        refs = [row.get("primary_artifact", "")] + split_paths(row.get("source_data", ""))
        checked = [item for item in refs if item and "*" not in item]
        matched_file_count = 0
        missing = []
        for item in checked:
            ok, count = reference_exists(root, item)
            matched_file_count += count
            if not ok:
                missing.append(item)
        status = "pass" if row.get("status") in {"ready", "planned_from_existing_material"} and not missing else "review_required"
        out = {
            "placement": row.get("placement", ""),
            "title_cn": row.get("title_cn", ""),
            "primary_artifact": row.get("primary_artifact", ""),
            "source_reference_count": len(split_paths(row.get("source_data", ""))),
            "checked_file_count": len(checked),
            "matched_file_count": matched_file_count,
            "missing_file_count": len(missing),
            "missing_files": "; ".join(missing),
            "recommended_use": row.get("recommended_use", ""),
            "claim_supported": row.get("claim_supported", ""),
            "boundary": row.get("boundary", ""),
            "status": status,
        }
        rows.append(out)
        if missing:
            issues.append(
                {
                    "item_type": "figure_or_table",
                    "item_id": out["placement"],
                    "severity": "error",
                    "issue": "missing_or_empty_referenced_file",
                    "details": out["missing_files"],
                }
            )
    return rows, issues


def build_video_rows(video_rows):
    rows = []
    issues = []
    for row in video_rows:
        status = "pass" if row.get("status") == "pass" and row.get("exists") in {"True", "true", "1"} else "review_required"
        out = {
            "video_id": row.get("video_id", ""),
            "scene": row.get("scene", ""),
            "view": row.get("view", ""),
            "algorithm": row.get("algorithm", ""),
            "benchmark": row.get("benchmark", ""),
            "num_agents": row.get("num_agents", ""),
            "seed": row.get("seed", ""),
            "gif_path": row.get("gif_path", ""),
            "size_mb": row.get("size_mb", ""),
            "submission_role": row.get("submission_role", ""),
            "caption": row.get("caption", ""),
            "claim_boundary": row.get("claim_boundary", ""),
            "status": status,
        }
        rows.append(out)
        if status != "pass":
            issues.append(
                {
                    "item_type": "video",
                    "item_id": out["video_id"],
                    "severity": "error",
                    "issue": "video_index_row_not_pass",
                    "details": row.get("errors", ""),
                }
            )
    return rows, issues


def build_claim_rows(source_crosswalk):
    rows = []
    for row in source_crosswalk:
        rows.append(
            {
                "claim_id": row.get("claim_id", ""),
                "claim_cn": row.get("claim_cn", ""),
                "recommended_location": row.get("recommended_location", ""),
                "primary_source": row.get("primary_source", ""),
                "secondary_source": row.get("secondary_source", ""),
                "boundary": row.get("boundary", ""),
                "status": "pass" if row.get("primary_source") and row.get("boundary") else "review_required",
            }
        )
    return rows


def build_report(root):
    navigator = read_json(root / NAVIGATOR_QA)
    numbering = read_json(root / NUMBERING_MANIFEST)
    upload = read_json(root / UPLOAD_MANIFEST)
    video_manifest = read_json(root / VIDEO_MANIFEST)
    final = read_json(root / FINAL_READINESS)
    source_facts = count_source_facts(root)
    supplement_rows, supplement_issues = build_supplement_rows(root, read_csv(root / SUPPLEMENT_INDEX), read_csv(root / UPLOAD_SLOTS))
    figure_rows, figure_issues = build_figure_rows(root, read_csv(root / FIGURE_TABLE_PLAN))
    video_rows, video_issues = build_video_rows(read_csv(root / VIDEO_INDEX))
    claim_rows = build_claim_rows(read_csv(root / SOURCE_CROSSWALK))
    issues = supplement_issues + figure_issues + video_issues
    upload_slots = read_csv(root / UPLOAD_SLOTS)
    summary = {
        "status": "pass" if not [item for item in issues if item["severity"] == "error"] else "review_required",
        "supplement_entries": len(supplement_rows),
        "figure_table_entries": len(figure_rows),
        "video_entries": len(video_rows),
        "claim_crosswalk_entries": len(claim_rows),
        "upload_slots": len(upload_slots),
        "issue_count": len(issues),
        "error_count": sum(1 for item in issues if item["severity"] == "error"),
        "warning_count": sum(1 for item in issues if item["severity"] == "warning"),
        "source_rows": source_facts["source_rows"],
        "matched_case_count": source_facts["matched_case_count"],
        "algorithm_count": source_facts["algorithm_count"],
        "final_readiness": f"{final.get('pass_count', 'NA')}/{final.get('gate_count', 'NA')}",
        "navigator_status": navigator.get("status"),
        "numbering_status": numbering.get("status"),
        "upload_bundle_status": upload.get("status"),
        "video_index_status": video_manifest.get("status"),
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "supplements": supplement_rows,
        "figures": figure_rows,
        "videos": video_rows,
        "claims": claim_rows,
        "issues": issues,
        "boundary": [
            "This pack is a submission-routing and supplementary-index layer; it does not create new empirical results.",
            "Formal performance claims should cite the frozen 240-row source data, confirmatory evidence pack and recompute audits.",
            "GIF/Video entries are qualitative representative visual evidence; final format conversion remains author-side.",
            "DOI/accession, repository URL, license, author metadata and IEEE template conversion remain author-owned tasks.",
        ],
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Supplementary Submission Index Pack",
        "",
        "This pack consolidates supplementary notes, figures/tables, source-data claims, upload slots and representative videos into one submission-facing index.",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Recommended Supplementary Items", "", "| ID | Title | Slot | Status | Files | Missing | Reviewer Route |", "|---|---|---|---|---:|---:|---|"])
    for row in report["supplements"]:
        lines.append(
            f"| {row['supplement_id']} | {row['title_cn']} | {row['submission_slot']} | {row['status']} | "
            f"{row['matched_file_count']} | {row['missing_file_count']} | {row['reviewer_route']} |"
        )
    lines.extend(["", "## Figure And Table Routing", "", "| Placement | Title | Status | Checked Files | Missing | Claim Supported | Boundary |", "|---|---|---|---:|---:|---|---|"])
    for row in report["figures"]:
        lines.append(
            f"| {row['placement']} | {row['title_cn']} | {row['status']} | {row['checked_file_count']} | "
            f"{row['missing_file_count']} | {row['claim_supported']} | {row['boundary']} |"
        )
    lines.extend(["", "## Supplementary Videos", "", "| Video | Scene | View | Algorithm | Size MB | Status | Boundary |", "|---|---|---|---|---:|---|---|"])
    for row in report["videos"]:
        lines.append(
            f"| {row['video_id']} | {row['scene']} | {row['view']} | {row['algorithm']} | "
            f"{row['size_mb']} | {row['status']} | {row['claim_boundary']} |"
        )
    lines.extend(["", "## Claim-Source Crosswalk", "", "| Claim | Location | Primary Source | Boundary |", "|---|---|---|---|"])
    for row in report["claims"]:
        lines.append(f"| {row['claim_id']} | {row['recommended_location']} | `{row['primary_source']}` | {row['boundary']} |")
    if report["issues"]:
        lines.extend(["", "## Issues", "", "| Type | Item | Severity | Issue | Details |", "|---|---|---|---|---|"])
        for issue in report["issues"]:
            lines.append(f"| {issue['item_type']} | {issue['item_id']} | {issue['severity']} | {issue['issue']} | {issue['details']} |")
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in report["boundary"])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export a supplementary submission index pack for the T-ITS package.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    paths = {
        "report_md": write_text(out_dir / "materials" / "SUPPLEMENTARY_SUBMISSION_INDEX.md", build_markdown(report)),
        "supplement_index_csv": write_csv(
            out_dir / "tables" / "supplementary_submission_items.csv",
            report["supplements"],
            [
                "supplement_id",
                "title_cn",
                "submission_slot",
                "slot_destination",
                "entry_file",
                "include_file_count",
                "checked_file_count",
                "matched_file_count",
                "missing_file_count",
                "missing_files",
                "purpose",
                "reviewer_route",
                "status",
                "boundary",
            ],
        ),
        "figure_table_csv": write_csv(
            out_dir / "tables" / "supplementary_figure_table_routing.csv",
            report["figures"],
            [
                "placement",
                "title_cn",
                "primary_artifact",
                "source_reference_count",
                "checked_file_count",
                "matched_file_count",
                "missing_file_count",
                "missing_files",
                "recommended_use",
                "claim_supported",
                "boundary",
                "status",
            ],
        ),
        "video_csv": write_csv(
            out_dir / "tables" / "supplementary_video_routing.csv",
            report["videos"],
            [
                "video_id",
                "scene",
                "view",
                "algorithm",
                "benchmark",
                "num_agents",
                "seed",
                "gif_path",
                "size_mb",
                "submission_role",
                "caption",
                "claim_boundary",
                "status",
            ],
        ),
        "claim_crosswalk_csv": write_csv(
            out_dir / "tables" / "supplementary_claim_source_crosswalk.csv",
            report["claims"],
            ["claim_id", "claim_cn", "recommended_location", "primary_source", "secondary_source", "boundary", "status"],
        ),
        "issues_csv": write_csv(
            out_dir / "tables" / "supplementary_submission_index_issues.csv",
            report["issues"],
            ["item_type", "item_id", "severity", "issue", "details"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
        "inputs": {
            "navigator_qa": NAVIGATOR_QA,
            "supplement_index": SUPPLEMENT_INDEX,
            "figure_table_plan": FIGURE_TABLE_PLAN,
            "source_crosswalk": SOURCE_CROSSWALK,
            "upload_slots": UPLOAD_SLOTS,
            "video_index": VIDEO_INDEX,
            "numbering_manifest": NUMBERING_MANIFEST,
        },
        "boundary": report["boundary"],
    }
    manifest_path = write_json(out_dir / "tits_supplementary_submission_index_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
