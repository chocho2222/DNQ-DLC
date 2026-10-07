#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def method_summary(report, method):
    for row in report["method_summaries"]:
        if row["method"] == method:
            return row
    raise KeyError(method)


def stage_key(row):
    return (row["heldout"], row["stage"])


def as_int(value):
    return int(float(value))


def as_float(value):
    return float(value)


def check_row(checks, check_id, category, description, passed, expected, observed, evidence, interpretation):
    checks.append(
        {
            "id": check_id,
            "category": category,
            "status": "pass" if passed else "fail",
            "description": description,
            "expected": expected,
            "observed": observed,
            "evidence": evidence,
            "interpretation": interpretation,
        }
    )


def build_report(root):
    full = load_json(root / "tables" / "full_statistical_report.json")
    synthesis = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")
    supplement = load_json(root / "tables" / "cross_heldout_statistical_supplement.json")
    sample = load_json(root / "materials" / "SAMPLE_SIZE_SENSITIVITY_BRIEF.json")
    figure_audit = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    fig3_rows = read_csv(root / "figures" / "figure_3_source_data.csv")
    stat_rows = read_csv(root / "tables" / "cross_heldout_statistical_supplement_rows.csv")
    method_rows = read_csv(root / "tables" / "full_statistical_report_method_summary.csv")

    checks = []
    overtake = method_summary(full, "main:overtake_base_only")
    graph_adaptive = method_summary(full, "adaptive:graph_adaptive_shield")
    method_csv = {row["method"]: row for row in method_rows}
    check_row(
        checks,
        "SC01_locked_overtake_baseline",
        "locked_method_summary",
        "Locked overtake baseline pass count is consistent between JSON and CSV method summaries.",
        overtake["pass_count"] == as_int(method_csv["main:overtake_base_only"]["pass_count"]) == 8,
        "8/10",
        f"{overtake['pass_count']}/{overtake['n']} and CSV {method_csv['main:overtake_base_only']['pass_count']}/{method_csv['main:overtake_base_only']['n']}",
        "tables/full_statistical_report.json; tables/full_statistical_report_method_summary.csv",
        "Strongest rule baseline remains the conservative locked comparator.",
    )
    check_row(
        checks,
        "SC02_locked_graph_adaptive",
        "locked_method_summary",
        "Graph-adaptive shield pass count is consistent between JSON and CSV method summaries.",
        graph_adaptive["pass_count"] == as_int(method_csv["adaptive:graph_adaptive_shield"]["pass_count"]) == 7,
        "7/10",
        f"{graph_adaptive['pass_count']}/{graph_adaptive['n']} and CSV {method_csv['adaptive:graph_adaptive_shield']['pass_count']}/{method_csv['adaptive:graph_adaptive_shield']['n']}",
        "tables/full_statistical_report.json; tables/full_statistical_report_method_summary.csv",
        "Learned/shielded method narrows but does not surpass the strongest rule baseline.",
    )

    synth_by_stage = {stage_key(row): row for row in synthesis["entries"]}
    stat_by_stage = {stage_key(row): row for row in supplement["stage_statistics"]}
    fig_by_stage = {stage_key(row): row for row in fig3_rows}
    csv_stat_by_stage = {stage_key(row): row for row in stat_rows}
    for key, synth in synth_by_stage.items():
        stat = stat_by_stage[key]
        fig = fig_by_stage[key]
        csv_stat = csv_stat_by_stage[key]
        expected = f"{synth['selector_pass_count']}/{synth['oracle_pass_count']}/{synth['n']}"
        observed = (
            f"stat {stat['selector_pass_count']}/{stat['oracle_pass_count']}/{stat['n']}; "
            f"figure {fig['selector_pass_count']}/{fig['oracle_pass_count']}/{fig['n']}; "
            f"csv {csv_stat['selector_pass_count']}/{csv_stat['oracle_pass_count']}/{csv_stat['n']}"
        )
        passed = (
            synth["selector_pass_count"] == stat["selector_pass_count"] == as_int(fig["selector_pass_count"]) == as_int(csv_stat["selector_pass_count"])
            and synth["oracle_pass_count"] == stat["oracle_pass_count"] == as_int(fig["oracle_pass_count"]) == as_int(csv_stat["oracle_pass_count"])
            and synth["n"] == stat["n"] == as_int(fig["n"]) == as_int(csv_stat["n"])
            and len(synth["selector_miss_seeds"]) == as_int(fig["selector_miss_count"]) == stat["selector_miss_count"] == as_int(csv_stat["selector_miss_count"])
            and len(synth["candidate_gap_seeds"]) == as_int(fig["candidate_gap_count"]) == stat["candidate_gap_count"] == as_int(csv_stat["candidate_gap_count"])
        )
        check_row(
            checks,
            f"SC_stage_{key[0]}_{key[1]}",
            "cross_heldout_stage",
            f"Cross-heldout stage counts match synthesis JSON, statistical supplement, Figure 3 source data, and supplement CSV for {key[0]} {key[1]}.",
            passed,
            expected,
            observed,
            "tables/cross_heldout_validation_synthesis.json; tables/cross_heldout_statistical_supplement.json; tables/cross_heldout_statistical_supplement_rows.csv; figures/figure_3_source_data.csv",
            "Stage-level figure and statistical evidence are synchronized.",
        )

    agg = synthesis["aggregate_expanded_or_later"]
    supp_agg = supplement["aggregate_expanded_or_later"]
    sample_summary = sample["summary"]
    check_row(
        checks,
        "SC10_cross_heldout_aggregate",
        "cross_heldout_aggregate",
        "Expanded-or-later aggregate selector/oracle counts match synthesis, statistical supplement, and sample-size brief.",
        agg["n"] == supp_agg["n"] == 50
        and agg["selector_pass_count"] == supp_agg["selector_pass_count"] == 31
        and agg["oracle_pass_count"] == supp_agg["oracle_pass_count"] == 45
        and sample_summary["expanded_or_later_selector"] == "31/50",
        "selector 31/50; oracle 45/50",
        f"synthesis {agg}; supplement selector {supp_agg['selector_pass_count']}/{supp_agg['n']} oracle {supp_agg['oracle_pass_count']}/{supp_agg['n']}; sample {sample_summary['expanded_or_later_selector']}",
        "tables/cross_heldout_validation_synthesis.json; tables/cross_heldout_statistical_supplement.json; materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
        "Aggregate is descriptive and remains aligned across statistical materials.",
    )
    check_row(
        checks,
        "SC11_figure_source_data_audit",
        "figure_source_data",
        "Figure/source-data audit reports all registered figures complete.",
        figure_audit["summary"]["complete_count"] == figure_audit["summary"]["figure_count"] == 3,
        "3/3 figures complete",
        f"{figure_audit['summary']['complete_count']}/{figure_audit['summary']['figure_count']}",
        "materials/FIGURE_SOURCE_DATA_AUDIT.json",
        "Figure packaging and source-data traceability are complete.",
    )
    check_row(
        checks,
        "SC12_publication_verification",
        "package_verification",
        "Publication verification snapshot is recorded without making statistical consistency depend on the final package gate.",
        True,
        "package gate snapshot loaded",
        f"{verification['summary']['status']} with {verification['summary']['failed_gates']} failed gates",
        "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        "Statistical consistency is evaluated from saved numerical artifacts; final package preflight is enforced by publication verification and smoke tests.",
    )

    failed = [row for row in checks if row["status"] != "pass"]
    return {
        "root": str(root),
        "title": "Statistical Consistency Audit",
        "purpose": (
            "Cross-check key numerical claims, method-summary rows, cross-heldout stage counts, Figure 3 source data, "
            "sample-size summaries, and the current publication-verification snapshot."
        ),
        "summary": {
            "check_count": len(checks),
            "failed_checks": len(failed),
            "status": "pass" if not failed else "fail",
            "locked_overtake_baseline": f"{overtake['pass_count']}/{overtake['n']}",
            "locked_graph_adaptive": f"{graph_adaptive['pass_count']}/{graph_adaptive['n']}",
            "expanded_or_later_selector": f"{agg['selector_pass_count']}/{agg['n']}",
            "expanded_or_later_oracle": f"{agg['oracle_pass_count']}/{agg['n']}",
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
        },
        "checks": checks,
        "interpretation": (
            "This audit is a static consistency check over saved statistical artifacts. It does not rerun rollouts "
            "or recompute all statistics from raw traces, but it catches drift among the manuscript-facing numerical summaries."
        ),
    }


FIELDS = ["id", "category", "status", "description", "expected", "observed", "evidence", "interpretation"]


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in report["checks"]:
            writer.writerow({key: row[key] for key in FIELDS})


def write_markdown(report, path):
    lines = [
        "# Statistical Consistency Audit",
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
            "| id | category | status | expected | observed | evidence |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["checks"]:
        lines.append(
            f"| {row['id']} | {row['category']} | {row['status']} | {row['expected']} | "
            f"{row['observed']} | `{row['evidence']}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export statistical consistency audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "STATISTICAL_CONSISTENCY_AUDIT.json"
    out_md = materials / "STATISTICAL_CONSISTENCY_AUDIT.md"
    out_csv = materials / "STATISTICAL_CONSISTENCY_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "status": report["summary"]["status"]}, indent=2))


if __name__ == "__main__":
    main()
