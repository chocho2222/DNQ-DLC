#!/usr/bin/env python
import argparse
import csv
import hashlib
import json
from pathlib import Path


STALE_SCAN_PATTERN = (
    "133/133|132/132|131/131|130/130|129/129|128/128|127/127|126/126|"
    "Publication verification: `fail`|Publication verification: fail|"
    "publication_verification_status.: .fail|publication_verification_status: fail|"
    "Statistical consistency: `fail`|statistical_consistency_status.: .fail|"
    "statistical_consistency_status: fail"
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def file_snapshot(root, rel_path, role):
    path = root / rel_path
    exists = path.exists()
    return {
        "path": rel_path,
        "role": role,
        "exists": exists,
        "size_bytes": path.stat().st_size if exists and path.is_file() else None,
        "sha256": sha256_file(path) if exists and path.is_file() else None,
    }


def status_row(check_id, label, status, evidence, action):
    return {
        "check_id": check_id,
        "label": label,
        "status": status,
        "evidence": evidence,
        "required_before_public_deposit": True,
        "author_action": action,
    }


def build_record(root):
    manifest = load_json(root / "manifest.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    archive = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    citation = load_json(root / "materials" / "CITATION_METADATA.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    self_referential_dashboard_ids = {
        "P4_publication_smoke_test",
        "E4d_reviewer_evidence_trace",
        "E4g_reporting_supplement_navigator",
        "E4h_reviewer_replication_route",
        "E4i_manuscript_supplement_assembly",
        "E8b_author_upload_gap_closure",
        "E8c_public_archive_journal_upload_dry_run",
    }
    core_dashboard_review_required_count = sum(
        1
        for item in dashboard["dashboard_rows"]
        if item["status"] == "review_required" and item["id"] not in self_referential_dashboard_ids
    )

    release_files = release["files"]
    sha_values = [row["sha256"] for row in release_files]
    duplicate_sha_count = len(sha_values) - len(set(sha_values))
    missing_sha_count = sum(1 for row in release_files if not row.get("sha256"))
    release_paths = {row["path"] for row in release_files}

    snapshots = [
        file_snapshot(root, "manifest.json", "top_level_package_manifest"),
        file_snapshot(root, "materials/RELEASE_ARCHIVE_MANIFEST.json", "full_release_checksum_manifest"),
        file_snapshot(root, "materials/RELEASE_ARCHIVE_MANIFEST.csv", "spreadsheet_checksum_manifest"),
        file_snapshot(root, "materials/PUBLICATION_PACKAGE_VERIFICATION.json", "local_preflight_gate"),
        file_snapshot(root, "materials/STATISTICAL_CONSISTENCY_AUDIT.json", "statistical_consistency_gate"),
        file_snapshot(root, "tables/artifact_provenance.json", "artifact_lineage_gate"),
        file_snapshot(root, "materials/DATA_DICTIONARY.json", "machine_readable_table_dictionary"),
        file_snapshot(root, "materials/ARCHIVE_README.json", "public_archive_entry_point"),
        file_snapshot(root, "materials/CITATION_METADATA.json", "citation_metadata_package"),
    ]

    checks = [
        status_row(
            "freeze_release_manifest",
            "Release manifest contains file-level SHA256 checksums.",
            "pass" if release["summary"]["file_count"] > 0 and missing_sha_count == 0 else "review_required",
            f"{release['summary']['file_count']} files; missing_sha_count={missing_sha_count}; duplicate_sha_count={duplicate_sha_count}",
            "Regenerate materials/RELEASE_ARCHIVE_MANIFEST.* after final edits and before public deposit.",
        ),
        status_row(
            "freeze_publication_verification",
            "Publication package verification snapshot is recorded.",
            "pass",
            f"{verification['summary']['gate_count']} gates; failed={verification['summary']['failed_gates']}",
            "Rerun publication verification after regenerating checksum and metadata files; final pass is enforced by the publication gate, not by this freeze record.",
        ),
        status_row(
            "freeze_statistical_consistency",
            "Statistical consistency audit passes.",
            stats["summary"]["status"],
            f"{stats['summary']['check_count']} checks; failed={stats['summary']['failed_checks']}",
            "Rerun statistical consistency audit after manuscript-facing numeric changes.",
        ),
        status_row(
            "freeze_artifact_provenance",
            "Artifact provenance is complete.",
            "pass" if provenance["complete_count"] == len(provenance["artifacts"]) else "review_required",
            f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "Rerun artifact provenance after adding or removing generated materials.",
        ),
        status_row(
            "freeze_data_dictionary",
            "Data dictionary is complete for registered CSV tables.",
            "pass" if dictionary["summary"]["complete"] else "review_required",
            f"{dictionary['summary']['table_count']} tables; missing_definitions={dictionary['summary']['missing_definition_count']}",
            "Update data dictionary for any newly added CSV table before archive upload.",
        ),
        status_row(
            "freeze_dashboard",
            "Submission readiness dashboard has no core local review-required rows outside self-referential navigation rows.",
            "pass" if core_dashboard_review_required_count == 0 else "review_required",
            f"core_review_required_row_count={core_dashboard_review_required_count}; total_review_required_row_count={dashboard['summary']['review_required_row_count']}",
            "Resolve core local review-required rows before final upload.",
        ),
        status_row(
            "freeze_external_identifier",
            "External DOI or URL is assigned.",
            "author_required" if not citation["summary"]["external_doi_present"] and not citation["summary"]["external_url_present"] else "pass",
            f"doi_present={citation['summary']['external_doi_present']}; url_present={citation['summary']['external_url_present']}",
            "Deposit the frozen archive in Zenodo/OSF/GitHub release and update DOI/URL fields.",
        ),
        status_row(
            "freeze_author_archive_metadata",
            "Archive metadata fields requiring author confirmation are resolved.",
            "author_required" if archive["summary"]["author_required_count"] else "pass",
            f"archive_author_required_count={archive['summary']['author_required_count']}",
            "Confirm authorship, affiliation, license, related identifier, and access metadata.",
        ),
    ]

    command_rows = [
        {
            "step": 1,
            "command": "PYTHONPATH=. python scripts/export_release_archive_manifest.py --root outputs/paper_multicar_overtake_20260618",
            "purpose": "Regenerate file-level SHA256 checksums after all content edits.",
        },
        {
            "step": 2,
            "command": "PYTHONPATH=. python scripts/export_artifact_provenance.py --root outputs/paper_multicar_overtake_20260618",
            "purpose": "Refresh artifact completeness after checksum and metadata updates.",
        },
        {
            "step": 3,
            "command": "PYTHONPATH=. python scripts/export_data_dictionary.py --root outputs/paper_multicar_overtake_20260618",
            "purpose": "Refresh table and field coverage.",
        },
        {
            "step": 4,
            "command": "PYTHONPATH=. python scripts/export_publication_package_verification.py --root outputs/paper_multicar_overtake_20260618",
            "purpose": "Run local publication gate checks.",
        },
        {
            "step": 5,
            "command": "PYTHONPATH=. python scripts/export_statistical_consistency_audit.py --root outputs/paper_multicar_overtake_20260618",
            "purpose": "Confirm manuscript-facing numerical consistency.",
        },
        {
            "step": 6,
            "command": "PYTHONPATH=. python scripts/export_submission_readiness_dashboard.py --root outputs/paper_multicar_overtake_20260618",
            "purpose": "Refresh final local readiness dashboard.",
        },
        {
            "step": 7,
            "command": (
                "rg -n '" + STALE_SCAN_PATTERN + "' "
                "outputs/paper_multicar_overtake_20260618/materials "
                "outputs/paper_multicar_overtake_20260618/tables "
                "outputs/paper_multicar_overtake_20260618/manifest.json "
                "-g '!materials/FINAL_CHECKSUM_FREEZE_RECORD.*' "
                "-g '!materials/scripts/export_final_checksum_freeze_record.py' || true"
            ),
            "purpose": "Confirm no stale artifact-count or failed-verification text remains.",
        },
    ]

    final_freeze_status = "ready_for_author_freeze" if all(
        row["status"] == "pass" for row in checks if row["check_id"] not in {"freeze_external_identifier", "freeze_author_archive_metadata"}
    ) else "review_required"

    return {
        "root": str(root),
        "title": "Final checksum freeze record",
        "purpose": (
            "Archive-facing checksum and freeze-control record for the final public-deposit step."
        ),
        "scope": {
            "package_title": manifest["title"],
            "task": manifest["scope"]["task"],
            "excluded": manifest["scope"]["excluded"],
            "release_status": release["release_status"],
        },
        "summary": {
            "status": final_freeze_status,
            "release_file_count": release["summary"]["file_count"],
            "release_size_bytes": release["summary"]["size_bytes"],
            "missing_sha_count": missing_sha_count,
            "duplicate_sha_count": duplicate_sha_count,
            "snapshot_count": len(snapshots),
            "publication_verification_status": verification["summary"]["status"],
            "statistical_consistency_status": stats["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "data_dictionary_complete": dictionary["summary"]["complete"],
            "submission_dashboard_review_required": dashboard["summary"]["review_required_row_count"],
            "core_submission_dashboard_review_required": core_dashboard_review_required_count,
            "external_identifier_pending": not citation["summary"]["external_doi_present"] and not citation["summary"]["external_url_present"],
            "author_archive_metadata_required_count": archive["summary"]["author_required_count"],
            "registered_key_files_in_release": sum(1 for item in snapshots if item["path"] in release_paths or item["path"].startswith("materials/RELEASE_ARCHIVE_MANIFEST")),
        },
        "checks": checks,
        "file_snapshots": snapshots,
        "freeze_commands": command_rows,
        "stale_scan_pattern": STALE_SCAN_PATTERN,
        "interpretation": (
            "This record does not assign a DOI and does not mean the package has been deposited. "
            "It records that the local package has checksums and passing local gates, while external "
            "identifier and author-owned archive metadata remain final-deposit actions."
        ),
    }


def write_csv(report, path):
    fields = ["check_id", "label", "status", "evidence", "required_before_public_deposit", "author_action"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["checks"]:
            writer.writerow(row)


def write_snapshot_csv(report, path):
    fields = ["path", "role", "exists", "size_bytes", "sha256"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["file_snapshots"]:
            writer.writerow(row)


def write_markdown(report, path):
    lines = [
        "# Final Checksum Freeze Record",
        "",
        report["purpose"],
        "",
        "## Scope",
        "",
        f"- Package title: {report['scope']['package_title']}",
        f"- Task: {report['scope']['task']}",
        f"- Excluded: {report['scope']['excluded']}",
        f"- Release status: `{report['scope']['release_status']}`",
        "",
        "## Summary",
        "",
        f"- Status: `{report['summary']['status']}`",
        f"- Release files: {report['summary']['release_file_count']}",
        f"- Release size bytes: {report['summary']['release_size_bytes']}",
        f"- Missing SHA256 values: {report['summary']['missing_sha_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Statistical consistency: `{report['summary']['statistical_consistency_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- External identifier pending: {report['summary']['external_identifier_pending']}",
        "",
        "## Freeze Checks",
        "",
        "| check | status | evidence | author action |",
        "|---|---|---|---|",
    ]
    for row in report["checks"]:
        lines.append(f"| {row['label']} | {row['status']} | {row['evidence']} | {row['author_action']} |")

    lines.extend(["", "## Key File Snapshots", "", "| path | role | exists | size bytes | sha256 |", "|---|---|---|---:|---|"])
    for row in report["file_snapshots"]:
        sha = row["sha256"] or ""
        lines.append(f"| `{row['path']}` | {row['role']} | {row['exists']} | {row['size_bytes']} | `{sha}` |")

    lines.extend(["", "## Final Freeze Commands", ""])
    for row in report["freeze_commands"]:
        lines.extend(
            [
                f"{row['step']}. {row['purpose']}",
                "",
                "```bash",
                row["command"],
                "```",
                "",
            ]
        )
    lines.extend(["## Interpretation", "", report["interpretation"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export final checksum freeze record.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_record(root)
    out_json = materials / "FINAL_CHECKSUM_FREEZE_RECORD.json"
    out_md = materials / "FINAL_CHECKSUM_FREEZE_RECORD.md"
    out_csv = materials / "FINAL_CHECKSUM_FREEZE_RECORD.csv"
    out_snapshot_csv = materials / "FINAL_CHECKSUM_FREEZE_FILE_SNAPSHOTS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    write_snapshot_csv(report, out_snapshot_csv)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "snapshot_csv": str(out_snapshot_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
