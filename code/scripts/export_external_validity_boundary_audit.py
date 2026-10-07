#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ratio(count, n):
    return f"{count}/{n}"


def build_audit(root):
    synthesis = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")
    supplement = load_json(root / "tables" / "cross_heldout_statistical_supplement.json")
    heldout3 = load_json(root / "tables" / "heldout3_external_validation.json")
    heldout3_expansion = load_json(root / "tables" / "heldout3_candidate_expansion.json")
    heldout4 = load_json(root / "tables" / "heldout4_external_validation.json")
    heldout4_atlas = load_json(root / "tables" / "heldout4_failure_atlas.json")
    learned = load_json(root / "tables" / "learned_selector_report.json")
    claim_matrix = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")

    stage_rows = {
        (row["heldout"], row["stage"]): row for row in synthesis["entries"]
    }

    stages = [
        {
            "id": "heldout1_expanded",
            "validation_role": "positive held-out batch",
            "selector_result": ratio(stage_rows[("heldout1", "six_candidate_expanded")]["selector_pass_count"], stage_rows[("heldout1", "six_candidate_expanded")]["n"]),
            "oracle_result": ratio(stage_rows[("heldout1", "six_candidate_expanded")]["oracle_pass_count"], stage_rows[("heldout1", "six_candidate_expanded")]["n"]),
            "selector_oracle_gap": stage_rows[("heldout1", "six_candidate_expanded")]["oracle_pass_count"] - stage_rows[("heldout1", "six_candidate_expanded")]["selector_pass_count"],
            "evidence_strength": "supportive but small-n",
            "allowed_interpretation": "The expanded online selector can solve the first disjoint held-out batch under the saved strict validator.",
            "prohibited_interpretation": "Do not describe this as broad robustness because later held-out batches contradict that reading.",
            "primary_evidence": "tables/expanded_selector_generalization.md; tables/heldout_generalization.md",
            "next_validation": "Report with heldout2-4 rather than in isolation.",
        },
        {
            "id": "heldout2_expanded",
            "validation_role": "second held-out stress batch",
            "selector_result": ratio(stage_rows[("heldout2", "six_candidate_expanded")]["selector_pass_count"], stage_rows[("heldout2", "six_candidate_expanded")]["n"]),
            "oracle_result": ratio(stage_rows[("heldout2", "six_candidate_expanded")]["oracle_pass_count"], stage_rows[("heldout2", "six_candidate_expanded")]["n"]),
            "selector_oracle_gap": stage_rows[("heldout2", "six_candidate_expanded")]["oracle_pass_count"] - stage_rows[("heldout2", "six_candidate_expanded")]["selector_pass_count"],
            "evidence_strength": "stress-test boundary",
            "allowed_interpretation": "Candidate expansion improves heldout2 coverage, but online simulator-loop selection still misses seeds where a passing candidate exists.",
            "prohibited_interpretation": "Do not present candidate-oracle gains as online selector gains.",
            "primary_evidence": "tables/heldout2_candidate_expansion.md; tables/expanded_selector_generalization.md",
            "next_validation": "Reduce selector misses on seeds 103, 109, and 113 without reducing heldout1.",
        },
        {
            "id": "heldout3_external",
            "validation_role": "negative external validation",
            "selector_result": ratio(heldout3["expanded_selector"]["pass_count"], heldout3["expanded_selector"]["n"]),
            "oracle_result": ratio(heldout3["oracle"]["pass_count"], heldout3["oracle"]["n"]),
            "selector_oracle_gap": heldout3["oracle"]["pass_count"] - heldout3["expanded_selector"]["pass_count"],
            "evidence_strength": "external boundary",
            "allowed_interpretation": "Heldout3 exposes a sharp generalization boundary for both hand-scored and learned selectors.",
            "prohibited_interpretation": "Do not use heldout2 learned-selector improvement as evidence of external robustness.",
            "primary_evidence": "tables/heldout3_external_validation.md; tables/learned_selector_report.md",
            "next_validation": "Treat heldout3-targeted repair as diagnostic repair work, then evaluate on a fresh external batch.",
        },
        {
            "id": "heldout3_targeted_repair",
            "validation_role": "targeted diagnostic repair",
            "selector_result": ratio(stage_rows[("heldout3", "seven_candidate_targeted")]["selector_pass_count"], stage_rows[("heldout3", "seven_candidate_targeted")]["n"]),
            "oracle_result": ratio(heldout3_expansion["expanded_oracle"]["pass_count"], heldout3_expansion["expanded_oracle"]["n"]),
            "selector_oracle_gap": heldout3_expansion["expanded_oracle"]["pass_count"] - stage_rows[("heldout3", "seven_candidate_targeted")]["selector_pass_count"],
            "evidence_strength": "targeted diagnostic only",
            "allowed_interpretation": "Targeted repair closes heldout3 candidate coverage gaps in the oracle pool.",
            "prohibited_interpretation": "Do not present this as external validation because the repair was targeted to heldout3 failures.",
            "primary_evidence": "tables/heldout3_candidate_expansion.md; tables/heldout3_targeted_selector_generalization.md",
            "next_validation": "Freeze changes and test on heldout4 or a later unused held-out batch.",
        },
        {
            "id": "heldout4_post_repair",
            "validation_role": "post-repair external validation",
            "selector_result": ratio(heldout4["selector"]["pass_count"], heldout4["selector"]["n"]),
            "oracle_result": ratio(heldout4["oracle"]["pass_count"], heldout4["oracle"]["n"]),
            "selector_oracle_gap": heldout4["oracle"]["pass_count"] - heldout4["selector"]["pass_count"],
            "evidence_strength": "partial transfer",
            "allowed_interpretation": "Heldout4 shows partial transfer after targeted repair and separates selector misses from candidate-policy gaps.",
            "prohibited_interpretation": "Do not present heldout4 as solved generalization or broad robustness.",
            "primary_evidence": "tables/heldout4_external_validation.md; tables/heldout4_failure_atlas.md",
            "next_validation": "Use heldout5 or larger-N sweeps after freezing the next selector/candidate design.",
        },
    ]

    claims = [
        {
            "id": "online_selector_boundary",
            "evidence": " ; ".join(row["primary_evidence"] for row in stages),
            "allowed_wording": "online simulator-loop selector remains limited by selector misses and candidate gaps",
            "must_not_claim": "robust deployed overtaking policy",
            "reason": "Selector pass rates vary from 10/10 on heldout1 to 4/10 on heldout3 and 6/10 on heldout4.",
        },
        {
            "id": "oracle_boundary",
            "evidence": "tables/cross_heldout_validation_synthesis.md; tables/seed_outcome_ledger.md",
            "allowed_wording": "oracle results are diagnostic upper bounds over saved candidates",
            "must_not_claim": "oracle portfolio is an online selector output",
            "reason": "Oracle choices use full-rollout outcomes and cannot be selected at decision time.",
        },
        {
            "id": "targeted_repair_boundary",
            "evidence": "tables/heldout3_candidate_expansion.md; tables/heldout4_external_validation.md",
            "allowed_wording": "heldout3-targeted repair improves candidate coverage and heldout4 shows partial transfer",
            "must_not_claim": "targeted repair proves external robustness",
            "reason": "Heldout3 repair was informed by heldout3 failures, while heldout4 retains selector and candidate-policy gaps.",
        },
    ]

    aggregate = synthesis["aggregate_expanded_or_later"]
    learned_primary = learned["variants"][learned["primary_variant"]]
    summary = {
        "stage_count": len(stages),
        "claim_boundary_count": len(claims),
        "expanded_or_later_selector": ratio(aggregate["selector_pass_count"], aggregate["n"]),
        "expanded_or_later_oracle": ratio(aggregate["oracle_pass_count"], aggregate["n"]),
        "expanded_or_later_selector_oracle_gap": aggregate["selector_oracle_gap"],
        "learned_selector_heldout2": ratio(learned_primary["test"]["pass_count"], learned_primary["test"]["n"]),
        "learned_selector_heldout3": ratio(learned_primary["external_heldout3"]["pass_count"], learned_primary["external_heldout3"]["n"]),
        "heldout4_selector_miss_seeds": heldout4["selector"]["selector_miss_seeds"],
        "heldout4_candidate_gap_seeds": heldout4["oracle"]["candidate_gap_seeds"],
        "publication_verification_status": verification["summary"]["status"],
        "artifact_provenance": verification["summary"]["artifact_provenance"],
    }

    return {
        "root": str(root),
        "title": "External validity boundary audit",
        "purpose": (
            "Summarize what the held-out evidence can and cannot support, with explicit separation between "
            "online simulator-loop selector results, diagnostic oracle upper bounds, targeted repair, and external validation."
        ),
        "summary": summary,
        "stages": stages,
        "claim_boundaries": claims,
        "statistical_context": {
            "source": "tables/cross_heldout_statistical_supplement.json",
            "rows": supplement["stage_statistics"],
            "interpretation": "Intervals and tests are descriptive because each held-out batch has small n=10 seed samples.",
        },
        "linked_claim_matrix_ids": [row["id"] for row in claim_matrix["claims"] if row["claim_type"] in {"generalization_boundary", "oracle_upper_bound", "innovation_with_limitation"}],
        "interpretation": (
            "The evidence supports a reproducible method-development package with useful online portfolio selection, "
            "not a broad robustness claim. Heldout3 and heldout4 are retained as negative and partial-transfer "
            "evidence so that future manuscript wording cannot average away external-validation boundaries."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "id",
            "validation_role",
            "selector_result",
            "oracle_result",
            "selector_oracle_gap",
            "evidence_strength",
            "allowed_interpretation",
            "prohibited_interpretation",
            "primary_evidence",
            "next_validation",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["stages"]:
            writer.writerow(row)


def write_markdown(report, path):
    lines = [
        "# External Validity Boundary Audit",
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
            "## Held-out Evidence Boundaries",
            "",
            "| stage | role | selector | oracle | gap | evidence strength | allowed interpretation | prohibited interpretation | evidence | next validation |",
            "|---|---|---:|---:|---:|---|---|---|---|---|",
        ]
    )
    for row in report["stages"]:
        lines.append(
            f"| {row['id']} | {row['validation_role']} | {row['selector_result']} | {row['oracle_result']} | "
            f"{row['selector_oracle_gap']} | {row['evidence_strength']} | {row['allowed_interpretation']} | "
            f"{row['prohibited_interpretation']} | `{row['primary_evidence']}` | {row['next_validation']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundaries",
            "",
            "| id | allowed wording | must not claim | reason | evidence |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["claim_boundaries"]:
        lines.append(
            f"| {row['id']} | {row['allowed_wording']} | {row['must_not_claim']} | {row['reason']} | `{row['evidence']}` |"
        )
    lines.extend(
        [
            "",
            "## Statistical Context",
            "",
            f"- Source: `{report['statistical_context']['source']}`",
            f"- Interpretation: {report['statistical_context']['interpretation']}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export external-validity boundary audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_audit(root)
    out_json = materials / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json"
    out_md = materials / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md"
    out_csv = materials / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
