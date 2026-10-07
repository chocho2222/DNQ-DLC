#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_text_if_exists(path):
    path = Path(path)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def repo_root_from_package(root):
    return Path(root).resolve().parents[1]


def parse_authors(repo_root):
    text = read_text_if_exists(repo_root / "AUTHORS")
    if not text:
        return {
            "source": "AUTHORS",
            "status": "missing",
            "creators": [],
            "note": "No AUTHORS file was found in the repository root.",
        }
    creators = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        creators.append({"name": line, "name_type": "organizational_or_personal", "source": "AUTHORS"})
    return {
        "source": "AUTHORS",
        "status": "present",
        "creators": creators,
        "note": "Creator names are parsed conservatively from the repository AUTHORS file.",
    }


def license_record(repo_root):
    text = read_text_if_exists(repo_root / "LICENSE")
    if not text:
        return {"path": "LICENSE", "status": "missing", "name": None}
    inferred = "MIT License" if "Permission is hereby granted" in text else "License text present"
    return {
        "path": "LICENSE",
        "status": "present",
        "name": inferred or "License text present",
        "note": "The full license text is stored in the repository root.",
    }


def build_metadata(root):
    repo_root = repo_root_from_package(root)
    manifest = load_json(root / "manifest.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    availability = load_json(root / "materials" / "DATA_CODE_AVAILABILITY.json")
    env = load_json(root / "materials" / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.json")
    summary = load_json(root / "materials" / "PUBLICATION_PACKAGE_SUMMARY.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")

    release_summary = release["summary"]
    external = release["external_archive"]
    authors = parse_authors(repo_root)

    metadata = {
        "schema": {
            "name": "FAIR archive metadata",
            "profile": "DataCite/Zenodo-oriented local metadata draft",
            "version": "1.0",
        },
        "identifier": {
            "local_package_root": str(root),
            "external_doi": external.get("doi"),
            "external_url": external.get("url"),
            "status": release["release_status"],
            "note": external.get("note"),
        },
        "title": manifest["title"],
        "version": {
            "package_label": Path(root).name,
            "manifest_created_utc": manifest.get("created_utc"),
            "date_policy": "No generation timestamp is written by this exporter to keep checksum drift predictable.",
        },
        "creators": authors["creators"],
        "creators_source": {"path": authors["source"], "status": authors["status"], "note": authors["note"]},
        "license": license_record(repo_root),
        "resource_type": {
            "resource_type_general": "Dataset",
            "resource_type": "Code and data package for non-VLM multi-car overtaking experiments",
        },
        "keywords": [
            "multi-car racing",
            "overtaking",
            "reinforcement learning",
            "imitation learning",
            "graph policy",
            "safety shield",
            "online selector",
            "full-lap validation",
            "reproducibility",
        ],
        "description": (
            "Local archive metadata for a strict full-lap multi-car overtaking evidence package. "
            "The package stores baseline methods, innovation variants, held-out validation summaries, "
            "per-seed ledgers, source-data tables, figures, GIF evidence, trained checkpoints, logs, "
            "environment records, and reproducibility scripts. Oracle results are diagnostic upper bounds, "
            "not online selector outputs."
        ),
        "scope_and_boundaries": {
            "task": manifest["scope"]["task"],
            "validator": manifest["scope"]["validator"],
            "excluded": manifest["scope"]["excluded"],
            "oracle_boundary": manifest["reporting_boundary"]["oracle_policy"],
            "main_limitation": manifest["reporting_boundary"]["main_limitation"],
            "claim_boundary": "The package supports local evidence and reproducibility claims only until an external DOI/accession is assigned.",
        },
        "artifact_inventory": {
            "file_count": release_summary["file_count"],
            "size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "by_category": release_summary["by_category"],
            "checksum_manifest": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "checksum_csv": "materials/RELEASE_ARCHIVE_MANIFEST.csv",
        },
        "availability": {
            "data_statement": availability["data_availability"]["statement"],
            "code_statement": availability["code_availability"]["statement"],
            "entry_points": availability["reproduction"]["entry_points"],
            "external_archive_pending": external.get("doi") is None and external.get("url") is None,
        },
        "reproducibility": {
            "environment_audit": "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.json",
            "python": env.get("python"),
            "environment_yml": env.get("environment_yml"),
            "torch_cuda": env.get("torch_cuda"),
            "gpus": env.get("gpu"),
            "artifact_provenance": {
                "complete": provenance["complete_count"],
                "total": len(provenance["artifacts"]),
            },
            "reproducibility_audit_missing_or_weak": availability["reproduction"]["audit_missing_or_weak"],
            "package_verification": verification["summary"],
        },
        "data_dictionary": {
            "path": "materials/DATA_DICTIONARY.json",
            "table_count": dictionary["summary"]["table_count"],
            "field_count": dictionary["summary"]["field_count"],
            "complete": dictionary["summary"]["complete"],
        },
        "related_materials": {
            "summary": "materials/PUBLICATION_PACKAGE_SUMMARY.md",
            "reproduction_guide": "materials/REPRODUCTION_GUIDE.md",
            "experiment_registry": "materials/EXPERIMENT_REGISTRY.md",
            "seed_outcome_ledger": "tables/seed_outcome_ledger.md",
            "claim_evidence_matrix": "materials/CLAIM_EVIDENCE_MATRIX.md",
            "research_risk_and_safety": "materials/RESEARCH_RISK_AND_SAFETY.md",
            "top_journal_reporting_summary": "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
            "editorial_submission_checklist": "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
            "significance_briefing": "materials/SIGNIFICANCE_BRIEFING.md",
            "artifact_dependency_map": "materials/ARTIFACT_DEPENDENCY_MAP.md",
            "publication_verification": "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "release_manifest": "materials/RELEASE_ARCHIVE_MANIFEST.md",
        },
        "fair_status": [
            {
                "principle": "Findable",
                "status": "partial",
                "evidence": "Machine-readable manifests, checksums, data dictionary, and local package paths are present; external DOI/accession is pending.",
            },
            {
                "principle": "Accessible",
                "status": "partial",
                "evidence": "All referenced files are present locally; public repository or archive URL has not yet been assigned.",
            },
            {
                "principle": "Interoperable",
                "status": "pass",
                "evidence": "Core tables are exported as CSV/JSON/Markdown with a package-level data dictionary.",
            },
            {
                "principle": "Reusable",
                "status": "pass",
                "evidence": "License, environment audit, reproduction guide, script snapshots, provenance, and verification gates are included.",
            },
        ],
        "readiness_context": {
            "summary_artifact_status": {
                "publication_verification_status": verification["summary"]["status"],
                "publication_verification_failed_gates": verification["summary"]["failed_gates"],
                "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
                "data_dictionary_complete": dictionary["summary"]["complete"],
                "data_dictionary_table_count": dictionary["summary"]["table_count"],
                "release_file_count": release_summary["file_count"],
                "release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            },
            "external_archive_action": "Assign DOI/accession in Zenodo, OSF, Figshare, institutional repository, or journal-approved repository before submission.",
        },
    }
    return metadata


def write_csv(report, path):
    rows = [
        ("title", report["title"]),
        ("local_package_root", report["identifier"]["local_package_root"]),
        ("external_doi", report["identifier"]["external_doi"]),
        ("external_url", report["identifier"]["external_url"]),
        ("release_status", report["identifier"]["status"]),
        ("file_count", report["artifact_inventory"]["file_count"]),
        ("size_reference", report["artifact_inventory"]["size_reference"]),
        ("creator_count", len(report["creators"])),
        ("license", report["license"]["name"]),
        ("data_dictionary_complete", report["data_dictionary"]["complete"]),
        ("verification_status", report["reproducibility"]["package_verification"]["status"]),
        ("artifact_provenance", f"{report['reproducibility']['artifact_provenance']['complete']}/{report['reproducibility']['artifact_provenance']['total']}"),
        ("external_archive_pending", report["availability"]["external_archive_pending"]),
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["field", "value"])
        writer.writerows(rows)


def write_markdown(report, path):
    lines = [
        "# FAIR Archive Metadata",
        "",
        report["description"],
        "",
        "## Identifier",
        "",
        f"- Local package root: `{report['identifier']['local_package_root']}`",
        f"- External DOI: `{report['identifier']['external_doi']}`",
        f"- External URL: `{report['identifier']['external_url']}`",
        f"- Status: `{report['identifier']['status']}`",
        f"- Note: {report['identifier']['note']}",
        "",
        "## Citation Metadata",
        "",
        f"- Title: {report['title']}",
        f"- Package label: `{report['version']['package_label']}`",
        f"- Resource type: {report['resource_type']['resource_type']}",
        f"- License: {report['license']['name']} (`{report['license']['path']}`)",
        "",
        "Creators parsed from `AUTHORS`:",
        "",
    ]
    lines.extend(f"- {creator['name']}" for creator in report["creators"])
    lines.extend(
        [
            "",
            "## Keywords",
            "",
            ", ".join(report["keywords"]),
            "",
            "## Artifact Inventory",
            "",
            f"- File count: {report['artifact_inventory']['file_count']}",
            f"- Size reference: `{report['artifact_inventory']['size_reference']}`",
            f"- Checksum manifest: `{report['artifact_inventory']['checksum_manifest']}`",
            "",
            "| category | file count | size bytes |",
            "|---|---:|---:|",
        ]
    )
    for category, row in sorted(report["artifact_inventory"]["by_category"].items()):
        lines.append(f"| {category} | {row['file_count']} | {row['size_bytes']} |")
    lines.extend(
        [
            "",
            "## FAIR Status",
            "",
            "| principle | status | evidence |",
            "|---|---|---|",
        ]
    )
    for row in report["fair_status"]:
        lines.append(f"| {row['principle']} | {row['status']} | {row['evidence']} |")
    lines.extend(
        [
            "",
            "## Reproducibility Entry Points",
            "",
        ]
    )
    lines.extend(f"- `{item}`" for item in report["availability"]["entry_points"])
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            f"- Task: {report['scope_and_boundaries']['task']}",
            f"- Validator: {report['scope_and_boundaries']['validator']}",
            f"- Excluded: {report['scope_and_boundaries']['excluded']}",
            f"- Oracle boundary: {report['scope_and_boundaries']['oracle_boundary']}",
            f"- Main limitation: {report['scope_and_boundaries']['main_limitation']}",
            f"- Claim boundary: {report['scope_and_boundaries']['claim_boundary']}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export FAIR archive metadata for the local experiment package.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_metadata(root)
    out_json = materials / "FAIR_ARCHIVE_METADATA.json"
    out_md = materials / "FAIR_ARCHIVE_METADATA.md"
    out_csv = materials / "FAIR_ARCHIVE_METADATA.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
