#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


SELF_REFERENTIAL_DASHBOARD_IDS = {
    "E4d_reviewer_evidence_trace",
    "E4g_reporting_supplement_navigator",
    "E4h_reviewer_replication_route",
    "E4i_manuscript_supplement_assembly",
    "E8b_author_upload_gap_closure",
}

ACCEPTED_AUTHOR_BLOCKERS = {
    "AF1_target_journal_template",
    "AF2_external_archive_doi",
    "AF3_author_identity_orcid",
    "AF4_credit_contributions",
    "AF5_disclosures_funding_ethics",
    "AF8_claim_and_boundary_final_pass",
    "AF9_final_checksum_freeze",
    "AF10_cover_letter_and_portal_copy",
}

ACCEPTED_AUTHOR_SELECTION_PATHS = {
    "tables/",
    "materials/",
    "evaluations/",
    "baselines/",
    "materials/scripts/",
    "materials/dlc/",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verification_status_excluding_local_author_gate(verification):
    blocking_gates = [
        gate
        for gate in verification["gates"]
        if gate["id"] != "local_author_readiness_separation_pass"
        and gate["status"] != "pass"
    ]
    return "pass" if not blocking_gates else "fail", blocking_gates


def cross_status_excluding_verification_driven_rows(cross):
    blocking_rows = []
    for item in cross.get("rows", []):
        if item.get("status") == "pass":
            continue
        check_id = item.get("check_id", "")
        location = item.get("location", "")
        if check_id == "CM_authoritative_package_gates":
            continue
        if "publication_verification" in check_id:
            continue
        if "publication_package_verification" in check_id:
            continue
        if "publication_verification_status" in location:
            continue
        if (
            check_id == "CM_text_publication_smoke_status"
            and item.get("file") == "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.md"
        ):
            continue
        if "statistical_consistency_status" in check_id:
            continue
        if "statistical_consistency_status" in location:
            continue
        blocking_rows.append(item)
    return "pass" if not blocking_rows else "fail", blocking_rows


def smoke_status_excluding_self_referential_checks(smoke):
    excluded = {
        "SM4_publication_verification_pass",
        "SM6b_cross_material_consistency_pass",
        "SM5_statistical_consistency_pass",
        "SM6c_statistical_analysis_plan_audit_pass",
        "SM6f_local_author_readiness_separation_pass",
        "SM6h_stale_snapshot_boundary_pass",
        "SM7_reviewer_trace_pass",
        "SM10_checksum_freeze_ready",
        "SM12_no_stale_status_snapshots",
    }
    blocking = [
        item
        for item in smoke.get("checks", [])
        if item.get("status") != "pass" and item.get("check_id") not in excluded
    ]
    return "pass" if not blocking else "fail", blocking


def row(check_id, category, status, expected, observed, evidence, interpretation):
    return {
        "check_id": check_id,
        "category": category,
        "status": status,
        "expected": expected,
        "observed": observed,
        "evidence": evidence,
        "interpretation": interpretation,
    }


def build_report(root):
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    upload = load_json(root / "materials" / "SUBMISSION_UPLOAD_SELECTION_PLAN.json")
    navigator = load_json(root / "materials" / "REPORTING_SUPPLEMENT_NAVIGATOR.json")
    assembly = load_json(root / "materials" / "MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.json")
    blockers = load_json(root / "materials" / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json")
    freeze_plan = load_json(root / "materials" / "AUTHOR_ACTION_FREEZE_PLAN.json")
    author_owned = load_json(root / "materials" / "AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    cross = load_json(root / "materials" / "CROSS_MATERIAL_CONSISTENCY_AUDIT.json")
    narrative = load_json(root / "materials" / "NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.json")
    freeze = load_json(root / "materials" / "FINAL_CHECKSUM_FREEZE_RECORD.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")

    checks = []

    core_dashboard_review = [
        item
        for item in dashboard["dashboard_rows"]
        if item["status"] == "review_required" and item["id"] not in SELF_REFERENTIAL_DASHBOARD_IDS
    ]
    checks.append(
        row(
            "LA01_no_core_dashboard_review_required",
            "local_package_readiness",
            "pass" if not core_dashboard_review else "fail",
            "zero core dashboard review_required rows outside self-referential navigation rows",
            len(core_dashboard_review),
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "Remaining dashboard review-required rows should be navigation/self-reference or journal-author workflow, not local evidence defects.",
        )
    )

    verification_core_status, verification_core_failures = verification_status_excluding_local_author_gate(verification)
    cross_core_status, cross_core_failures = cross_status_excluding_verification_driven_rows(cross)
    smoke_core_status, smoke_core_failures = smoke_status_excluding_self_referential_checks(smoke)
    core_gate_failures = {
        "publication_verification_excluding_local_author_gate": verification_core_status,
        "publication_verification_self_referential_gate": verification["summary"]["status"],
        "publication_verification_blocking_gates": [gate["id"] for gate in verification_core_failures],
        "publication_smoke_test": smoke["summary"]["status"],
        "publication_smoke_test_excluding_self_referential_checks": smoke_core_status,
        "publication_smoke_test_blocking_checks": [item["check_id"] for item in smoke_core_failures],
        "cross_material_consistency_excluding_verification_driven_rows": cross_core_status,
        "cross_material_consistency_self_referential_status": cross["summary"]["status"],
        "cross_material_consistency_blocking_rows": [
            {
                "check_id": item.get("check_id"),
                "file": item.get("file"),
                "location": item.get("location"),
                "observed": item.get("observed"),
            }
            for item in cross_core_failures[:20]
        ],
        "narrative_numeric_consistency": narrative["summary"]["status"],
        "checksum_freeze": freeze["summary"]["status"],
        "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
    }
    checks.append(
        row(
            "LA02_core_local_gates_pass",
            "local_package_readiness",
            "pass"
            if verification_core_status == "pass"
            and smoke_core_status == "pass"
            and cross_core_status == "pass"
            and narrative["summary"]["status"] == "pass"
            and freeze["summary"]["status"] == "ready_for_author_freeze"
            and provenance["complete_count"] == len(provenance["artifacts"])
            else "fail",
            "verification gates excluding the local-author self-reference pass; cross-material rows excluding verification-driven self-reference pass; smoke/narrative pass; freeze ready; provenance complete",
            core_gate_failures,
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json; materials/PUBLICATION_SMOKE_TEST.json; materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
            "Core package gates must be clean before treating remaining work as author-owned; publication-verification and cross-material rows that consume this audit are excluded to avoid circular failures.",
        )
    )

    missing_required = bundle["summary"]["missing_required_count"]
    checks.append(
        row(
            "LA03_no_missing_required_bundle_files",
            "local_file_bundle",
            "pass" if missing_required == 0 else "fail",
            "0 missing required files",
            missing_required,
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "The local upload/archive file map should have no missing required files before author selection.",
        )
    )

    author_selection_rows = [item for item in upload["rows"] if item.get("author_selection_required")]
    unexpected_selection = [
        item
        for item in author_selection_rows
        if item["path"] not in ACCEPTED_AUTHOR_SELECTION_PATHS
    ]
    checks.append(
        row(
            "LA04_author_selection_rows_are_bundle_scope_choices",
            "author_selection_boundary",
            "pass" if not unexpected_selection else "fail",
            sorted(ACCEPTED_AUTHOR_SELECTION_PATHS),
            [item["path"] for item in unexpected_selection],
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "Author-selection rows should be upload-scope choices, not missing local files or hidden evidence gaps.",
        )
    )

    blocker_rows = [item for item in blockers["rows"] if item["status"] == "author_required"]
    blocker_ids = {item["id"] for item in blocker_rows}
    unexpected_blockers = sorted(blocker_ids - ACCEPTED_AUTHOR_BLOCKERS)
    missing_blockers = sorted(ACCEPTED_AUTHOR_BLOCKERS - blocker_ids)
    checks.append(
        row(
            "LA05_author_blockers_are_expected",
            "author_action_boundary",
            "pass" if not unexpected_blockers and not missing_blockers else "fail",
            sorted(ACCEPTED_AUTHOR_BLOCKERS),
            {"unexpected": unexpected_blockers, "missing": missing_blockers},
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
            "Upload blockers should be explicit author/target-journal/archive actions, not unresolved local analyses.",
        )
    )

    local_blockers = [item for item in blocker_rows if item.get("can_be_completed_locally") and item["id"] not in {"AF8_claim_and_boundary_final_pass", "AF9_final_checksum_freeze"}]
    checks.append(
        row(
            "LA06_no_unclassified_local_blockers",
            "author_action_boundary",
            "pass" if not local_blockers else "fail",
            "no local-completable blockers except final claim-QA/freeze after author edits",
            [item["id"] for item in local_blockers],
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
            "Locally completable blockers should only be final reruns that depend on author-edited text or final file changes.",
        )
    )

    freeze_blocker_ids = {item["id"] for item in freeze_plan["rows"] if item["blocker_if_missing"]}
    checks.append(
        row(
            "LA07_freeze_plan_matches_author_blockers",
            "author_action_boundary",
            "pass" if freeze_blocker_ids == blocker_ids else "fail",
            sorted(blocker_ids),
            sorted(freeze_blocker_ids),
            "materials/AUTHOR_ACTION_FREEZE_PLAN.json; materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
            "The freeze plan and remaining blocker matrix should identify the same hard upload blockers.",
        )
    )

    allowed_navigator_review = {
        "reviewer_evidence_trace",
        "reviewer_replication_route",
        "supplementary_materials_index",
    }
    navigator_review = {item["item"] for item in navigator["rows"] if item["status"] == "review_required"}
    checks.append(
        row(
            "LA08_navigator_review_rows_are_workflow_or_supplement_style",
            "review_required_boundary",
            "pass" if navigator_review.issubset(allowed_navigator_review) else "fail",
            sorted(allowed_navigator_review),
            sorted(navigator_review),
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
            "Navigator review rows should reflect optional reviewer rerun workflow or supplement style adaptation, not missing evidence.",
        )
    )

    allowed_assembly_review = {"required_supplement_tables", "package_gates", "reviewer_navigation"}
    assembly_review = {
        item["manuscript_location"]
        for item in assembly["rows"]
        if item["status"] == "review_required"
    }
    checks.append(
        row(
            "LA09_assembly_review_rows_are_supplement_style",
            "review_required_boundary",
            "pass" if assembly_review.issubset(allowed_assembly_review) else "fail",
            sorted(allowed_assembly_review),
            sorted(assembly_review),
            "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.json",
            "Manuscript/supplement assembly review rows should be journal numbering/style or final gate-rerun workflow tasks, not missing result files.",
        )
    )

    checks.append(
        row(
            "LA10_author_owned_integrity_is_enforced",
            "author_action_boundary",
            "pass"
            if author_owned["summary"]["status"] == "pass"
            and author_owned["summary"]["failed_checks"] == 0
            and author_owned["summary"]["external_identifier_pending"]
            else "fail",
            "author-owned integrity pass with external identifier pending",
            author_owned["summary"],
            "materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json",
            "Author-certified metadata and archive identifiers should remain visible and unfilled until authors complete them.",
        )
    )

    failed = [item for item in checks if item["status"] != "pass"]
    author_owned_rows = [item for item in blockers["rows"] if item["status"] == "author_required"]
    local_ready_rows = [item for item in dashboard["dashboard_rows"] if item["status"] in {"pass", "ready"}]
    return {
        "root": str(root),
        "title": "Local-vs-author readiness separation audit",
        "purpose": (
            "Separate local evidence-package completeness from author-owned, target-journal, and external-archive "
            "tasks so top-journal preflight does not confuse legitimate author-required work with local package defects."
        ),
        "checks": checks,
        "summary": {
            "status": "pass" if not failed else "fail",
            "check_count": len(checks),
            "failed_checks": len(failed),
            "core_dashboard_review_required": len(core_dashboard_review),
            "author_required_blockers": len(author_owned_rows),
            "author_selection_rows": len(author_selection_rows),
            "local_ready_or_pass_dashboard_rows": len(local_ready_rows),
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "external_identifier_pending": author_owned["summary"]["external_identifier_pending"],
        },
        "interpretation": (
            "A pass means the local package is internally ready for author review/freeze, while journal choice, "
            "official template conversion, certified author metadata, funding/conflict declarations, and public archive "
            "DOI/accession remain author-owned tasks. It is not a claim that submission upload is complete."
        ),
    }


def write_csv(report, path):
    fields = ["check_id", "category", "status", "expected", "observed", "evidence", "interpretation"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["checks"])


def write_markdown(report, path):
    lines = [
        "# Local-vs-author Readiness Separation Audit",
        "",
        report["purpose"],
        "",
        report["interpretation"],
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
            "| check_id | category | status | expected | observed | evidence | interpretation |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["checks"]:
        lines.append(
            f"| {item['check_id']} | {item['category']} | {item['status']} | "
            f"{item['expected']} | {item['observed']} | `{item['evidence']}` | {item['interpretation']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export local-vs-author readiness separation audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json"
    out_md = materials / "LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.md"
    out_csv = materials / "LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
