#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def exists_all(root, evidence):
    paths = [part.strip() for part in evidence.split(";") if part.strip()]
    return all((root / path).exists() for path in paths), paths


def response_row(
    row_id,
    phase,
    likely_critique,
    response_seed,
    evidence,
    boundary,
    escalation,
    status,
):
    return {
        "id": row_id,
        "phase": phase,
        "likely_critique": likely_critique,
        "response_seed": response_seed,
        "evidence": evidence,
        "claim_boundary": boundary,
        "escalation_or_revision_action": escalation,
        "status": status,
    }


def build_report(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    claim_pack = load_json(root / "materials" / "CLAIM_BOUNDARY_COMMUNICATION_PACK.json")
    risk = load_json(root / "materials" / "REVIEWER_RISK_RESPONSE_DOSSIER.json")
    ledger = load_json(root / "tables" / "seed_outcome_ledger.json")
    external = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")

    provenance_ratio = f"{provenance['complete_count']}/{len(provenance['artifacts'])}"
    ledger_summary = ledger["summary"]
    external_summary = external["summary"]
    negative_summary = negative["summary"]

    rows = [
        response_row(
            "RQ1_main_claim_strength",
            "editorial_triage",
            "The manuscript appears to overstate a simulator study as a robust autonomy result.",
            (
                "We agree that the evidence should be framed narrowly. The revised framing is simulator-only, "
                "seed-set bounded, and explicitly separates online simulator-loop selector outcomes from diagnostic upper bounds."
            ),
            "materials/CLAIM_DOWNGRADE_MAP.md; materials/WHAT_THIS_PAPER_DOES_NOT_CLAIM.md; materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "Do not claim real-road readiness, public-road deployment, perception robustness, safety certification, or broad robustness.",
            "Use the claim downgrade map to revise title, abstract, highlights, cover letter, and response wording.",
            "ready",
        ),
        response_row(
            "RQ2_baseline_strength",
            "reviewer_round_1",
            "The baseline set may be too weak or selectively reported.",
            (
                "The package preserves the locked telemetry/rule baselines and negative controls under the same validator and seed partitions. "
                "The strongest single locked method remains visible rather than being hidden by portfolio results."
            ),
            "materials/BASELINE_FAIRNESS_AUDIT.md; tables/full_statistical_report.md; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
            "Do not claim the learned graph method uniformly dominates the strongest locked baseline.",
            "If requested, add an author-written paragraph emphasizing baseline preservation and negative-control retention.",
            "ready",
        ),
        response_row(
            "RQ3_oracle_deployability",
            "reviewer_round_1",
            "Oracle portfolios may be mistaken for online selector outputs and may inflate the reported performance if misread.",
            (
                "The oracle rows are intentionally diagnostic upper bounds. They are used to decompose selector misses from candidate-policy gaps, "
                "not to claim online controller performance."
            ),
            "materials/CLAIM_EVIDENCE_MATRIX.md; tables/seed_outcome_ledger.md; figures/figure_2_source_data.csv",
            "Oracle portfolios must be described only as diagnostic upper bounds.",
            "Keep oracle labels in tables, figures, legends, and rebuttal text; never call oracle rows controllers.",
            "ready",
        ),
        response_row(
            "RQ4_heldout3_reuse",
            "reviewer_round_1",
            "Heldout3 appears to have been used for repair, so it should not be called external validation.",
            (
                "Correct. Heldout3-targeted repair is labeled diagnostic reuse. The post-repair external validation claim is limited to heldout4, "
                "and even heldout4 is reported as partial transfer with remaining selector and candidate gaps."
            ),
            "materials/SEED_PARTITION_AUDIT.md; tables/heldout3_candidate_expansion.md; tables/heldout4_external_validation.md",
            "Do not describe heldout3 targeted repair as external validation.",
            "Use the exact wording: heldout3 diagnostic reuse; heldout4 post-repair external validation with partial transfer.",
            "ready",
        ),
        response_row(
            "RQ5_failure_visibility",
            "reviewer_round_1",
            "The paper may be hiding failure cases or near misses.",
            (
                f"The package keeps {negative_summary['item_count']} negative-result/limitation rows and a seed-level ledger with "
                f"{ledger_summary['selector_miss_count']} selector misses and {ledger_summary['candidate_gap_count']} candidate gaps."
            ),
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; tables/seed_outcome_ledger.md; tables/heldout4_failure_atlas.md",
            "Do not average away heldout3/heldout4 failures or omit failed variants.",
            "Route detailed seed-level questions to the failure atlas and seed outcome ledger.",
            "ready",
        ),
        response_row(
            "RQ6_sample_size",
            "reviewer_round_1",
            "The held-out batches are too small for broad claims.",
            (
                "The current seed batches are presented as bounded simulator evidence, with Wilson intervals and a preregistered larger-N planning grid. "
                "They are not used to claim population-level robustness."
            ),
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md; materials/STATISTICAL_REPORTING_APPENDIX.md; materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.md",
            "Current evidence supports descriptive held-out performance and stress testing, not population-level robustness.",
            "For revision, run the preregistered larger-N validation before strengthening robustness language.",
            "ready",
        ),
        response_row(
            "RQ7_selector_rule",
            "technical_review",
            "The online selector may be opaque or hand-tuned to outcomes.",
            (
                "The selector decision audit recomputes saved decisions from probe-only fields and registered priorities, separating online choice from full-rollout outcomes."
            ),
            "materials/SELECTOR_DECISION_AUDIT.md; materials/METHODS_TO_CODE_TRACEABILITY.md; tables/seed_outcome_ledger.md",
            "Selector transparency does not prove optimality or out-of-distribution safety.",
            "Point reviewers to selector audit rows and code traceability instead of adding unsupported optimality language.",
            "ready",
        ),
        response_row(
            "RQ8_endpoint_dependence",
            "technical_review",
            "The result may depend on the strict PASS definition.",
            (
                "The endpoint sensitivity audit reports nearby threshold and gate-ablation checks computed from saved rollout summaries. "
                "The strict endpoint remains the registered primary endpoint."
            ),
            "materials/ENDPOINT_SENSITIVITY_AUDIT.md; materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.md; materials/STATISTICAL_CONSISTENCY_AUDIT.md",
            "Endpoint sensitivity is local to predefined thresholds and does not replace new validation rollouts.",
            "Keep the strict endpoint definition before sensitivity interpretations.",
            "ready",
        ),
        response_row(
            "RQ9_visual_evidence",
            "figure_review",
            "The qualitative GIFs may be cherry-picked or used as evidence for quantitative claims.",
            (
                "GIFs are treated as qualitative illustrations only. Quantitative claims route to source-data CSVs, seed-level ledgers, and strict validator summaries."
            ),
            "materials/VISUAL_EVIDENCE_AUDIT.md; figures/figure_1_source_data.csv; figures/figure_2_source_data.csv; figures/figure_3_source_data.csv",
            "Do not use GIFs as substitutes for seed-level PASS/FAIL evidence.",
            "If reviewers request examples, choose GIFs whose seed/method rows are documented in the visual evidence audit.",
            "ready",
        ),
        response_row(
            "RQ10_reproducibility",
            "methods_review",
            "The package may not be reproducible enough for review.",
            (
                f"Local package gates pass: publication verification {verification['summary']['status']}, smoke test {smoke['summary']['status']}, "
                f"and artifact provenance {provenance_ratio}. The public DOI/accession remains author-owned until deposition."
            ),
            "materials/REVIEWER_REPLICATION_ROUTE.md; materials/RELEASE_ARCHIVE_MANIFEST.md; tables/artifact_provenance.md",
            "Local reproducibility does not imply public archive deposition or journal acceptance.",
            "Before submission, deposit the archive and update DOI/URL/accession fields.",
            "ready" if verification["summary"]["status"] == "pass" and smoke["summary"]["status"] == "pass" else "review_required",
        ),
        response_row(
            "RQ11_response_scope",
            "rebuttal_drafting",
            "The response letter may accidentally strengthen claims beyond the evidence.",
            (
                f"Use the do-not-claim guardrail with {claim_pack['summary']['not_claim_row_count']} prohibited-claim categories and rerun front-matter claim audit after response edits."
            ),
            "materials/WHAT_THIS_PAPER_DOES_NOT_CLAIM.md; materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.md; materials/CLAIM_BOUNDARY_COMMUNICATION_PACK.json",
            "Response wording must remain inside the same simulator-only and diagnostic-boundary rules as the manuscript.",
            "After drafting responses, rerun claim QA and editorial front-matter claim audit.",
            "ready",
        ),
        response_row(
            "RQ12_quick_review_route",
            "reviewer_navigation",
            "Reviewers may not know which files to inspect first.",
            (
                "Start with the quick-look packet and evidence trace, then drill down to source data and seed ledgers."
            ),
            "materials/REVIEWER_QUICKLOOK_PACKET.md; materials/REVIEWER_EVIDENCE_TRACE_PACK.md; materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
            "Navigation aids are not evidence themselves; source data and registered reports remain authoritative.",
            "Use these routes in cover-letter or response text only if the journal permits reviewer-support attachments.",
            "ready",
        ),
    ]

    enriched = []
    missing = []
    for item in rows:
        ok, paths = exists_all(root, item["evidence"])
        enriched.append({**item, "evidence_complete": ok, "evidence_paths": paths})
        if not ok:
            missing.append(item["id"])

    status_counts = {}
    for item in enriched:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1

    return {
        "root": str(root),
        "title": "Reviewer Response Seed Pack",
        "purpose": (
            "Provide journal-neutral seed text for likely editor and reviewer critiques, with direct evidence routes "
            "and explicit claim boundaries."
        ),
        "summary": {
            "status": "pass" if not missing else "review_required",
            "row_count": len(enriched),
            "evidence_incomplete_count": len(missing),
            "status_counts": status_counts,
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": provenance_ratio,
            "risk_response_rows": risk["summary"]["row_count"],
            "external_validity_selector": external_summary.get("expanded_or_later_selector"),
            "external_validity_oracle": external_summary.get("expanded_or_later_oracle"),
        },
        "rows": enriched,
        "interpretation": (
            "These are response seeds, not final author-certified rebuttal text. Authors should adapt tone, add manuscript "
            "line references after revision, and avoid strengthening claims beyond the listed boundaries."
        ),
    }


def write_csv(report, path):
    fields = [
        "id",
        "phase",
        "likely_critique",
        "response_seed",
        "evidence",
        "claim_boundary",
        "escalation_or_revision_action",
        "status",
        "evidence_complete",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# Reviewer Response Seed Pack",
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
            "## Response Seeds",
            "",
            "| id | phase | status | likely critique | response seed | evidence | boundary | action |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['id']} | {row['phase']} | {row['status']} | {row['likely_critique']} | "
            f"{row['response_seed']} | `{row['evidence']}` | {row['claim_boundary']} | "
            f"{row['escalation_or_revision_action']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export journal-neutral reviewer response seed pack.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "REVIEWER_RESPONSE_SEED_PACK.json"
    out_md = materials / "REVIEWER_RESPONSE_SEED_PACK.md"
    out_csv = materials / "REVIEWER_RESPONSE_SEED_PACK.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
