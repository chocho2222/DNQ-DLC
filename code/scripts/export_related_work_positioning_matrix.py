#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def comparison_route(route_id, likely_comparison, cite_keys, defensible_response, evidence, do_not_claim, manuscript_use):
    return {
        "route_id": route_id,
        "likely_comparison": likely_comparison,
        "citation_keys": cite_keys,
        "defensible_response": defensible_response,
        "evidence": evidence,
        "do_not_claim": do_not_claim,
        "manuscript_use": manuscript_use,
    }


def build_report(root):
    references = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")
    novelty = load_json(root / "materials" / "NOVELTY_POSITIONING_MATRIX.json")
    triage = load_json(root / "materials" / "EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.json")
    replication = load_json(root / "materials" / "REVIEWER_REPLICATION_ROUTE.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")

    rows = [
        {
            "id": "RW1_autonomous_racing_field",
            "literature_area": "autonomous_racing_surveys",
            "citation_keys": "betz2022survey",
            "what_prior_work_establishes": "Autonomous racing spans perception, planning, control, end-to-end learning, and platform development.",
            "positioning_for_this_work": "Use this field framing to motivate strict racing-style evaluation without claiming a full autonomous-racing stack.",
            "local_evidence": "materials/NOVELTY_POSITIONING_MATRIX.md; materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "claim_boundary": "No real-road, perception-stack, or safety-certification claim.",
        },
        {
            "id": "RW2_open_platforms_and_benchmarks",
            "literature_area": "autonomous_racing_platforms",
            "citation_keys": "okelly2020f1tenth",
            "what_prior_work_establishes": "Scaled racing platforms make continuous-control and reinforcement-learning evaluation safer and more repeatable.",
            "positioning_for_this_work": "Frame the package as a simulator benchmark/evidence bundle with strict seed-level reporting rather than a hardware platform.",
            "local_evidence": "materials/EXPERIMENT_REGISTRY.md; tables/artifact_provenance.md; materials/REPRODUCTION_GUIDE.md",
            "claim_boundary": "Simulator-only package; no hardware-in-the-loop or real-vehicle evidence.",
        },
        {
            "id": "RW3_optimization_control_racing",
            "literature_area": "optimization_and_mpc",
            "citation_keys": "liniger2015optimization",
            "what_prior_work_establishes": "Optimization and MPC racing can combine progress objectives, track constraints, and opponent avoidance in real time.",
            "positioning_for_this_work": "Contrast our telemetry/rule, graph, and selector portfolio with optimization-control baselines while avoiding superiority claims.",
            "local_evidence": "materials/BASELINE_FAIRNESS_AUDIT.md; tables/full_statistical_report.md",
            "claim_boundary": "Do not claim the current learned/shielded methods surpass strong optimization-control racing systems.",
        },
        {
            "id": "RW4_learning_based_overtaking",
            "literature_area": "curriculum_rl_overtaking",
            "citation_keys": "song2021autonomous",
            "what_prior_work_establishes": "Curriculum reinforcement learning can improve autonomous overtaking in a high-fidelity racing simulator.",
            "positioning_for_this_work": "Position our work as strict validation and failure decomposition for multi-car overtaking rather than a new end-to-end RL training claim.",
            "local_evidence": "tables/heldout3_external_validation.md; tables/heldout4_external_validation.md; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
            "claim_boundary": "No claim of human-comparable overtaking performance.",
        },
        {
            "id": "RW5_champion_level_deep_rl_racing",
            "literature_area": "deep_rl_tactical_racing",
            "citation_keys": "wurman2022outracing",
            "what_prior_work_establishes": "Deep RL can reach high-level tactical racing performance in Gran Turismo with mixed-scenario training.",
            "positioning_for_this_work": "Use as a high-end comparator for simulator racing capability while emphasizing that our contribution is evidence discipline, selector transparency, and boundary reporting.",
            "local_evidence": "materials/SELECTOR_DECISION_AUDIT.md; materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.md",
            "claim_boundary": "Do not claim champion-level racing, raw vision control, or broad multi-agent robustness.",
        },
    ]

    comparison_routes = [
        comparison_route(
            "RC1_mpc_and_optimization",
            "Optimization/MPC racing already provides real-time track and opponent constraints.",
            "liniger2015optimization",
            "Position the current work as a strict simulator evaluation and controller-selection evidence package, not as a replacement for MPC racing control.",
            "materials/BASELINE_FAIRNESS_AUDIT.md; materials/NOVELTY_POSITIONING_MATRIX.md; tables/full_statistical_report.md",
            "Do not claim superiority over MPC or optimization-control racing systems.",
            "Use in Related Work and Discussion when explaining why strong rule baselines are preserved.",
        ),
        comparison_route(
            "RC2_f1tenth_and_platforms",
            "Open racing platforms already support repeatable continuous-control evaluation.",
            "okelly2020f1tenth",
            "Position the package as a simulator evidence bundle with strict full-lap seed-level reporting, source data, and reviewer quickstarts.",
            "materials/EXPERIMENT_REGISTRY.md; materials/REVIEWER_REPLICATION_ROUTE.md; tables/artifact_provenance.md",
            "Do not imply hardware-in-the-loop, F1TENTH deployment, or public-road evidence.",
            "Use in Methods/Availability to explain the local package and archive-readiness contribution.",
        ),
        comparison_route(
            "RC3_curriculum_rl_overtaking",
            "Curriculum RL has demonstrated overtaking in high-fidelity racing simulators.",
            "song2021autonomous",
            "Frame this work around evaluation discipline, negative validation, and seed-level failure decomposition rather than a new end-to-end RL training result.",
            "tables/heldout3_external_validation.md; tables/heldout4_external_validation.md; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
            "Do not claim human-comparable overtaking, simulator dominance, or solved overtaking.",
            "Use in Related Work and Results when motivating why heldout failures are part of the contribution.",
        ),
        comparison_route(
            "RC4_champion_level_deep_rl",
            "GT Sophy-style systems show that deep RL can reach champion-level tactical racing in a rich simulator.",
            "wurman2022outracing",
            "Use this as an upper-end field reference while stating that the present work is narrower: telemetry/state, non-VLM, strict full-lap overtaking evidence and transparent selector auditing.",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.md; materials/SELECTOR_DECISION_AUDIT.md; materials/THREATS_TO_VALIDITY_AUDIT.md",
            "Do not claim champion-level racing, raw-vision control, broad multi-agent robustness, or deployment readiness.",
            "Use in Introduction/Discussion to prevent overclaiming against high-end racing-agent literature.",
        ),
        comparison_route(
            "RC5_graph_and_relational_learning",
            "Graph/relational inductive biases are well established for structured learning.",
            "battaglia2018relational",
            "Present the graph actor as one candidate in a broader full-lap evaluation and portfolio-selection study, not as the sole novelty.",
            "materials/POLICY_MODEL_CARD.md; tables/full_statistical_report.md; materials/CLAIM_EVIDENCE_MATRIX.md",
            "Do not claim a new graph-network architecture or that the graph method beats the strongest rule baseline.",
            "Use in Methods to motivate representation choice while keeping the main contribution on evaluation and selection.",
        ),
        comparison_route(
            "RC6_reproducibility_and_reporting",
            "Reviewers may ask whether this is a method paper or mainly an artifact/reporting package.",
            "brockman2016openai; wilson1927probable",
            "Emphasize that the scientific claim is the strict evaluation ladder, controller complementarity, and transparent generalization boundary, supported by reproducibility infrastructure.",
            "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md; materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md; materials/REVIEWER_REPLICATION_ROUTE.md",
            "Do not present local package readiness as journal acceptance or public archive completion.",
            "Use in cover letter, Data/Code Availability, and reviewer response planning.",
        ),
    ]

    return {
        "root": str(root),
        "title": "Related-work Positioning Matrix",
        "purpose": (
            "Map the expanded starter bibliography to manuscript positioning, evidence files, and claim boundaries "
            "so the related-work section supports novelty without overstating the current simulator package."
        ),
        "rows": rows,
        "comparison_routes": comparison_routes,
        "summary": {
            "row_count": len(rows),
            "comparison_route_count": len(comparison_routes),
            "citation_key_count": references["summary"]["citation_key_count"],
            "bib_entry_count": references["summary"]["bib_entry_count"],
            "topic_needs_author_completion_count": references["summary"]["topic_needs_author_completion_count"],
            "novelty_axes": novelty["summary"]["innovation_axes"],
            "triage_checklist_count": triage["summary"]["checklist_count"],
            "reviewer_quickstart_count": replication["summary"]["quickstart_count"],
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
        },
        "interpretation": (
            "The matrix supplies a defensible related-work scaffold for the local manuscript draft. It is not a claim "
            "that the final target-journal literature review is complete or optimally balanced."
        ),
    }


def write_csv(report, path):
    fields = [
        "kind",
        "id",
        "literature_area",
        "citation_keys",
        "what_prior_work_establishes",
        "positioning_for_this_work",
        "local_evidence",
        "claim_boundary",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({"kind": "positioning_row", **{key: row[key] for key in fields if key != "kind"}})
        for row in report["comparison_routes"]:
            writer.writerow(
                {
                    "kind": "comparison_route",
                    "id": row["route_id"],
                    "literature_area": row["likely_comparison"],
                    "citation_keys": row["citation_keys"],
                    "what_prior_work_establishes": row["likely_comparison"],
                    "positioning_for_this_work": row["defensible_response"],
                    "local_evidence": row["evidence"],
                    "claim_boundary": row["do_not_claim"] + " Manuscript use: " + row["manuscript_use"],
                }
            )


def write_markdown(report, path):
    lines = [
        "# Related-work Positioning Matrix",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Rows: {report['summary']['row_count']}",
        f"- Reviewer comparison routes: {report['summary']['comparison_route_count']}",
        f"- Citation keys: {report['summary']['citation_key_count']}",
        f"- Bib entries: {report['summary']['bib_entry_count']}",
        f"- Related-work topics needing author completion: {report['summary']['topic_needs_author_completion_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        "",
        "## Matrix",
        "",
        "| id | literature area | citation keys | prior work establishes | positioning for this work | evidence | boundary |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['id']} | {row['literature_area']} | `{row['citation_keys']}` | "
            f"{row['what_prior_work_establishes']} | {row['positioning_for_this_work']} | "
            f"`{row['local_evidence']}` | {row['claim_boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Reviewer Comparison Routes",
            "",
            "| route | likely comparison | citation keys | defensible response | evidence | do not claim | manuscript use |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["comparison_routes"]:
        lines.append(
            f"| {row['route_id']} | {row['likely_comparison']} | `{row['citation_keys']}` | "
            f"{row['defensible_response']} | `{row['evidence']}` | {row['do_not_claim']} | {row['manuscript_use']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export related-work positioning matrix.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "RELATED_WORK_POSITIONING_MATRIX.json"
    out_md = materials / "RELATED_WORK_POSITIONING_MATRIX.md"
    out_csv = materials / "RELATED_WORK_POSITIONING_MATRIX.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
