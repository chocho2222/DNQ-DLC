#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def row(section, item, statistic, evidence, interpretation, boundary, status="ready"):
    return {
        "section": section,
        "item": item,
        "statistic": statistic,
        "evidence": evidence,
        "interpretation": interpretation,
        "boundary": boundary,
        "status": status,
    }


def readiness_row(row_id, current_status, current_evidence, confirmatory_upgrade_requirement, blocker_or_boundary, manuscript_instruction):
    return {
        "id": row_id,
        "current_status": current_status,
        "current_evidence": current_evidence,
        "confirmatory_upgrade_requirement": confirmatory_upgrade_requirement,
        "blocker_or_boundary": blocker_or_boundary,
        "manuscript_instruction": manuscript_instruction,
    }


def build_report(root):
    stats = load_json(root / "tables" / "cross_heldout_statistical_supplement.json")
    consistency = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    sample = load_json(root / "materials" / "SAMPLE_SIZE_SENSITIVITY_BRIEF.json")
    endpoint = load_json(root / "materials" / "ENDPOINT_SENSITIVITY_AUDIT.json")
    seed_partition = load_json(root / "materials" / "SEED_PARTITION_AUDIT.json")
    external = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    legends = load_json(root / "materials" / "SUPPLEMENTARY_TABLE_LEGENDS.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    effects = load_json(root / "materials" / "EFFECT_SIZE_UNCERTAINTY_SUMMARY.json")
    prereg = load_json(root / "materials" / "CONFIRMATORY_EXPERIMENT_PREREGISTRATION.json")

    aggregate = stats["aggregate_expanded_or_later"]
    stage_rows = sample["stage_rows"]
    widest_stage = max(stage_rows, key=lambda item: item["selector_ci95_width"])
    endpoint_sensitive = endpoint["summary"]["endpoint_sensitive_stage_methods"]
    method_count = endpoint["summary"]["stage_method_count"]

    rows = [
        row(
            "primary_counts",
            "locked_overtake_baseline",
            consistency["summary"]["locked_overtake_baseline"],
            "materials/STATISTICAL_CONSISTENCY_AUDIT.md; tables/full_statistical_report.md",
            "Strongest preserved rule baseline remains a required comparator.",
            "Comparator strength does not imply proposed-method dominance.",
        ),
        row(
            "primary_counts",
            "locked_graph_adaptive",
            consistency["summary"]["locked_graph_adaptive"],
            "materials/STATISTICAL_CONSISTENCY_AUDIT.md; tables/full_statistical_report.md",
            "Graph-adaptive method narrows but does not exceed the strongest locked rule baseline.",
            "Report as simulator seed-set evidence only.",
        ),
        row(
            "cross_heldout",
            "expanded_or_later_selector",
            (
                f"{aggregate['selector_pass_count']}/{aggregate['n']} "
                f"({aggregate['selector_pass_rate']:.2f}; 95% Wilson "
                f"{aggregate['selector_ci95_low']:.2f}-{aggregate['selector_ci95_high']:.2f})"
            ),
            "tables/cross_heldout_statistical_supplement.md; figures/figure_3_source_data.csv",
            "Aggregated post-expansion selector performance is descriptive and uncertainty-bounded.",
            "The aggregate mixes stages and cannot be presented as a confirmatory robustness estimate.",
        ),
        row(
            "cross_heldout",
            "expanded_or_later_oracle",
            (
                f"{aggregate['oracle_pass_count']}/{aggregate['n']} "
                f"({aggregate['oracle_pass_rate']:.2f}; 95% Wilson "
                f"{aggregate['oracle_ci95_low']:.2f}-{aggregate['oracle_ci95_high']:.2f})"
            ),
            "tables/cross_heldout_statistical_supplement.md",
            "Oracle value is a diagnostic upper bound for candidate availability.",
            "Do not describe oracle rows as online selector outputs.",
        ),
        row(
            "paired_tests",
            "selector_oracle_gap",
            (
                f"gap {aggregate['selector_oracle_gap_count']}/{aggregate['n']}; "
                f"exact paired p={aggregate['mcnemar_exact_p_selector_vs_oracle']:.3g}"
            ),
            "tables/cross_heldout_statistical_supplement_rows.csv",
            "Exact paired gap quantifies selector misses relative to the diagnostic oracle.",
            "P-values are descriptive diagnostics over small, fixed seed batches.",
        ),
        row(
            "effect_sizes",
            "selector_oracle_magnitude",
            (
                f"aggregate selector-oracle rate difference="
                f"{effects['summary']['aggregate_selector_minus_oracle_rate']:.2f}; "
                f"gap={effects['summary']['aggregate_gap_per_10_seeds']:.1f} per 10 seeds"
            ),
            "materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.md; materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.csv",
            "Magnitude-focused effect rows separate practical selector shortfall from p-value reporting.",
            "Effect sizes are descriptive for fixed simulator seed batches and do not establish broad robustness.",
        ),
        row(
            "sample_size",
            "widest_stage_interval",
            (
                f"{widest_stage['id']} selector Wilson width="
                f"{widest_stage['selector_ci95_width']:.3f}"
            ),
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md",
            "Per-stage n=10 intervals are wide and should be visibly reported.",
            "Do not convert small-N held-out stages into broad robustness claims.",
        ),
        row(
            "sample_size",
            "future_precision_target",
            (
                f"n={sample['summary']['n_for_assumed_80pct_width_le_0_20']} for assumed 80% pass-rate "
                "Wilson width <=0.20"
            ),
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md",
            "Future confirmatory validation should freeze policy/selector design and use larger seed batches.",
            "Planning rows are not evidence for current performance.",
        ),
        row(
            "endpoint_sensitivity",
            "endpoint_sensitive_stage_methods",
            f"{endpoint_sensitive}/{method_count}",
            "materials/ENDPOINT_SENSITIVITY_AUDIT.md",
            "Most stage-method summaries change under nearby endpoint thresholds.",
            "Endpoint sensitivity supports transparent limitations, not relaxed pass criteria.",
        ),
        row(
            "seed_partition",
            "partition_status",
            (
                f"{seed_partition['summary']['primary_seed_set_count']} primary seed sets; "
                f"unexpected overlaps={seed_partition['summary']['unexpected_overlap_count']}"
            ),
            "materials/SEED_PARTITION_AUDIT.md",
            "Seed partition audit supports interpretation of locked, held-out, diagnostic, and post-repair rows.",
            "heldout3 targeted repair remains diagnostic reuse; heldout4 remains partial-transfer validation.",
        ),
        row(
            "external_validity",
            "bounded_external_claim",
            (
                f"selector {external['summary']['expanded_or_later_selector']}; "
                f"oracle {external['summary']['expanded_or_later_oracle']}"
            ),
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "External-validity statement keeps held-out results bounded to simulator seed batches.",
            "No real-road, VLM, safety-certification, or broad robustness claim is supported.",
        ),
        row(
            "supplement_packaging",
            "statistical_tables_and_legends",
            (
                f"{legends['summary']['supplementary_table_count']} supplementary-table legends; "
                f"{legends['summary']['source_data_count']} source-data legends"
            ),
            "materials/SUPPLEMENTARY_TABLE_LEGENDS.md; materials/DATA_DICTIONARY.md",
            "Statistical tables have draft legends and dictionary links for reviewer inspection.",
            "Final numbering and journal style remain author actions.",
        ),
    ]
    review_required = [item for item in rows if item["status"] != "ready"]
    confirmatory_readiness = [
        readiness_row(
            "CR1_locked_baseline_comparison",
            "descriptive_locked_seed_result",
            "Locked baseline 8/10 and graph-adaptive 7/10 on the registered 10-seed locked set.",
            "Freeze comparator set and evaluate a larger independent seed batch before making superiority claims.",
            "Current result does not show learned/shielded dominance over the strongest rule baseline.",
            "Use as baseline-fairness evidence, not as a superiority test.",
        ),
        readiness_row(
            "CR2_heldout1_selector_positive",
            "positive_control",
            "Heldout1 selector reaches 10/10 and matches diagnostic oracle.",
            "Replicate on additional disjoint held-out sets without post-hoc selector/candidate edits.",
            "Heldout2 and heldout3 prevent generalizing heldout1 to robustness.",
            "Report heldout1 together with heldout2/heldout3/heldout4 boundaries.",
        ),
        readiness_row(
            "CR3_heldout2_candidate_expansion",
            "exploratory_or_method_development",
            "Candidate expansion improves heldout2 selector to 7/10 and oracle to 10/10.",
            "Freeze the expanded candidate pool and selector before external validation; avoid using heldout2 as both design and validation evidence.",
            "Heldout2 was part of iterative method development and still has selector misses.",
            "Use as development progress, not confirmatory external validation.",
        ),
        readiness_row(
            "CR4_heldout3_targeted_repair",
            "diagnostic_reuse",
            "Heldout3-targeted repair closes candidate coverage for seeds 157 and 173.",
            "Validate any targeted repair on fresh unused seeds; heldout4 is the first post-repair external validation.",
            "Targeted repair reuses heldout3 failures and cannot be called independent validation.",
            "Label as diagnostic targeted repair wherever reported.",
        ),
        readiness_row(
            "CR5_heldout4_partial_transfer",
            "post_repair_external_validation_with_partial_transfer",
            "Heldout4 selector is 6/10 against an 8/10 diagnostic oracle, with selector misses and candidate gaps retained.",
            (
                f"Freeze the seven-candidate selector and run at least n={sample['summary']['n_for_assumed_80pct_width_le_0_20']} "
                "fresh seeds for narrower descriptive precision, or n=100+ if a Wilson lower-bound target near 0.70 is desired."
            ),
            "Heldout4 supports partial transfer, not broad robustness.",
            "Report as bounded external validation after targeted repair.",
        ),
        readiness_row(
            "CR6_cross_heldout_aggregate",
            "descriptive_synthesis",
            "Expanded-or-later selector 31/50 versus diagnostic oracle 45/50, with aggregate selector-oracle gap of 14 seeds.",
            "Pre-register a single frozen analysis over a fresh seed batch before using aggregate estimates as confirmatory performance claims.",
            "The aggregate mixes development, diagnostic, and post-repair validation stages.",
            "Use to summarize failure modes and selector-oracle gap, not as robustness evidence.",
        ),
        readiness_row(
            "CR7_future_confirmatory_protocol",
            "planned_not_executed",
            "Confirmatory preregistration material exists for a future larger-N validation.",
            "Complete a new frozen-policy run under the preregistered protocol and archive commands/results before upgrading claims.",
            (
                f"Current preregistration has {prereg['summary']['row_count']} planning rows, including "
                f"{prereg['summary']['required_before_new_external_validation']} required-before-validation row(s); "
                "it is planning material, not outcome evidence."
            ),
            "Mention only as future validation plan or revision-ready protocol.",
        ),
    ]
    return {
        "root": str(root),
        "title": "Statistical Reporting Appendix",
        "purpose": (
            "Consolidate reviewer-facing statistical reporting choices, uncertainty intervals, exact tests, "
            "sample-size limitations, endpoint sensitivity, and claim boundaries."
        ),
        "scope": {
            "reruns_rollouts": False,
            "confirmatory_claim": False,
            "confirmatory_readiness": "not_yet_confirmatory",
            "primary_boundary": (
                "All statistics are computed from saved simulator artifacts. They are descriptive for the "
                "specified seed partitions and do not establish broad robustness or real-world readiness."
            ),
        },
        "rows": rows,
        "confirmatory_readiness": confirmatory_readiness,
        "summary": {
            "status": "pass" if not review_required else "review_required",
            "row_count": len(rows),
            "confirmatory_readiness_row_count": len(confirmatory_readiness),
            "review_required_count": len(review_required),
            "stage_statistic_count": len(stats["stage_statistics"]),
            "sample_stage_count": sample["summary"]["stage_count"],
            "endpoint_sensitive_stage_methods": endpoint_sensitive,
            "endpoint_stage_method_count": method_count,
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "effect_size_uncertainty_status": effects["summary"]["status"],
            "statistical_consistency_status": consistency["summary"]["status"],
            "confirmatory_preregistration_rows": prereg["summary"]["row_count"],
            "confirmatory_preregistration_required_before_validation": prereg["summary"]["required_before_new_external_validation"],
        },
        "interpretation": (
            "This appendix is a reporting and audit layer. It consolidates statistics already present in the "
            "package and should be cited alongside the source-data CSVs and statistical supplement."
        ),
    }


def write_csv(report, path):
    fields = ["kind", "section", "item", "statistic", "evidence", "interpretation", "boundary", "status"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({"kind": "reporting_row", **row})
        for row in report["confirmatory_readiness"]:
            writer.writerow(
                {
                    "kind": "confirmatory_readiness",
                    "section": "confirmatory_readiness",
                    "item": row["id"],
                    "statistic": row["current_status"],
                    "evidence": row["current_evidence"],
                    "interpretation": row["confirmatory_upgrade_requirement"],
                    "boundary": row["blocker_or_boundary"],
                    "status": "ready",
                }
            )


def write_markdown(report, path):
    lines = [
        "# Statistical Reporting Appendix",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Scope",
        "",
    ]
    for key, value in report["scope"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Summary", ""])
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Reporting Rows",
            "",
            "| section | item | statistic | evidence | interpretation | boundary | status |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['section']} | {item['item']} | {item['statistic']} | "
            f"`{item['evidence']}` | {item['interpretation']} | {item['boundary']} | {item['status']} |"
        )
    lines.extend(
        [
            "",
            "## Confirmatory-readiness Ladder",
            "",
            "| id | current status | current evidence | confirmatory upgrade requirement | blocker/boundary | manuscript instruction |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in report["confirmatory_readiness"]:
        lines.append(
            f"| {item['id']} | {item['current_status']} | {item['current_evidence']} | "
            f"{item['confirmatory_upgrade_requirement']} | {item['blocker_or_boundary']} | {item['manuscript_instruction']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export statistical reporting appendix.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "STATISTICAL_REPORTING_APPENDIX.json"
    out_md = materials / "STATISTICAL_REPORTING_APPENDIX.md"
    out_csv = materials / "STATISTICAL_REPORTING_APPENDIX.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
