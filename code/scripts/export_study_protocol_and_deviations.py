#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def seed_text(seeds):
    if isinstance(seeds, str):
        return seeds
    return ",".join(str(seed) for seed in seeds)


def ratio(count, n):
    return f"{count}/{n}"


def build_report(root):
    manifest = load_json(root / "manifest.json")
    registry = load_json(root / "materials" / "EXPERIMENT_REGISTRY.json")
    sap = load_json(root / "materials" / "STATISTICAL_ANALYSIS_PLAN.json")
    external = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")
    policy_card = load_json(root / "materials" / "POLICY_MODEL_CARD.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")

    key = manifest["key_results"]
    rows = [
        {
            "id": "P01_locked_development_benchmark",
            "stage": "locked",
            "seed_set": "locked",
            "seed_list": seed_text(manifest["seed_sets"]["locked"]),
            "status": "predefined_development_benchmark",
            "primary_endpoint": sap["primary_endpoint"]["name"],
            "evidence": "materials/EXPERIMENT_REGISTRY.md; materials/STATISTICAL_ANALYSIS_PLAN.md; tables/full_statistical_report.md",
            "allowed_interpretation": (
                f"Locked seeds support within-package method comparison; strongest single baseline is "
                f"overtake_base_only {ratio(key['locked_single_methods']['overtake_base_only']['pass_count'], key['locked_single_methods']['overtake_base_only']['n'])}."
            ),
            "prohibited_interpretation": "Do not treat locked development seeds as external validation.",
            "action": "Report locked results with held-out results and failure decomposition.",
            "provenance_artifacts": "full_statistical_report; experiment_registry; statistical_analysis_plan",
        },
        {
            "id": "P02_heldout1_selector_validation",
            "stage": "heldout1",
            "seed_set": "heldout1",
            "seed_list": seed_text(manifest["seed_sets"]["heldout1"]),
            "status": "positive_heldout_result",
            "primary_endpoint": sap["primary_endpoint"]["name"],
            "evidence": "tables/heldout_generalization.md; tables/portfolio_probe_selector_1200_heldout_dagger_v2.md; tables/seed_outcome_ledger.md",
            "allowed_interpretation": (
                f"First held-out online selector result is {ratio(key['heldout1_five_candidate_selector']['pass_count'], key['heldout1_five_candidate_selector']['n'])} "
                f"against oracle {ratio(key['heldout1_five_candidate_selector']['oracle_pass_count'], key['heldout1_five_candidate_selector']['oracle_n'])}."
            ),
            "prohibited_interpretation": "Do not cite heldout1 alone as robustness evidence.",
            "action": "Pair heldout1 with heldout2, heldout3, heldout4, and cross-heldout synthesis.",
            "provenance_artifacts": "heldout_generalization; online_probe_selector_1200_heldout_dagger_v2",
        },
        {
            "id": "P03_heldout2_stress_repeat",
            "stage": "heldout2",
            "seed_set": "heldout2",
            "seed_list": seed_text(manifest["seed_sets"]["heldout2"]),
            "status": "negative_generalization_boundary",
            "primary_endpoint": sap["primary_endpoint"]["name"],
            "evidence": "tables/heldout_generalization.md; tables/selector_calibration.md; tables/heldout2_failure_atlas.md",
            "allowed_interpretation": (
                f"Same selector family drops to {ratio(key['heldout2_five_candidate_selector']['pass_count'], key['heldout2_five_candidate_selector']['n'])} "
                f"against oracle {ratio(key['heldout2_five_candidate_selector']['oracle_pass_count'], key['heldout2_five_candidate_selector']['oracle_n'])}, exposing selector and candidate gaps."
            ),
            "prohibited_interpretation": "Do not hide heldout2 when reporting heldout1.",
            "action": "Retain as a negative stress repeat and failure-atlas anchor.",
            "provenance_artifacts": "heldout_generalization; selector_calibration; heldout2_failure_atlas",
        },
        {
            "id": "P04_candidate_expansion_diagnostic",
            "stage": "heldout2_candidate_expansion",
            "seed_set": "heldout2",
            "seed_list": seed_text(manifest["seed_sets"]["heldout2"]),
            "status": "diagnostic_followup",
            "primary_endpoint": "diagnostic candidate oracle after adding candidates",
            "evidence": "tables/heldout2_candidate_expansion.md; tables/expanded_selector_generalization.md",
            "allowed_interpretation": (
                f"Candidate expansion raises heldout2 oracle from {key['heldout2_candidate_expansion']['original_oracle_pass_count']}/10 "
                f"to {key['heldout2_candidate_expansion']['expanded_oracle_pass_count']}/10; online expanded selector remains {key['expanded_online_selector']['heldout2_pass_count']}/10."
            ),
            "prohibited_interpretation": "Do not report expanded oracle as online selector performance.",
            "action": "Use this as candidate-coverage evidence and preserve selector misses as unresolved.",
            "provenance_artifacts": "heldout2_candidate_expansion; expanded_selector_generalization",
        },
        {
            "id": "P05_learned_selector_exploratory",
            "stage": "heldout1_train_heldout2_test_heldout3_external",
            "seed_set": "heldout1/heldout2/heldout3",
            "seed_list": seed_text(manifest["seed_sets"]["heldout1"] + manifest["seed_sets"]["heldout2"] + manifest["seed_sets"]["heldout3"]),
            "status": "exploratory_not_accepted_replacement",
            "primary_endpoint": sap["primary_endpoint"]["name"],
            "evidence": "tables/learned_selector_report.md; materials/POLICY_MODEL_CARD.md",
            "allowed_interpretation": (
                f"Learned selector diagnostic reaches heldout2 {key['learned_selector_exploratory']['heldout2_pass_count']}/10 "
                f"but heldout3 {key['learned_selector_exploratory']['heldout3_pass_count']}/10 and is not accepted as a replacement."
            ),
            "prohibited_interpretation": "Do not present learned selector diagnostics as a finalized selector.",
            "action": "Require a frozen selector and fresh heldout batch before promotion.",
            "provenance_artifacts": "learned_selector_diagnostic; policy_model_card",
        },
        {
            "id": "P06_heldout3_external_validation",
            "stage": "heldout3",
            "seed_set": "heldout3",
            "seed_list": seed_text(manifest["seed_sets"]["heldout3"]),
            "status": "negative_external_validation",
            "primary_endpoint": sap["primary_endpoint"]["name"],
            "evidence": "tables/heldout3_external_validation.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "allowed_interpretation": (
                f"Heldout3 is negative external validation: expanded selector {key['heldout3_external_validation']['expanded_selector_pass_count']}/10, "
                f"oracle {key['heldout3_external_validation']['candidate_oracle_pass_count']}/10."
            ),
            "prohibited_interpretation": "Do not use targeted heldout3 repair to erase this external-validation result.",
            "action": "Report heldout3 before targeted repair and keep its failed seeds visible.",
            "provenance_artifacts": "heldout3_external_validation; external_validity_boundary_audit",
        },
        {
            "id": "P07_heldout3_targeted_repair",
            "stage": "heldout3_targeted_repair",
            "seed_set": "heldout3",
            "seed_list": seed_text(manifest["seed_sets"]["heldout3"]),
            "status": "targeted_diagnostic_repair",
            "primary_endpoint": "targeted candidate coverage after observing heldout3 failures",
            "evidence": "tables/heldout3_candidate_expansion.md; tables/heldout3_targeted_selector_generalization.md; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
            "allowed_interpretation": (
                f"Targeted repair covers heldout3 candidate gaps and raises targeted oracle to "
                f"{key['heldout3_targeted_candidate_expansion']['expanded_oracle_pass_count']}/10."
            ),
            "prohibited_interpretation": "Do not count targeted heldout3 repair as independent external validation.",
            "action": "Use only as a diagnostic for hard-state data aggregation.",
            "provenance_artifacts": "heldout3_candidate_expansion; heldout3_targeted_selector_generalization; negative_results_failure_register",
        },
        {
            "id": "P08_heldout4_post_repair_external_boundary",
            "stage": "heldout4",
            "seed_set": "heldout4",
            "seed_list": seed_text(manifest["seed_sets"]["heldout4"]),
            "status": "post_repair_external_validation_with_partial_transfer",
            "primary_endpoint": sap["primary_endpoint"]["name"],
            "evidence": "tables/heldout4_external_validation.md; tables/heldout4_failure_atlas.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "allowed_interpretation": (
                f"Heldout4 after targeted repair shows partial transfer: selector "
                f"{key['heldout4_external_after_targeted_repair']['selector_pass_count']}/10, oracle "
                f"{key['heldout4_external_after_targeted_repair']['oracle_pass_count']}/10."
            ),
            "prohibited_interpretation": "Do not call this broad robustness; selector misses and candidate gaps remain.",
            "action": "Freeze the next design before a fresh heldout5-style validation.",
            "provenance_artifacts": "heldout4_external_validation; heldout4_failure_atlas; external_validity_boundary_audit",
        },
        {
            "id": "P09_cross_heldout_synthesis",
            "stage": "cross_heldout",
            "seed_set": "heldout1-4 plus targeted stages",
            "seed_list": "see tables/seed_outcome_ledger.md",
            "status": "descriptive_synthesis",
            "primary_endpoint": "selector-oracle gap across saved validation stages",
            "evidence": "tables/cross_heldout_validation_synthesis.md; tables/cross_heldout_statistical_supplement.md; figures/figure_3_cross_heldout_validation.png",
            "allowed_interpretation": (
                f"Expanded-or-later selector is {external['summary']['expanded_or_later_selector']} against oracle "
                f"{external['summary']['expanded_or_later_oracle']} with a {external['summary']['expanded_or_later_selector_oracle_gap']}-seed gap."
            ),
            "prohibited_interpretation": "Do not convert the descriptive aggregate into confirmatory robustness evidence.",
            "action": "Use synthesis to prioritize fresh validation, not to overstate current scope.",
            "provenance_artifacts": "cross_heldout_validation_synthesis; cross_heldout_statistical_supplement",
        },
    ]

    return {
        "root": str(root),
        "title": "Study Protocol and Deviations",
        "protocol_scope": manifest["scope"],
        "design_principles": [
            "Preserve locked baselines and all three originally implemented baseline methods for comparison.",
            "Separate online simulator-loop selector results from diagnostic oracle upper bounds.",
            "Report heldout3 targeted repair as a diagnostic, not independent validation.",
            "Report heldout4 as post-repair external validation with partial transfer and unresolved gaps.",
            "Keep negative controls and failed generalization stages visible.",
        ],
        "rows": rows,
        "summary": {
            "row_count": len(rows),
            "experiment_registry_complete": registry["summary"]["all_primary_evidence_present"],
            "policy_model_card_complete": policy_card["summary"]["complete"],
            "negative_result_items": negative["summary"]["item_count"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
        },
        "interpretation": (
            "This protocol/deviation record is retrospective for the saved package but separates locked analyses, "
            "held-out validation, diagnostic follow-ups, targeted repair, and post-repair external validation so that "
            "manuscript claims do not blur development and validation evidence."
        ),
    }


CSV_FIELDS = [
    "id",
    "stage",
    "seed_set",
    "seed_list",
    "status",
    "primary_endpoint",
    "evidence",
    "allowed_interpretation",
    "prohibited_interpretation",
    "action",
    "provenance_artifacts",
]


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({key: row[key] for key in CSV_FIELDS})


def write_markdown(report, path):
    lines = [
        "# Study Protocol and Deviations",
        "",
        report["interpretation"],
        "",
        "## Scope",
        "",
        f"- Task: {report['protocol_scope']['task']}",
        f"- Excluded: {report['protocol_scope']['excluded']}",
        f"- Validator: {report['protocol_scope']['validator']}",
        "",
        "## Design Principles",
        "",
    ]
    lines.extend(f"- {item}" for item in report["design_principles"])
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Rows: {report['summary']['row_count']}",
            f"- Experiment registry evidence complete: {report['summary']['experiment_registry_complete']}",
            f"- Policy/model card complete: {report['summary']['policy_model_card_complete']}",
            f"- Negative-result items: {report['summary']['negative_result_items']}",
            f"- Artifact provenance: {report['summary']['artifact_provenance']}",
            "",
            "## Protocol Rows",
            "",
            "| id | stage | seed set | status | allowed interpretation | prohibited interpretation |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['id']} | {row['stage']} | {row['seed_set']} | {row['status']} | "
            f"{row['allowed_interpretation']} | {row['prohibited_interpretation']} |"
        )
    lines.extend(["", "## Evidence and Actions", ""])
    for row in report["rows"]:
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- Seeds: `{row['seed_list']}`",
                f"- Primary endpoint: {row['primary_endpoint']}",
                f"- Evidence: `{row['evidence']}`",
                f"- Action: {row['action']}",
                f"- Provenance artifacts: `{row['provenance_artifacts']}`",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export study protocol and deviation record.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "STUDY_PROTOCOL_AND_DEVIATIONS.json"
    out_md = materials / "STUDY_PROTOCOL_AND_DEVIATIONS.md"
    out_csv = materials / "STUDY_PROTOCOL_AND_DEVIATIONS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "rows": report["summary"]["row_count"]}, indent=2))


if __name__ == "__main__":
    main()
