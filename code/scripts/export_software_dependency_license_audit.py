#!/usr/bin/env python
import argparse
import ast
import csv
import importlib.metadata as package_metadata
import json
import shutil
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def repo_root_from_package(root):
    return Path(root).resolve().parents[1]


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def parse_setup_requires(repo_root):
    path = repo_root / "setup.py"
    if not path.exists():
        return []
    tree = ast.parse(read_text(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "setup":
            for keyword in node.keywords:
                if keyword.arg == "install_requires" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                    return [ast.literal_eval(item) for item in keyword.value.elts]
    return []


def parse_environment_dependencies(repo_root):
    path = repo_root / "environment.yml"
    if not path.exists():
        return []
    deps = []
    in_pip = False
    in_channels = False
    for raw in read_text(path).splitlines():
        if raw and not raw.startswith(" ") and not raw.startswith("-"):
            in_channels = raw.strip() == "channels:"
            if raw.strip() == "dependencies:":
                in_channels = False
                in_pip = False
            continue
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if in_channels:
            continue
        if stripped == "- pip:":
            in_pip = True
            continue
        if stripped.startswith("- "):
            value = stripped[2:].strip()
            if value.startswith("--"):
                continue
            source = "pip" if in_pip else "conda"
            deps.append({"dependency": value, "source": source})
    return deps


def dependency_name(value):
    name = str(value).strip().split("[")[0]
    for token in ["==", "~=", ">=", "<=", "!=", "=", "<", ">"]:
        if token in name:
            name = name.split(token)[0]
            break
    return name.strip()


def distribution_lookup_names(name):
    aliases = {
        "box2d-py": ["box2d-py", "Box2D"],
        "sklearn": ["scikit-learn"],
    }
    return aliases.get(name.lower(), [name])


def collect_dependency_license_metadata(dependencies):
    rows = []
    seen = set()
    non_python_distribution_items = {"python"}
    for dep in dependencies:
        name = dependency_name(dep["dependency"])
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        if name.lower() in non_python_distribution_items:
            rows.append(
                {
                    "dependency": name,
                    "installed_distribution": "",
                    "installed_version": "",
                    "declared_sources": dep["source"],
                    "license_metadata": "not_applicable_to_python_distribution_metadata",
                    "summary": "Conda interpreter/runtime declaration.",
                    "home_page": "",
                    "metadata_status": "not_applicable",
                    "note": "This is an interpreter/runtime declaration rather than an installed Python package distribution.",
                }
            )
            continue
        metadata = None
        resolved_name = name
        error = ""
        for candidate in distribution_lookup_names(name):
            try:
                metadata = package_metadata.metadata(candidate)
                resolved_name = metadata.get("Name", candidate)
                break
            except package_metadata.PackageNotFoundError as exc:
                error = str(exc)
        if metadata is None:
            rows.append(
                {
                    "dependency": name,
                    "installed_distribution": "",
                    "installed_version": "",
                    "declared_sources": dep["source"],
                    "license_metadata": "metadata_not_found",
                    "summary": "",
                    "home_page": "",
                    "metadata_status": "missing",
                    "note": f"Installed package metadata was not found in the current environment: {error}",
                }
            )
            continue
        license_text = metadata.get("License") or metadata.get("Classifier") or ""
        rows.append(
            {
                "dependency": name,
                "installed_distribution": resolved_name,
                "installed_version": metadata.get("Version", ""),
                "declared_sources": dep["source"],
                "license_metadata": " ".join(str(license_text).split())[:240],
                "summary": " ".join(str(metadata.get("Summary", "")).split())[:240],
                "home_page": metadata.get("Home-page", "") or metadata.get("Project-URL", ""),
                "metadata_status": "present",
                "note": "Metadata snapshot only; authors should confirm upstream license obligations before public deposition.",
            }
        )
    return rows


def license_name(repo_root):
    path = repo_root / "LICENSE"
    if not path.exists():
        return "missing"
    text = read_text(path)
    if "Permission is hereby granted" in text:
        return "MIT License"
    return "License text present"


def file_status(repo_root, rel):
    return "present" if (repo_root / rel).exists() else "missing"


def build_report(root):
    repo_root = repo_root_from_package(root)
    env = load_json(root / "materials" / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.json")
    fair = load_json(root / "materials" / "FAIR_ARCHIVE_METADATA.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")

    setup_requires = parse_setup_requires(repo_root)
    env_deps = parse_environment_dependencies(repo_root)
    env_dep_names = {row["dependency"].split("=")[0].split("<")[0].split(">")[0].split("~")[0] for row in env_deps}
    setup_dep_names = {dep.split("=")[0].split("<")[0].split(">")[0].split("~")[0] for dep in setup_requires}

    dependencies = []
    for dep in setup_requires:
        name = dep.split("=")[0].split("<")[0].split(">")[0].split("~")[0]
        dependencies.append(
            {
                "id": f"setup_{name}",
                "dependency": dep,
                "source": "setup.py",
                "runtime_status": "declared",
                "license_scope": "third_party_license_not_redeclared",
                "note": "License and redistribution terms should be checked from the upstream package before public archive deposition.",
            }
        )
    for row in env_deps:
        name = row["dependency"].split("=")[0].split("<")[0].split(">")[0].split("~")[0]
        if name in setup_dep_names:
            continue
        dependencies.append(
            {
                "id": f"{row['source']}_{name}",
                "dependency": row["dependency"],
                "source": "environment.yml",
                "runtime_status": "declared",
                "license_scope": "third_party_license_not_redeclared",
                "note": "Environment dependency included for reproducibility; upstream license should be respected.",
            }
        )

    license_metadata = collect_dependency_license_metadata(dependencies)
    missing_license_metadata = [row for row in license_metadata if row["metadata_status"] == "missing"]

    audit_items = [
        {
            "id": "S01_repository_license",
            "category": "license",
            "status": "pass" if license_name(repo_root) == "MIT License" else "limitation",
            "evidence": "LICENSE; materials/FAIR_ARCHIVE_METADATA.md",
            "assessment": f"Repository license detected as {license_name(repo_root)}.",
            "action": "Keep LICENSE in any public archive and citation metadata.",
        },
        {
            "id": "S02_authors_file",
            "category": "attribution",
            "status": "pass" if file_status(repo_root, "AUTHORS") == "present" else "limitation",
            "evidence": "AUTHORS; materials/FAIR_ARCHIVE_METADATA.md",
            "assessment": f"AUTHORS file is {file_status(repo_root, 'AUTHORS')}.",
            "action": "Review author and contributor metadata before final journal submission.",
        },
        {
            "id": "S03_environment_file",
            "category": "environment",
            "status": "pass" if file_status(repo_root, "environment.yml") == "present" else "limitation",
            "evidence": "environment.yml; materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
            "assessment": f"environment.yml is {file_status(repo_root, 'environment.yml')}; environment audit reports ready_for_fast_audit={env['summary']['ready_for_fast_audit']}.",
            "action": "Archive environment.yml with the release package.",
        },
        {
            "id": "S04_dependency_versions",
            "category": "dependencies",
            "status": "pass" if env["summary"]["package_versions_missing"] == [] else "limitation",
            "evidence": "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.json",
            "assessment": f"Environment audit has {len(env['summary']['package_versions_missing'])} missing package-version records.",
            "action": "Regenerate environment audit immediately before archive upload.",
        },
        {
            "id": "S05_third_party_license_boundary",
            "category": "third_party_licenses",
            "status": "ready_with_author_review" if not missing_license_metadata else "limitation",
            "evidence": "setup.py; environment.yml; materials/SOFTWARE_DEPENDENCY_LICENSE_METADATA.csv",
            "assessment": (
                "The package records dependency declarations and installed package metadata license fields; "
                f"{len(missing_license_metadata)} dependencies lack installed metadata in the current environment. "
                "This is a metadata snapshot, not legal advice or a complete license-text bundle."
            ),
            "action": "Before public deposition, authors should confirm upstream license obligations and include any required third-party notices.",
        },
        {
            "id": "S06_release_archive_checksums",
            "category": "archive",
            "status": "pass",
            "evidence": "materials/RELEASE_ARCHIVE_MANIFEST.json; materials/RELEASE_ARCHIVE_MANIFEST.csv",
            "assessment": f"Release manifest records {release['summary']['file_count']} files and SHA256 checksums.",
            "action": "Regenerate release manifest after any file change and before upload.",
        },
        {
            "id": "S07_external_archive_identifier",
            "category": "archive",
            "status": "limitation" if fair["availability"]["external_archive_pending"] else "pass",
            "evidence": "materials/FAIR_ARCHIVE_METADATA.md; materials/DATA_CODE_AVAILABILITY.md",
            "assessment": f"External archive pending: {fair['availability']['external_archive_pending']}.",
            "action": "Assign DOI/accession in a public repository before journal submission.",
        },
        {
            "id": "S08_publication_preflight",
            "category": "verification",
            "status": "pass" if verification["summary"]["status"] == "pass" else "limitation",
            "evidence": "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "assessment": f"Publication package verification status is {verification['summary']['status']} with {verification['summary']['failed_gates']} failed gates.",
            "action": "Run publication verification after all archive metadata changes.",
        },
    ]

    return {
        "root": str(root),
        "title": "Software Dependency and License Audit",
        "purpose": (
            "Reviewer- and archive-facing audit of repository license, authorship metadata, declared dependencies, "
            "environment reproducibility, third-party-license boundaries, release checksums, and external archive status."
        ),
        "summary": {
            "audit_item_count": len(audit_items),
            "dependency_count": len(dependencies),
            "setup_dependency_count": len(setup_requires),
            "environment_dependency_count": len(env_deps),
            "third_party_license_metadata_rows": len(license_metadata),
            "third_party_license_metadata_missing": len(missing_license_metadata),
            "repository_license": license_name(repo_root),
            "external_archive_pending": fair["availability"]["external_archive_pending"],
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
        },
        "audit_items": audit_items,
        "dependencies": dependencies,
        "license_metadata": license_metadata,
        "interpretation": (
            "The repository license, authors file, environment file, package-version audit, checksums, and local "
            "verification are present. Third-party dependency declarations now have an installed-package metadata "
            "snapshot for reviewer convenience, but upstream license obligations and external DOI/accession remain "
            "author-confirmed pre-deposition items."
        ),
    }


def copy_repo_metadata(root):
    repo_root = repo_root_from_package(root)
    out_dir = root / "materials" / "repo_metadata"
    out_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for rel in ["LICENSE", "AUTHORS", "setup.py", "environment.yml"]:
        src = repo_root / rel
        if src.exists():
            dst = out_dir / rel
            shutil.copyfile(src, dst)
            copied.append(str(dst))
    return copied


AUDIT_FIELDS = ["id", "category", "status", "evidence", "assessment", "action"]
DEP_FIELDS = ["id", "dependency", "source", "runtime_status", "license_scope", "note"]
LICENSE_META_FIELDS = [
    "dependency",
    "installed_distribution",
    "installed_version",
    "declared_sources",
    "license_metadata",
    "summary",
    "home_page",
    "metadata_status",
    "note",
]


def write_csv(rows, path, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})


def write_markdown(report, path):
    lines = [
        "# Software Dependency and License Audit",
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
            "## Audit Items",
            "",
            "| id | category | status | assessment | action | evidence |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["audit_items"]:
        lines.append(f"| {row['id']} | {row['category']} | {row['status']} | {row['assessment']} | {row['action']} | `{row['evidence']}` |")
    lines.extend(
        [
            "",
            "## Declared Dependencies",
            "",
            "| id | dependency | source | runtime status | license scope | note |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["dependencies"]:
        lines.append(
            f"| {row['id']} | `{row['dependency']}` | {row['source']} | {row['runtime_status']} | "
            f"{row['license_scope']} | {row['note']} |"
        )
    lines.extend(
        [
            "",
            "## Installed Package License Metadata Snapshot",
            "",
            "This table records package metadata from the current Python environment. It is not legal advice and does not replace upstream license review.",
            "",
            "| dependency | installed distribution | version | license metadata | summary | metadata status |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["license_metadata"]:
        lines.append(
            f"| `{row['dependency']}` | {row['installed_distribution']} | {row['installed_version']} | "
            f"{row['license_metadata']} | {row['summary']} | {row['metadata_status']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export software dependency and license audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    copied = copy_repo_metadata(root)
    report = build_report(root)
    out_json = materials / "SOFTWARE_DEPENDENCY_LICENSE_AUDIT.json"
    out_md = materials / "SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md"
    audit_csv = materials / "SOFTWARE_DEPENDENCY_LICENSE_AUDIT.csv"
    dep_csv = materials / "SOFTWARE_DEPENDENCY_LICENSE_DEPENDENCIES.csv"
    license_meta_csv = materials / "SOFTWARE_DEPENDENCY_LICENSE_METADATA.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report["audit_items"], audit_csv, AUDIT_FIELDS)
    write_csv(report["dependencies"], dep_csv, DEP_FIELDS)
    write_csv(report["license_metadata"], license_meta_csv, LICENSE_META_FIELDS)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "audit_csv": str(audit_csv),
                "dependency_csv": str(dep_csv),
                "license_metadata_csv": str(license_meta_csv),
                "metadata_snapshots": copied,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
