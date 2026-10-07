#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def add_check(rows, check_id, section, status, expected, observed, evidence, interpretation, boundary):
    rows.append(
        {
            "check_id": check_id,
            "section": section,
            "status": status,
            "expected": expected,
            "observed": observed,
            "evidence": evidence,
            "interpretation": interpretation,
            "boundary": boundary,
        }
    )


def has_all(text, terms):
    lowered = text.lower()
    return all(term.lower() in lowered for term in terms)


def build_report(root):
    plan = load_json(root / "materials" / "STATISTICAL_ANALYSIS_PLAN.json")
    full = load_json(root / "tables" / "full_statistical_report.json")
    cross_stats = load_json(root / "tables" / "cross_heldout_statistical_supplement.json")
    sample = load_json(root / "materials" / "SAMPLE_SIZE_SENSITIVITY_BRIEF.json")
    endpoint = load_json(root / "materials" / "ENDPOINT_SENSITIVITY_AUDIT.json")
    effect = load_json(root / "materials" / "EFFECT_SIZE_UNCERTAINTY_SUMMARY.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")
    external = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    reporting = load_json(root / "materials" / "STATISTICAL_REPORTING_APPENDIX.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")

    rows = []
    endpoint_text = plan["primary_endpoint"]["definition"]
    endpoint_terms = ["full lap", "rank 1", "first-ahead", "grass", "traffic"]
    add_check(
        rows,
        "SAP01_primary_endpoint_declared",
        "endpoint",
        "pass" if plan["primary_endpoint"]["name"] == "strict_full_lap_pass" and has_all(endpoint_text, endpoint_terms) else "fail",
        "strict_full_lap_pass includes lap completion, rank, first-ahead, grass, and traffic quality.",
        plan["primary_endpoint"]["name"] + ": " + endpoint_text,
        "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/METHODS.md; scripts/validate_overtake_behavior.py",
        "The primary endpoint is explicit enough to prevent GIF-only or partial-lap cherry-picking.",
        "Endpoint definition supports simulator validation only, not road deployment.",
    )

    expected_seed_sets = {"locked", "heldout1", "heldout2", "heldout3", "heldout4", "hard_smoke"}
    seed_sets = plan["seed_sets"]
    seed_lengths = {key: len(value) for key, value in seed_sets.items()}
    add_check(
        rows,
        "SAP02_seed_sets_registered",
        "study_design",
        "pass" if expected_seed_sets.issubset(seed_sets.keys()) and all(seed_lengths[k] == 10 for k in ["locked", "heldout1", "heldout2", "heldout3", "heldout4"]) else "fail",
        "Locked plus four held-out 10-seed sets and a hard-smoke diagnostic set are registered.",
        json.dumps(seed_lengths, sort_keys=True),
        "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/SEED_PARTITION_AUDIT.md; materials/EXPERIMENT_REGISTRY.md",
        "Seed partitions are visible before claim interpretation.",
        "The fixed seed sets support method-development evidence, not population-level robustness.",
    )

    comparison_names = {row["comparison"] for row in plan["main_comparisons"]}
    expected_comparisons = {
        "locked single-method comparison",
        "held-out online selector generalization",
        "oracle portfolio upper bound",
        "selector calibration diagnosis",
        "cross-heldout selector-oracle synthesis",
    }
    add_check(
        rows,
        "SAP03_main_comparisons_covered",
        "comparisons",
        "pass" if expected_comparisons.issubset(comparison_names) else "fail",
        "All planned comparator families are listed.",
        "; ".join(sorted(comparison_names)),
        "materials/STATISTICAL_ANALYSIS_PLAN.md; tables/full_statistical_report.md; tables/cross_heldout_validation_synthesis.md",
        "The plan separates locked baselines, online simulator-loop selectors, calibration diagnostics, and diagnostic oracles.",
        "Oracle rows must remain diagnostic upper bounds, not online selector outputs.",
    )

    tests = " ".join(plan["intervals_and_tests"]).lower()
    add_check(
        rows,
        "SAP04_intervals_and_tests_supported",
        "statistics",
        "pass" if all(term in tests for term in ["wilson", "bootstrap", "mcnemar", "failure-type", "exact"]) else "fail",
        "Plan includes Wilson intervals, paired bootstrap intervals, McNemar tests, exact selector-oracle tests, and failure-type counts.",
        " | ".join(plan["intervals_and_tests"]),
        "materials/STATISTICAL_ANALYSIS_PLAN.md; tables/cross_heldout_statistical_supplement.md; materials/STATISTICAL_REPORTING_APPENDIX.md",
        "The statistical plan matches the uncertainty and paired-test materials.",
        "Tests are descriptive under small fixed seed batches.",
    )

    multiplicity = plan["multiplicity_policy"].lower()
    add_check(
        rows,
        "SAP05_multiplicity_policy_conservative",
        "statistics",
        "pass" if all(term in multiplicity for term in ["descriptive", "small", "confidence", "negative"]) else "fail",
        "Multiplicity wording treats tests as descriptive and retains negative results.",
        plan["multiplicity_policy"],
        "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/CLAIM_EVIDENCE_MATRIX.md",
        "Multiplicity policy prevents isolated p-values from being overclaimed.",
        "The policy does not convert exploratory simulator evidence into confirmatory robustness.",
    )

    add_check(
        rows,
        "SAP06_cross_heldout_uncertainty_linked",
        "uncertainty",
        "pass" if len(cross_stats["stage_statistics"]) == sample["summary"]["stage_count"] == 7 and effect["summary"]["status"] == "pass" else "fail",
        "Seven stage rows have uncertainty statistics and effect-size summaries.",
        f"cross_stats={len(cross_stats['stage_statistics'])}; sample={sample['summary']['stage_count']}; effect={effect['summary']['status']}",
        "tables/cross_heldout_statistical_supplement.md; materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.md; materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md",
        "Uncertainty is reported at both stage and aggregate levels.",
        "The expanded-or-later aggregate mixes stages and remains descriptive.",
    )

    add_check(
        rows,
        "SAP07_sample_size_limitation_quantified",
        "sample_size",
        "pass" if sample["summary"]["per_stage_n"] == 10 and sample["summary"]["expanded_or_later_n"] == 50 and sample["summary"]["n_for_assumed_80pct_width_le_0_20"] > 10 else "fail",
        "n=10 stage limitation and larger-N planning grid are present.",
        json.dumps(sample["summary"], sort_keys=True),
        "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md",
        "The plan has a quantitative answer to reviewer questions about seed counts.",
        "Planning rows are future-study guidance, not completed larger-N evidence.",
    )

    add_check(
        rows,
        "SAP08_endpoint_sensitivity_reported",
        "endpoint",
        "pass" if endpoint["summary"]["scenario_count"] >= 3000 and endpoint["summary"]["endpoint_sensitive_stage_methods"] > 0 else "fail",
        "Endpoint sensitivity audit spans threshold scenarios and reports sensitive method-stage rows.",
        json.dumps(endpoint["summary"], sort_keys=True),
        "materials/ENDPOINT_SENSITIVITY_AUDIT.md",
        "Endpoint choices are stress-tested rather than left as unexamined post hoc thresholds.",
        "Sensitivity does not establish real-world robustness.",
    )

    add_check(
        rows,
        "SAP09_negative_results_preserved",
        "negative_results",
        "pass" if negative["summary"]["item_count"] >= 7 and negative["summary"]["heldout3_failed_seeds"] else "fail",
        "Negative held-out, selector-miss, candidate-gap, and targeted-repair boundary results are retained.",
        json.dumps(negative["summary"], sort_keys=True),
        "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
        "Negative evidence is explicitly preserved for reviewer interpretation.",
        "Negative-result preservation constrains claims and is not a failure to report.",
    )

    add_check(
        rows,
        "SAP10_external_validity_boundary_linked",
        "external_validity",
        "pass" if external["summary"]["expanded_or_later_selector"] == "31/50" and external["summary"]["expanded_or_later_oracle"] == "45/50" else "fail",
        "External-validity boundary reports selector/oracle aggregate and heldout4 failure seeds.",
        json.dumps(external["summary"], sort_keys=True),
        "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md; materials/REVIEWER_RISK_RESPONSE_DOSSIER.md",
        "The analysis plan has a clear boundary against broad robustness claims.",
        "Heldout4 is post-repair external validation with partial transfer, not broad robustness.",
    )

    reporting_items = {row["item"] for row in reporting["rows"]}
    required_reporting_items = {
        "locked_overtake_baseline",
        "locked_graph_adaptive",
        "expanded_or_later_selector",
        "expanded_or_later_oracle",
        "selector_oracle_magnitude",
        "endpoint_sensitive_stage_methods",
        "future_precision_target",
    }
    add_check(
        rows,
        "SAP11_minimum_reporting_set_materialized",
        "reporting",
        "pass" if required_reporting_items.issubset(reporting_items) and reporting["summary"]["status"] == "pass" else "fail",
        "Minimum statistical reporting rows are materialized in the statistical appendix.",
        "; ".join(sorted(reporting_items)),
        "materials/STATISTICAL_REPORTING_APPENDIX.md",
        "The plan's reporting obligations are represented in reviewer-facing statistical appendices.",
        "Appendix rows are reporting support, not a substitute for final journal formatting.",
    )

    prohibited = " ".join(plan["prohibited_claims"]).lower()
    add_check(
        rows,
        "SAP12_prohibited_claims_cover_overclaim_risks",
        "claim_control",
        "pass" if all(term in prohibited for term in ["broad robustness", "oracle", "cross-heldout aggregate"]) else "fail",
        "Prohibited claims cover broad robustness, oracle-as-selector, and aggregate-confirmatory overclaims.",
        " | ".join(plan["prohibited_claims"]),
        "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/MANUSCRIPT_CLAIM_QA.md",
        "Claim controls are explicit in the statistical plan.",
        "The audit cannot certify author-edited future manuscript text unless claim QA is rerun.",
    )

    add_check(
        rows,
        "SAP13_package_gates_current",
        "package_qc",
        "pass" if provenance["complete_count"] == len(provenance["artifacts"]) else "fail",
        "Artifact provenance is complete and the current publication-verification snapshot is recorded.",
        f"verification={verification['summary']['status']}; provenance={provenance['complete_count']}/{len(provenance['artifacts'])}",
        "materials/PUBLICATION_PACKAGE_VERIFICATION.md; tables/artifact_provenance.md",
        "The analysis-plan audit verifies saved analysis coverage; final package gate pass is enforced by publication verification and smoke tests to avoid a circular dependency.",
        "External DOI and author metadata remain outside local automation.",
    )

    failed = [row for row in rows if row["status"] != "pass"]
    return {
        "root": str(root),
        "title": "Statistical Analysis Plan Audit",
        "purpose": (
            "Verify that the statistical analysis plan is implemented by the saved statistical, endpoint-sensitivity, "
            "sample-size, effect-size, negative-result, and external-validity materials."
        ),
        "summary": {
            "status": "pass" if not failed else "fail",
            "check_count": len(rows),
            "failed_checks": len(failed),
            "primary_endpoint": plan["primary_endpoint"]["name"],
            "seed_set_count": len(seed_sets),
            "main_comparison_count": len(plan["main_comparisons"]),
            "cross_heldout_stage_count": len(cross_stats["stage_statistics"]),
            "sample_size_stage_n": sample["summary"]["per_stage_n"],
            "endpoint_scenario_count": endpoint["summary"]["scenario_count"],
            "negative_result_count": negative["summary"]["item_count"],
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
        },
        "rows": rows,
        "interpretation": (
            "This audit checks saved analysis-plan coverage and reporting consistency. It does not rerun simulations "
            "or convert the fixed seed batches into confirmatory population-level evidence."
        ),
    }


FIELDS = ["check_id", "section", "status", "expected", "observed", "evidence", "interpretation", "boundary"]


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({key: row[key] for key in FIELDS})


def write_markdown(report, path):
    lines = [
        "# Statistical Analysis Plan Audit",
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
            "## Checks",
            "",
            "| check_id | section | status | expected | observed | evidence | interpretation | boundary |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        safe = {key: str(value).replace("|", "\\|") for key, value in row.items()}
        lines.append(
            "| {check_id} | {section} | {status} | {expected} | {observed} | `{evidence}` | {interpretation} | {boundary} |".format(
                **safe
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "STATISTICAL_ANALYSIS_PLAN_AUDIT.json"
    out_md = materials / "STATISTICAL_ANALYSIS_PLAN_AUDIT.md"
    out_csv = materials / "STATISTICAL_ANALYSIS_PLAN_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(
        json.dumps(
            {"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]},
            indent=2,
        )
    )
    if report["summary"]["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
