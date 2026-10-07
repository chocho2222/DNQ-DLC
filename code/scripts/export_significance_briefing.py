#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_briefing(root):
    outline = load_json(root / "materials" / "MANUSCRIPT_OUTLINE.json")
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    summary = load_json(root / "materials" / "PUBLICATION_PACKAGE_SUMMARY.json")
    reporting = load_json(root / "materials" / "TOP_JOURNAL_REPORTING_SUMMARY.json")
    editorial = load_json(root / "materials" / "EDITORIAL_SUBMISSION_CHECKLIST.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")

    claim_rows = claims["claims"]
    allowed = {row["id"]: row for row in claim_rows}
    main = summary["main_results"]

    significance_points = [
        {
            "id": "strict_full_lap_focus",
            "statement": (
                "The package shifts the evidence standard from short visual demonstrations to strict full-lap "
                "multi-car validation with completion, rank, first-ahead, grass-rate, and traffic-quality criteria."
            ),
            "evidence": "materials/METHODS.md; materials/STATISTICAL_ANALYSIS_PLAN.md; figures/figure_1_multicar_overtake_results.*",
            "boundary": "Frame as an evaluation and reproducibility contribution, not as road-deployment evidence.",
        },
        {
            "id": "baseline_preservation",
            "statement": (
                f"The strongest locked single controller remains the rule overtake baseline at {main['locked_rule_overtake']}, "
                f"while graph-adaptive shielding reaches {main['locked_graph_adaptive']}; this makes the comparison conservative."
            ),
            "evidence": allowed["C1_locked_baseline_strength"]["primary_evidence"],
            "boundary": allowed["C1_locked_baseline_strength"]["do_not_claim"],
        },
        {
            "id": "portfolio_complementarity",
            "statement": (
                "Seed-level complementarity motivates online portfolio selection, but oracle portfolios are kept as diagnostic upper bounds."
            ),
            "evidence": allowed["C2_oracle_complementarity"]["primary_evidence"],
            "boundary": allowed["C2_oracle_complementarity"]["do_not_claim"],
        },
        {
            "id": "heldout_positive_and_boundary",
            "statement": (
                f"The online selector reaches {main['heldout1_expanded_selector']} on heldout1 and improves heldout2 to "
                f"{main['heldout2_expanded_selector']} after candidate expansion, but remains below the heldout2 expanded oracle."
            ),
            "evidence": allowed["C10_expanded_selector_progress"]["primary_evidence"],
            "boundary": allowed["C10_expanded_selector_progress"]["do_not_claim"],
        },
        {
            "id": "external_validation_boundary",
            "statement": (
                f"Heldout3 and heldout4 prevent overstatement: heldout3 selector performance is {main['heldout3_expanded_selector']} "
                f"against an {main['heldout3_candidate_oracle']} oracle, and heldout4 selector performance is {main['heldout4_selector']} "
                f"against an {main['heldout4_oracle']} oracle."
            ),
            "evidence": "tables/heldout3_external_validation.md; tables/heldout4_external_validation.md; figures/figure_3_cross_heldout_validation.*",
            "boundary": "Report heldout3 as negative external validation and heldout4 as partial transfer after targeted repair.",
        },
        {
            "id": "reproducible_package",
            "statement": (
                f"The local evidence package has complete artifact provenance ({verification['summary']['artifact_provenance']}), "
                "zero missing/weak reproducibility-audit items, source-data tables, figure exports, logs, and script snapshots."
            ),
            "evidence": allowed["C17_reproducible_package"]["primary_evidence"],
            "boundary": allowed["C17_reproducible_package"]["do_not_claim"],
        },
    ]

    cover_letter_material = {
        "one_sentence_pitch": (
            "We provide a strict, reproducible full-lap multi-car overtaking evaluation package showing that online "
            "portfolio probing can exploit controller complementarity, while disjoint held-out validation exposes the "
            "remaining selector and candidate-policy gaps."
        ),
        "suggested_opening": (
            "This manuscript addresses a common weakness in autonomous overtaking reports: visually convincing short "
            "rollouts can hide failures in lap completion, final rank, off-track behavior, and traffic quality. We "
            "therefore build a strict non-VLM full-lap evaluation package with preserved rule baselines, learned and "
            "shielded candidates, online portfolio selection, and evidence-linked reproducibility materials."
        ),
        "editor_interest": [
            "Strict full-lap multi-car validation replaces selected visual demonstrations as the primary evidence standard.",
            "Strong rule baselines are preserved, so learned and shielded methods are judged against a hard comparator.",
            "Positive selector results are reported together with negative held-out evidence and seed-level failure decomposition.",
            "The package includes source data, artifact provenance, claim guardrails, reporting summaries, and archive metadata.",
        ],
        "must_not_say": [
            "Do not present oracle portfolios as online selector outputs.",
            "Do not present heldout3-targeted repair as external validation.",
            "Do not present heldout4 partial transfer as solved generalization.",
            "Do not imply real-world deployment readiness.",
            "Do not imply that author disclosures, funding, or final submission metadata are complete.",
        ],
    }

    return {
        "root": str(root),
        "title": "Evidence-bound significance and cover-letter briefing",
        "recommended_title": outline["recommended_title"],
        "purpose": (
            "Provide editor-facing significance material while keeping novelty claims constrained by saved evidence, "
            "external-validation boundaries, and submission limitations."
        ),
        "significance_points": significance_points,
        "cover_letter_material": cover_letter_material,
        "reporting_snapshot": reporting["summary"],
        "editorial_snapshot": editorial["summary"],
        "verification_snapshot": verification["summary"],
        "interpretation": (
            "This briefing is source material for a cover letter or editor-facing significance statement. It is not a "
            "final cover letter because journal target, author contributions, competing interests, funding, and "
            "correspondence metadata require author input."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "statement", "evidence", "boundary"])
        writer.writeheader()
        for row in report["significance_points"]:
            writer.writerow(row)


def write_markdown(report, path):
    cover = report["cover_letter_material"]
    lines = [
        "# Evidence-bound Significance Briefing",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Suggested Positioning",
        "",
        f"- Recommended title: {report['recommended_title']}",
        f"- One-sentence pitch: {cover['one_sentence_pitch']}",
        "",
        "Suggested opening:",
        "",
        cover["suggested_opening"],
        "",
        "## Editor Interest",
        "",
    ]
    lines.extend(f"- {item}" for item in cover["editor_interest"])
    lines.extend(
        [
            "",
            "## Significance Points",
            "",
            "| id | statement | evidence | boundary |",
            "|---|---|---|---|",
        ]
    )
    for row in report["significance_points"]:
        lines.append(f"| {row['id']} | {row['statement']} | `{row['evidence']}` | {row['boundary']} |")
    lines.extend(
        [
            "",
            "## Must Not Say",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in cover["must_not_say"])
    lines.extend(
        [
            "",
            "## Snapshots",
            "",
            f"- Publication verification: `{report['verification_snapshot']['status']}`",
            f"- Artifact provenance: {report['verification_snapshot']['artifact_provenance']}",
            f"- Reporting summary status counts: {report['reporting_snapshot']['status_counts']}",
            f"- Editorial checklist status counts: {report['editorial_snapshot']['status_counts']}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export evidence-bound significance and cover-letter briefing.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_briefing(root)
    out_json = materials / "SIGNIFICANCE_BRIEFING.json"
    out_md = materials / "SIGNIFICANCE_BRIEFING.md"
    out_csv = materials / "SIGNIFICANCE_BRIEFING.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
