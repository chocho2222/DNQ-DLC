#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_statement(root):
    manifest = load_json(root / "manifest.json")
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    gap_plan = load_json(root / "materials" / "SUBMISSION_GAP_ACTION_PLAN.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    fair = load_json(root / "materials" / "FAIR_ARCHIVE_METADATA.json")

    prohibited = []
    for claim in claims["claims"]:
        text = claim.get("do_not_claim")
        if text and text not in prohibited:
            prohibited.append(text)

    high_priority_actions = [
        action
        for action in gap_plan["actions"]
        if action.get("priority") in {"P0", "P1"}
    ]

    risk_items = [
        {
            "id": "simulation_only",
            "category": "deployment_boundary",
            "risk": "Readers may mistake the simulator package for road-vehicle deployment evidence.",
            "mitigation": "State explicitly that all evidence is simulation-only and non-VLM; no real-vehicle, human-subject, or public-road deployment is included.",
            "evidence": "manifest.json; materials/CLAIM_EVIDENCE_MATRIX.md",
            "status": "controlled_by_wording",
        },
        {
            "id": "oracle_misinterpretation",
            "category": "method_boundary",
            "risk": "Diagnostic oracle portfolios may be misread as online selector outputs.",
            "mitigation": "Report oracle results only as upper bounds and separate them from online selector results in every claim.",
            "evidence": "materials/CLAIM_EVIDENCE_MATRIX.md; materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "status": "controlled_by_claim_qa",
        },
        {
            "id": "overgeneralization",
            "category": "evidence_boundary",
            "risk": "Held-out seed results may be overgeneralized into broad robustness claims.",
            "mitigation": "Use heldout3/heldout4 and cross-heldout summaries as bounded validation evidence; preserve selector misses and candidate gaps.",
            "evidence": "tables/cross_heldout_validation_synthesis.md; tables/seed_outcome_ledger.md",
            "status": "controlled_by_reporting_boundary",
        },
        {
            "id": "cherry_picked_visuals",
            "category": "evidence_boundary",
            "risk": "GIFs could be treated as stronger evidence than strict full-lap validation tables.",
            "mitigation": "Use GIFs only as qualitative evidence; make strict pass/fail tables, source data, and seed ledgers the primary evidence.",
            "evidence": "materials/REPRODUCTION_GUIDE.md; materials/DATA_DICTIONARY.md",
            "status": "controlled_by_evidence_hierarchy",
        },
        {
            "id": "compute_reproducibility",
            "category": "reproducibility_boundary",
            "risk": "A reviewer may not be able to rerun expensive rollouts exactly on different hardware.",
            "mitigation": "Archive fast audit paths, environment records, GPU inventory, logs, checksums, and expensive rollout commands separately.",
            "evidence": "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md; tables/artifact_provenance.md",
            "status": "controlled_by_reproduction_materials",
        },
        {
            "id": "archive_access",
            "category": "availability_boundary",
            "risk": "The local package is not yet a public archived dataset with DOI/accession.",
            "mitigation": "Treat FAIR status as partial until an external archive URL or DOI is assigned.",
            "evidence": "materials/FAIR_ARCHIVE_METADATA.md; materials/RELEASE_ARCHIVE_MANIFEST.md",
            "status": "pending_external_archive",
        },
    ]

    return {
        "root": str(root),
        "title": "Research risk and safety statement for the multi-car overtaking package",
        "scope": {
            "task": manifest["scope"]["task"],
            "excluded": manifest["scope"]["excluded"],
            "validator": manifest["scope"]["validator"],
            "oracle_policy": manifest["reporting_boundary"]["oracle_policy"],
            "main_limitation": manifest["reporting_boundary"]["main_limitation"],
        },
        "ethics_context": {
            "human_subjects": "not_applicable",
            "animal_subjects": "not_applicable",
            "real_vehicle_testing": "not_included",
            "public_road_testing": "not_included",
            "personal_data": "not_included",
            "rationale": (
                "The current package contains simulator rollouts, generated telemetry, trained checkpoints, "
                "figures, and reproducibility materials. It does not include human-subject data, animal data, "
                "personal data, real-vehicle trials, or public-road deployment."
            ),
        },
        "risk_items": risk_items,
        "prohibited_claims": prohibited,
        "required_submission_wording": [
            "All reported driving evidence is from simulation.",
            "Oracle portfolios are diagnostic upper bounds, not online selector outputs.",
            "Heldout3 targeted repair is a targeted diagnostic, not external validation.",
            "Heldout4 is post-repair external validation with partial transfer.",
            "GIFs are qualitative illustrations and do not replace strict full-lap pass/fail tables.",
            "The local package still requires an external DOI or accession before public submission.",
        ],
        "remaining_high_priority_actions": [
            {
                "id": action["id"],
                "priority": action["priority"],
                "gap": action.get("gap", action["id"]),
                "problem": action.get("problem", ""),
                "acceptance_criteria": action["acceptance_criteria"],
            }
            for action in high_priority_actions
        ],
        "verification_snapshot": verification["summary"],
        "fair_snapshot": {
            "release_status": fair["identifier"]["status"],
            "external_doi": fair["identifier"]["external_doi"],
            "external_url": fair["identifier"]["external_url"],
            "external_archive_pending": fair["availability"]["external_archive_pending"],
        },
        "interpretation": (
            "This statement is a manuscript- and reviewer-facing risk boundary document. It supports careful "
            "reporting of the saved simulator evidence but does not certify deployment readiness."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "category", "risk", "mitigation", "evidence", "status"],
        )
        writer.writeheader()
        for row in report["risk_items"]:
            writer.writerow(row)


def write_markdown(report, path):
    scope = report["scope"]
    ethics = report["ethics_context"]
    lines = [
        "# Research Risk And Safety Statement",
        "",
        report["interpretation"],
        "",
        "## Scope",
        "",
        f"- Task: {scope['task']}",
        f"- Excluded: {scope['excluded']}",
        f"- Validator: {scope['validator']}",
        f"- Oracle policy: {scope['oracle_policy']}",
        f"- Main limitation: {scope['main_limitation']}",
        "",
        "## Ethics Context",
        "",
        f"- Human subjects: `{ethics['human_subjects']}`",
        f"- Animal subjects: `{ethics['animal_subjects']}`",
        f"- Real-vehicle testing: `{ethics['real_vehicle_testing']}`",
        f"- Public-road testing: `{ethics['public_road_testing']}`",
        f"- Personal data: `{ethics['personal_data']}`",
        "",
        ethics["rationale"],
        "",
        "## Risk Register",
        "",
        "| id | category | status | risk | mitigation | evidence |",
        "|---|---|---|---|---|---|",
    ]
    for row in report["risk_items"]:
        lines.append(
            f"| {row['id']} | {row['category']} | {row['status']} | {row['risk']} | {row['mitigation']} | `{row['evidence']}` |"
        )
    lines.extend(
        [
            "",
            "## Required Submission Wording",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["required_submission_wording"])
    lines.extend(
        [
            "",
            "## Prohibited Claims",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["prohibited_claims"])
    lines.extend(
        [
            "",
            "## Remaining High-priority Actions",
            "",
        ]
    )
    for item in report["remaining_high_priority_actions"]:
        lines.extend(
            [
                f"### {item['id']} ({item['priority']})",
                "",
                f"- Gap: {item['gap']}",
                f"- Problem: {item['problem']}",
                "- Acceptance criteria:",
            ]
        )
        lines.extend(f"  - {criterion}" for criterion in item["acceptance_criteria"])
        lines.append("")
    lines.extend(
        [
            "## Verification Snapshot",
            "",
            f"- Publication package verification: `{report['verification_snapshot']['status']}`",
            f"- Failed gates: {report['verification_snapshot']['failed_gates']}",
            f"- Artifact provenance: {report['verification_snapshot']['artifact_provenance']}",
            f"- External archive pending: `{report['fair_snapshot']['external_archive_pending']}`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export research risk and safety statement.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_statement(root)
    out_json = materials / "RESEARCH_RISK_AND_SAFETY.json"
    out_md = materials / "RESEARCH_RISK_AND_SAFETY.md"
    out_csv = materials / "RESEARCH_RISK_AND_SAFETY.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
