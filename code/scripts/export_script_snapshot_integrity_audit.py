#!/usr/bin/env python
import argparse
import csv
import hashlib
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_info(path):
    if not path.exists():
        return {"exists": False, "size_bytes": "", "sha256": ""}
    return {"exists": True, "size_bytes": path.stat().st_size, "sha256": sha256(path)}


def build_report(root):
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    release_paths = {item["path"] for item in release["files"]}

    script_to_artifacts = {}
    for artifact in provenance["artifacts"]:
        for script in artifact["scripts"]:
            script_to_artifacts.setdefault(script, []).append(artifact["name"])

    rows = []
    for script, artifacts in sorted(script_to_artifacts.items()):
        source_path = Path(script)
        snapshot_rel = f"materials/scripts/{source_path.name}"
        snapshot_path = root / snapshot_rel
        source = file_info(source_path)
        snapshot = file_info(snapshot_path)
        status = "pass"
        reason = "source_and_snapshot_match"
        if not source["exists"]:
            status = "review_required"
            reason = "source_script_missing"
        elif not snapshot["exists"]:
            status = "review_required"
            reason = "snapshot_missing"
        elif source["sha256"] != snapshot["sha256"]:
            status = "review_required"
            reason = "snapshot_sha256_mismatch"
        elif snapshot_rel not in release_paths:
            status = "review_required"
            reason = "snapshot_not_in_release_manifest"
        rows.append(
            {
                "script": script,
                "snapshot": snapshot_rel,
                "artifact": ";".join(sorted(artifacts)),
                "source_exists": source["exists"],
                "snapshot_exists": snapshot["exists"],
                "source_size_bytes": source["size_bytes"],
                "snapshot_size_bytes": snapshot["size_bytes"],
                "source_sha256": source["sha256"],
                "snapshot_sha256": snapshot["sha256"],
                "in_release_manifest": snapshot_rel in release_paths,
                "status": status,
                "reason": reason,
            }
        )

    expected_snapshot_names = {Path(script).name for script in script_to_artifacts}
    extra_rows = []
    scripts_dir = root / "materials" / "scripts"
    if scripts_dir.exists():
        for path in sorted(scripts_dir.glob("*.py")):
            if path.name in expected_snapshot_names:
                continue
            rel = f"materials/scripts/{path.name}"
            info = file_info(path)
            extra_rows.append(
                {
                    "script": "",
                    "snapshot": rel,
                    "artifact": "",
                    "source_exists": "",
                    "snapshot_exists": info["exists"],
                    "source_size_bytes": "",
                    "snapshot_size_bytes": info["size_bytes"],
                    "source_sha256": "",
                    "snapshot_sha256": info["sha256"],
                    "in_release_manifest": rel in release_paths,
                    "status": "extra_snapshot",
                    "reason": "snapshot_not_referenced_by_artifact_provenance",
                }
            )

    failed = [row for row in rows if row["status"] != "pass"]
    return {
        "root": str(root),
        "title": "Script Snapshot Integrity Audit",
        "purpose": (
            "Verify that every script registered in artifact provenance has a materials/scripts snapshot, "
            "that the snapshot SHA256 matches the live source script, and that the snapshot is listed in the release manifest."
        ),
        "summary": {
            "status": "pass" if not failed else "review_required",
            "registered_script_count": len(rows),
            "passing_script_count": len(rows) - len(failed),
            "review_required_count": len(failed),
            "extra_snapshot_count": len(extra_rows),
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_status": smoke["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "release_file_count": release["summary"]["file_count"],
        },
        "rows": rows,
        "extra_rows": extra_rows,
        "interpretation": (
            "This audit is a source-code snapshot integrity check. It does not execute scripts or validate expensive "
            "simulation outputs; those checks remain in the publication smoke test and artifact provenance commands."
        ),
    }


def write_csv(rows, path):
    fields = [
        "script",
        "snapshot",
        "artifact",
        "source_exists",
        "snapshot_exists",
        "source_size_bytes",
        "snapshot_size_bytes",
        "source_sha256",
        "snapshot_sha256",
        "in_release_manifest",
        "status",
        "reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# Script Snapshot Integrity Audit",
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
            "## Registered Scripts",
            "",
            "| status | reason | script | snapshot | artifacts |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['status']} | {row['reason']} | `{row['script']}` | `{row['snapshot']}` | `{row['artifact']}` |"
        )
    if report["extra_rows"]:
        lines.extend(
            [
                "",
                "## Extra Snapshots",
                "",
                "| status | reason | snapshot | in release manifest |",
                "|---|---|---|---|",
            ]
        )
        for row in report["extra_rows"]:
            lines.append(f"| {row['status']} | {row['reason']} | `{row['snapshot']}` | {row['in_release_manifest']} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export script snapshot integrity audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json"
    out_md = materials / "SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.md"
    out_csv = materials / "SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.csv"
    extra_csv = materials / "SCRIPT_SNAPSHOT_EXTRA_FILES.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report["rows"], out_csv)
    write_csv(report["extra_rows"], extra_csv)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "extra_csv": str(extra_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
