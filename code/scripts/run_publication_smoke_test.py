#!/usr/bin/env python
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


STALE_SCAN_DIRS = ["materials", "tables"]
STALE_SKIP_PREFIXES = {
    "FINAL_CHECKSUM_FREEZE_RECORD",
    "PUBLICATION_SMOKE_TEST",
    "CROSS_MATERIAL_CONSISTENCY_AUDIT",
    "CROSS_REPORT_FRESHNESS_AUDIT",
    "STALE_SNAPSHOT_BOUNDARY_AUDIT",
    "SUBMISSION_READINESS_DASHBOARD",
    "FINAL_SUBMISSION_FILE_BUNDLE",
    "SUBMISSION_UPLOAD_SELECTION_PLAN",
    "REVIEWER_EVIDENCE_TRACE_PACK",
    "REPORTING_SUPPLEMENT_NAVIGATOR",
    "REVIEWER_REPLICATION_ROUTE",
    "MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP",
    "SUPPLEMENTARY_TABLE_LEGENDS",
    "STATISTICAL_REPORTING_APPENDIX",
    "CITATION_METADATA",
    "CITATION",
    "STATISTICAL_CONSISTENCY_AUDIT",
    "STATISTICAL_ANALYSIS_PLAN_AUDIT",
    "LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT",
    "PUBLICATION_PACKAGE_VERIFICATION",
}

STALE_SCAN_FILES = {
    "materials/ARCHIVE_README.md",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
    "materials/METHODS_REPRODUCIBILITY_CAPSULE.md",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
    "materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
    "materials/SUBMISSION_READINESS_DASHBOARD.md",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
    "materials/TRANSPARENT_REPORTING_CHECKLIST.md",
    "tables/artifact_provenance.md",
}


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def csv_header(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle))


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def add_check(checks, check_id, description, passed, evidence, observed="", severity="required"):
    checks.append(
        {
            "check_id": check_id,
            "description": description,
            "status": "pass" if passed else "fail",
            "severity": severity,
            "evidence": evidence,
            "observed": observed,
        }
    )


SELF_REFERENTIAL_DASHBOARD_IDS = {
    "P4_publication_smoke_test",
    "E4d_reviewer_evidence_trace",
    "E4g_reporting_supplement_navigator",
    "E4h_reviewer_replication_route",
    "E4i_manuscript_supplement_assembly",
    "E8b_author_upload_gap_closure",
    "E8c_public_archive_journal_upload_dry_run",
}

SELF_REFERENTIAL_TRACE_IDS = {
    f"DASH_{row_id}" for row_id in SELF_REFERENTIAL_DASHBOARD_IDS
}


def scan_stale(root, expected_artifact_count):
    findings = []
    artifact_count_regex = re.compile(r"\b(1[0-9]{2})/\1\b")
    expected = f"{expected_artifact_count}/{expected_artifact_count}"
    for base in STALE_SCAN_DIRS:
        folder = root / base
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            rel_path = path.relative_to(root)
            if rel_path.as_posix() not in STALE_SCAN_FILES:
                continue
            if len(rel_path.parts) >= 2 and rel_path.parts[0] == "materials" and rel_path.parts[1] == "scripts":
                continue
            if not path.is_file() or any(path.name.startswith(prefix) for prefix in STALE_SKIP_PREFIXES):
                continue
            if path.suffix.lower() not in {".md", ".json", ".csv"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in artifact_count_regex.finditer(text):
                if match.group(0) != expected:
                    findings.append({"path": str(path.relative_to(root)), "matched_text": match.group(0)})
                    if len(findings) >= 50:
                        return findings
    return findings


def build_report(root):
    checks = []
    required_json = [
        "manifest.json",
        "tables/artifact_provenance.json",
        "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
        "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.json",
        "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.json",
        "materials/CROSS_REPORT_FRESHNESS_AUDIT.json",
        "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.json",
        "materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json",
        "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json",
        "materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.json",
        "materials/DATA_DICTIONARY.json",
        "materials/SUBMISSION_READINESS_DASHBOARD.json",
        "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
        "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
        "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
        "materials/CLAIM_DECISION_TREE.json",
        "materials/RELEASE_ARCHIVE_MANIFEST.json",
        "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
    ]
    parsed = {}
    missing_json = []
    invalid_json = []
    for rel in required_json:
        path = root / rel
        if not path.exists():
            missing_json.append(rel)
            continue
        try:
            parsed[rel] = load_json(path)
        except Exception as exc:
            invalid_json.append({"path": rel, "error": str(exc)})
    add_check(
        checks,
        "SM1_required_json_parse",
        "Required publication-package JSON files exist and parse.",
        not missing_json and not invalid_json,
        "; ".join(required_json),
        {"missing": missing_json, "invalid": invalid_json},
    )

    required_csv = [
        "materials/DATA_DICTIONARY.csv",
        "materials/REVIEWER_EVIDENCE_TRACE_PACK.csv",
        "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.csv",
        "materials/FINAL_SUBMISSION_FILE_BUNDLE.csv",
        "materials/RELEASE_ARCHIVE_MANIFEST.csv",
        "figures/figure_1_source_data.csv",
        "figures/figure_2_source_data.csv",
        "figures/figure_3_source_data.csv",
    ]
    csv_failures = []
    for rel in required_csv:
        path = root / rel
        if not path.exists():
            csv_failures.append({"path": rel, "error": "missing"})
            continue
        try:
            header = csv_header(path)
            if not header:
                csv_failures.append({"path": rel, "error": "empty_header"})
        except Exception as exc:
            csv_failures.append({"path": rel, "error": str(exc)})
    add_check(
        checks,
        "SM2_required_csv_headers",
        "Required reviewer/source-data CSV files exist and have readable headers.",
        not csv_failures,
        "; ".join(required_csv),
        csv_failures,
    )

    provenance = parsed.get("tables/artifact_provenance.json", {})
    complete = provenance.get("complete_count")
    total = len(provenance.get("artifacts", []))
    add_check(
        checks,
        "SM3_artifact_provenance_complete",
        "Artifact provenance complete count equals total and has no incomplete artifacts.",
        complete == total and not provenance.get("incomplete_artifacts"),
        "tables/artifact_provenance.json",
        f"{complete}/{total}",
    )

    verification = parsed.get("materials/PUBLICATION_PACKAGE_VERIFICATION.json", {})
    add_check(
        checks,
        "SM4_publication_verification_pass",
        "Publication package verification is pass with zero failed gates.",
        verification.get("summary", {}).get("status") == "pass"
        and verification.get("summary", {}).get("failed_gates") == 0,
        "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        verification.get("summary", {}),
    )

    stats = parsed.get("materials/STATISTICAL_CONSISTENCY_AUDIT.json", {})
    add_check(
        checks,
        "SM5_statistical_consistency_pass",
        "Statistical consistency audit is pass with zero failed checks.",
        stats.get("summary", {}).get("status") == "pass"
        and stats.get("summary", {}).get("failed_checks") == 0,
        "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
        stats.get("summary", {}),
    )

    dictionary = parsed.get("materials/DATA_DICTIONARY.json", {})
    add_check(
        checks,
        "SM6_data_dictionary_complete",
        "Data dictionary is complete and has no missing field definitions.",
        dictionary.get("summary", {}).get("complete") is True
        and dictionary.get("summary", {}).get("missing_definition_count") == 0,
        "materials/DATA_DICTIONARY.json",
        dictionary.get("summary", {}),
    )

    cross_material = parsed.get("materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.json", {})
    add_check(
        checks,
        "SM6b_cross_material_consistency_pass",
        "Cross-material consistency audit is pass with zero failed rows.",
        cross_material.get("summary", {}).get("status") == "pass"
        and cross_material.get("summary", {}).get("failed_row_count") == 0,
        "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.json",
        cross_material.get("summary", {}),
    )

    statistical_plan_audit = parsed.get("materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.json", {})
    add_check(
        checks,
        "SM6c_statistical_analysis_plan_audit_pass",
        "Statistical analysis plan audit is pass with zero failed checks.",
        statistical_plan_audit.get("summary", {}).get("status") == "pass"
        and statistical_plan_audit.get("summary", {}).get("failed_checks") == 0,
        "materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.json",
        statistical_plan_audit.get("summary", {}),
    )

    narrative_numeric = parsed.get("materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.json", {})
    add_check(
        checks,
        "SM6d_narrative_numeric_consistency_pass",
        "Narrative numeric consistency audit is pass with zero failed rows.",
        narrative_numeric.get("summary", {}).get("status") == "pass"
        and narrative_numeric.get("summary", {}).get("failed_row_count") == 0,
        "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.json",
        narrative_numeric.get("summary", {}),
    )

    freshness = parsed.get("materials/CROSS_REPORT_FRESHNESS_AUDIT.json", {})
    add_check(
        checks,
        "SM6g_cross_report_freshness_pass",
        "Cross-report freshness audit is pass with zero failed rows.",
        freshness.get("summary", {}).get("status") == "pass"
        and freshness.get("summary", {}).get("failed_row_count") == 0,
        "materials/CROSS_REPORT_FRESHNESS_AUDIT.json",
        freshness.get("summary", {}),
    )

    stale_boundary = parsed.get("materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.json", {})
    add_check(
        checks,
        "SM6h_stale_snapshot_boundary_pass",
        "Stale snapshot boundary audit is pass with zero blocking core-entry stale snapshots.",
        stale_boundary.get("summary", {}).get("status") == "pass"
        and stale_boundary.get("summary", {}).get("blocking_core_count") == 0,
        "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.json",
        stale_boundary.get("summary", {}),
    )

    author_owned = parsed.get("materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json", {})
    add_check(
        checks,
        "SM6e_author_owned_submission_integrity_pass",
        "Author-owned submission integrity audit is pass with zero failed checks.",
        author_owned.get("summary", {}).get("status") == "pass"
        and author_owned.get("summary", {}).get("failed_checks") == 0,
        "materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json",
        author_owned.get("summary", {}),
    )

    local_author = parsed.get("materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json", {})
    add_check(
        checks,
        "SM6f_local_author_readiness_separation_pass",
        "Local-vs-author readiness separation audit is pass with zero failed checks.",
        local_author.get("summary", {}).get("status") == "pass"
        and local_author.get("summary", {}).get("failed_checks") == 0,
        "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json",
        local_author.get("summary", {}),
    )

    trace = parsed.get("materials/REVIEWER_EVIDENCE_TRACE_PACK.json", {})
    trace_review_rows = [
        row
        for row in trace.get("rows", [])
        if row.get("status") == "review_required" and row.get("trace_id") not in SELF_REFERENTIAL_TRACE_IDS
    ]
    add_check(
        checks,
        "SM7_reviewer_trace_pass",
        "Reviewer evidence trace pack has zero core review-required rows outside self-referential navigation rows.",
        not trace_review_rows,
        "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
        trace_review_rows,
    )

    dashboard = parsed.get("materials/SUBMISSION_READINESS_DASHBOARD.json", {})
    dashboard_review_rows = [
        row
        for row in dashboard.get("dashboard_rows", [])
        if row.get("id") not in SELF_REFERENTIAL_DASHBOARD_IDS and row.get("status") == "review_required"
    ]
    add_check(
        checks,
        "SM8_submission_dashboard_clean",
        "Submission dashboard has zero core review-required rows outside self-referential navigation rows.",
        not dashboard_review_rows,
        "materials/SUBMISSION_READINESS_DASHBOARD.json",
        dashboard_review_rows,
    )

    bundle = parsed.get("materials/FINAL_SUBMISSION_FILE_BUNDLE.json", {})
    add_check(
        checks,
        "SM9_final_bundle_complete",
        "Final submission bundle has zero missing required files.",
        bundle.get("summary", {}).get("missing_required_count") == 0,
        "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
        bundle.get("summary", {}),
    )

    release = parsed.get("materials/RELEASE_ARCHIVE_MANIFEST.json", {})
    freeze = parsed.get("materials/FINAL_CHECKSUM_FREEZE_RECORD.json", {})
    release_summary = release.get("summary", {})
    freeze_summary = freeze.get("summary", {})
    freeze_release_mismatches = []
    release_entry_mismatches = []
    if freeze_summary.get("release_file_count") != release_summary.get("file_count"):
        freeze_release_mismatches.append(
            {
                "field": "release_file_count",
                "freeze_value": freeze_summary.get("release_file_count"),
                "release_manifest_value": release_summary.get("file_count"),
            }
        )
    if freeze_summary.get("release_size_bytes") != release_summary.get("size_bytes"):
        freeze_release_mismatches.append(
            {
                "field": "release_size_bytes",
                "freeze_value": freeze_summary.get("release_size_bytes"),
                "release_manifest_value": release_summary.get("size_bytes"),
            }
        )
    for row in release.get("files", []):
        rel = row.get("path")
        path = root / rel if rel else None
        if not rel or path is None:
            release_entry_mismatches.append({"path": rel, "issue": "missing_path_field"})
        elif not path.exists():
            release_entry_mismatches.append({"path": rel, "issue": "missing_file"})
        elif not path.is_file():
            release_entry_mismatches.append({"path": rel, "issue": "not_a_file"})
        else:
            size = path.stat().st_size
            if size != row.get("size_bytes"):
                release_entry_mismatches.append(
                    {
                        "path": rel,
                        "issue": "size_changed",
                        "manifest_size_bytes": row.get("size_bytes"),
                        "actual_size_bytes": size,
                    }
                )
            expected_sha = row.get("sha256")
            actual_sha = sha256_file(path)
            if actual_sha != expected_sha:
                release_entry_mismatches.append(
                    {
                        "path": rel,
                        "issue": "sha256_changed",
                        "manifest_sha256": expected_sha,
                        "actual_sha256": actual_sha,
                    }
                )
        if len(release_entry_mismatches) >= 50:
            break
    add_check(
        checks,
        "SM10_checksum_freeze_ready",
        "Final checksum freeze is ready, matches the current release manifest, and release-listed files are present with unchanged sizes and SHA256 hashes.",
        freeze_summary.get("status") == "ready_for_author_freeze"
        and not freeze_release_mismatches
        and not release_entry_mismatches,
        "materials/FINAL_CHECKSUM_FREEZE_RECORD.json; materials/RELEASE_ARCHIVE_MANIFEST.json",
        {
            "freeze": freeze_summary,
            "release_manifest": release_summary,
            "mismatches": freeze_release_mismatches,
            "release_entry_mismatches": release_entry_mismatches,
        },
    )

    figure_exports = [
        "figures/figure_1_multicar_overtake_results.pdf",
        "figures/figure_1_multicar_overtake_results.tiff",
        "figures/figure_2_portfolio_selector_summary.pdf",
        "figures/figure_2_portfolio_selector_summary.tiff",
        "figures/figure_3_cross_heldout_validation.pdf",
        "figures/figure_3_cross_heldout_validation.tiff",
    ]
    missing_figures = [rel for rel in figure_exports if not (root / rel).exists()]
    add_check(
        checks,
        "SM11_main_figure_exports_present",
        "Main figure PDF/TIFF exports are present.",
        not missing_figures,
        "; ".join(figure_exports),
        missing_figures,
    )

    stale_findings = scan_stale(root, total)
    add_check(
        checks,
        "SM12_no_stale_status_snapshots",
        "Reviewer-facing materials contain no stale artifact-count or fail-status snapshots.",
        not stale_findings,
        "materials/; tables/",
        stale_findings,
    )

    failed = [item for item in checks if item["status"] != "pass"]
    return {
        "root": str(root),
        "title": "Publication Smoke Test",
        "purpose": "Fast independent smoke test for reviewer-facing package integrity without rerunning expensive simulation rollouts.",
        "checks": checks,
        "summary": {
            "status": "pass" if not failed else "fail",
            "check_count": len(checks),
            "failed_checks": len(failed),
            "artifact_provenance": f"{complete}/{total}",
            "publication_verification_status": verification.get("summary", {}).get("status"),
            "statistical_consistency_status": stats.get("summary", {}).get("status"),
            "cross_material_consistency_status": cross_material.get("summary", {}).get("status"),
            "cross_report_freshness_status": freshness.get("summary", {}).get("status"),
            "data_dictionary_complete": dictionary.get("summary", {}).get("complete"),
        },
        "interpretation": (
            "This smoke test checks saved artifacts, source-data headers, package gates, and stale-status snapshots. "
            "It is intentionally fast and does not reproduce expensive rollout experiments."
        ),
    }


def write_csv(report, path):
    fields = ["check_id", "description", "status", "severity", "evidence", "observed"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["checks"]:
            writer.writerow(row)


def write_markdown(report, path):
    lines = [
        "# Publication Smoke Test",
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
    lines.extend(["", "## Checks", "", "| id | status | description | evidence | observed |", "|---|---|---|---|---|"])
    for row in report["checks"]:
        lines.append(
            f"| {row['check_id']} | {row['status']} | {row['description']} | "
            f"`{row['evidence']}` | {row['observed']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run fast publication-package smoke test.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    if args.write_report:
        materials = root / "materials"
        materials.mkdir(parents=True, exist_ok=True)
        out_json = materials / "PUBLICATION_SMOKE_TEST.json"
        out_md = materials / "PUBLICATION_SMOKE_TEST.md"
        out_csv = materials / "PUBLICATION_SMOKE_TEST.csv"
        out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        write_markdown(report, out_md)
        write_csv(report, out_csv)
        print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))
    else:
        print(json.dumps(report["summary"], indent=2))
    raise SystemExit(0 if report["summary"]["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
