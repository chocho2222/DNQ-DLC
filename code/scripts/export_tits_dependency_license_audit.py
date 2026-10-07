#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import ast
import csv
import json
from importlib import metadata
from pathlib import Path


ENVIRONMENT_YML = "environment.yml"
SETUP_PY = "setup.py"
LICENSE_FILE = "LICENSE"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
PUBLIC_RELEASE = "outputs/tits_dynamic_graph/public_release_plan/public_release_plan_manifest.json"
UPLOAD_MAP = "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/tits_submission_upload_bundle_map_manifest.json"

PACKAGE_ALIASES = {
    "box2d-py": "box2d-py",
    "numpy": "numpy",
    "pyglet": "pyglet",
    "shapely": "shapely",
    "gym": "gym",
    "torch": "torch",
    "pip": "pip",
}

KNOWN_LICENSES = {
    "python": ("PSF-2.0", "manual_catalog"),
    "pip": ("MIT", "manual_catalog"),
    "setuptools": ("MIT", "manual_catalog"),
    "gym": ("MIT", "project_history_manual_review_required"),
    "numpy": ("BSD-3-Clause with bundled runtime notices", "package_metadata_summary"),
    "box2d-py": ("zlib", "package_metadata"),
    "pyglet": ("BSD-3-Clause", "package_metadata"),
    "shapely": ("BSD-3-Clause", "package_metadata"),
    "torch": ("BSD-3-Clause", "package_metadata"),
}

COPYLEFT_MARKERS = ["GPL", "LGPL", "AGPL"]
PERMISSIVE_MARKERS = ["MIT", "BSD", "Apache", "zlib", "PSF"]


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


def normalize_dep_name(value):
    value = value.strip()
    if not value or value.startswith("--"):
        return ""
    for sep in ["==", "~=", ">=", "<=", "=", ">", "<"]:
        if sep in value:
            return value.split(sep, 1)[0].strip()
    return value.strip()


def parse_environment(path):
    path = Path(path)
    rows = []
    if not path.exists():
        return rows
    in_pip = False
    in_dependencies = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "dependencies:":
            in_dependencies = True
            in_pip = False
            continue
        if not in_dependencies:
            continue
        if stripped == "- pip:":
            in_pip = True
            continue
        if stripped.startswith("- "):
            value = stripped[2:].strip()
            if value == "pip:":
                in_pip = True
                continue
            name = normalize_dep_name(value)
            if name:
                rows.append({"source": "environment.yml/pip" if in_pip else "environment.yml/conda", "requirement": value, "package": name})
    return rows


def parse_setup_requires(path):
    path = Path(path)
    if not path.exists():
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "install_requires" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                    for item in keyword.value.elts:
                        if isinstance(item, ast.Constant) and isinstance(item.value, str):
                            rows.append({"source": "setup.py/install_requires", "requirement": item.value, "package": normalize_dep_name(item.value)})
    return rows


def metadata_for(package):
    distribution = PACKAGE_ALIASES.get(package, package)
    try:
        md = metadata.metadata(distribution)
        version = metadata.version(distribution)
        license_text = md.get("License") or ""
        classifiers = md.get_all("Classifier") or []
        license_classifiers = [item for item in classifiers if "License" in item]
        return {
            "installed": True,
            "installed_version": version,
            "metadata_license": compact(license_text),
            "license_classifiers": "; ".join(license_classifiers[:5]),
        }
    except Exception as exc:
        return {
            "installed": False,
            "installed_version": "",
            "metadata_license": "",
            "license_classifiers": "",
            "metadata_error": f"{type(exc).__name__}: {exc}",
        }


def compact(text, limit=320):
    text = " ".join(str(text or "").split())
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def classify_license(license_value, metadata_license, classifiers):
    text = " ".join([license_value or "", metadata_license or "", classifiers or ""]).upper()
    copyleft = [marker for marker in COPYLEFT_MARKERS if marker in text]
    permissive = [marker for marker in PERMISSIVE_MARKERS if marker.upper() in text]
    if copyleft:
        if "EXCEPTION" in text or "RUNTIME" in text or "BUNDLED" in text:
            return "review_required_runtime_or_bundled_notice", ";".join(copyleft)
        return "review_required_copyleft_marker", ";".join(copyleft)
    if permissive:
        return "permissive_or_common_scientific_stack", ";".join(sorted(set(permissive)))
    return "author_review_required_unknown_license", ""


def build_dependency_rows(root):
    env_rows = parse_environment(root / ENVIRONMENT_YML)
    setup_rows = parse_setup_requires(root / SETUP_PY)
    by_package = {}
    for row in env_rows + setup_rows:
        package = row["package"]
        if not package:
            continue
        item = by_package.setdefault(package, {"package": package, "sources": [], "requirements": []})
        item["sources"].append(row["source"])
        item["requirements"].append(row["requirement"])
    rows = []
    for package, item in sorted(by_package.items()):
        md = metadata_for(package)
        known_license, license_source = KNOWN_LICENSES.get(package, ("", "metadata_or_author_review"))
        license_class, markers = classify_license(known_license, md.get("metadata_license", ""), md.get("license_classifiers", ""))
        rows.append(
            {
                "package": package,
                "sources": "; ".join(sorted(set(item["sources"]))),
                "requirements": "; ".join(sorted(set(item["requirements"]))),
                "installed": md.get("installed", False),
                "installed_version": md.get("installed_version", ""),
                "declared_license": known_license,
                "license_source": license_source,
                "metadata_license": md.get("metadata_license", ""),
                "license_classifiers": md.get("license_classifiers", ""),
                "license_class": license_class,
                "copyleft_markers": markers,
                "author_action": author_action_for(license_class, package),
            }
        )
    return rows


def author_action_for(license_class, package):
    if license_class == "permissive_or_common_scientific_stack":
        return "Confirm final citation/license notice before public release."
    if license_class == "review_required_runtime_or_bundled_notice":
        return "Review bundled/runtime notices and include required notices in archive if distributing binaries."
    if license_class == "review_required_copyleft_marker":
        return "Legal/license review required before public release."
    return f"Confirm license metadata for {package} before release."


def build_metadata_rows(root):
    license_path = root / LICENSE_FILE
    license_text = license_path.read_text(encoding="utf-8", errors="ignore") if license_path.exists() else ""
    return [
        {
            "item": "repository_license_file",
            "path": LICENSE_FILE,
            "exists": license_path.exists(),
            "status": "pass" if license_path.exists() and "Permission is hereby granted" in license_text else "review_required",
            "detail": "MIT-style permission text detected." if "Permission is hereby granted" in license_text else "License file missing or not recognized.",
        },
        {
            "item": "environment_file",
            "path": ENVIRONMENT_YML,
            "exists": (root / ENVIRONMENT_YML).exists(),
            "status": "pass" if (root / ENVIRONMENT_YML).exists() else "review_required",
            "detail": "Conda/pip dependency file present.",
        },
        {
            "item": "setup_metadata",
            "path": SETUP_PY,
            "exists": (root / SETUP_PY).exists(),
            "status": "pass" if (root / SETUP_PY).exists() else "review_required",
            "detail": "Python package setup metadata present.",
        },
    ]


def build_report(root):
    dependency_rows = build_dependency_rows(root)
    metadata_rows = build_metadata_rows(root)
    final = read_json(root / FINAL_READINESS)
    release = read_json(root / PUBLIC_RELEASE)
    upload = read_json(root / UPLOAD_MAP)
    blocking = [row for row in metadata_rows if row["status"] != "pass"]
    copyleft = [row for row in dependency_rows if row["license_class"] == "review_required_copyleft_marker"]
    runtime_review = [row for row in dependency_rows if row["license_class"] == "review_required_runtime_or_bundled_notice"]
    unknown = [row for row in dependency_rows if row["license_class"] == "author_review_required_unknown_license"]
    summary = {
        "status": "pass" if not blocking and not copyleft else "review_required",
        "dependency_count": len(dependency_rows),
        "metadata_check_count": len(metadata_rows),
        "blocking_metadata_count": len(blocking),
        "copyleft_marker_count": len(copyleft),
        "runtime_or_bundled_notice_count": len(runtime_review),
        "unknown_license_count": len(unknown),
        "final_readiness": f"{final.get('pass_count', 'NA')}/{final.get('gate_count', 'NA')}",
        "public_release_status": release.get("status"),
        "upload_bundle_status": upload.get("status"),
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "dependency_rows": dependency_rows,
        "metadata_rows": metadata_rows,
        "boundary": [
            "This audit is a technical dependency/license metadata inventory, not legal advice.",
            "Repository license, model/data/GIF/track license choices and third-party notices remain author-owned final release decisions.",
            "If binary wheels or containers are redistributed, bundled runtime notices from packages such as NumPy/PyTorch should be reviewed and preserved as required.",
        ],
    }


def build_markdown(report):
    lines = [
        "# T-ITS Dependency and License Audit",
        "",
        "该审计把 `environment.yml` 与 `setup.py` 中的依赖、当前环境安装版本、包元数据许可证和作者侧许可边界整理成投稿/开源前检查表。",
        "它不是法律意见；它用于避免在 GitHub release、数据仓库或补充材料中遗漏第三方依赖和许可说明。",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Dependency Rows", "", "| Package | Sources | Installed | Version | Declared license | Class | Author action |", "|---|---|---:|---|---|---|---|"])
    for row in report["dependency_rows"]:
        lines.append(
            f"| {row['package']} | {row['sources']} | {row['installed']} | {row['installed_version']} | "
            f"{row['declared_license']} | {row['license_class']} | {row['author_action']} |"
        )
    lines.extend(["", "## Repository Metadata", "", "| Item | Path | Status | Detail |", "|---|---|---|---|"])
    for row in report["metadata_rows"]:
        lines.append(f"| {row['item']} | `{row['path']}` | {row['status']} | {row['detail']} |")
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in report["boundary"])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export T-ITS dependency and license audit.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_dependency_license_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    dep_fields = [
        "package",
        "sources",
        "requirements",
        "installed",
        "installed_version",
        "declared_license",
        "license_source",
        "metadata_license",
        "license_classifiers",
        "license_class",
        "copyleft_markers",
        "author_action",
    ]
    meta_fields = ["item", "path", "exists", "status", "detail"]
    paths = {
        "audit_md": write_text(materials / "DEPENDENCY_LICENSE_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "DEPENDENCY_LICENSE_AUDIT.json", report),
        "dependency_csv": write_csv(tables / "dependency_license_inventory.csv", report["dependency_rows"], dep_fields),
        "metadata_csv": write_csv(tables / "repository_license_metadata_checks.csv", report["metadata_rows"], meta_fields),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_dependency_license_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
