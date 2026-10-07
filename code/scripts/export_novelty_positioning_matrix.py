#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_report(root):
    manifest = load_json(root / "manifest.json")
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    reviewer = load_json(root / "materials" / "REVIEWER_RISK_RESPONSE_DOSSIER.json")
    references = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    external = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")

    key = manifest["key_results"]
    claim_by_id = {row["id"]: row for row in claims["claims"]}
    rows = [
        {
            "id": "N1_strict_full_lap_endpoint",
            "innovation_axis": "evaluation_standard",
            "positioning_claim": (
                "The work treats full-lap completion, final rank, first-ahead event, off-track exposure, "
                "and traffic quality as a single strict overtaking endpoint."
            ),
            "evidence": "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/METHODS.md; tables/full_statistical_report.md",
            "novelty_role": "Moves the evaluation emphasis from selected qualitative rollouts to auditable full-lap criteria.",
            "reviewer_risk": "Endpoint choices may be seen as arbitrary or post hoc.",
            "defense": "Endpoint definitions are explicit, reused across suites, and stress-tested in endpoint-sensitivity audits.",
            "boundary": "This is a simulator evaluation contribution, not real-road validation.",
        },
        {
            "id": "N2_baseline_preservation",
            "innovation_axis": "baseline_fairness",
            "positioning_claim": (
                f"Strong rule baselines are retained rather than removed: the locked overtake baseline is "
                f"{key['locked_single_methods']['overtake_base_only']['pass_count']}/"
                f"{key['locked_single_methods']['overtake_base_only']['n']}, while graph-adaptive shielding is "
                f"{key['locked_single_methods']['graph_adaptive_shield']['pass_count']}/"
                f"{key['locked_single_methods']['graph_adaptive_shield']['n']}."
            ),
            "evidence": claim_by_id["C1_locked_baseline_strength"]["primary_evidence"],
            "novelty_role": "Frames the contribution as complementarity and selection under strong baselines.",
            "reviewer_risk": "Reviewers may ask whether the learned/shielded stack beats a simple hand-tuned policy.",
            "defense": "Report the strong baseline openly and use portfolio/selector analyses only where supported.",
            "boundary": claim_by_id["C1_locked_baseline_strength"]["do_not_claim"],
        },
        {
            "id": "N3_portfolio_complementarity",
            "innovation_axis": "controller_complementarity",
            "positioning_claim": "Different controller families pass different seeds, motivating online portfolio probing.",
            "evidence": "tables/portfolio_oracle.md; tables/heldout_v2_portfolio.md; tables/seed_outcome_ledger.md",
            "novelty_role": "Treats overtaking policy design as a seed-conditional selection problem rather than a single-controller contest.",
            "reviewer_risk": "Oracle portfolio results may be misread as deployable control.",
            "defense": "Separate oracle upper bounds from online selector rows in every table and figure.",
            "boundary": "Oracle portfolios are diagnostic upper bounds only.",
        },
        {
            "id": "N4_probe_selector_auditability",
            "innovation_axis": "online_selection",
            "positioning_claim": "The online selector commits after probe telemetry and can be replayed from saved probe-only fields.",
            "evidence": "materials/SELECTOR_DECISION_AUDIT.md; tables/seed_outcome_ledger.md",
            "novelty_role": "Provides a transparent selector audit instead of an opaque post-hoc best-method choice.",
            "reviewer_risk": "Probe selection may be seen as expensive or leaking full-rollout labels.",
            "defense": "Report probe cost, decision replay, and forbidden-field checks alongside performance.",
            "boundary": "Selector transparency does not imply optimality or out-of-distribution safety.",
        },
        {
            "id": "N5_negative_validation_as_contribution",
            "innovation_axis": "honest_generalization_boundary",
            "positioning_claim": (
                f"Cross-held-out evidence preserves both positive and negative results: expanded-or-later selector "
                f"{external['summary']['expanded_or_later_selector']} versus oracle "
                f"{external['summary']['expanded_or_later_oracle']}."
            ),
            "evidence": "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; figures/figure_3_cross_heldout_validation.*",
            "novelty_role": "Makes failure decomposition and selector-oracle gaps part of the reported contribution.",
            "reviewer_risk": "Negative held-out results may weaken the headline.",
            "defense": "Use them to define the next confirmatory experiment instead of hiding them.",
            "boundary": "Do not claim broad robustness from the current seed ladder.",
        },
        {
            "id": "N6_reproducible_publication_package",
            "innovation_axis": "reproducibility_and_reporting",
            "positioning_claim": (
                f"The package is organized as a reproducible evidence bundle with artifact provenance "
                f"{verification['summary']['artifact_provenance']}, source-data tables, scripts, logs, and claim QA."
            ),
            "evidence": "tables/artifact_provenance.md; materials/RELEASE_ARCHIVE_MANIFEST.md; materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "novelty_role": "Raises the submission from a result demo to an auditable method-development package.",
            "reviewer_risk": "Local reproducibility is not the same as public deposition.",
            "defense": "Retain local checks and update DOI/accession after external archive upload.",
            "boundary": "Public archive/DOI remains author-owned until deposition is complete.",
        },
    ]

    return {
        "root": str(root),
        "title": "Novelty Positioning Matrix",
        "purpose": (
            "Define the claim-safe novelty and significance positioning for a top-journal-style submission. "
            "The matrix distinguishes evidence-backed contributions from boundaries that must remain explicit."
        ),
        "rows": rows,
        "summary": {
            "row_count": len(rows),
            "innovation_axes": sorted({row["innovation_axis"] for row in rows}),
            "reference_topics_needing_author_completion": references["summary"]["topic_needs_author_completion_count"],
            "reviewer_dossier_rows": reviewer["summary"]["row_count"],
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
        },
        "recommended_use": [
            "Use N1-N2 to frame the problem and baseline fairness in the Introduction.",
            "Use N3-N4 to explain the method contribution without presenting oracle rows as controllers.",
            "Use N5 to make the limitations and next validation plan credible.",
            "Use N6 in Data/Code Availability, cover-letter, and reviewer-response material.",
        ],
        "interpretation": (
            "The matrix supports novelty framing only within simulator, telemetry/state, and saved-validation evidence. "
            "It does not replace a complete related-work section."
        ),
    }


def write_csv(report, path):
    fields = ["id", "innovation_axis", "positioning_claim", "evidence", "novelty_role", "reviewer_risk", "defense", "boundary"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({key: row[key] for key in fields})


def write_markdown(report, path):
    lines = [
        "# Novelty Positioning Matrix",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Rows: {report['summary']['row_count']}",
        f"- Innovation axes: {', '.join(report['summary']['innovation_axes'])}",
        f"- Reference topics needing author completion: {report['summary']['reference_topics_needing_author_completion']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        "",
        "## Matrix",
        "",
        "| id | axis | positioning claim | evidence | novelty role | reviewer risk | defense | boundary |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['id']} | {row['innovation_axis']} | {row['positioning_claim']} | `{row['evidence']}` | "
            f"{row['novelty_role']} | {row['reviewer_risk']} | {row['defense']} | {row['boundary']} |"
        )
    lines.extend(["", "## Recommended Use", ""])
    lines.extend(f"- {item}" for item in report["recommended_use"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export novelty and significance positioning matrix.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "NOVELTY_POSITIONING_MATRIX.json"
    out_md = materials / "NOVELTY_POSITIONING_MATRIX.md"
    out_csv = materials / "NOVELTY_POSITIONING_MATRIX.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
