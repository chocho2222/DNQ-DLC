#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
PUBLIC_RELEASE_FILE_PLAN = "outputs/tits_dynamic_graph/public_release_plan/public_release_file_plan.csv"
PUBLIC_RELEASE_MANIFEST = "outputs/tits_dynamic_graph/public_release_plan/public_release_plan_manifest.json"
ARTIFACT_MANIFEST = "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
DATA_CARD = "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/DATA_CARD_md_DRAFT.md"
AUTHOR_CLOSURE = "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tits_author_submission_closure_pack_manifest.json"


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def count_csv_rows(path):
    return len(read_csv(path))


def size_mb(size_bytes):
    try:
        return round(float(size_bytes) / (1024 * 1024), 3)
    except (TypeError, ValueError):
        return 0.0


def summarize_release_rows(rows):
    summary = {}
    for row in rows:
        role = row.get("release_role", "unknown")
        item = summary.setdefault(role, {"release_role": role, "file_count": 0, "size_bytes": 0, "size_mb": 0.0})
        item["file_count"] += 1
        item["size_bytes"] += int(row.get("size_bytes") or 0)
    for item in summary.values():
        item["size_mb"] = size_mb(item["size_bytes"])
    return [summary[key] for key in sorted(summary)]


def fair_rows():
    return [
        {
            "principle": "Findable",
            "status": "partial_author_action_required",
            "current_evidence": "SHA256 artifact manifest, source-data tables, release file plan and citation draft are present.",
            "remaining_action": "Assign DOI/accession and final repository URL.",
        },
        {
            "principle": "Accessible",
            "status": "partial_author_action_required",
            "current_evidence": "Public release plan separates GitHub code, mandatory data archive, optional archive and local-only files.",
            "remaining_action": "Upload archive and code repository under selected access policy.",
        },
        {
            "principle": "Interoperable",
            "status": "local_ready",
            "current_evidence": "Core evidence is exported as CSV, JSON, Markdown, PDF/SVG/PNG/TIFF and GIF with source-data crosswalks.",
            "remaining_action": "Keep final archive paths stable and repository-relative.",
        },
        {
            "principle": "Reusable",
            "status": "partial_author_action_required",
            "current_evidence": "Environment audit, reviewer replication packet, model/data cards, checksums and claim boundaries are present.",
            "remaining_action": "Confirm license, third-party track/data notices and citation metadata.",
        },
    ]


def citation_placeholder_rows():
    return [
        {
            "field": "doi_or_accession",
            "required": True,
            "current_value": "[data archive DOI/accession]",
            "author_action": "Fill after deposition.",
        },
        {
            "field": "repository_url",
            "required": True,
            "current_value": "[repository URL]",
            "author_action": "Fill after public repository or release tag exists.",
        },
        {
            "field": "creators",
            "required": True,
            "current_value": "[author list / ORCID]",
            "author_action": "Fill from final manuscript author metadata.",
        },
        {
            "field": "license",
            "required": True,
            "current_value": "[license identifier]",
            "author_action": "Confirm with authors/institution before upload.",
        },
        {
            "field": "version",
            "required": True,
            "current_value": "[release tag]",
            "author_action": "Use the final GitHub/data-archive release label.",
        },
    ]


def build_datacite_metadata(source_rows, release_summary, artifact, readiness):
    return {
        "schema": "DataCite/Zenodo-oriented metadata draft",
        "identifier": {
            "identifier": "[data archive DOI/accession]",
            "identifierType": "DOI_or_repository_accession",
            "status": "author_action_required",
        },
        "creators": [
            {
                "name": "[Author Name]",
                "nameType": "Personal",
                "givenName": "[Given]",
                "familyName": "[Family]",
                "nameIdentifiers": [{"nameIdentifier": "[ORCID]", "nameIdentifierScheme": "ORCID"}],
            }
        ],
        "titles": [{"title": "Dynamic-Neighborhood World Models for Online Multi-Car Overtaking: Source Data and Reproducibility Artifacts"}],
        "publisher": "[Repository / data archive name]",
        "publicationYear": "[year]",
        "resourceType": {"resourceTypeGeneral": "Dataset", "resourceType": "Source data, code, model artifacts, figures and visual evidence"},
        "version": "[release tag]",
        "rightsList": [{"rights": "[license name]", "rightsIdentifier": "[SPDX identifier if available]"}],
        "descriptions": [
            {
                "descriptionType": "Abstract",
                "description": (
                    "This archive supports a simulation study of optimized DLC-style graph world models "
                    "with runtime dynamic neighborhoods for online multi-car overtaking. It contains the "
                    f"formal {source_rows}-row online benchmark source table, trained model artifacts, "
                    "configuration files, track files, analysis scripts, figure source data, top-down and "
                    "first-person GIF evidence, checksum manifests and reviewer-facing reproducibility material."
                ),
            },
            {
                "descriptionType": "Other",
                "description": "Simulation-only evidence; no real-vehicle data or deployment safety certification is included.",
            },
        ],
        "subjects": [
            {"subject": "Intelligent transportation systems"},
            {"subject": "Autonomous driving simulation"},
            {"subject": "Multi-car overtaking"},
            {"subject": "World model"},
            {"subject": "Graph neural policy"},
            {"subject": "Reproducible research"},
        ],
        "relatedIdentifiers": [
            {"relatedIdentifier": "[repository URL]", "relatedIdentifierType": "URL", "relationType": "IsSupplementTo"},
            {"relatedIdentifier": "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv", "relatedIdentifierType": "LocalPath", "relationType": "IsDocumentedBy"},
        ],
        "sizes": [
            f"{artifact.get('summary', {}).get('file_count', 'NA')} local files in current artifact manifest",
            f"{artifact.get('summary', {}).get('size_bytes', 'NA')} bytes in current artifact manifest",
        ],
        "readiness": {
            "final_readiness": f"{readiness.get('pass_count', 'NA')}/{readiness.get('gate_count', 'NA')}",
            "release_summary": release_summary,
        },
    }


def build_report(root):
    source_row_count = count_csv_rows(root / SOURCE_DATA)
    release_rows = read_csv(root / PUBLIC_RELEASE_FILE_PLAN)
    release_summary = summarize_release_rows(release_rows)
    artifact = read_json(root / ARTIFACT_MANIFEST)
    public_release = read_json(root / PUBLIC_RELEASE_MANIFEST)
    readiness = read_json(root / FINAL_READINESS)
    author_closure = read_json(root / AUTHOR_CLOSURE)
    required_inputs = [
        SOURCE_DATA,
        PUBLIC_RELEASE_FILE_PLAN,
        PUBLIC_RELEASE_MANIFEST,
        ARTIFACT_MANIFEST,
        FINAL_READINESS,
        DATA_CARD,
        AUTHOR_CLOSURE,
    ]
    missing_inputs = [path for path in required_inputs if not (root / path).exists()]
    datacite = build_datacite_metadata(source_row_count, release_summary, artifact, readiness)
    summary = {
        "status": "pass" if not missing_inputs and source_row_count == 240 else "review_required",
        "source_rows": source_row_count,
        "release_file_plan_rows": len(release_rows),
        "artifact_files": artifact.get("summary", {}).get("file_count"),
        "artifact_size_bytes": artifact.get("summary", {}).get("size_bytes"),
        "public_release_status": public_release.get("status"),
        "final_readiness": f"{readiness.get('pass_count', 'NA')}/{readiness.get('gate_count', 'NA')}",
        "author_closure_status": author_closure.get("status"),
        "missing_input_count": len(missing_inputs),
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "datacite_metadata": datacite,
        "release_summary": release_summary,
        "fair_rows": fair_rows(),
        "citation_placeholders": citation_placeholder_rows(),
        "missing_inputs": missing_inputs,
        "boundary": [
            "This pack is a metadata draft and does not create an external DOI/accession.",
            "License, author names, ORCID, repository URL and archive URL remain author-owned.",
            "The archive supports simulation reproducibility only and does not certify real-vehicle safety.",
        ],
    }


def build_markdown(report):
    lines = [
        "# T-ITS FAIR Archive Metadata Pack",
        "",
        "该包面向 Zenodo/OSF/Figshare/机构仓储等数据仓库，整理 DataCite 风格元数据、归档内容摘要、FAIR checklist、引用占位符和复用边界。它不创建 DOI，也不替代作者侧 license/作者信息确认。",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Recommended Archive Description",
            "",
            report["datacite_metadata"]["descriptions"][0]["description"],
            "",
            "## FAIR Checklist",
            "",
            "| Principle | Status | Current Evidence | Remaining Action |",
            "|---|---|---|---|",
        ]
    )
    for row in report["fair_rows"]:
        lines.append(f"| {row['principle']} | {row['status']} | {row['current_evidence']} | {row['remaining_action']} |")
    lines.extend(
        [
            "",
            "## Release Role Summary",
            "",
            "| Release role | Files | Size MB |",
            "|---|---:|---:|",
        ]
    )
    for row in report["release_summary"]:
        lines.append(f"| {row['release_role']} | {row['file_count']} | {row['size_mb']} |")
    lines.extend(
        [
            "",
            "## Citation Placeholders",
            "",
            "| Field | Required | Current Value | Author Action |",
            "|---|---|---|---|",
        ]
    )
    for row in report["citation_placeholders"]:
        lines.append(f"| {row['field']} | {row['required']} | `{row['current_value']}` | {row['author_action']} |")
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {item}" for item in report["boundary"])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export FAIR archive metadata pack for T-ITS dynamic graph study.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    paths = {
        "pack_md": write_text(materials / "FAIR_ARCHIVE_METADATA_PACK.md", build_markdown(report)),
        "pack_json": write_json(materials / "FAIR_ARCHIVE_METADATA_PACK.json", report),
        "datacite_json": write_json(materials / "datacite_metadata_draft.json", report["datacite_metadata"]),
        "release_summary_csv": write_csv(
            tables / "fair_archive_release_role_summary.csv",
            report["release_summary"],
            ["release_role", "file_count", "size_bytes", "size_mb"],
        ),
        "fair_checklist_csv": write_csv(
            tables / "fair_archive_checklist.csv",
            report["fair_rows"],
            ["principle", "status", "current_evidence", "remaining_action"],
        ),
        "citation_placeholders_csv": write_csv(
            tables / "fair_archive_citation_placeholders.csv",
            report["citation_placeholders"],
            ["field", "required", "current_value", "author_action"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_fair_archive_metadata_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
