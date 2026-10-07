#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_statement(root):
    manifest = load_json(root / "manifest.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    external = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")
    sample = load_json(root / "materials" / "SAMPLE_SIZE_SENSITIVITY_BRIEF.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    sample_summary = dict(sample["summary"])
    sample_summary["publication_verification_status"] = verification["summary"]["status"]
    sample_summary["artifact_provenance"] = verification["summary"]["artifact_provenance"]

    dimensions = [
        {
            "id": "simulator_scope",
            "dimension": "environment",
            "current_evidence": "Saved rollouts are from the local multi-car racing simulator under strict full-lap validation.",
            "not_covered": "No public-road, proving-ground, hardware-in-the-loop, or real-vehicle evidence is included.",
            "risk_if_overstated": "Simulation evidence could be misread as road-deployment readiness.",
            "required_wording": "Report all driving results as simulation-only.",
            "evidence": "manifest.json; materials/RESEARCH_RISK_AND_SAFETY.md",
            "status": "bounded",
        },
        {
            "id": "sensor_and_perception_gap",
            "dimension": "perception",
            "current_evidence": "Policies use simulator telemetry/state abstractions rather than raw sensor perception.",
            "not_covered": "No camera, lidar, radar, localization, perception uncertainty, or sensor-fusion stack is evaluated.",
            "risk_if_overstated": "Telemetry control could be confused with deployable autonomous-driving perception.",
            "required_wording": "Do not imply perception-stack or VLM capability.",
            "evidence": "materials/METHODS.md; materials/DATA_CODE_AVAILABILITY.md",
            "status": "not_covered",
        },
        {
            "id": "dynamics_transfer_gap",
            "dimension": "vehicle dynamics",
            "current_evidence": "Validation uses simulator dynamics and strict off-track/grass thresholds.",
            "not_covered": "No tire, actuator, latency, weather, road-friction, damage, or system-identification transfer study is included.",
            "risk_if_overstated": "A simulator full-lap PASS may be mistaken for physical safety under real dynamics.",
            "required_wording": "Frame the work as a simulator method-development and evaluation package.",
            "evidence": "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
            "status": "not_covered",
        },
        {
            "id": "selector_and_oracle_boundary",
            "dimension": "decision policy",
            "current_evidence": "Online selectors use early probe telemetry; oracle portfolios use full-rollout outcomes only as diagnostic upper bounds.",
            "not_covered": "No zero-probe real-time deployment selector, runtime safety monitor, or certified fallback policy is provided.",
            "risk_if_overstated": "Diagnostic oracle performance could be misrepresented as deployable decision-making.",
            "required_wording": "Keep online simulator-loop selector results separate from oracle upper bounds.",
            "evidence": "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md; materials/CLAIM_EVIDENCE_MATRIX.md",
            "status": "bounded",
        },
        {
            "id": "external_validity_gap",
            "dimension": "generalization",
            "current_evidence": (
                f"Cross-heldout expanded-or-later selector is {external['summary']['expanded_or_later_selector']}; "
                f"negative and partial-transfer evidence is preserved."
            ),
            "not_covered": "No frozen larger-N heldout5-style validation, traffic-density robustness campaign, or physical-domain replication is included.",
            "risk_if_overstated": "Small held-out batches could be averaged into an unsupported broad robustness claim.",
            "required_wording": "State that current validation is descriptive and bounded.",
            "evidence": "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
            "status": "bounded_with_limitations",
        },
        {
            "id": "regulatory_and_safety_case_gap",
            "dimension": "safety assurance",
            "current_evidence": "The package contains reproducibility checks, claim guardrails, and simulator failure-mode audits.",
            "not_covered": "No ISO 26262, SOTIF, safety case, hazard analysis, operational design domain, or regulatory approval evidence is included.",
            "risk_if_overstated": "Research artifacts could be mistaken for certified safety evidence.",
            "required_wording": "Do not present the package as a safety-certified autonomous-driving system.",
            "evidence": "materials/RESEARCH_RISK_AND_SAFETY.md; materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "status": "not_covered",
        },
    ]

    prohibited = [
        "Do not claim real-road deployment readiness.",
        "Do not imply sensor/perception-stack validation.",
        "Do not imply VLM capability in this non-VLM package.",
        "Do not describe oracle portfolios as online selector outputs.",
        "Do not describe simulator PASS as physical safety certification.",
        "Do not present current held-out results as broad robustness.",
    ]

    return {
        "root": str(root),
        "title": "Simulation-to-real applicability boundary statement",
        "purpose": (
            "Provide a submission-facing boundary statement that separates the simulator evidence package from "
            "real-world vehicle deployment, sensor perception, physical dynamics transfer, and safety certification."
        ),
        "scope": {
            "task": manifest["scope"]["task"],
            "excluded": manifest["scope"]["excluded"],
            "risk_statement": risk["interpretation"],
            "claim_matrix": claims["interpretation"],
        },
        "dimensions": dimensions,
        "prohibited_wording": prohibited,
        "required_wording": [
            "All driving evidence is simulation-only.",
            "The package is non-VLM and telemetry/state based.",
            "Oracle portfolios are diagnostic upper bounds.",
            "External validation remains bounded by small held-out seed batches and partial-transfer evidence.",
            "The package is not a road-deployable or safety-certified autonomous-driving system.",
        ],
        "linked_boundaries": {
            "external_validity_boundary": external["summary"],
            "negative_results_register": negative["summary"],
            "sample_size_sensitivity": sample_summary,
        },
        "verification_snapshot": verification["summary"],
        "interpretation": (
            "The current package is suitable for simulator-based method development, transparent evaluation, and "
            "reproducibility review. It is not evidence of real-world deployment readiness."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "id",
            "dimension",
            "current_evidence",
            "not_covered",
            "risk_if_overstated",
            "required_wording",
            "evidence",
            "status",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["dimensions"])


def write_markdown(report, path):
    lines = [
        "# Simulation-to-real Applicability Boundary Statement",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Scope",
        "",
        f"- Task: {report['scope']['task']}",
        f"- Excluded: {report['scope']['excluded']}",
        f"- Risk statement: {report['scope']['risk_statement']}",
        "",
        "## Boundary Dimensions",
        "",
        "| id | dimension | current evidence | not covered | risk if overstated | required wording | evidence | status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in report["dimensions"]:
        lines.append(
            f"| {row['id']} | {row['dimension']} | {row['current_evidence']} | {row['not_covered']} | "
            f"{row['risk_if_overstated']} | {row['required_wording']} | `{row['evidence']}` | {row['status']} |"
        )
    lines.extend(["", "## Required Wording", ""])
    lines.extend(f"- {item}" for item in report["required_wording"])
    lines.extend(["", "## Prohibited Wording", ""])
    lines.extend(f"- {item}" for item in report["prohibited_wording"])
    lines.extend(
        [
            "",
            "## Verification Snapshot",
            "",
            f"- Publication verification: `{report['verification_snapshot']['status']}`",
            f"- Artifact provenance: {report['verification_snapshot']['artifact_provenance']}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export simulation-to-real applicability boundary statement.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_statement(root)
    out_json = materials / "SIMULATION_TO_REAL_APPLICABILITY.json"
    out_md = materials / "SIMULATION_TO_REAL_APPLICABILITY.md"
    out_csv = materials / "SIMULATION_TO_REAL_APPLICABILITY.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
