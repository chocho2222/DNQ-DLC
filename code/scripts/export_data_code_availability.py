#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_statement(root):
    manifest = load_json(root / "manifest.json")
    audit = load_json(root / "tables" / "reproducibility_audit.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    fair = load_json(root / "materials" / "FAIR_ARCHIVE_METADATA.json")
    archive_upload = load_json(root / "materials" / "ARCHIVE_UPLOAD_READINESS_MATRIX.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")

    data_locations = [
        "evaluations/*/multiseed_suite_summary.json",
        "evaluations/portfolio_probe_selector*/portfolio_probe_selector_summary.json",
        "tables/*.json",
        "tables/*_rows.csv",
        "tables/seed_outcome_ledger.csv",
        "materials/DATA_DICTIONARY.csv",
        "figures/*_source_data.csv",
        "models/*/train_summary.json",
        "baselines/*/*.json",
        "logs/*.log",
    ]
    code_locations = [
        "scripts/",
        "dlc/",
        "gym_multi_car_racing/",
        "materials/scripts/",
        "materials/dlc/",
        "environment.yml",
    ]
    entry_points = [
        "materials/REPRODUCTION_GUIDE.md",
        "materials/DATA_DICTIONARY.md",
        "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
        "materials/EXPERIMENT_REGISTRY.md",
        "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
        "materials/RELEASE_ARCHIVE_MANIFEST.md",
        "materials/FAIR_ARCHIVE_METADATA.md",
        "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md",
        "materials/RESEARCH_RISK_AND_SAFETY.md",
        "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
        "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
        "materials/SIGNIFICANCE_BRIEFING.md",
        "materials/EDITORIAL_DECISION_BRIEF.md",
        "materials/ARTIFACT_DEPENDENCY_MAP.md",
        "materials/SUBMISSION_READINESS_DASHBOARD.md",
        "tables/artifact_provenance.md",
        "tables/reproducibility_audit.md",
        "manifest.json",
    ]

    return {
        "root": str(root),
        "data_availability": {
            "statement": (
                "All data generated for the current non-VLM multi-car overtaking study are stored in the "
                "experiment package root. This includes raw rollout summaries, validation JSON files, "
                "spreadsheet-ready CSV tables, figure source data, GIF evidence, logs, trained model "
                "checkpoints, and machine-readable manifests."
            ),
            "primary_locations": data_locations,
        },
        "code_availability": {
            "statement": (
                "The code used to generate, evaluate, summarize, and audit the package is stored in the "
                "repository and snapshotted under the package materials directory. The package includes "
                "script snapshots for reproduction commands and policy/rollout code snapshots used by the "
                "reported experiments."
            ),
            "primary_locations": code_locations,
        },
        "reproduction": {
            "entry_points": entry_points,
            "devices_recorded": manifest["device"],
            "artifact_provenance": {
                "complete": provenance["complete_count"],
                "total": len(provenance["artifacts"]),
            },
            "audit_missing_or_weak": len(audit["missing_or_weak_items"]),
        },
        "boundaries": {
            "excluded": manifest["scope"]["excluded"],
            "oracle_boundary": manifest["reporting_boundary"]["oracle_policy"],
            "main_limitation": manifest["reporting_boundary"]["main_limitation"],
            "not_included": [
                "A final external manuscript PDF/source package.",
                "A public DOI or repository accession number.",
                "A broad robustness claim beyond the saved seed sets.",
            ],
        },
        "summary": {
            "status": "ready_local_pending_external_archive",
            "data_location_count": len(data_locations),
            "code_location_count": len(code_locations),
            "reproduction_entry_point_count": len(entry_points),
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "reproducibility_missing_or_weak": len(audit["missing_or_weak_items"]),
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "archive_upload_readiness_status": archive_upload["summary"]["status"],
            "external_archive_pending": fair["availability"]["external_archive_pending"],
            "external_identifier_present": bool(
                fair.get("identifier", {}).get("external_doi") or fair.get("identifier", {}).get("external_url")
            ),
        },
    }


def write_markdown(report, path):
    data = report["data_availability"]
    code = report["code_availability"]
    reproduction = report["reproduction"]
    boundaries = report["boundaries"]

    lines = [
        "# Data And Code Availability",
        "",
        "## Data Availability",
        "",
        data["statement"],
        "",
        "Primary data locations:",
        "",
    ]
    lines.extend(f"- `{item}`" for item in data["primary_locations"])
    lines.extend(
        [
            "",
            "## Code Availability",
            "",
            code["statement"],
            "",
            "Primary code locations:",
            "",
        ]
    )
    lines.extend(f"- `{item}`" for item in code["primary_locations"])
    lines.extend(
        [
            "",
            "## Reproduction Entry Points",
            "",
        ]
    )
    lines.extend(f"- `{item}`" for item in reproduction["entry_points"])
    lines.extend(
        [
            "",
            "## Recorded Compute",
            "",
            f"- Devices used in recorded runs: `{reproduction['devices_recorded']}`",
            "",
            "## Integrity Status",
            "",
            (
                f"- Artifact provenance: {reproduction['artifact_provenance']['complete']}/"
                f"{reproduction['artifact_provenance']['total']}"
            ),
            f"- Reproducibility missing/weak items: {reproduction['audit_missing_or_weak']}",
            "",
            "## Boundaries",
            "",
            f"- Excluded components: {boundaries['excluded']}",
            f"- Oracle boundary: {boundaries['oracle_boundary']}",
            f"- Main limitation: {boundaries['main_limitation']}",
            "",
            "Not included:",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in boundaries["not_included"])
    lines.append("")
    lines.extend(
        [
            "## Submission Readiness Navigation",
            "",
            "- `materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md`",
            "- `materials/EDITORIAL_DECISION_BRIEF.md`",
            "- `materials/SUBMISSION_READINESS_DASHBOARD.md`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(report, path):
    rows = []
    rows.append(
        {
            "section": "data_availability",
            "item": "statement",
            "value": report["data_availability"]["statement"],
            "status": "ready_local_pending_external_archive",
            "evidence": "materials/DATA_CODE_AVAILABILITY.md; materials/DATA_DICTIONARY.md",
        }
    )
    for location in report["data_availability"]["primary_locations"]:
        rows.append(
            {
                "section": "data_availability",
                "item": "primary_location",
                "value": location,
                "status": "ready_local",
                "evidence": location,
            }
        )
    rows.append(
        {
            "section": "code_availability",
            "item": "statement",
            "value": report["code_availability"]["statement"],
            "status": "ready_local_pending_external_archive",
            "evidence": "materials/DATA_CODE_AVAILABILITY.md; materials/scripts/",
        }
    )
    for location in report["code_availability"]["primary_locations"]:
        rows.append(
            {
                "section": "code_availability",
                "item": "primary_location",
                "value": location,
                "status": "ready_local",
                "evidence": location,
            }
        )
    for entry in report["reproduction"]["entry_points"]:
        rows.append(
            {
                "section": "reproduction",
                "item": "entry_point",
                "value": entry,
                "status": "ready_local",
                "evidence": entry,
            }
        )
    for boundary in report["boundaries"]["not_included"]:
        rows.append(
            {
                "section": "boundary",
                "item": "not_included",
                "value": boundary,
                "status": "author_or_scope_boundary",
                "evidence": "materials/RESEARCH_RISK_AND_SAFETY.md; materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md",
            }
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["section", "item", "value", "status", "evidence"])
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Export data and code availability statement.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_statement(root)
    out_json = root / "materials" / "DATA_CODE_AVAILABILITY.json"
    out_md = root / "materials" / "DATA_CODE_AVAILABILITY.md"
    out_csv = root / "materials" / "DATA_CODE_AVAILABILITY.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
