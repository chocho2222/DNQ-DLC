#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


AUTHOR_CLOSURE = "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tits_author_submission_closure_pack_manifest.json"
SUBMISSION_METADATA = "outputs/tits_dynamic_graph/tits_submission_metadata_pack/tits_submission_metadata_pack_manifest.json"
GITHUB_RELEASE = "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tits_github_release_readiness_pack_manifest.json"
PUBLIC_RELEASE = "outputs/tits_dynamic_graph/public_release_plan/public_release_plan_manifest.json"
FAIR_ARCHIVE = "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tits_fair_archive_metadata_pack_manifest.json"
SUBMISSION_CHECKLIST = "outputs/tits_dynamic_graph/tits_submission_metadata_pack/tables/submission_portal_checklist.csv"
GITHUB_AUTHOR_ACTIONS = "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tables/github_release_author_actions.csv"
AUTHOR_ACTIONS = "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tables/author_owned_action_matrix.csv"
PLACEHOLDER_INVENTORY = "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tables/author_placeholder_inventory.csv"
EVIDENCE_CHECKS = "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tables/author_action_evidence_checks.csv"

AUTHOR_ACTION_CATEGORIES = {
    "data_archive",
    "code_release",
    "license",
    "ieee_template",
    "author_metadata",
    "funding_conflict_ethics",
    "portal_metadata",
    "supplement_selection",
    "final_freeze",
}

AUTHOR_REQUIRED_STATUSES = {
    "author_action_required",
    "author_finalization_required",
    "author_archive_required",
    "author_format_required",
    "data_archive_required",
}

COMPLETION_MARKERS = {
    "complete",
    "completed",
    "certified",
    "author_certified",
    "submitted",
    "uploaded",
    "doi_obtained",
    "release_created",
    "ready_without_author_action",
}

SENSITIVE_TERMS = (
    "DOI",
    "accession",
    "repository",
    "release tag",
    "license",
    "IEEE",
    "ORCID",
    "funding",
    "conflict",
    "AI disclosure",
    "ScholarOne",
    "corresponding author",
)


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


def check_row(check_id, category, status, expected, observed, evidence, note):
    return {
        "check_id": check_id,
        "category": category,
        "status": status,
        "expected": expected,
        "observed": observed,
        "evidence": evidence,
        "note": note,
    }


def status_is_author_owned(status):
    return status in AUTHOR_REQUIRED_STATUSES or status.startswith("author_")


def contains_completion_marker(value):
    lowered = str(value).strip().lower()
    return lowered in COMPLETION_MARKERS


def build_report(root):
    author_closure = read_json(root / AUTHOR_CLOSURE)
    submission_metadata = read_json(root / SUBMISSION_METADATA)
    github_release = read_json(root / GITHUB_RELEASE)
    public_release = read_json(root / PUBLIC_RELEASE)
    fair_archive = read_json(root / FAIR_ARCHIVE)
    submission_rows = read_csv(root / SUBMISSION_CHECKLIST)
    github_rows = read_csv(root / GITHUB_AUTHOR_ACTIONS)
    action_rows = read_csv(root / AUTHOR_ACTIONS)
    placeholder_rows = read_csv(root / PLACEHOLDER_INVENTORY)
    evidence_rows = read_csv(root / EVIDENCE_CHECKS)

    rows = []

    missing_inputs = [
        rel
        for rel in [
            AUTHOR_CLOSURE,
            SUBMISSION_METADATA,
            GITHUB_RELEASE,
            PUBLIC_RELEASE,
            FAIR_ARCHIVE,
            SUBMISSION_CHECKLIST,
            GITHUB_AUTHOR_ACTIONS,
            AUTHOR_ACTIONS,
            PLACEHOLDER_INVENTORY,
            EVIDENCE_CHECKS,
        ]
        if not (root / rel).exists()
    ]
    rows.append(
        check_row(
            "AO_inputs_exist",
            "input_presence",
            "pass" if not missing_inputs else "fail",
            "all author-facing manifests and tables exist",
            missing_inputs if missing_inputs else "all present",
            "; ".join([AUTHOR_CLOSURE, SUBMISSION_METADATA, GITHUB_RELEASE, PUBLIC_RELEASE, FAIR_ARCHIVE]),
            "The integrity audit depends on the author closure pack, metadata pack, release pack, FAIR metadata pack and their author-action tables.",
        )
    )

    categories = {row.get("category", "") for row in action_rows}
    missing_categories = sorted(AUTHOR_ACTION_CATEGORIES - categories)
    rows.append(
        check_row(
            "AO_author_action_categories_complete",
            "author_action_coverage",
            "pass" if not missing_categories else "fail",
            sorted(AUTHOR_ACTION_CATEGORIES),
            missing_categories if missing_categories else "all categories present",
            AUTHOR_ACTIONS,
            "DOI/archive, repository, license, IEEE template, author metadata, declarations, portal fields, supplements and final checksum freeze must remain visible.",
        )
    )

    wrong_action_status = [
        {"action_id": row.get("action_id"), "category": row.get("category"), "status": row.get("status")}
        for row in action_rows
        if row.get("status") != "author_action_required"
    ]
    rows.append(
        check_row(
            "AO_author_actions_not_auto_completed",
            "author_action_status",
            "pass" if not wrong_action_status else "fail",
            "author_action_required for every closure action",
            wrong_action_status if wrong_action_status else "all author_action_required",
            AUTHOR_ACTIONS,
            "Local automation must not mark author-owned submission tasks as completed.",
        )
    )

    sensitive_submission = [
        row
        for row in submission_rows
        if any(term.lower() in (row.get("item", "") + " " + row.get("author_action", "")).lower() for term in ["ai", "data/code", "final pdf", "cover letter"])
    ]
    wrong_submission = [
        {"item": row.get("item"), "local_status": row.get("local_status")}
        for row in sensitive_submission
        if row.get("local_status") not in {"draft_ready"} and not status_is_author_owned(row.get("local_status", ""))
    ]
    rows.append(
        check_row(
            "AO_submission_sensitive_fields_author_bounded",
            "submission_metadata",
            "pass" if not wrong_submission else "fail",
            "draft_ready or author_* status for sensitive portal fields",
            wrong_submission if wrong_submission else "sensitive fields bounded",
            SUBMISSION_CHECKLIST,
            "AI disclosure, data/code availability, final PDF/template and cover-letter declarations require author confirmation.",
        )
    )

    github_author_rows = [
        row
        for row in github_rows
        if row.get("item") in {"release tag", "large artifacts"} or "author" in row.get("status", "")
    ]
    wrong_github = [
        {"item": row.get("item"), "status": row.get("status")}
        for row in github_author_rows
        if row.get("status") not in AUTHOR_REQUIRED_STATUSES
    ]
    rows.append(
        check_row(
            "AO_github_release_author_actions_visible",
            "github_release",
            "pass" if not wrong_github and len(github_author_rows) >= 2 else "fail",
            "release tag and large artifacts remain author/archive actions",
            wrong_github if wrong_github else f"{len(github_author_rows)} author/archive rows",
            GITHUB_AUTHOR_ACTIONS,
            "The public repository/release tag and large artifact routing cannot be certified by local files alone.",
        )
    )

    placeholder_count = len([row for row in placeholder_rows if row.get("status") == "author_fill_required"])
    missing_scan_count = len([row for row in placeholder_rows if row.get("status") == "missing_scan_file"])
    rows.append(
        check_row(
            "AO_placeholders_remain_explicit",
            "placeholder_inventory",
            "pass" if placeholder_count >= 5 and missing_scan_count == 0 else "fail",
            "visible author-fill placeholders and no missing scan files",
            {"author_fill_required": placeholder_count, "missing_scan_file": missing_scan_count},
            PLACEHOLDER_INVENTORY,
            "Author-owned placeholders should remain discoverable until real DOI, URL, author, license and disclosure text exists.",
        )
    )

    missing_evidence = [row for row in evidence_rows if str(row.get("exists", "")).lower() not in {"true", "1", "yes"}]
    rows.append(
        check_row(
            "AO_author_action_local_evidence_exists",
            "local_evidence",
            "pass" if not missing_evidence else "fail",
            "all local evidence paths for author actions exist",
            len(missing_evidence),
            EVIDENCE_CHECKS,
            "Author actions can remain open, but each action should point to concrete local evidence or drafts.",
        )
    )

    release_summary = public_release.get("summary", {})
    fair_summary = fair_archive.get("summary", {})
    release_url_text = json.dumps(public_release, ensure_ascii=False)
    fair_text = json.dumps(fair_archive, ensure_ascii=False)
    fabricated_identifier = bool(
        re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", release_url_text + fair_text)
        or re.search(r"https?://(?:zenodo|osf|figshare|github)\.[^\s\"']+", release_url_text + fair_text)
    )
    rows.append(
        check_row(
            "AO_no_fabricated_public_identifier",
            "external_identifier",
            "pass" if not fabricated_identifier else "fail",
            "no real-looking DOI/archive/repository URL before deposition",
            "none detected" if not fabricated_identifier else "real-looking DOI or URL detected",
            f"{PUBLIC_RELEASE}; {FAIR_ARCHIVE}",
            "The package may contain URL/DOI placeholders, but should not invent public identifiers before author deposition.",
        )
    )

    author_finalization_required = submission_metadata.get("summary", {}).get("author_finalization_required")
    rows.append(
        check_row(
            "AO_submission_manifest_declares_author_finalization",
            "submission_metadata",
            "pass" if author_finalization_required is True else "fail",
            "author_finalization_required true",
            author_finalization_required,
            SUBMISSION_METADATA,
            "The submission metadata pack should state that final author-side confirmation is still required.",
        )
    )

    closure_summary = author_closure.get("summary", {})
    rows.append(
        check_row(
            "AO_closure_pack_has_expected_author_actions",
            "author_closure_pack",
            "pass" if closure_summary.get("author_action_count") == len(AUTHOR_ACTION_CATEGORIES) else "fail",
            len(AUTHOR_ACTION_CATEGORIES),
            closure_summary.get("author_action_count"),
            AUTHOR_CLOSURE,
            "The closure pack should carry one explicit action for each author-owned category.",
        )
    )

    false_completion = []
    for table_name, table_rows, status_column in [
        ("submission_portal_checklist", submission_rows, "local_status"),
        ("github_release_author_actions", github_rows, "status"),
        ("author_owned_action_matrix", action_rows, "status"),
    ]:
        for index, row in enumerate(table_rows, start=2):
            if contains_completion_marker(row.get(status_column, "")):
                false_completion.append(
                    {
                        "table": table_name,
                        "row": index,
                        "status": row.get(status_column, ""),
                        "item": row.get("item") or row.get("action_id"),
                    }
                )
    rows.append(
        check_row(
            "AO_no_false_completion_markers",
            "false_completion_guard",
            "pass" if not false_completion else "fail",
            "no completion/certification markers in author-owned status fields",
            false_completion if false_completion else "none",
            f"{SUBMISSION_CHECKLIST}; {GITHUB_AUTHOR_ACTIONS}; {AUTHOR_ACTIONS}",
            "This prevents a local PASS dashboard from being confused with actual ScholarOne submission, DOI deposition, release creation or legal certification.",
        )
    )

    sensitive_coverage = {}
    text_blob = json.dumps(action_rows + submission_rows + github_rows + placeholder_rows, ensure_ascii=False)
    for term in SENSITIVE_TERMS:
        sensitive_coverage[term] = term.lower() in text_blob.lower()
    missing_sensitive_terms = [term for term, present in sensitive_coverage.items() if not present]
    rows.append(
        check_row(
            "AO_sensitive_author_terms_covered",
            "author_action_coverage",
            "pass" if not missing_sensitive_terms else "fail",
            list(SENSITIVE_TERMS),
            missing_sensitive_terms if missing_sensitive_terms else "all covered",
            f"{AUTHOR_ACTIONS}; {SUBMISSION_CHECKLIST}; {GITHUB_AUTHOR_ACTIONS}; {PLACEHOLDER_INVENTORY}",
            "The author-facing materials should explicitly name sensitive submission tasks that cannot be automated locally.",
        )
    )

    failed = [row for row in rows if row["status"] != "pass"]
    summary = {
        "status": "pass" if not failed else "fail",
        "check_count": len(rows),
        "failed_checks": len(failed),
        "author_action_count": len(action_rows),
        "author_action_category_count": len(categories),
        "placeholder_count": placeholder_count,
        "missing_evidence_count": len(missing_evidence),
        "submission_author_finalization_required": author_finalization_required,
        "public_release_status": public_release.get("status"),
        "public_release_review_required_files": release_summary.get("review_required_file_count"),
        "fair_status": fair_archive.get("status"),
        "fair_artifact_files": fair_summary.get("artifact_files"),
        "boundary": "Pass means author-owned submission tasks remain explicit and locally bounded; it does not mean DOI, repository release, license, ORCID, funding/conflict statements, IEEE template conversion, or ScholarOne submission are completed.",
    }
    return {
        "status": summary["status"],
        "title": "T-ITS Author-Owned Submission Integrity Audit",
        "purpose": "Check that local automation keeps DOI, repository/release, license, author metadata, declarations, IEEE template conversion, portal fields, supplementary upload choices and final checksum freeze visibly author-owned.",
        "summary": summary,
        "rows": rows,
    }


def build_markdown(report):
    lines = [
        "# T-ITS Author-Owned Submission Integrity Audit",
        "",
        report["purpose"],
        "",
        "该审计的角色是“防误读”：它要求作者侧事项继续以 `author_action_required`、`author_finalization_required`、`author_archive_required` 或类似状态出现，而不是被本地自动流程标成真实完成。",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| check_id | category | status | expected | observed | evidence | note |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['check_id']} | {row['category']} | {row['status']} | {row['expected']} | {row['observed']} | `{row['evidence']}` | {row['note']} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "PASS 不代表作者已经完成 DOI/URL、license、ORCID、基金/冲突声明、IEEE 模板排版或 ScholarOne 提交；PASS 只代表这些事项没有被本地证据链错误地自动声明为完成。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_author_owned_submission_integrity_audit.py --out-dir outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export T-ITS author-owned submission integrity audit.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    report = build_report(root)
    paths = {
        "report_md": write_text(materials / "AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.md", build_markdown(report)),
        "report_json": write_json(materials / "AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json", report),
        "check_rows_csv": write_csv(
            tables / "author_owned_submission_integrity_checks.csv",
            report["rows"],
            ["check_id", "category", "status", "expected", "observed", "evidence", "note"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_author_owned_submission_integrity_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
