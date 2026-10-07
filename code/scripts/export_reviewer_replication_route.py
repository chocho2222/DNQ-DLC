#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def route(
    route_id,
    tier,
    objective,
    command,
    expected_outputs,
    evidence,
    reviewer_decision,
    cost_class,
    boundary,
    status,
):
    return {
        "route_id": route_id,
        "tier": tier,
        "objective": objective,
        "command": command,
        "expected_outputs": expected_outputs,
        "evidence": evidence,
        "reviewer_decision": reviewer_decision,
        "cost_class": cost_class,
        "boundary": boundary,
        "status": status,
    }


def quickstart_step(step_id, reviewer_time, action, command, pass_criterion, outputs, notes):
    return {
        "step_id": step_id,
        "reviewer_time": reviewer_time,
        "action": action,
        "command": command,
        "pass_criterion": pass_criterion,
        "outputs": outputs,
        "notes": notes,
    }


def command_for(provenance, name):
    for artifact in provenance["artifacts"]:
        if artifact["name"] == name:
            return artifact["command"]
    return ""


def build_report(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    trace = load_json(root / "materials" / "REVIEWER_EVIDENCE_TRACE_PACK.json")
    navigator = load_json(root / "materials" / "REPORTING_SUPPLEMENT_NAVIGATOR.json")
    figure_qc = load_json(root / "materials" / "FIGURE_TECHNICAL_QC.json")
    figure_source = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    selector_audit = load_json(root / "materials" / "SELECTOR_DECISION_AUDIT.json")
    seed_partition = load_json(root / "materials" / "SEED_PARTITION_AUDIT.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    compute = load_json(root / "tables" / "compute_cost_report.json")
    self_referential_dashboard_ids = {
        "E4d_reviewer_evidence_trace",
        "E4g_reporting_supplement_navigator",
        "E4h_reviewer_replication_route",
        "E4i_manuscript_supplement_assembly",
    }
    core_dashboard_review_required_count = sum(
        1
        for item in dashboard["dashboard_rows"]
        if item["status"] == "review_required" and item["id"] not in self_referential_dashboard_ids
    )

    py_prefix = "PYTHONPATH=scripts:. /home/itrc/.conda/envs/vlm_planner/bin/python"
    rows = [
        route(
            "RR0_start_here",
            "tier0_fast_integrity",
            "Confirm the saved package is internally consistent before reading individual claims.",
            f"{py_prefix} scripts/run_publication_smoke_test.py --root {root} --write-report",
            "materials/PUBLICATION_SMOKE_TEST.md/json/csv",
            "materials/PUBLICATION_SMOKE_TEST.md; materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            f"Proceed if smoke status is {smoke['summary']['status']} and failed checks are {smoke['summary']['failed_checks']}.",
            "seconds_to_minutes_no_rollout",
            "This verifies saved artifacts and does not rerun simulations.",
            smoke["summary"]["status"],
        ),
        route(
            "RR1_package_gates",
            "tier0_fast_integrity",
            "Check all local package gates, stale-count scans, claim QA, release coverage, and key artifacts.",
            f"{py_prefix} scripts/export_publication_package_verification.py --root {root}",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md/json/csv",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            f"Proceed if verification status is {verification['summary']['status']} with {verification['summary']['failed_gates']} failed gates.",
            "seconds_to_minutes_no_rollout",
            "Local gate pass is not journal acceptance.",
            verification["summary"]["status"],
        ),
        route(
            "RR2_navigation",
            "tier0_fast_integrity",
            "Open the one-page navigator and trace pack to locate Methods, figures, statistics, ethics, archive, and author-action evidence.",
            f"{py_prefix} scripts/export_reporting_supplement_navigator.py --root {root} && {py_prefix} scripts/export_reviewer_evidence_trace_pack.py --root {root}",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md; materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md; materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
            (
                "Proceed if core dashboard review-required rows are "
                f"{core_dashboard_review_required_count}; navigator/trace self-references are refreshed in the final closure pass."
            ),
            "seconds_to_minutes_no_rollout",
            "Navigation files point to authoritative evidence; they do not replace source data.",
            "pass" if core_dashboard_review_required_count == 0 else "review_required",
        ),
        route(
            "RR3_statistical_consistency",
            "tier1_result_numbers",
            "Recompute consistency checks for locked results, expanded held-out summaries, intervals, and table/manuscript numbers.",
            f"{py_prefix} scripts/export_statistical_consistency_audit.py --root {root}",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.md/json/csv",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.md; tables/full_statistical_report.md",
            (
                f"Proceed if {stats['summary']['check_count']} checks have "
                f"{stats['summary']['failed_checks']} failures and status {stats['summary']['status']}."
            ),
            "seconds_to_minutes_no_rollout",
            "Statistics are descriptive for registered seed sets and do not support broad robustness claims.",
            stats["summary"]["status"],
        ),
        route(
            "RR4_seed_partition",
            "tier1_result_numbers",
            "Verify that locked, held-out, targeted-repair, and post-repair external-validation seed labels are preserved.",
            f"{py_prefix} scripts/export_seed_partition_audit.py --root {root}",
            "materials/SEED_PARTITION_AUDIT.md/json/csv",
            "materials/SEED_PARTITION_AUDIT.md; materials/STUDY_PROTOCOL_AND_DEVIATIONS.md",
            (
                f"Proceed if unexpected overlaps={seed_partition['summary']['unexpected_overlap_count']} "
                f"and protocol review rows={seed_partition['summary']['protocol_review_count']}."
            ),
            "seconds_to_minutes_no_rollout",
            "Heldout3 targeted repair remains diagnostic reuse; heldout4 is post-repair external validation with partial transfer.",
            seed_partition["summary"]["status"],
        ),
        route(
            "RR5_selector_decisions",
            "tier1_result_numbers",
            "Replay selector decisions from saved probe-only fields to check probe-only online decision-making and no full-rollout label leakage.",
            f"{py_prefix} scripts/export_selector_decision_audit.py --root {root}",
            "materials/SELECTOR_DECISION_AUDIT.md/json/csv",
            "materials/SELECTOR_DECISION_AUDIT.md; materials/SELECTOR_DECISION_AUDIT_ROWS.csv",
            (
                f"Proceed if status={selector_audit['summary']['status']}, "
                f"mismatches={selector_audit['summary']['total_mismatch_count']}, "
                f"forbidden probe fields={selector_audit['summary']['total_forbidden_probe_field_count']}."
            ),
            "seconds_to_minutes_no_rollout",
            "Selector replay validates saved decision logic, not new driving performance.",
            selector_audit["summary"]["status"],
        ),
        route(
            "RR6_figure_source_data",
            "tier2_figures_and_source_data",
            "Check figure manifests, source-data files, and technical export requirements.",
            f"{py_prefix} scripts/export_figure_source_data_audit.py --root {root} && {py_prefix} scripts/export_figure_technical_qc.py --root {root}",
            "materials/FIGURE_SOURCE_DATA_AUDIT.md; materials/FIGURE_TECHNICAL_QC.md",
            "figures/figure_1_source_data.csv; figures/figure_2_source_data.csv; figures/figure_3_source_data.csv",
            (
                f"Proceed if figure source incomplete={figure_source['summary']['incomplete_count']} "
                f"and technical QC status={figure_qc['summary']['status']}."
            ),
            "seconds_to_minutes_no_rollout",
            "Figures and GIFs are qualitative/summary evidence and do not replace strict seed-level tables.",
            "pass" if figure_source["summary"]["incomplete_count"] == 0 and figure_qc["summary"]["status"] == "pass" else "review_required",
        ),
        route(
            "RR7_archive_freeze",
            "tier2_figures_and_source_data",
            "Check file-level release coverage, checksums, citation metadata, and archive-facing documentation.",
            f"{py_prefix} scripts/export_release_archive_manifest.py --root {root} && {py_prefix} scripts/export_final_checksum_freeze_record.py --root {root}",
            "materials/RELEASE_ARCHIVE_MANIFEST.md; materials/FINAL_CHECKSUM_FREEZE_RECORD.md",
            "materials/ARCHIVE_README.md; materials/CITATION_METADATA.md; materials/FAIR_ARCHIVE_METADATA.md",
            "Proceed if release manifest and checksum freeze remain ready, then add DOI/URL after public deposition.",
            "minutes_no_rollout",
            "Local archive freeze is not a public DOI/accession.",
            "ready_with_author_completion",
        ),
        route(
            "RR8_fast_regeneration_bundle",
            "tier3_fast_regeneration",
            "Regenerate all reviewer-facing metadata, dashboard, bundle, navigator, smoke test, and trace files from saved artifacts.",
            (
                f"{py_prefix} scripts/export_reporting_supplement_navigator.py --root {root} && "
                f"{py_prefix} scripts/export_final_submission_file_bundle.py --root {root} && "
                f"{py_prefix} scripts/export_submission_readiness_dashboard.py --root {root} && "
                f"{py_prefix} scripts/run_publication_smoke_test.py --root {root} --write-report"
            ),
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md; materials/FINAL_SUBMISSION_FILE_BUNDLE.md; materials/SUBMISSION_READINESS_DASHBOARD.md; materials/PUBLICATION_SMOKE_TEST.md",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md; materials/SUBMISSION_READINESS_DASHBOARD.md",
            (
                f"Proceed if core dashboard review_required={core_dashboard_review_required_count} "
                f"and smoke failed={smoke['summary']['failed_checks']}."
            ),
            "minutes_no_rollout",
            "This path updates saved reports and metadata; it does not rerun expensive Box2D rollouts.",
            "pass" if core_dashboard_review_required_count == 0 and smoke["summary"]["failed_checks"] == 0 else "review_required",
        ),
        route(
            "RR9_selective_rollout_rerun",
            "tier4_expensive_rollout_optional",
            "Optionally rerun registered rollout suites or selector probes when reviewers require end-to-end reproduction.",
            "Use the relevant commands in tables/artifact_provenance.md for main suites, held-out suites, or selector probes.",
            "evaluations/*/multiseed_suite_summary.json; tables/*_report.md; tables/*_rows.csv",
            "tables/artifact_provenance.md; tables/compute_cost_report.md",
            (
                f"Use GPU resources according to registered commands; saved compute summary records "
                f"{compute['summary']['full_rollout_simulated_steps']} full-rollout simulated steps."
            ),
            "expensive_gpu_rollout",
            "Optional reruns should preserve registered seeds, methods, endpoints, and no-broad-robustness boundaries.",
            "optional",
        ),
        route(
            "RR10_artifact_specific_command_lookup",
            "tier4_expensive_rollout_optional",
            "Use provenance as the command source of truth for any single artifact a reviewer chooses to rerun.",
            f"{py_prefix} scripts/export_artifact_provenance.py --root {root}",
            "tables/artifact_provenance.md/json",
            "tables/artifact_provenance.md; materials/ARTIFACT_DEPENDENCY_MAP.md",
            f"Proceed if artifact provenance is {provenance['complete_count']}/{len(provenance['artifacts'])}.",
            "depends_on_selected_artifact",
            "Provenance lists commands; rerun cost depends on the selected artifact.",
            "ready",
        ),
    ]

    review_required = [item for item in rows if item["status"] == "review_required"]
    optional = [item for item in rows if item["status"] == "optional"]
    expensive = [item for item in rows if item["cost_class"].startswith("expensive")]
    quickstart = [
        quickstart_step(
            "QS1_saved_package_integrity",
            "under_10_minutes_no_rollout",
            "Run the smoke test and package gate before reading any result claim.",
            (
                f"{py_prefix} scripts/run_publication_smoke_test.py --root {root} --write-report && "
                f"{py_prefix} scripts/export_publication_package_verification.py --root {root}"
            ),
            (
                f"Smoke status={smoke['summary']['status']} with failed_checks={smoke['summary']['failed_checks']}; "
                f"verification status={verification['summary']['status']} with failed_gates={verification['summary']['failed_gates']}."
            ),
            "materials/PUBLICATION_SMOKE_TEST.md; materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "No Box2D rollout rerun; verifies saved artifacts, claims, and package gates.",
        ),
        quickstart_step(
            "QS2_main_claim_numbers",
            "under_10_minutes_no_rollout",
            "Check manuscript-facing statistics, seed labels, selector decisions, and narrative counts.",
            (
                f"{py_prefix} scripts/export_statistical_consistency_audit.py --root {root} && "
                f"{py_prefix} scripts/export_seed_partition_audit.py --root {root} && "
                f"{py_prefix} scripts/export_selector_decision_audit.py --root {root} && "
                f"{py_prefix} scripts/export_narrative_numeric_consistency_audit.py --root {root}"
            ),
            (
                f"Statistical consistency status={stats['summary']['status']} with failed_checks={stats['summary']['failed_checks']}; "
                f"seed partition status={seed_partition['summary']['status']}; "
                f"selector audit status={selector_audit['summary']['status']}."
            ),
            "materials/STATISTICAL_CONSISTENCY_AUDIT.md; materials/SEED_PARTITION_AUDIT.md; materials/SELECTOR_DECISION_AUDIT.md; materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.md",
            "Confirms the headline numbers and diagnostic-reuse labels without generating new rollouts.",
        ),
        quickstart_step(
            "QS3_figures_source_data",
            "under_10_minutes_no_rollout",
            "Verify that main figures have source data and technical export QC.",
            (
                f"{py_prefix} scripts/export_figure_source_data_audit.py --root {root} && "
                f"{py_prefix} scripts/export_figure_technical_qc.py --root {root}"
            ),
            (
                f"Figure source incomplete_count={figure_source['summary']['incomplete_count']}; "
                f"figure technical QC status={figure_qc['summary']['status']}."
            ),
            "materials/FIGURE_SOURCE_DATA_AUDIT.md; materials/FIGURE_TECHNICAL_QC.md; figures/*_source_data.csv",
            "Checks source-data traceability; GIFs remain qualitative orientation only.",
        ),
        quickstart_step(
            "QS4_archive_checksum",
            "minutes_no_rollout",
            "Regenerate the local release manifest and checksum freeze after any report refresh.",
            (
                f"{py_prefix} scripts/export_release_archive_manifest.py --root {root} && "
                f"{py_prefix} scripts/export_final_checksum_freeze_record.py --root {root}"
            ),
            "Freeze status should be ready_for_author_freeze, with missing_sha_count=0.",
            "materials/RELEASE_ARCHIVE_MANIFEST.md; materials/FINAL_CHECKSUM_FREEZE_RECORD.md",
            "Local checksum readiness is not a public DOI/accession or journal submission receipt.",
        ),
        quickstart_step(
            "QS5_optional_gpu_rerun_lookup",
            "expensive_optional_gpu",
            "If a reviewer requests end-to-end reruns, select a registered artifact and use provenance as the command source of truth.",
            f"{py_prefix} scripts/export_artifact_provenance.py --root {root}",
            f"Artifact provenance should remain {provenance['complete_count']}/{len(provenance['artifacts'])}; rerun only the selected registered command.",
            "tables/artifact_provenance.md/json; evaluations/*; tables/*_report.md",
            (
                f"Optional rollout reruns should use GPU resources and preserve registered seeds/endpoints; "
                f"saved full-rollout simulated steps={compute['summary']['full_rollout_simulated_steps']}."
            ),
        ),
    ]
    return {
        "root": str(root),
        "title": "Reviewer Replication Route",
        "purpose": (
            "Provide a tiered reviewer replication route from fast saved-artifact integrity checks to optional "
            "GPU rollout reruns, while preserving simulator-only and diagnostic-oracle boundaries."
        ),
        "quickstart": quickstart,
        "rows": rows,
        "summary": {
            "status": "pass" if not review_required else "review_required",
            "quickstart_count": len(quickstart),
            "route_count": len(rows),
            "review_required_count": len(review_required),
            "optional_route_count": len(optional),
            "expensive_route_count": len(expensive),
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "data_dictionary_complete": load_json(root / "materials" / "DATA_DICTIONARY.json")["summary"]["complete"],
            "dashboard_review_required": dashboard["summary"]["review_required_row_count"],
            "core_dashboard_review_required": core_dashboard_review_required_count,
        },
        "interpretation": (
            "This route is an audit plan, not a new experiment. Fast tiers verify saved evidence; optional rollout tiers "
            "should be used only when reviewers require end-to-end reruns on appropriate GPU resources."
        ),
    }


def write_csv(report, path):
    fields = [
        "kind",
        "step_or_route_id",
        "route_id",
        "tier",
        "objective",
        "command",
        "expected_outputs",
        "evidence",
        "reviewer_decision",
        "cost_class",
        "boundary",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["quickstart"]:
            writer.writerow(
                {
                    "kind": "quickstart",
                    "step_or_route_id": item["step_id"],
                    "route_id": "",
                    "tier": item["reviewer_time"],
                    "objective": item["action"],
                    "command": item["command"],
                    "expected_outputs": item["outputs"],
                    "evidence": item["outputs"],
                    "reviewer_decision": item["pass_criterion"],
                    "cost_class": item["reviewer_time"],
                    "boundary": item["notes"],
                    "status": "ready",
                }
            )
        for item in report["rows"]:
            writer.writerow({"kind": "route", "step_or_route_id": item["route_id"], **item})


def write_markdown(report, path):
    lines = [
        "# Reviewer Replication Route",
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
            "## Reviewer Quickstart",
            "",
            "| step | time/cost | action | command | pass criterion | outputs | notes |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["quickstart"]:
        lines.append(
            f"| {item['step_id']} | {item['reviewer_time']} | {item['action']} | `{item['command']}` | "
            f"{item['pass_criterion']} | `{item['outputs']}` | {item['notes']} |"
        )
    lines.extend(
        [
            "",
            "## Routes",
            "",
            "| route | tier | status | cost | objective | command | expected outputs | evidence | reviewer decision | boundary |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['route_id']} | {item['tier']} | {item['status']} | {item['cost_class']} | "
            f"{item['objective']} | `{item['command']}` | `{item['expected_outputs']}` | "
            f"`{item['evidence']}` | {item['reviewer_decision']} | {item['boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export tiered reviewer replication route.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "REVIEWER_REPLICATION_ROUTE.json"
    out_md = materials / "REVIEWER_REPLICATION_ROUTE.md"
    out_csv = materials / "REVIEWER_REPLICATION_ROUTE.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
