#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def row(section, item, response, evidence, status="complete"):
    return {
        "section": section,
        "item": item,
        "response": response,
        "evidence": evidence,
        "status": status,
    }


def build_summary(root):
    manifest = load_json(root / "manifest.json")
    stat_plan = load_json(root / "materials" / "STATISTICAL_ANALYSIS_PLAN.json")
    availability = load_json(root / "materials" / "DATA_CODE_AVAILABILITY.json")
    registry = load_json(root / "materials" / "EXPERIMENT_REGISTRY.json")
    ledger = load_json(root / "tables" / "seed_outcome_ledger.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    fair = load_json(root / "materials" / "FAIR_ARCHIVE_METADATA.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")

    seed_sets = stat_plan["seed_sets"]
    rows = [
        row(
            "Study design",
            "Study type",
            "Simulator-only method-development and validation study for strict non-VLM multi-car full-lap overtaking.",
            "manifest.json; materials/METHODS.md",
        ),
        row(
            "Study design",
            "Primary endpoint",
            stat_plan["primary_endpoint"]["definition"],
            "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/EXPERIMENT_REGISTRY.md",
        ),
        row(
            "Study design",
            "Secondary endpoints",
            "; ".join(stat_plan["secondary_endpoints"]),
            "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/DATA_DICTIONARY.md",
        ),
        row(
            "Study design",
            "Experimental units",
            "Simulator seeds and method-seed rollout outcomes; seed-level outcomes are preserved in the ledger.",
            "tables/seed_outcome_ledger.md",
        ),
        row(
            "Study design",
            "Sample sizes",
            "; ".join(f"{name}: {len(seeds)} seeds" for name, seeds in seed_sets.items()),
            "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/EXPERIMENT_REGISTRY.md",
        ),
        row(
            "Study design",
            "Sample size determination",
            "Fixed seed batches were used for method development, stress repeats, and external validation; tests are descriptive because seed counts are small.",
            "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/CLAIM_EVIDENCE_MATRIX.md",
            "limitation",
        ),
        row(
            "Study design",
            "Randomization",
            "Track/traffic variation is controlled by preregistered simulator seed lists rather than post-hoc cherry picking.",
            "materials/EXPERIMENT_REGISTRY.md; tables/seed_outcome_ledger.md",
        ),
        row(
            "Study design",
            "Blinding",
            "Blinding is not applicable to deterministic scripted evaluation exports; oracle outcomes are explicitly separated from online simulator-loop selector outcomes.",
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/CLAIM_EVIDENCE_MATRIX.md",
        ),
        row(
            "Study design",
            "Exclusion criteria",
            "No seed-level exclusions are used in the registered ledgers; failed seeds are retained and labeled by selector miss, candidate gap, or strict failure.",
            "tables/seed_outcome_ledger.md; materials/EXPERIMENT_REGISTRY.md",
        ),
        row(
            "Statistics",
            "Analysis plan",
            "A publication-facing statistical analysis plan defines endpoints, comparisons, intervals, tests, and multiplicity policy.",
            "materials/STATISTICAL_ANALYSIS_PLAN.md",
        ),
        row(
            "Statistics",
            "Intervals and tests",
            "; ".join(stat_plan["intervals_and_tests"]),
            "tables/full_statistical_report.md; tables/cross_heldout_statistical_supplement.md",
        ),
        row(
            "Statistics",
            "Multiplicity and interpretation",
            stat_plan["multiplicity_policy"],
            "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/CLAIM_EVIDENCE_MATRIX.md",
        ),
        row(
            "Statistics",
            "Per-seed transparency",
            (
                f"The seed ledger contains {ledger['summary']['rows']} rows across {ledger['summary']['stages']} stages, "
                f"with selector passes, oracle passes, selector misses, and candidate gaps separated."
            ),
            "tables/seed_outcome_ledger.md; tables/seed_outcome_ledger.csv",
        ),
        row(
            "Reproducibility",
            "Artifact provenance",
            f"{provenance['complete_count']}/{len(provenance['artifacts'])} artifacts have complete provenance in the local package.",
            "tables/artifact_provenance.md; materials/PUBLICATION_PACKAGE_VERIFICATION.md",
        ),
        row(
            "Reproducibility",
            "Preflight verification",
            f"Publication package verification status is {verification['summary']['status']} with {verification['summary']['failed_gates']} failed gates.",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
        ),
        row(
            "Reproducibility",
            "Environment",
            "Python, conda, CUDA, GPU inventory, package versions, and environment.yml checksum are recorded.",
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
        ),
        row(
            "Data and code",
            "Data availability",
            availability["data_availability"]["statement"],
            "materials/DATA_CODE_AVAILABILITY.md; materials/DATA_DICTIONARY.md",
        ),
        row(
            "Data and code",
            "Code availability",
            availability["code_availability"]["statement"],
            "materials/DATA_CODE_AVAILABILITY.md; materials/scripts/",
        ),
        row(
            "Data and code",
            "Archive status",
            (
                f"Local release manifest lists {release['summary']['file_count']} files; "
                "exact byte size is locked in RELEASE_ARCHIVE_MANIFEST.json and external DOI/accession is pending."
            ),
            "materials/RELEASE_ARCHIVE_MANIFEST.md; materials/FAIR_ARCHIVE_METADATA.md",
            "limitation",
        ),
        row(
            "Data and code",
            "Archive and upload readiness matrix",
            "A destination-level matrix separates journal submission, source data, supplementary information, public archive, reviewer support, internal QC, and author-certified metadata.",
            "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md; materials/SUBMISSION_READINESS_DASHBOARD.md",
        ),
        row(
            "Ethics and safety",
            "Human or animal participants",
            risk["ethics_context"]["rationale"],
            "materials/RESEARCH_RISK_AND_SAFETY.md",
        ),
        row(
            "Ethics and safety",
            "Deployment boundary",
            "No real-vehicle or public-road testing is included; simulator evidence must not be reported as deployment readiness.",
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/CLAIM_EVIDENCE_MATRIX.md",
        ),
        row(
            "Ethics and safety",
            "Oracle boundary",
            manifest["reporting_boundary"]["oracle_policy"],
            "materials/CLAIM_EVIDENCE_MATRIX.md; materials/PUBLICATION_PACKAGE_VERIFICATION.md",
        ),
        row(
            "Manuscript readiness",
            "Claim guardrails",
            "Allowed claims, prohibited claims, evidence files, and limitation files are mapped explicitly.",
            "materials/CLAIM_EVIDENCE_MATRIX.md; materials/MANUSCRIPT_CLAIM_QA.md",
        ),
        row(
            "Manuscript readiness",
            "Final manuscript source",
            "A local evidence-linked manuscript draft exists, but a final submission PDF/source package is not yet included.",
            "manuscript/main.md; materials/SUBMISSION_GAP_ACTION_PLAN.md",
            "limitation",
        ),
    ]

    status_counts = {}
    for item in rows:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1

    return {
        "root": str(root),
        "title": "Top-journal reporting summary",
        "purpose": (
            "Editor-facing reporting summary for methods transparency, statistical reporting, "
            "data/code availability, reproducibility, and safety boundaries."
        ),
        "rows": rows,
        "summary": {
            "item_count": len(rows),
            "status_counts": status_counts,
            "experiment_registry_complete": registry["summary"]["all_primary_evidence_present"]
            and registry["summary"]["all_provenance_complete"],
            "publication_verification_status": verification["summary"]["status"],
            "fair_external_archive_pending": fair["availability"]["external_archive_pending"],
        },
        "interpretation": (
            "This reporting summary is designed to support manuscript submission checks. It is not a claim "
            "that remaining limitations have been resolved."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["section", "item", "response", "evidence", "status"])
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow(item)


def write_markdown(report, path):
    lines = [
        "# Top-journal Reporting Summary",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Items: {report['summary']['item_count']}",
        f"- Status counts: {report['summary']['status_counts']}",
        f"- Experiment registry complete: `{report['summary']['experiment_registry_complete']}`",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- External archive pending: `{report['summary']['fair_external_archive_pending']}`",
        "",
        "## Reporting Items",
        "",
        "| section | item | status | response | evidence |",
        "|---|---|---|---|---|",
    ]
    for item in report["rows"]:
        lines.append(
            f"| {item['section']} | {item['item']} | {item['status']} | {item['response']} | `{item['evidence']}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export top-journal reporting summary.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_summary(root)
    out_json = materials / "TOP_JOURNAL_REPORTING_SUMMARY.json"
    out_md = materials / "TOP_JOURNAL_REPORTING_SUMMARY.md"
    out_csv = materials / "TOP_JOURNAL_REPORTING_SUMMARY.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
