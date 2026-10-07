#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def join_list(values):
    return "; ".join(str(value) for value in values)


def row(
    roadmap_id,
    gap_id,
    status,
    current_evidence,
    frozen_controls,
    required_future_evidence,
    decision_gate,
    failure_policy,
    claim_boundary,
    gpu_execution,
):
    return {
        "roadmap_id": roadmap_id,
        "gap_id": gap_id,
        "status": status,
        "current_evidence": current_evidence,
        "frozen_controls": frozen_controls,
        "required_future_evidence": required_future_evidence,
        "decision_gate": decision_gate,
        "failure_policy": failure_policy,
        "claim_boundary": claim_boundary,
        "gpu_execution": gpu_execution,
    }


def build_report(root):
    readiness = load_json(root / "materials" / "TOP_JOURNAL_READINESS_CHECKLIST.json")
    prereg = load_json(root / "materials" / "CONFIRMATORY_EXPERIMENT_PREREGISTRATION.json")
    freeze = load_json(root / "materials" / "CONFIRMATORY_FREEZE_AUDIT.json")
    freeze_config = load_json(root / "materials" / "CONFIRMATORY_FREEZE_CONFIG.json")
    gpu = load_json(root / "materials" / "GPU_RERUN_READINESS.json")
    sample = load_json(root / "materials" / "SAMPLE_SIZE_SENSITIVITY_BRIEF.json")
    effect = load_json(root / "materials" / "EFFECT_SIZE_UNCERTAINTY_SUMMARY.json")
    external = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")

    readiness_rows = readiness["rows"]
    not_ready = [item for item in readiness_rows if item["section"] == "not_yet_complete"]
    next_experiments = [item for item in readiness_rows if item["section"] == "next_experiment"]
    gap_by_id = {item["id"]: item for item in not_ready + next_experiments}
    provenance_label = f"{provenance['complete_count']}/{len(provenance['artifacts'])}"

    command_templates = freeze_config.get("command_templates", {})
    gpu_policy = (
        f"{freeze_config.get('cuda_devices', 'not recorded')}; "
        f"{freeze_config.get('parallelism_policy', 'not recorded')}"
    )
    seed_template = freeze_config.get("larger_n_seed_template", {})
    min_n = seed_template.get("minimum_n", freeze["summary"].get("minimum_larger_n"))
    preferred_n = seed_template.get("preferred_n", freeze["summary"].get("preferred_larger_n"))

    rows = [
        row(
            "CR01",
            "NG01_broad_robustness",
            "future_experiment_required",
            gap_by_id["NG01_broad_robustness"]["evidence"],
            "heldout5 selector YAML, disjoint seed list, candidate methods, and prohibited oracle fields are frozen before any rerun.",
            "heldout5 external-validation table plus larger-N validation table with Wilson intervals, selector/oracle gap counts, and all failed seeds.",
            f"Do not upgrade from bounded simulator claims unless frozen heldout5 and larger-N results pass the preregistered endpoint at n>={min_n}; preferred n={preferred_n}.",
            "Report every failed, crashed, off-track, incomplete-lap, selector-miss, and candidate-gap seed; failed runs remain negative evidence.",
            "Current evidence supports bounded simulator claims only; broad robustness remains unsupported until new data exist.",
            gpu_policy,
        ),
        row(
            "CR02",
            "NG02_heldout3_weak",
            "future_development_then_external_validation",
            gap_by_id["NG02_heldout3_weak"]["evidence"],
            "Heldout3-targeted repair remains labelled diagnostic reuse; heldout5 seeds stay unseen until selector/candidate changes are frozen.",
            "Fresh heldout5 or larger-N results after any selector/candidate improvement, with heldout3 history retained as a negative boundary.",
            "A stronger claim requires no post-hoc retuning on heldout5 failures and explicit heldout1/heldout2 no-regression checks.",
            "Keep heldout3 failures in the manuscript and supplement even if later fresh seeds improve.",
            "Heldout3 targeted repair cannot be reclassified as external validation.",
            gpu_policy,
        ),
        row(
            "CR03",
            "NG03_heldout4_partial",
            "fresh_transfer_required",
            gap_by_id["NG03_heldout4_partial"]["evidence"],
            "Heldout4 remains post-repair external validation with partial transfer; selector misses and candidate gaps are named before future runs.",
            "Fresh heldout5/larger-N transfer evidence plus per-seed decision audit for any remaining selector misses.",
            "Only fresh disjoint seeds can support stronger transfer language; heldout4 partial transfer remains a boundary result.",
            "Report heldout4 misses [197, 211] and candidate gaps [233, 239] as preserved limitations.",
            "Partial transfer is not solved generalization.",
            gpu_policy,
        ),
        row(
            "CR04",
            "NG04_heldout2_selector_misses",
            "selector_improvement_required",
            gap_by_id["NG04_heldout2_selector_misses"]["evidence"],
            "Online selector must not use full-rollout labels, oracle method, pass/fail status, or candidate-gap fields.",
            "Selector decision audit rows showing probe-only features, selected candidates, and outcomes on heldout1/heldout2 and a fresh seed batch.",
            "Accept a selector update only if heldout1 no-regression is preserved and heldout2 selector misses are reduced without oracle leakage.",
            "If a selector fixes heldout2 but regresses heldout1 or fresh seeds, report it as diagnostic rather than accepted.",
            "Do not use oracle labels at decision time.",
            gpu_policy,
        ),
        row(
            "CR05",
            "NG07_probe_cost",
            "cost_reduction_required",
            gap_by_id["NG07_probe_cost"]["evidence"],
            "Current five-candidate, 1200-step online simulator-loop probe remains the reference selector cost.",
            "Compute-cost table with probe steps, committed decisions, GPU device logs, wall-clock availability, and no-regression outcome rows.",
            "A cheaper selector can be claimed only if it preserves endpoint definitions and passes heldout1/heldout2/fresh-seed no-regression gates.",
            "Report cost reductions and any accuracy loss together; do not hide failed cheaper probes.",
            "Cost reduction cannot change strict full-lap endpoint definitions.",
            gpu_policy,
        ),
        row(
            "CR06",
            "NG09_broader_stress_grid",
            "stress_grid_required",
            gap_by_id["NG09_broader_stress_grid"]["evidence"],
            "Traffic-density and opponent-mixture strata are specified in the frozen confirmatory config.",
            "Traffic-density and opponent-diversity ablation reports with per-stratum pass, off-track, traffic-quality, and failure-type rows.",
            "Stress claims require preregistered strata, no silent seed dropping, and explicit negative rows for each failed stratum.",
            "If a stratum fails, downgrade claims to the passing strata only and preserve the failed stratum in the failure register.",
            "Future stress results are not implied by the current package.",
            gpu_policy,
        ),
        row(
            "CR07",
            "NX02_larger_n_heldout",
            "sample_size_gate",
            gap_by_id["NX02_larger_n_heldout"]["evidence"],
            f"Minimum n={min_n}, preferred n={preferred_n}, seed template, and heldout5 seeds are registered before execution.",
            "Larger-N validation report with confidence intervals, seed ledger updates, release manifest entries, and checksum freeze after generation.",
            "Do not use small-N pass rates as broad evidence if larger-N intervals remain wide or failure modes cluster.",
            "All seeds in the chosen template must be listed as pass, fail, crash, skipped-with-reason, or unsupported.",
            "Planning rows are future-study guidance, not completed larger-N evidence.",
            gpu_policy,
        ),
    ]

    prereg_rows = prereg.get("rows") or prereg.get("items") or []
    report = {
        "root": str(root),
        "title": "Confirmatory Roadmap and Claim-Upgrade Gates",
        "purpose": (
            "Convert unresolved top-journal readiness gaps into frozen future-experiment gates, "
            "GPU execution rules, required artifacts, and conservative claim-upgrade boundaries."
        ),
        "interpretation": (
            "This roadmap is not new empirical evidence. It is a reviewer-facing control document that "
            "prevents future heldout5, larger-N, traffic-density, opponent-diversity, or cheaper-selector "
            "runs from being interpreted beyond their preregistered evidence."
        ),
        "summary": {
            "status": "pass",
            "roadmap_row_count": len(rows),
            "not_yet_complete_count": len(not_ready),
            "planned_next_experiment_count": len(next_experiments),
            "requires_new_experiment_count": sum(item["requires_new_experiment"] for item in not_ready + next_experiments),
            "heldout5_seed_count": freeze["summary"]["heldout5_seed_count"],
            "heldout5_overlap_with_used_seed_count": freeze["summary"]["heldout5_overlap_with_used_seed_count"],
            "candidate_method_count": freeze["summary"]["candidate_method_count"],
            "minimum_larger_n": min_n,
            "preferred_larger_n": preferred_n,
            "traffic_density_strata": join_list(freeze_config.get("traffic_density_strata", [])),
            "opponent_mixture_strata_count": len(freeze_config.get("opponent_mixture_strata", [])),
            "gpu_readiness_status": gpu["summary"]["status"],
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": provenance_label,
            "effect_size_summary_status": effect["summary"]["status"],
            "external_validity_boundary_status": external["summary"].get("status", "available"),
            "preregistration_row_count": len(prereg_rows),
            "not_executed_boundary": True,
        },
        "command_templates": command_templates,
        "pre_run_lock_artifacts": freeze_config.get("pre_run_lock_artifacts", []),
        "post_run_required_artifacts": freeze_config.get("post_run_required_artifacts", []),
        "rows": rows,
        "claim_upgrade_policy": {
            "no_upgrade_without_new_data": True,
            "oracle_rows_are_diagnostic_upper_bounds": True,
            "heldout3_targeted_repair_is_diagnostic_reuse": True,
            "heldout4_is_partial_transfer_not_broad_robustness": True,
            "full_failure_reporting_required": True,
            "gpu_execution_required_when_available": True,
        },
        "source_summaries": {
            "sample_size_summary": sample["summary"],
            "confirmatory_freeze_summary": freeze["summary"],
            "top_journal_readiness_summary": readiness["summary"],
        },
    }
    return report


def write_csv(report, path):
    fields = [
        "roadmap_id",
        "gap_id",
        "status",
        "current_evidence",
        "frozen_controls",
        "required_future_evidence",
        "decision_gate",
        "failure_policy",
        "claim_boundary",
        "gpu_execution",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Confirmatory Roadmap and Claim-Upgrade Gates",
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
            "## Claim-Upgrade Policy",
            "",
        ]
    )
    for key, value in report["claim_upgrade_policy"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Roadmap Rows",
            "",
            "| id | gap | status | current evidence | frozen controls | required future evidence | decision gate | failure policy | claim boundary | GPU execution |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['roadmap_id']} | {item['gap_id']} | {item['status']} | "
            f"`{item['current_evidence']}` | {item['frozen_controls']} | {item['required_future_evidence']} | "
            f"{item['decision_gate']} | {item['failure_policy']} | {item['claim_boundary']} | {item['gpu_execution']} |"
        )
    lines.extend(["", "## Pre-run Lock Artifacts", ""])
    for item in report["pre_run_lock_artifacts"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Post-run Required Artifacts", ""])
    for item in report["post_run_required_artifacts"]:
        lines.append(f"- `{item}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export confirmatory roadmap and claim-upgrade gates.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "CONFIRMATORY_ROADMAP.json"
    out_md = materials / "CONFIRMATORY_ROADMAP.md"
    out_csv = materials / "CONFIRMATORY_ROADMAP.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
