#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def row(section, item, value, evidence, reporting_use, boundary):
    return {
        "section": section,
        "item": item,
        "value": value,
        "evidence": evidence,
        "reporting_use": reporting_use,
        "boundary": boundary,
    }


def join_list(values):
    return "; ".join(str(value) for value in values)


def build_report(root):
    registry = load_json(root / "materials" / "EXPERIMENT_REGISTRY.json")
    seed_partition = load_json(root / "materials" / "SEED_PARTITION_AUDIT.json")
    stat_plan = load_json(root / "materials" / "STATISTICAL_ANALYSIS_PLAN.json")
    stat_consistency = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    compute = load_json(root / "tables" / "compute_cost_report.json")
    environment = load_json(root / "materials" / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    trace = load_json(root / "materials" / "REVIEWER_EVIDENCE_TRACE_PACK.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")

    seed_rows = []
    for seed_set, seeds in registry["seed_sets"].items():
        seed_rows.append(
            row(
                "seed_partitions",
                seed_set,
                f"{len(seeds)} seeds: {join_list(seeds)}",
                "materials/EXPERIMENT_REGISTRY.md; materials/SEED_PARTITION_AUDIT.md",
                "Report exact seed partitioning in Methods or Supplementary Methods.",
                "Held-out partitions support bounded simulator validation, not broad robustness.",
            )
        )

    experiment_rows = []
    for exp in registry["experiments"]:
        experiment_rows.append(
            row(
                "experiment_registry",
                exp["id"],
                f"{exp['role']}; {exp['primary_result']}",
                join_list(exp["primary_evidence"]),
                "Use as the concise experiment-role and evidence map.",
                exp["interpretation_boundary"],
            )
        )

    rows = [
        row(
            "task_scope",
            "task",
            stat_plan["scope"]["task"],
            "materials/METHODS.md; materials/STATISTICAL_ANALYSIS_PLAN.md",
            "Methods task definition.",
            stat_plan["scope"]["excluded"],
        ),
        row(
            "task_scope",
            "primary_endpoint",
            stat_plan["primary_endpoint"]["definition"],
            "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/ENDPOINT_SENSITIVITY_AUDIT.md",
            "Primary endpoint definition.",
            "Do not reinterpret visual rollouts as strict PASS outcomes.",
        ),
        row(
            "task_scope",
            "secondary_endpoints",
            join_list(stat_plan["secondary_endpoints"]),
            "materials/STATISTICAL_ANALYSIS_PLAN.md",
            "Secondary endpoint list.",
            "Secondary endpoints support diagnosis, not endpoint switching.",
        ),
        row(
            "statistics",
            "analysis_methods",
            join_list(stat_plan["intervals_and_tests"]),
            "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/STATISTICAL_CONSISTENCY_AUDIT.md",
            "Reporting Summary statistics field.",
            stat_plan["multiplicity_policy"],
        ),
        row(
            "statistics",
            "consistency_status",
            f"{stat_consistency['summary']['check_count']} checks; failed={stat_consistency['summary']['failed_checks']}; status={stat_consistency['summary']['status']}",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.md",
            "Methods/statistics QA statement.",
            "Static audit supports consistency but does not enlarge sample size.",
        ),
        row(
            "compute",
            "simulated_steps_and_devices",
            (
                f"{compute['summary']['full_rollout_rows']} full-rollout rows, "
                f"{compute['summary']['full_rollout_simulated_steps']} full-rollout simulated steps, "
                f"{compute['summary']['selector_probe_rows']} selector probe rows, "
                f"{compute['summary']['selector_probe_simulated_steps']} selector probe steps, "
                f"devices={join_list(compute['summary']['devices_from_suites'])}"
            ),
            "tables/compute_cost_report.md",
            "Reporting Summary compute field.",
            compute["summary"]["interpretation"],
        ),
        row(
            "environment",
            "software_hardware",
            (
                f"environment.yml present={environment['summary']['environment_yml_present']}; "
                f"torch CUDA available={environment['summary']['torch_cuda_available']}; "
                f"GPU count={environment['summary']['nvidia_smi_gpu_count']}; "
                f"missing package versions={len(environment['summary']['package_versions_missing'])}"
            ),
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md; environment.yml",
            "Reporting Summary software/hardware field.",
            "Environment audit documents local run context, not guaranteed cross-platform performance.",
        ),
        row(
            "reproducibility",
            "artifact_provenance",
            f"{provenance['complete_count']}/{len(provenance['artifacts'])} artifacts complete",
            "tables/artifact_provenance.md",
            "Reviewer reproducibility statement.",
            "Expensive rollout commands are registered; fast audit can be run first.",
        ),
        row(
            "reproducibility",
            "smoke_test",
            f"{smoke['summary']['check_count']} smoke checks; failed={smoke['summary']['failed_checks']}; status={smoke['summary']['status']}",
            "materials/PUBLICATION_SMOKE_TEST.md",
            "Fast independent package-integrity statement.",
            "Smoke test does not rerun expensive rollouts.",
        ),
        row(
            "reproducibility",
            "reviewer_trace",
            f"{trace['summary']['trace_row_count']} trace rows; review_required={trace['summary']['review_required_count']}",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
            "Reviewer navigation statement.",
            "Trace pack is a navigation aid, not a replacement for source data.",
        ),
        row(
            "validity_boundaries",
            "seed_partition_status",
            (
                f"{seed_partition['summary']['seed_set_count']} seed sets; "
                f"unexpected overlaps={seed_partition['summary']['unexpected_overlap_count']}; "
                f"external-validation eligible experiments={seed_partition['summary']['external_validation_eligible_count']}"
            ),
            "materials/SEED_PARTITION_AUDIT.md",
            "Methods seed-partition disclosure.",
            "Targeted repair and diagnostic reuse must remain labelled.",
        ),
        row(
            "validity_boundaries",
            "required_wording",
            join_list(risk["required_submission_wording"]),
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "Discussion/Reporting Summary limitation wording.",
            "No real-road, VLM, perception-stack, or safety-certification evidence is included.",
        ),
        row(
            "validity_boundaries",
            "prohibited_claims",
            join_list(stat_plan["prohibited_claims"]),
            "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/CLAIM_EVIDENCE_MATRIX.md",
            "Final claim-control checklist.",
            "Prohibited claims remain prohibited unless new independent evidence is generated.",
        ),
        row(
            "package_gates",
            "publication_verification",
            f"status={verification['summary']['status']}; gates={verification['summary']['gate_count']}; failed={verification['summary']['failed_gates']}",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "Pre-submission local gate statement.",
            "Local gate pass is not journal acceptance.",
        ),
    ]
    rows.extend(seed_rows)
    rows.extend(experiment_rows)

    return {
        "root": str(root),
        "title": "Methods and Reproducibility Capsule",
        "purpose": (
            "Condense task scope, endpoints, seed partitions, statistics, compute, environment, reproducibility, "
            "and claim boundaries into a Methods/Reporting Summary-ready evidence table."
        ),
        "rows": rows,
        "summary": {
            "status": "pass",
            "row_count": len(rows),
            "seed_partition_count": len(seed_rows),
            "experiment_count": len(experiment_rows),
            "publication_verification_status": verification["summary"]["status"],
            "statistical_consistency_status": stat_consistency["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "data_dictionary_complete": load_json(root / "materials" / "DATA_DICTIONARY.json")["summary"]["complete"],
        },
        "interpretation": (
            "This capsule is a structured reporting aid. Authors still need to adapt wording to the selected journal template "
            "and preserve all simulator-only and no-broad-robustness boundaries."
        ),
    }


def write_csv(report, path):
    fields = ["section", "item", "value", "evidence", "reporting_use", "boundary"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Methods and Reproducibility Capsule",
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
            "## Capsule Rows",
            "",
            "| section | item | value | evidence | reporting use | boundary |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['section']} | {item['item']} | {item['value']} | "
            f"`{item['evidence']}` | {item['reporting_use']} | {item['boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export Methods/Reporting Summary reproducibility capsule.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "METHODS_REPRODUCIBILITY_CAPSULE.json"
    out_md = materials / "METHODS_REPRODUCIBILITY_CAPSULE.md"
    out_csv = materials / "METHODS_REPRODUCIBILITY_CAPSULE.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
