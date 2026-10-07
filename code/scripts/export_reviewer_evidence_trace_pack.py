#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def exists_all(root, paths):
    checked = []
    for rel in paths:
        if "*" in rel:
            matches = list(root.glob(rel))
            checked.append({"path": rel, "exists": bool(matches), "matched_count": len(matches)})
        else:
            checked.append({"path": rel, "exists": (root / rel).exists(), "matched_count": 1 if (root / rel).exists() else 0})
    return checked


def trace_row(trace_id, section, item, evidence, reviewer_check, boundary, status="ready"):
    return {
        "trace_id": trace_id,
        "section": section,
        "item": item,
        "evidence": evidence,
        "reviewer_check": reviewer_check,
        "claim_boundary": boundary,
        "status": status,
    }


def compact_list(items):
    return "; ".join(items)


SELF_REFERENTIAL_DASHBOARD_IDS = {
    "E4d_reviewer_evidence_trace",
    "E4g_reporting_supplement_navigator",
    "E4h_reviewer_replication_route",
    "E4i_manuscript_supplement_assembly",
    "E8b_author_upload_gap_closure",
    "E8c_public_archive_journal_upload_dry_run",
}


def build_report(root):
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    figure_audit = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    figure_qc = load_json(root / "materials" / "FIGURE_TECHNICAL_QC.json")
    ledger = load_json(root / "tables" / "seed_outcome_ledger.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    threats = load_json(root / "materials" / "THREATS_TO_VALIDITY_AUDIT.json")
    limitation = load_json(root / "materials" / "MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.json")
    portal_fields = load_json(root / "materials" / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")
    upload_plan = load_json(root / "materials" / "SUBMISSION_UPLOAD_SELECTION_PLAN.json")
    claim_boundary = load_json(root / "materials" / "CLAIM_BOUNDARY_COMMUNICATION_PACK.json")
    response_seed = load_json(root / "materials" / "REVIEWER_RESPONSE_SEED_PACK.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    provenance_ratio = f"{provenance['complete_count']}/{len(provenance['artifacts'])}"

    rows = []

    for claim in claims["claims"]:
        evidence = claim.get("primary_evidence", [])
        limitations = claim.get("limitations", [])
        checked = exists_all(root, evidence + limitations)
        status = "ready" if all(item["exists"] for item in checked) else "review_required"
        rows.append(
            trace_row(
                claim["id"],
                "claim_to_evidence",
                (
                    f"The package has complete artifact provenance ({provenance_ratio}), no missing/weak "
                    "reproducibility-audit items (0), a dedicated environment audit, and an experiment registry."
                    if claim["id"] == "C17_reproducible_package"
                    else claim["claim"]
                ),
                compact_list(evidence + limitations),
                "Confirm the claim is supported by all listed evidence files and limited by the listed limitations.",
                claim["do_not_claim"],
                status,
            )
        )

    for fig in figure_audit["figures"]:
        evidence = [
            fig["manifest"],
            fig["source_data"],
            f"figures/{fig['figure']}.pdf",
            f"figures/{fig['figure']}.tiff",
            f"figures/{fig['figure']}.svg",
        ]
        rows.append(
            trace_row(
                f"FIG_{fig['figure']}",
                "figure_to_source_data",
                f"{fig['figure']} source-data and export trace",
                compact_list(evidence),
                (
                    f"Check {fig['source_rows']} source rows, {fig['source_columns']} columns, "
                    f"{fig['panel_count']} panels, and {fig['export_count']} exports."
                ),
                "Figures summarize simulator evidence only; source data and legends must remain linked after journal production edits.",
                "ready" if fig["complete"] else "review_required",
            )
        )

    for row in ledger["stage_summaries"]:
        rows.append(
            trace_row(
                f"LEDGER_{row['stage']}",
                "seed_level_outcomes",
                f"{row['stage']} selector/oracle ledger",
                "tables/seed_outcome_ledger.md; tables/seed_outcome_ledger.json",
                (
                    f"Review selector/oracle outcomes for {row['seed_set']}; "
                    f"selector misses={row['selector_miss_count']}, candidate gaps={row['candidate_gap_count']}."
                ),
                "Seed-level rows support descriptive held-out claims, not broad robustness.",
                "ready",
            )
        )

    rows.extend(
        [
            trace_row(
                "STAT_CONSISTENCY",
                "statistics",
                "Statistical consistency audit",
                "materials/STATISTICAL_CONSISTENCY_AUDIT.md; materials/STATISTICAL_CONSISTENCY_AUDIT.json",
                f"Confirm {stats['summary']['check_count']} static numerical checks and {stats['summary']['failed_checks']} failures.",
                "Descriptive seed-set statistics; small-N limits remain.",
                "ready" if stats["summary"]["failed_checks"] == 0 else "review_required",
            ),
            trace_row(
                "VALIDITY_THREATS",
                "limitations",
                "Threats-to-validity and manuscript integration",
                "materials/THREATS_TO_VALIDITY_AUDIT.md; materials/MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.md",
                (
                    f"Confirm {threats['summary']['row_count']} validity threats and "
                    f"{limitation['summary']['covered_count']}/{limitation['summary']['threat_count']} manuscript coverage."
                ),
                "Threat-control material prevents overclaiming but does not add empirical evidence.",
                "ready" if limitation["summary"]["status"] == "pass" else "review_required",
            ),
            trace_row(
                "CLAIM_BOUNDARY_COMMUNICATION",
                "claims",
                "Claim downgrade and do-not-claim communication pack",
                "materials/CLAIM_DOWNGRADE_MAP.md; materials/WHAT_THIS_PAPER_DOES_NOT_CLAIM.md; materials/CLAIM_BOUNDARY_COMMUNICATION_PACK.json",
                (
                    f"Confirm {claim_boundary['summary']['downgrade_row_count']} downgrade rows and "
                    f"{claim_boundary['summary']['not_claim_row_count']} do-not-claim rows have complete support."
                ),
                "Communication guardrails prevent overclaiming but do not add empirical results.",
                "ready" if claim_boundary["summary"]["status"] == "pass" else "review_required",
            ),
            trace_row(
                "REVIEWER_RESPONSE_SEEDS",
                "reviewer_response",
                "Reviewer response seed pack",
                "materials/REVIEWER_RESPONSE_SEED_PACK.md; materials/REVIEWER_RESPONSE_SEED_PACK.json; materials/REVIEWER_RISK_RESPONSE_DOSSIER.md",
                f"Confirm {response_seed['summary']['row_count']} response seeds have complete evidence routes and claim boundaries.",
                "Response seeds are rebuttal-preparation aids, not final author-certified response text.",
                "ready" if response_seed["summary"]["status"] == "pass" else "review_required",
            ),
            trace_row(
                "PORTAL_FIELDS",
                "submission",
                "Portal field completion pack",
                "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md; materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md",
                (
                    f"Confirm {portal_fields['summary']['field_count']} portal fields and "
                    f"{upload_plan['summary']['row_count']} upload rows."
                ),
                "Portal drafts require author metadata, disclosures, target-journal formatting, and archive DOI before upload.",
                "ready",
            ),
            trace_row(
                "PACKAGE_GATES",
                "package_integrity",
                "Publication gates and artifact provenance",
                "materials/PUBLICATION_PACKAGE_VERIFICATION.md; tables/artifact_provenance.md; materials/DATA_DICTIONARY.md",
                (
                    f"Confirm verification={verification['summary']['status']}, "
                    f"provenance={provenance_ratio}, "
                    f"data dictionary complete={dictionary['summary']['complete']}."
                ),
                "Local package readiness is not journal acceptance or public deposition.",
                "ready" if provenance["complete_count"] == len(provenance["artifacts"]) and dictionary["summary"]["complete"] else "review_required",
            ),
        ]
    )

    for dash in dashboard["dashboard_rows"]:
        if dash["id"] in SELF_REFERENTIAL_DASHBOARD_IDS:
            continue
        rows.append(
            trace_row(
                f"DASH_{dash['id']}",
                f"dashboard_{dash['section']}",
                dash["id"],
                dash["evidence"],
                dash["action"],
                dash["boundary"],
                dash["status"],
            )
        )

    status_counts = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    review_required = [row for row in rows if row["status"] == "review_required"]

    return {
        "root": str(root),
        "title": "Reviewer Evidence Trace Pack",
        "purpose": (
            "Provide a compact reviewer-facing trace from claims, figures, seed-level outcomes, statistics, "
            "limitations, portal fields, and package gates to the files that support them."
        ),
        "rows": rows,
        "summary": {
            "status": "pass" if not review_required else "review_required",
            "trace_row_count": len(rows),
            "claim_trace_count": len(claims["claims"]),
            "figure_trace_count": figure_audit["summary"]["figure_count"],
            "seed_stage_trace_count": len(ledger["stage_summaries"]),
            "status_counts": status_counts,
            "review_required_count": len(review_required),
            "publication_verification_status": verification["summary"]["status"],
            "statistical_consistency_status": stats["summary"]["status"],
            "artifact_provenance": provenance_ratio,
            "figure_technical_qc_status": figure_qc["summary"]["status"],
            "data_dictionary_complete": dictionary["summary"]["complete"],
        },
        "interpretation": (
            "This trace pack is a navigation and consistency aid. It does not replace the underlying source data, "
            "statistical audit, claim QA, or author-certified submission fields."
        ),
    }


def write_csv(report, path):
    fields = ["trace_id", "section", "item", "evidence", "reviewer_check", "claim_boundary", "status"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Reviewer Evidence Trace Pack",
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
            "## Trace Rows",
            "",
            "| id | section | status | item | evidence | reviewer check | boundary |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['trace_id']} | {row['section']} | {row['status']} | {row['item']} | "
            f"`{row['evidence']}` | {row['reviewer_check']} | {row['claim_boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export reviewer evidence trace pack.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "REVIEWER_EVIDENCE_TRACE_PACK.json"
    out_md = materials / "REVIEWER_EVIDENCE_TRACE_PACK.md"
    out_csv = materials / "REVIEWER_EVIDENCE_TRACE_PACK.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
