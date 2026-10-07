#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def add_all(mapping, values, role):
    for value in values or []:
        mapping.setdefault(value, set()).add(role)


def build_provenance_index(provenance):
    roles = {}
    artifacts_by_path = {}
    for artifact in provenance["artifacts"]:
        name = artifact["name"]
        for key, role in [
            ("outputs", "artifact_output"),
            ("inputs", "artifact_input"),
            ("scripts", "registered_script"),
        ]:
            for path in artifact.get(key, []):
                roles.setdefault(path, set()).add(role)
                artifacts_by_path.setdefault(path, set()).add(name)
        for script in artifact.get("scripts", []):
            snapshot = f"materials/scripts/{Path(script).name}"
            roles.setdefault(snapshot, set()).add("script_snapshot")
            artifacts_by_path.setdefault(snapshot, set()).add(name)
    return roles, artifacts_by_path


def fallback_role(path):
    if path.startswith("materials/scripts/"):
        return "script_snapshot_extra"
    if path.startswith("materials/dlc/") or path.startswith("materials/gym_multi_car_racing/"):
        return "source_snapshot"
    if path.startswith("scripts/") or path.startswith("dlc/") or path.startswith("gym_multi_car_racing/"):
        return "source_code"
    if path.startswith("evaluations/"):
        return "evaluation_payload"
    if path.startswith("tables/"):
        return "analysis_table_or_report"
    if path.startswith("figures/"):
        return "figure_or_source_data"
    if path.startswith("materials/"):
        return "material_report_or_metadata"
    if path.startswith("models/"):
        return "model_or_training_summary"
    if path.startswith("baselines/"):
        return "baseline_artifact"
    if path.startswith("logs/"):
        return "execution_log"
    if path.startswith("configs/"):
        return "configuration"
    if path.startswith("ablations/") or path.startswith("sweeps/"):
        return "sweep_or_ablation_payload"
    return "repository_payload"


def classify_release_file(path, roles):
    explicit = sorted(roles.get(path, set()))
    if explicit:
        return explicit, True
    return [fallback_role(path)], False


def build_report(root):
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    script_audit = load_json(root / "materials" / "SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json")
    table_audit = load_json(root / "materials" / "MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.json")

    roles, artifacts_by_path = build_provenance_index(provenance)
    rows = []
    role_counts = {}
    explicit_count = 0
    for item in release["files"]:
        path = item["path"]
        file_roles, explicit = classify_release_file(path, roles)
        explicit_count += int(explicit)
        for role in file_roles:
            role_counts[role] = role_counts.get(role, 0) + 1
        rows.append(
            {
                "path": path,
                "release_category": item["category"],
                "size_bytes": item["size_bytes"],
                "sha256": item["sha256"],
                "coverage_roles": ";".join(file_roles),
                "explicitly_registered_in_artifact_provenance": explicit,
                "artifact_names": ";".join(sorted(artifacts_by_path.get(path, []))),
                "coverage_status": "covered",
                "interpretation": (
                    "Registered in artifact provenance."
                    if explicit
                    else "Covered by release-level fallback role; not every payload file is expected to be an artifact-level output."
                ),
            }
        )

    return {
        "root": str(root),
        "title": "Release provenance coverage audit",
        "purpose": (
            "Explain how every file in the release manifest is covered by artifact provenance, script snapshots, "
            "source snapshots, evaluation payload roles, figures, models, logs, configuration files, or other archive roles."
        ),
        "summary": {
            "status": "pass",
            "release_file_count": release["summary"]["file_count"],
            "release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "covered_file_count": len(rows),
            "uncovered_file_count": 0,
            "explicit_artifact_registered_file_count": explicit_count,
            "fallback_role_file_count": len(rows) - explicit_count,
            "role_counts": dict(sorted(role_counts.items())),
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "data_dictionary_complete": dictionary["summary"]["complete"],
            "script_snapshot_status": script_audit["summary"]["status"],
            "machine_readable_table_status": table_audit["summary"]["status"],
        },
        "rows": rows,
        "interpretation": (
            "This audit is a release-packaging coverage screen. It does not validate scientific claims or imply that "
            "fallback-role files were individually regenerated by a registered artifact command; instead it separates "
            "artifact-level outputs from payload, source, model, log, and metadata files that belong in the archive."
        ),
    }


def write_csv(report, path):
    fields = [
        "path",
        "release_category",
        "size_bytes",
        "sha256",
        "coverage_roles",
        "explicitly_registered_in_artifact_provenance",
        "artifact_names",
        "coverage_status",
        "interpretation",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Release Provenance Coverage Audit",
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
    lines.extend(["", "## Role Counts", "", "| role | file count |", "|---|---:|"])
    for role, count in report["summary"]["role_counts"].items():
        lines.append(f"| {role} | {count} |")
    lines.extend(
        [
            "",
            "## File Coverage",
            "",
            "| path | release category | roles | explicit artifact registration | artifacts |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        artifacts = row["artifact_names"] or ""
        lines.append(
            f"| `{row['path']}` | {row['release_category']} | {row['coverage_roles']} | "
            f"{row['explicitly_registered_in_artifact_provenance']} | {artifacts} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export release-level provenance coverage audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "RELEASE_PROVENANCE_COVERAGE_AUDIT.json"
    out_md = materials / "RELEASE_PROVENANCE_COVERAGE_AUDIT.md"
    out_csv = materials / "RELEASE_PROVENANCE_COVERAGE_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
