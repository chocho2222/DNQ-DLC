#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


AUTHOR_ACTIONS = "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tables/author_owned_action_matrix.csv"
AUTHOR_PLACEHOLDERS = "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tables/author_placeholder_inventory.csv"
AUTHOR_EVIDENCE = "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tables/author_action_evidence_checks.csv"
DRY_RUN = "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/tables/submission_dry_run_checklist.csv"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
AUTHOR_CLOSURE = "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tits_author_submission_closure_pack_manifest.json"
SUBMISSION_DRY_RUN = "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/tits_submission_dry_run_checklist_manifest.json"
UPLOAD_BUNDLE = "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/tits_submission_upload_bundle_map_manifest.json"
PUBLIC_RELEASE = "outputs/tits_dynamic_graph/public_release_plan/public_release_plan_manifest.json"
FAIR_ARCHIVE = "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tits_fair_archive_metadata_pack_manifest.json"


P0_CATEGORIES = {
    "data_archive",
    "code_release",
    "license",
    "ieee_template",
    "author_metadata",
    "funding_conflict_ethics",
    "final_freeze",
    "scope_and_article_type",
    "main_text",
    "source_data",
    "reproducibility_packet",
    "claim_boundary",
    "container_boundary",
}

P1_CATEGORIES = {
    "portal_metadata",
    "supplement_selection",
    "figures",
    "title_abstract_keywords",
    "supplementary_information",
    "visual_supplement",
    "code_repository",
    "data_archive",
    "author_declarations",
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


def priority_for(category, blocking_if_missing="yes"):
    if category in P0_CATEGORIES:
        return "P0_blocking"
    if category in P1_CATEGORIES or blocking_if_missing == "optional":
        return "P1_submission_quality"
    if blocking_if_missing == "yes":
        return "P1_submission_quality"
    return "P2_after_acceptance_or_optional"


def priority_rank(priority):
    return {"P0_blocking": 0, "P1_submission_quality": 1, "P2_after_acceptance_or_optional": 2}.get(priority, 3)


def action_gap_rows(root, action_rows, evidence_rows):
    missing_by_action = {}
    for row in evidence_rows:
        if str(row.get("exists", "")).lower() != "true":
            missing_by_action.setdefault(row.get("action_id", ""), []).append(row.get("evidence_path", ""))
    rows = []
    for item in action_rows:
        category = item.get("category", "")
        priority = priority_for(category)
        missing = missing_by_action.get(item.get("action_id", ""), [])
        rows.append(
            {
                "item_id": item.get("action_id", ""),
                "source": "author_closure",
                "priority": priority,
                "category": category,
                "action": item.get("author_action", ""),
                "why_now": item.get("why_required", ""),
                "local_evidence_status": item.get("local_evidence_ready", ""),
                "missing_evidence_count": len(missing),
                "missing_evidence": "; ".join(missing),
                "completion_evidence": item.get("completion_evidence", ""),
                "rerun_route": item.get("after_completion_rerun", ""),
                "blocking_scope": "blocks_public_submission_or_release",
                "evidence": item.get("local_evidence_paths", ""),
                "status": "author_action_required" if not missing else "local_evidence_review_required",
            }
        )
    return rows


def dry_run_gap_rows(root, dry_rows):
    rows = []
    for item in dry_rows:
        category = item.get("phase", "")
        priority = priority_for(category, item.get("blocking_if_missing", ""))
        missing_count = int(item.get("missing_evidence_count") or 0)
        rows.append(
            {
                "item_id": item.get("step_id", ""),
                "source": "submission_dry_run",
                "priority": priority,
                "category": category,
                "action": item.get("author_action", ""),
                "why_now": item.get("item", ""),
                "local_evidence_status": item.get("local_status", ""),
                "missing_evidence_count": missing_count,
                "missing_evidence": item.get("missing_evidence", ""),
                "completion_evidence": item.get("portal_or_upload_target", ""),
                "rerun_route": "make tits-refresh-gates after final author edits",
                "blocking_scope": "blocks_submission_package" if item.get("blocking_if_missing") == "yes" else "improves_submission_quality",
                "evidence": item.get("local_evidence", ""),
                "status": "author_action_required" if missing_count == 0 else "local_evidence_review_required",
            }
        )
    return rows


def add_order(rows):
    rows = sorted(rows, key=lambda row: (priority_rank(row["priority"]), row["source"], row["item_id"]))
    for idx, row in enumerate(rows, start=1):
        row["priority_order"] = idx
    return rows


def build_report(root):
    input_paths = [
        AUTHOR_ACTIONS,
        AUTHOR_PLACEHOLDERS,
        AUTHOR_EVIDENCE,
        DRY_RUN,
        FINAL_READINESS,
        AUTHOR_CLOSURE,
        SUBMISSION_DRY_RUN,
        UPLOAD_BUNDLE,
        PUBLIC_RELEASE,
        FAIR_ARCHIVE,
    ]
    missing_inputs = [rel for rel in input_paths if not (root / rel).exists()]
    author_rows = read_csv(root / AUTHOR_ACTIONS)
    placeholder_rows = read_csv(root / AUTHOR_PLACEHOLDERS)
    evidence_rows = read_csv(root / AUTHOR_EVIDENCE)
    dry_rows = read_csv(root / DRY_RUN)
    rows = add_order(action_gap_rows(root, author_rows, evidence_rows) + dry_run_gap_rows(root, dry_rows))
    local_evidence_issues = [row for row in rows if row["missing_evidence_count"]]
    p0_rows = [row for row in rows if row["priority"] == "P0_blocking"]
    p1_rows = [row for row in rows if row["priority"] == "P1_submission_quality"]
    final = read_json(root / FINAL_READINESS)
    author = read_json(root / AUTHOR_CLOSURE)
    dry = read_json(root / SUBMISSION_DRY_RUN)
    upload = read_json(root / UPLOAD_BUNDLE)
    public = read_json(root / PUBLIC_RELEASE)
    fair = read_json(root / FAIR_ARCHIVE)
    summary = {
        "status": "pass" if not missing_inputs and not local_evidence_issues else "review_required",
        "gap_item_count": len(rows),
        "p0_blocking_count": len(p0_rows),
        "p1_submission_quality_count": len(p1_rows),
        "p2_optional_count": len(rows) - len(p0_rows) - len(p1_rows),
        "author_placeholder_count": len(placeholder_rows),
        "missing_input_count": len(missing_inputs),
        "local_evidence_issue_count": len(local_evidence_issues),
        "final_readiness": f"{final.get('pass_count', 'NA')}/{final.get('gate_count', 'NA')}",
        "author_closure_status": author.get("status", ""),
        "submission_dry_run_status": dry.get("status", ""),
        "upload_bundle_status": upload.get("status", ""),
        "public_release_status": public.get("status", ""),
        "fair_archive_status": fair.get("status", ""),
        "author_action_boundary": "All listed gaps are author/platform actions; local PASS means the gaps are explicit, prioritized, and backed by local evidence routes.",
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "priority_rows": rows,
        "missing_inputs": missing_inputs,
        "local_evidence_issues": local_evidence_issues,
    }


def build_markdown(report):
    summary = report["summary"]
    rows = report["priority_rows"]
    lines = [
        "# T-ITS Submission Gap Priority Audit",
        "",
        "该审计把顶刊投稿前仍需作者或投稿平台完成的事项合并成优先级队列。它不把 DOI、license、作者信息、IEEE 模板或 ScholarOne 上传误判为已完成；PASS 仅表示这些缺口已经被显式排序、可由本地证据支撑，并且给出了完成后需要重跑的路线。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Priority Queue",
            "",
            "| Order | Priority | ID | Category | Action | Local evidence | Missing | Completion evidence | Rerun route |",
            "|---:|---|---|---|---|---|---:|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['priority_order']} | {row['priority']} | {row['item_id']} | {row['category']} | "
            f"{row['action']} | {row['local_evidence_status']} | {row['missing_evidence_count']} | "
            f"{row['completion_evidence']} | {row['rerun_route']} |"
        )
    lines.extend(
        [
            "",
            "## Recommended Author Execution Order",
            "",
            "1. 完成公开代码仓库/release tag、数据归档 DOI/accession 和 license 确认。",
            "2. 将 evidence-driven Markdown 草稿转换为当前 IEEE T-ITS 模板，并锁定图号、表号和补充材料编号。",
            "3. 填写作者、ORCID、基金、利益冲突、伦理/安全边界和 AI-tool disclosure。",
            "4. 选择最终上传的 source data、补充表、GIF/视频和复现包。",
            "5. 替换所有 DOI/URL/license/author 占位符后运行 `make tits-refresh-gates`，再冻结 checksum。",
            "",
            "## Boundary",
            "",
            "- P0/P1/P2 是投稿操作优先级，不是算法风险或实验失败等级。",
            "- 本审计不替代通讯作者确认、法律/license 审查、IEEE 模板实时要求或 ScholarOne 上传回执。",
            "- 修改 author closure、submission dry run、release plan、FAIR metadata 或 final dashboard 后需要重新运行本审计。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_submission_gap_priority_audit.py --out-dir outputs/tits_dynamic_graph/tits_submission_gap_priority_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export a prioritized T-ITS submission-gap audit.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_submission_gap_priority_audit")
    args = parser.parse_args()
    root = Path(".").resolve()
    report = build_report(root)
    out_dir = Path(args.out_dir)
    fields = [
        "priority_order",
        "item_id",
        "source",
        "priority",
        "category",
        "action",
        "why_now",
        "local_evidence_status",
        "missing_evidence_count",
        "missing_evidence",
        "completion_evidence",
        "rerun_route",
        "blocking_scope",
        "evidence",
        "status",
    ]
    paths = {
        "report_md": write_text(out_dir / "materials" / "SUBMISSION_GAP_PRIORITY_AUDIT.md", build_markdown(report)),
        "priority_csv": write_csv(out_dir / "tables" / "submission_gap_priority_queue.csv", report["priority_rows"], fields),
        "gap_json": write_json(out_dir / "materials" / "SUBMISSION_GAP_PRIORITY_AUDIT.json", report),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
        "boundary": "Author/platform submission prioritization only; it does not complete DOI, license, template conversion, legal review, or ScholarOne upload.",
    }
    manifest_path = write_json(out_dir / "tits_submission_gap_priority_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
