#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def entry(section, label, path, purpose, boundary, required=True):
    return {
        "section": section,
        "label": label,
        "path": path,
        "purpose": purpose,
        "boundary": boundary,
        "required": required,
    }


def build_readme(root):
    manifest = load_json(root / "manifest.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    data_dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    supplementary = load_json(root / "materials" / "SUPPLEMENTARY_MATERIALS_INDEX.json")
    archive = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    fair = load_json(root / "materials" / "FAIR_ARCHIVE_METADATA.json")
    blockers = load_json(root / "materials" / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")

    key = manifest["key_results"]
    entries = [
        entry(
            "start_here",
            "Package manifest",
            "manifest.json",
            "Machine-readable top-level package metadata, scope, seed sets, key results, and primary materials.",
            "Summarizes saved simulator evidence only.",
        ),
        entry(
            "start_here",
            "Archive README",
            "materials/ARCHIVE_README.md",
            "Human-readable public-archive entry point for data/code users and reviewers.",
            "Not a final journal submission receipt or public DOI by itself.",
        ),
        entry(
            "integrity",
            "Publication package verification",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "Local gate report for artifact presence, claim QA, stale text, manuscript references, and reporting readiness.",
            "Local preflight pass is not journal acceptance.",
        ),
        entry(
            "integrity",
            "Release archive manifest",
            "materials/RELEASE_ARCHIVE_MANIFEST.md",
            "File counts, category sizes, and checksums for public deposition.",
            "External DOI/accession remains pending until authors deposit the archive.",
        ),
        entry(
            "integrity",
            "Archive size and upload budget",
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.md",
            "Release size, largest files, upload partitions, and conservative size-budget checks for journal/archive routing.",
            "Budget checks are operational planning aids, not journal-specific requirements.",
        ),
        entry(
            "submission",
            "Slim submission package manifest",
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md",
            "Lightweight journal-facing upload set that points to the full archive while routing TIFFs, traces, sweeps, and diagnostics to archive or large-file upload.",
            "Operational planning aid only; target-journal rules and author-certified metadata still control final upload.",
        ),
        entry(
            "integrity",
            "Final checksum freeze record",
            "materials/FINAL_CHECKSUM_FREEZE_RECORD.md",
            "Archive-facing checksum snapshot, final local gate status, stale-scan command, and author-owned deposit actions.",
            "Records local freeze readiness; it is not an external repository receipt or DOI.",
        ),
        entry(
            "integrity",
            "Artifact provenance",
            "tables/artifact_provenance.md",
            "Artifact-level command, input, output, and script-snapshot map.",
            "Expensive rollout commands should be rerun selectively when full recomputation is needed.",
        ),
        entry(
            "reproduce",
            "Reproduction guide",
            "materials/REPRODUCTION_GUIDE.md",
            "Fast audit commands, expected outputs, expensive rollout commands, and reporting boundaries.",
            "Fast audit path regenerates reports from saved outputs without rerunning all simulations.",
        ),
        entry(
            "reproduce",
            "Environment reproducibility audit",
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
            "Environment file, package metadata, and reproducibility checks.",
            "Does not certify third-party platform or hardware equivalence.",
        ),
        entry(
            "data",
            "Data dictionary",
            "materials/DATA_DICTIONARY.md",
            "Definitions for key machine-readable CSV tables and fields.",
            "Complements journal-specific source-data formatting.",
        ),
        entry(
            "data",
            "Supplementary materials index",
            "materials/SUPPLEMENTARY_MATERIALS_INDEX.md",
            "Reviewer-facing index of supplementary tables, source data, analyses, archive files, and claim boundaries.",
            "Journal-specific numbering and upload-slot selection remain author actions.",
        ),
        entry(
            "data",
            "Figure source-data audit",
            "materials/FIGURE_SOURCE_DATA_AUDIT.md",
            "Figure manifests, source data, exported formats, and consistency checks.",
            "Figures summarize simulator evidence only.",
        ),
        entry(
            "claims",
            "Claim evidence matrix",
            "materials/CLAIM_EVIDENCE_MATRIX.md",
            "Allowed claims, prohibited claims, evidence paths, and limitations.",
            "Final manuscript, cover letter, and highlights must stay within these boundaries.",
        ),
        entry(
            "claims",
            "Simulation-to-real boundary statement",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "Boundary between simulator evidence and real-world deployment, perception, dynamics transfer, and safety certification.",
            "No real-road, VLM, perception-stack, or safety-certification claims are supported.",
        ),
        entry(
            "results",
            "Seed outcome ledger",
            "tables/seed_outcome_ledger.csv",
            "Per-seed selector, oracle, candidate-gap, and selector-miss outcomes.",
            "Oracle rows are diagnostic upper bounds, not online selector outputs.",
        ),
        entry(
            "results",
            "Cross-heldout validation synthesis",
            "tables/cross_heldout_validation_synthesis.md",
            "Heldout1-4 synthesis of selector, oracle, negative validation, and partial transfer.",
            "Supports bounded simulator validation, not broad robustness.",
        ),
        entry(
            "results",
            "Negative results and failure register",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
            "Negative controls, selector misses, candidate gaps, and failure-mode boundaries.",
            "Negative evidence must remain visible in final reporting.",
        ),
        entry(
            "submission",
            "Remaining author blockers",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.md",
            "Author-owned or external actions still needed before final journal upload.",
            "Automation cannot certify author identity, disclosures, target journal formatting, or DOI assignment.",
        ),
        entry(
            "submission",
            "Final submission file bundle",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.md",
            "Local manuscript, figure, source-data, supplement, and archive files mapped to upload slots.",
            "Final journal source/PDF still requires target-journal conversion.",
        ),
    ]

    release_paths = {item["path"] for item in release["files"]}
    enriched = []
    for item in entries:
        path = root / item["path"]
        is_archive_self = (
            item["path"].startswith("materials/RELEASE_ARCHIVE_MANIFEST")
            or item["path"].startswith("materials/PUBLICATION_PACKAGE_VERIFICATION")
            or item["path"].startswith("materials/PUBLICATION_SMOKE_TEST")
            or item["path"].startswith("materials/FINAL_CHECKSUM_FREEZE_RECORD")
            or item["path"].startswith("materials/FAIR_ARCHIVE_METADATA")
            or item["path"].startswith("materials/ARCHIVE_README")
            or item["path"].startswith("materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT")
            or item["path"].startswith("materials/EXTERNAL_ARCHIVE_PREFLIGHT")
            or item["path"].startswith("materials/FINAL_SUBMISSION_FILE_BUNDLE")
            or item["path"].startswith("materials/ARCHIVE_SIZE_BUDGET")
            or item["path"].startswith("materials/SLIM_SUBMISSION_PACKAGE")
        )
        exists = path.exists()
        in_release = item["path"] in release_paths or is_archive_self
        enriched.append(
            {
                **item,
                "exists": exists,
                "in_release_manifest": in_release,
                "size_bytes": path.stat().st_size if exists and path.is_file() else None,
                "status": "ready" if exists and in_release else "review_required",
            }
        )

    return {
        "root": str(root),
        "title": "Public archive README",
        "purpose": (
            "Provide a one-page, external-archive-facing entry point for reviewers and data/code users."
        ),
        "scope": {
            "package_title": manifest["title"],
            "task": manifest["scope"]["task"],
            "excluded": manifest["scope"]["excluded"],
            "external_identifier_status": fair["identifier"]["status"],
            "external_doi": fair["identifier"]["external_doi"],
            "external_url": fair["identifier"]["external_url"],
        },
        "key_results": {
            "locked_overtake_baseline": key["locked_single_methods"]["overtake_base_only"],
            "locked_graph_adaptive": key["locked_single_methods"]["graph_adaptive_shield"],
            "heldout1_expanded_selector": {
                "pass_count": key["expanded_online_selector"]["heldout1_pass_count"],
                "n": key["expanded_online_selector"]["heldout1_n"],
            },
            "heldout2_expanded_selector": {
                "pass_count": key["expanded_online_selector"]["heldout2_pass_count"],
                "n": key["expanded_online_selector"]["heldout2_n"],
            },
            "heldout3_external_validation": {
                "selector_pass_count": key["heldout3_external_validation"]["expanded_selector_pass_count"],
                "oracle_pass_count": key["heldout3_external_validation"]["candidate_oracle_pass_count"],
                "n": key["heldout3_external_validation"]["expanded_selector_n"],
            },
            "heldout4_post_repair_external_validation": {
                "selector_pass_count": key["heldout4_external_after_targeted_repair"]["selector_pass_count"],
                "oracle_pass_count": key["heldout4_external_after_targeted_repair"]["oracle_pass_count"],
                "n": key["heldout4_external_after_targeted_repair"]["selector_n"],
            },
        },
        "entries": enriched,
        "summary": {
            "entry_count": len(enriched),
            "ready_count": sum(1 for item in enriched if item["status"] == "ready"),
            "review_required_count": sum(1 for item in enriched if item["status"] != "ready"),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "release_file_count": release["summary"]["file_count"],
            "release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "data_dictionary_complete": data_dictionary["summary"]["complete"],
            "supplementary_index_ready": supplementary["summary"]["review_required_count"] == 0,
            "archive_author_required_count": archive["summary"]["author_required_count"],
            "remaining_author_required_count": blockers["summary"]["author_required_count"],
            "submission_dashboard_review_required": dashboard["summary"]["review_required_row_count"],
        },
        "boundaries": [
            "All driving evidence is simulation-only.",
            "The package is non-VLM and telemetry/state based.",
            "Oracle portfolios are diagnostic upper bounds, not online selector outputs.",
            "Heldout3 targeted repair is diagnostic, not external validation.",
            "Heldout4 is post-repair external validation with partial transfer, not broad robustness.",
            "No real-road deployment, perception-stack validation, or safety certification is claimed.",
            "External DOI/accession is not assigned until authors deposit the archive.",
        ],
        "author_next_actions": [
            "Deposit the release package in an approved repository and update DOI/URL/accession fields.",
            "Replace local paths with final public archive links in data/code availability text.",
            "Select target journal and convert manuscript materials to final source/PDF.",
            "Complete author, ORCID, affiliation, CRediT, funding, and competing-interest metadata.",
        ],
    }


def write_csv(report, path):
    fields = [
        "section",
        "label",
        "path",
        "purpose",
        "boundary",
        "required",
        "exists",
        "in_release_manifest",
        "size_bytes",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["entries"]:
            writer.writerow({field: item[field] for field in fields})


def write_markdown(report, path):
    lines = [
        "# Public Archive README",
        "",
        report["purpose"],
        "",
        "## Scope",
        "",
        f"- Package title: {report['scope']['package_title']}",
        f"- Task: {report['scope']['task']}",
        f"- Excluded: {report['scope']['excluded']}",
        f"- External identifier status: `{report['scope']['external_identifier_status']}`",
        f"- External DOI: `{report['scope']['external_doi']}`",
        f"- External URL: `{report['scope']['external_url']}`",
        "",
        "## Integrity Snapshot",
        "",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- Release files: {report['summary']['release_file_count']}",
        f"- Release size reference: `{report['summary']['release_size_reference']}`",
        f"- Data dictionary complete: {report['summary']['data_dictionary_complete']}",
        f"- Supplementary index ready: {report['summary']['supplementary_index_ready']}",
        "",
        "## Key Results Snapshot",
        "",
        f"- Locked overtake baseline: {report['key_results']['locked_overtake_baseline']['pass_count']}/{report['key_results']['locked_overtake_baseline']['n']}",
        f"- Locked graph-adaptive shield: {report['key_results']['locked_graph_adaptive']['pass_count']}/{report['key_results']['locked_graph_adaptive']['n']}",
        f"- Heldout1 expanded selector: {report['key_results']['heldout1_expanded_selector']['pass_count']}/{report['key_results']['heldout1_expanded_selector']['n']}",
        f"- Heldout2 expanded selector: {report['key_results']['heldout2_expanded_selector']['pass_count']}/{report['key_results']['heldout2_expanded_selector']['n']}",
        (
            "- Heldout3 external validation: "
            f"{report['key_results']['heldout3_external_validation']['selector_pass_count']}/"
            f"{report['key_results']['heldout3_external_validation']['n']} selector, "
            f"{report['key_results']['heldout3_external_validation']['oracle_pass_count']}/"
            f"{report['key_results']['heldout3_external_validation']['n']} oracle"
        ),
        (
            "- Heldout4 post-repair validation: "
            f"{report['key_results']['heldout4_post_repair_external_validation']['selector_pass_count']}/"
            f"{report['key_results']['heldout4_post_repair_external_validation']['n']} selector, "
            f"{report['key_results']['heldout4_post_repair_external_validation']['oracle_pass_count']}/"
            f"{report['key_results']['heldout4_post_repair_external_validation']['n']} oracle"
        ),
        "",
        "## Start Here",
        "",
        "| section | label | status | path | purpose | boundary |",
        "|---|---|---|---|---|---|",
    ]
    for item in report["entries"]:
        lines.append(
            f"| {item['section']} | {item['label']} | {item['status']} | `{item['path']}` | "
            f"{item['purpose']} | {item['boundary']} |"
        )
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {item}" for item in report["boundaries"])
    lines.extend(["", "## Author Actions Before Public Release Or Journal Upload", ""])
    lines.extend(f"- {item}" for item in report["author_next_actions"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export public archive README.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_readme(root)
    out_json = materials / "ARCHIVE_README.json"
    out_md = materials / "ARCHIVE_README.md"
    out_csv = materials / "ARCHIVE_README.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
