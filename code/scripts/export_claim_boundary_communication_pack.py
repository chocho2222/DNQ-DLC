#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_status(root, paths):
    checked = []
    for rel in paths:
        if "*" in rel:
            matches = list(root.glob(rel))
            checked.append({"path": rel, "exists": bool(matches), "matched_count": len(matches)})
        else:
            path = root / rel
            checked.append({"path": rel, "exists": path.exists(), "matched_count": 1 if path.exists() else 0})
    return checked


def theme_for_claim(claim):
    text = f"{claim['claim_type']} {claim['do_not_claim']}".lower()
    if "oracle" in text:
        return "diagnostic_oracle_boundary"
    if "robust" in text or "generaliz" in text:
        return "generalization_boundary"
    if "selector" in text:
        return "selector_boundary"
    if "baseline" in text:
        return "baseline_boundary"
    if "submission" in text or "reproduc" in text:
        return "package_boundary"
    return "claim_scope_boundary"


def boundary_reason(claim):
    claim_type = claim["claim_type"]
    reasons = {
        "oracle_upper_bound": "The oracle uses full-rollout outcomes and is retained only as a diagnostic upper bound.",
        "negative_generalization_result": "The saved held-out evidence exposes failures that bound the claim.",
        "diagnostic_negative_result": "The result is a negative diagnostic and cannot be reframed as a solved component.",
        "candidate_policy_progress": "The evidence improves candidate coverage but does not prove online selector success.",
        "online_simulator_loop_selector_progress_with_limitation": "The online simulator-loop selector improves on a bounded seed set while remaining below oracle coverage.",
        "external_validation_negative_result": "The external validation batch is adverse evidence and limits transfer claims.",
        "targeted_candidate_repair_with_limitation": "The repair reuses heldout3 diagnostically and is not external validation.",
        "external_validation_after_targeted_repair": "Heldout4 supports post-repair external validation with partial transfer only.",
        "cross_heldout_synthesis_with_limitation": "The aggregate is bounded by visible heldout3/heldout4 failures.",
        "reproducibility": "Local package integrity is separate from author-certified submission and public deposition.",
    }
    return reasons.get(claim_type, "The replacement wording is limited to the saved simulator evidence and listed limitations.")


def build_report(root):
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    frontmatter = load_json(root / "materials" / "EDITORIAL_FRONTMATTER_CLAIM_AUDIT.json")
    manuscript_qa = load_json(root / "materials" / "MANUSCRIPT_CLAIM_QA.json")
    external_validity = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    negative_register = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")

    downgrade_rows = []
    for claim in claims["claims"]:
        checked = evidence_status(root, claim["primary_evidence"] + claim["limitations"])
        missing = [item for item in checked if not item["exists"]]
        downgrade_rows.append(
            {
                "id": claim["id"],
                "theme": theme_for_claim(claim),
                "claim_type": claim["claim_type"],
                "unsupported_or_risky_wording": claim["do_not_claim"],
                "publication_safe_replacement": claim["claim"],
                "allowed_label": claim["allowed_wording"],
                "evidence": "; ".join(claim["primary_evidence"]),
                "limitations": "; ".join(claim["limitations"]),
                "boundary_reason": boundary_reason(claim),
                "evidence_complete": not missing,
                "missing_evidence_count": len(missing),
            }
        )

    not_claim_rows = [
        {
            "id": "NC1",
            "theme": "real_world_scope",
            "not_claim": "Do not claim public-road readiness, real-road deployment, perception robustness, or safety certification.",
            "safe_alternative": "Frame the work as simulator-only method evaluation with explicit sim-to-real limitations.",
            "evidence_boundary": "No real sensor, public-road, vehicle hardware, or safety-certification evidence is present.",
            "supporting_files": "materials/SIMULATION_TO_REAL_APPLICABILITY.md; materials/RESEARCH_RISK_AND_SAFETY.md",
        },
        {
            "id": "NC2",
            "theme": "oracle_scope",
            "not_claim": "Do not present oracle portfolios as controllers or online selector outputs.",
            "safe_alternative": "Call them diagnostic upper bounds used to separate candidate-policy coverage from selector errors.",
            "evidence_boundary": "Oracle rows use full-rollout outcomes unavailable to an online controller.",
            "supporting_files": "materials/CLAIM_EVIDENCE_MATRIX.md; tables/seed_outcome_ledger.md",
        },
        {
            "id": "NC3",
            "theme": "external_validation_scope",
            "not_claim": "Do not treat heldout3 targeted repair as external validation.",
            "safe_alternative": "Describe heldout3 targeted repair as diagnostic reuse and keep heldout4 as post-repair external validation with partial transfer.",
            "evidence_boundary": "Heldout3 informed targeted repair; heldout4 was unused until after the repair.",
            "supporting_files": "tables/heldout3_candidate_expansion.md; tables/heldout4_external_validation.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
        },
        {
            "id": "NC4",
            "theme": "robustness_scope",
            "not_claim": "Do not claim broad robustness, distributional robustness, or solved generalization.",
            "safe_alternative": "Report bounded simulator held-out results and visible selector/candidate gaps.",
            "evidence_boundary": "Cross-heldout synthesis retains heldout3/heldout4 failures and small seed batches.",
            "supporting_files": "tables/cross_heldout_validation_synthesis.md; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
        },
        {
            "id": "NC5",
            "theme": "baseline_scope",
            "not_claim": "Do not claim the learned graph method uniformly dominates the strongest locked baseline.",
            "safe_alternative": "Report baseline-preserved comparisons and portfolio complementarity.",
            "evidence_boundary": "The locked strict protocol retains a strong rule-based baseline result.",
            "supporting_files": "tables/full_statistical_report.md; materials/BASELINE_FAIRNESS_AUDIT.md",
        },
        {
            "id": "NC6",
            "theme": "submission_scope",
            "not_claim": "Do not claim journal submission, author disclosures, or public archive deposition are complete.",
            "safe_alternative": "State that local evidence packaging passes while author-owned metadata and external identifiers remain pending.",
            "evidence_boundary": "Author names, ORCID/contact details, disclosures, target-journal fields, and DOI/accession are author-owned.",
            "supporting_files": "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.md; materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.md",
        },
    ]

    missing_downgrade = [row for row in downgrade_rows if not row["evidence_complete"]]
    required_support = []
    for row in not_claim_rows:
        required_support.extend([part.strip() for part in row["supporting_files"].split(";")])
    missing_not_claim = [path for path in required_support if not (root / path).exists()]

    summary = {
        "status": "pass" if not missing_downgrade and not missing_not_claim else "review_required",
        "downgrade_row_count": len(downgrade_rows),
        "not_claim_row_count": len(not_claim_rows),
        "missing_downgrade_evidence_count": len(missing_downgrade),
        "missing_not_claim_support_count": len(missing_not_claim),
        "frontmatter_claim_audit_status": frontmatter["summary"]["status"],
        "frontmatter_blocker_count": frontmatter["summary"]["blocker_count"],
        "manuscript_claim_qa_status": manuscript_qa["summary"]["status"],
        "external_validity_status": external_validity["summary"].get("status", "available"),
        "negative_register_status": negative_register["summary"].get("status", "available"),
    }

    return {
        "root": str(root),
        "title": "Claim Boundary Communication Pack",
        "purpose": (
            "Provide editor- and reviewer-facing wording controls that downgrade risky claims to the exact "
            "strength supported by saved simulator evidence."
        ),
        "summary": summary,
        "downgrade_rows": downgrade_rows,
        "not_claim_rows": not_claim_rows,
        "interpretation": (
            "This pack is a communication guardrail. It does not add empirical results and should be rerun "
            "after edits to the manuscript, abstract, highlights, cover letter, or response drafts."
        ),
    }


def write_csv(rows, path, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_downgrade_md(report, path):
    lines = [
        "# Claim Downgrade Map",
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
            "## Downgrade Rows",
            "",
            "| id | theme | risky wording | safe replacement | boundary reason | evidence complete |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["downgrade_rows"]:
        lines.append(
            f"| {row['id']} | {row['theme']} | {row['unsupported_or_risky_wording']} | "
            f"{row['publication_safe_replacement']} | {row['boundary_reason']} | {row['evidence_complete']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_not_claim_md(report, path):
    lines = [
        "# What This Paper Does Not Claim",
        "",
        "This one-page guardrail lists claims that should stay out of the manuscript, abstract, highlights, "
        "cover letter, response letters, and submission portal fields unless new evidence is generated.",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Do-Not-Claim Rows",
            "",
            "| id | theme | not claim | safe alternative | evidence boundary | supporting files |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["not_claim_rows"]:
        lines.append(
            f"| {row['id']} | {row['theme']} | {row['not_claim']} | {row['safe_alternative']} | "
            f"{row['evidence_boundary']} | `{row['supporting_files']}` |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export editor-facing claim-boundary communication materials.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)

    out_json = materials / "CLAIM_BOUNDARY_COMMUNICATION_PACK.json"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    downgrade_md = materials / "CLAIM_DOWNGRADE_MAP.md"
    downgrade_csv = materials / "CLAIM_DOWNGRADE_MAP.csv"
    not_claim_md = materials / "WHAT_THIS_PAPER_DOES_NOT_CLAIM.md"
    not_claim_csv = materials / "WHAT_THIS_PAPER_DOES_NOT_CLAIM.csv"

    write_downgrade_md(report, downgrade_md)
    write_not_claim_md(report, not_claim_md)
    write_csv(
        report["downgrade_rows"],
        downgrade_csv,
        [
            "id",
            "theme",
            "claim_type",
            "unsupported_or_risky_wording",
            "publication_safe_replacement",
            "allowed_label",
            "evidence",
            "limitations",
            "boundary_reason",
            "evidence_complete",
            "missing_evidence_count",
        ],
    )
    write_csv(
        report["not_claim_rows"],
        not_claim_csv,
        ["id", "theme", "not_claim", "safe_alternative", "evidence_boundary", "supporting_files"],
    )
    print(
        json.dumps(
            {
                "json": str(out_json),
                "claim_downgrade_map": str(downgrade_md),
                "claim_downgrade_csv": str(downgrade_csv),
                "what_not_claim": str(not_claim_md),
                "what_not_claim_csv": str(not_claim_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
