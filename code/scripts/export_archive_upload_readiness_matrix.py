#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def split_paths(value):
    if isinstance(value, list):
        return value
    return [item.strip() for item in str(value).split(";") if item.strip()]


def exists_all(root, values):
    paths = split_paths(values)
    missing = [rel for rel in paths if not (root / rel).exists()]
    return not missing, missing


def in_release_all(release_paths, values):
    paths = split_paths(values)
    missing = [rel for rel in paths if rel not in release_paths]
    return not missing, missing


def status_for(priority, files_exist, sources_exist, in_release):
    if not files_exist or not sources_exist:
        return "review_required"
    if priority in {"author_required_identifier", "author_required_metadata", "target_journal_selection"}:
        return "author_action_required"
    if priority == "optional_reviewer_support":
        return "ready_with_author_selection"
    if priority == "internal_qc":
        return "ready_internal"
    if not in_release:
        return "ready_local_not_release_locked"
    return "ready"


def make_row(row_id, destination, package_role, priority, files, sources, rationale, author_action, boundary):
    return {
        "id": row_id,
        "destination": destination,
        "package_role": package_role,
        "priority": priority,
        "files": files,
        "sources": sources,
        "rationale": rationale,
        "author_action": author_action,
        "claim_boundary": boundary,
    }


def build_report(root):
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    fair = load_json(root / "materials" / "FAIR_ARCHIVE_METADATA.json")
    archive_preflight = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    upload_plan = load_json(root / "materials" / "SUBMISSION_UPLOAD_SELECTION_PLAN.json")
    supplement_decision = load_json(root / "materials" / "SUPPLEMENT_UPLOAD_DECISION_MATRIX.json")
    source_data = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    figure_qc = load_json(root / "materials" / "FIGURE_TECHNICAL_QC.json")
    data_dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    release_paths = {item["path"] for item in release["files"]}

    rows = [
        make_row(
            "AU01_main_manuscript",
            "journal_submission",
            "main_text_and_source",
            "target_journal_selection",
            "manuscript/main.md; manuscript/main.tex; manuscript/references.bib",
            "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.json; materials/REFERENCE_READINESS_AUDIT.json",
            "Main manuscript material and starter bibliography for conversion into the selected journal template.",
            "Select target journal, apply official template, complete author metadata and final citation style.",
            "Local manuscript scaffolds are not a final journal-formatted submission.",
        ),
        make_row(
            "AU02_figures",
            "journal_submission",
            "production_figures",
            "required_upload",
            "figures/figure_1_multicar_overtake_results.pdf; figures/figure_2_portfolio_selector_summary.pdf; figures/figure_3_cross_heldout_validation.pdf",
            "materials/FIGURE_TECHNICAL_QC.json; materials/FIGURE_SOURCE_DATA_AUDIT.json; materials/FIGURE_PANEL_REVIEW_MATRIX.csv",
            "Primary figures with technical QC, panel-level source-data filters, and claim-boundary notes.",
            "Re-export to the selected journal's final figure size, format, and panel-label convention if required.",
            "Figure evidence is simulator-only and does not establish real-road readiness.",
        ),
        make_row(
            "AU03_source_data",
            "source_data_upload",
            "figure_and_table_source_data",
            "required_source_data",
            "figures/figure_1_source_data.csv; figures/figure_2_source_data.csv; figures/figure_3_source_data.csv; tables/seed_outcome_ledger.csv; tables/cross_heldout_statistical_supplement_rows.csv",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json; materials/DATA_DICTIONARY.json; materials/SUPPLEMENTARY_TABLE_LEGENDS.json",
            "Machine-readable source data for figures, seed outcomes, and statistical reporting.",
            "Adapt filenames and sheet labels to the selected journal's source-data convention.",
            "Source data support the reported seed sets only; they do not imply broad robustness.",
        ),
        make_row(
            "AU04_supplement_core",
            "supplementary_information",
            "methods_statistics_limitations",
            "required_supplement",
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.md; materials/STATISTICAL_REPORTING_APPENDIX.md; materials/THREATS_TO_VALIDITY_AUDIT.md; materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md",
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.json; materials/STATISTICAL_REPORTING_APPENDIX.json; materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.json",
            "Core Methods, statistical reporting, limitations, and manuscript-to-supplement map for reviewer inspection.",
            "Convert into the selected journal's supplementary-information order and style.",
            "Supplementary reporting clarifies evidence boundaries; it does not add unreported validation.",
        ),
        make_row(
            "AU05_supplement_optional",
            "optional_supplement_or_reviewer_response_or_archive",
            "reviewer_support_analyses",
            "optional_reviewer_support",
            "materials/SELECTOR_DECISION_AUDIT.md; materials/ENDPOINT_SENSITIVITY_AUDIT.md; materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
            "materials/SUPPLEMENT_UPLOAD_DECISION_MATRIX.json; materials/REVIEWER_RISK_RESPONSE_DOSSIER.json",
            "Optional reviewer-support analyses that may be uploaded, held for response, or retained in archive depending on journal scope.",
            "Choose placement after target-journal selection and expected reviewer needs.",
            "Optional diagnostics should not be reframed as external validation.",
        ),
        make_row(
            "AU06_public_archive",
            "public_archive",
            "complete_reproducibility_package",
            "author_required_identifier",
            "materials/ARCHIVE_README.md; materials/RELEASE_ARCHIVE_MANIFEST.md; materials/FAIR_ARCHIVE_METADATA.md; materials/CITATION.cff; materials/DATA_CODE_AVAILABILITY.md",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json; materials/FINAL_CHECKSUM_FREEZE_RECORD.json; tables/artifact_provenance.json",
            "Archive landing materials, checksum manifest, FAIR metadata, citation metadata, and data/code availability wording.",
            "Deposit in a public repository and then replace pending DOI/URL/accession fields with real identifiers.",
            "Local archive readiness is not a public DOI, accession, or deposition receipt.",
        ),
        make_row(
            "AU07_reviewer_replication",
            "reviewer_or_archive_support",
            "replication_route",
            "recommended_archive",
            "materials/REVIEWER_REPLICATION_ROUTE.md; materials/GPU_RERUN_READINESS.md; materials/REPRODUCTION_GUIDE.md; tables/artifact_provenance.md",
            "materials/REVIEWER_REPLICATION_ROUTE.json; materials/GPU_RERUN_READINESS.json; tables/artifact_provenance.json",
            "Tiered route from fast saved-artifact checks to optional GPU reruns registered in provenance.",
            "Use GPU reruns only as reviewer-requested optional checks and keep outputs under the same claim boundaries.",
            "Optional reruns do not create stronger generalization claims unless pre-registered and analyzed separately.",
        ),
        make_row(
            "AU08_internal_qc",
            "internal_pre_submission_only",
            "quality_gates",
            "internal_qc",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md; materials/PUBLICATION_SMOKE_TEST.md; materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.md; materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.md",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json; materials/PUBLICATION_SMOKE_TEST.json; materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.json; materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json",
            "Local gate reports used to detect stale status, missing files, and author-owned action leakage before sharing.",
            "Rerun after final file edits; upload only if a journal or reviewer requests package-integrity evidence.",
            "Internal QC reports are not journal acceptance decisions.",
        ),
        make_row(
            "AU09_author_certified_fields",
            "journal_portal",
            "author_metadata_disclosures",
            "author_required_metadata",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md; materials/ETHICS_DISCLOSURE_READINESS_PACK.md; materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.md",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json; materials/ETHICS_DISCLOSURE_READINESS_PACK.json; materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json",
            "Portal-ready checklist separating local evidence from certified author fields.",
            "Authors must fill ORCID, affiliations, CRediT roles, funding, conflicts, and corresponding-author details.",
            "The package intentionally does not invent or certify author metadata.",
        ),
    ]

    enriched = []
    for item in rows:
        files_exist, missing_files = exists_all(root, item["files"])
        sources_exist, missing_sources = exists_all(root, item["sources"])
        in_release, missing_release = in_release_all(release_paths, item["files"])
        enriched.append(
            {
                **item,
                "files_exist": files_exist,
                "sources_exist": sources_exist,
                "in_release_manifest": in_release,
                "status": status_for(item["priority"], files_exist, sources_exist, in_release),
                "missing_files": "; ".join(missing_files),
                "missing_sources": "; ".join(missing_sources),
                "missing_from_release": "; ".join(missing_release),
            }
        )

    status_counts = {}
    destination_counts = {}
    for item in enriched:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
        destination_counts[item["destination"]] = destination_counts.get(item["destination"], 0) + 1

    review_required_count = sum(1 for item in enriched if item["status"] == "review_required")
    author_action_count = sum(1 for item in enriched if item["status"] == "author_action_required")
    return {
        "root": str(root),
        "title": "Archive and Upload Readiness Matrix",
        "purpose": (
            "Map the evidence package into journal submission, source-data upload, supplementary information, "
            "public archive, reviewer-support, internal-QC, and author-certified metadata destinations."
        ),
        "rows": enriched,
        "summary": {
            "status": "pass" if review_required_count == 0 else "review_required",
            "row_count": len(enriched),
            "review_required_count": review_required_count,
            "author_action_required_count": author_action_count,
            "status_counts": status_counts,
            "destination_counts": destination_counts,
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "release_file_count": release["summary"]["file_count"],
            "release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "fair_external_identifier_pending": not (
                fair.get("identifier", {}).get("external_doi") or fair.get("identifier", {}).get("external_url")
            ),
            "external_archive_pending": archive_preflight["summary"].get("external_archive_pending"),
            "final_bundle_rows": bundle["summary"].get("file_row_count"),
            "upload_plan_rows": upload_plan["summary"].get("row_count"),
            "supplement_upload_decision_status": supplement_decision["summary"].get("status"),
            "figure_source_data_status": source_data["summary"].get("status"),
            "figure_qc_status": figure_qc["summary"].get("status"),
            "data_dictionary_complete": data_dictionary["summary"].get("complete"),
        },
        "interpretation": (
            "A pass status means all local files and source reports needed by this matrix exist. "
            "Rows marked author_action_required remain intentionally incomplete until authors choose the target journal, "
            "deposit the public archive, and certify metadata/disclosures."
        ),
    }


def write_csv(report, path):
    fields = [
        "id",
        "destination",
        "package_role",
        "priority",
        "status",
        "files",
        "sources",
        "files_exist",
        "sources_exist",
        "in_release_manifest",
        "missing_files",
        "missing_sources",
        "missing_from_release",
        "rationale",
        "author_action",
        "claim_boundary",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow({field: item[field] for field in fields})


def write_markdown(report, path):
    lines = [
        "# Archive and Upload Readiness Matrix",
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
            "## Matrix",
            "",
            "| id | destination | role | priority | status | files | sources | author action | boundary |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['id']} | {item['destination']} | {item['package_role']} | {item['priority']} | "
            f"{item['status']} | `{item['files']}` | `{item['sources']}` | {item['author_action']} | {item['claim_boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export archive and upload readiness matrix.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "ARCHIVE_UPLOAD_READINESS_MATRIX.json"
    out_md = materials / "ARCHIVE_UPLOAD_READINESS_MATRIX.md"
    out_csv = materials / "ARCHIVE_UPLOAD_READINESS_MATRIX.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
