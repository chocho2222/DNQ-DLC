#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def current_artifact_provenance(root):
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    return f"{provenance['complete_count']}/{len(provenance['artifacts'])}"


def with_current_status(summary, verification, artifact_provenance):
    updated = dict(summary)
    updated["publication_verification_status"] = verification["summary"]["status"]
    updated["artifact_provenance"] = artifact_provenance
    return updated


def build_report(root):
    manifest = load_json(root / "manifest.json")
    gap = load_json(root / "materials" / "SUBMISSION_GAP_ACTION_PLAN.json")
    sap = load_json(root / "materials" / "STATISTICAL_ANALYSIS_PLAN.json")
    sample = load_json(root / "materials" / "SAMPLE_SIZE_SENSITIVITY_BRIEF.json")
    seed_audit = load_json(root / "materials" / "SEED_PARTITION_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    artifact_provenance = current_artifact_provenance(root)
    sample_summary = with_current_status(sample["summary"], verification, artifact_provenance)
    seed_audit_summary = with_current_status(seed_audit["summary"], verification, artifact_provenance)
    preferred_devices = "cuda:0,cuda:1,cuda:2,cuda:3"

    hard_numbers = with_current_status(gap["current_status"]["hard_numbers"], verification, artifact_provenance)
    rows = [
        {
            "id": "CP1_freeze_selector_before_heldout5",
            "phase": "design_freeze",
            "decision_role": "required_before_new_external_validation",
            "scope": "selector and candidate-pool design",
            "pre_registered_action": (
                "Freeze the online selector rule, candidate set, endpoint thresholds, tie-break order, and excluded oracle fields "
                "before evaluating any fresh heldout5 seeds."
            ),
            "acceptance_criterion": "A dated frozen config and selector audit script exist before heldout5 result files are generated.",
            "primary_metric": sap["primary_endpoint"]["name"],
            "analysis_plan": "Replay selector decisions from probe-only fields and compare selector pass count with diagnostic oracle pass count.",
            "stopping_rule": "No selector or candidate retuning on heldout5 before the first locked report is exported.",
            "evidence_to_generate": "configs/heldout5_frozen_selector.yaml; tables/heldout5_external_validation.md; materials/SELECTOR_DECISION_AUDIT.md",
            "frozen_design_elements": "candidate list; online-probe scoring rule; tie-break order; strict endpoint thresholds; prohibited oracle fields",
            "seed_policy": "Use a disjoint heldout5 seed block chosen before execution and never reuse it for selector or candidate edits.",
            "stress_factors": "none; this row is the design-freeze prerequisite for later external validation.",
            "leakage_controls": "Selector decisions may use only early probe telemetry and declared candidate identity fields; full-rollout PASS/FAIL labels remain diagnostic only.",
            "minimum_reporting": "frozen config hash; candidate manifest; selector audit; endpoint config; run command; all seeds evaluated.",
            "command_template": "python scripts/run_portfolio_probe_selector.py --root {root} --seeds {heldout5_seeds} --frozen-config configs/heldout5_frozen_selector.yaml",
            "gpu_execution": "No training required; use GPU only if candidate rollout scripts invoke learned policies. Keep device list recorded.",
            "pre_run_lock_artifacts": "configs/heldout5_frozen_selector.yaml; materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.json; materials/GPU_RERUN_READINESS.json",
            "post_run_required_artifacts": "tables/heldout5_external_validation.csv; tables/heldout5_external_validation.md; materials/SELECTOR_DECISION_AUDIT.csv",
            "minimum_seed_count": 0,
            "preferred_seed_count": 0,
            "cuda_devices": preferred_devices,
            "parallelism_policy": "Use all available GPUs for rollout workers when supported; preserve one process-to-device mapping in logs.",
            "failure_reporting": "If the frozen config is missing or changed after any heldout5 rollout, mark the validation invalid and restart with a new frozen seed block.",
            "claim_upgrade_gate": "No claim upgrade is allowed from CP1 alone; it only authorizes fresh validation.",
            "claim_allowed_if_pass": "Fresh external-validation evidence for the frozen selector.",
            "claim_prohibited": "Do not merge heldout5 into tuning after observing failures.",
        },
        {
            "id": "CP2_larger_n_seed_sweep",
            "phase": "confirmatory_validation",
            "decision_role": "recommended_before_broad_robustness_claim",
            "scope": "larger-N fresh simulator seeds",
            "pre_registered_action": (
                "Evaluate the frozen selector on a larger disjoint seed batch and report Wilson intervals, exact tests, "
                "selector-oracle gaps, and failure atlas rows."
            ),
            "acceptance_criterion": "Report pass rate, Wilson 95% interval, selector-oracle gap, and all failed seeds without filtering.",
            "primary_metric": sap["primary_endpoint"]["name"],
            "analysis_plan": "Use the same strict endpoint and the same reporting fields as heldout1-4.",
            "stopping_rule": "Predetermine seed count and publish all seeds regardless of outcome.",
            "evidence_to_generate": "tables/larger_n_generalization_report.md; tables/larger_n_failure_atlas.md; figures/figure_4_generalization_stress.*",
            "frozen_design_elements": "same frozen selector/candidate/endpoint package generated by CP1",
            "seed_policy": "Use one larger disjoint seed block; n=75 is the minimum planning target for Wilson width near 0.20 and n=100 is preferred for a lower-bound-oriented robustness estimate.",
            "stress_factors": "fresh simulator seeds with the default traffic setting used by heldout1-4",
            "leakage_controls": "Do not inspect seed-level failures until the first locked larger-N report, failure atlas, and source CSV are written.",
            "minimum_reporting": "pass count; Wilson 95% interval; exact selector-oracle gap test; all failed seeds; candidate-gap and selector-miss decomposition.",
            "command_template": "python scripts/run_multiseed_overtake_suite.py --root {root} --seeds {larger_n_seeds} --methods {frozen_candidate_pool} --devices {cuda_devices}",
            "gpu_execution": "Run rollout workers across all recorded CUDA devices where the suite supports parallel devices; log device assignment per seed.",
            "pre_run_lock_artifacts": "configs/heldout5_frozen_selector.yaml; materials/SEED_PARTITION_AUDIT.json; materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "post_run_required_artifacts": "tables/larger_n_generalization_report.csv; tables/larger_n_failure_atlas.csv; figures/figure_4_source_data.csv",
            "minimum_seed_count": 75,
            "preferred_seed_count": 100,
            "cuda_devices": preferred_devices,
            "parallelism_policy": "Prefer one rollout worker per GPU, then batch seeds in deterministic order; do not alter endpoints to improve throughput.",
            "failure_reporting": "Every scheduled seed must appear in the output ledger with pass/fail/error status; crashed seeds are not silently dropped.",
            "claim_upgrade_gate": "Only consider stronger simulator generalization wording if the frozen larger-N report, failure atlas, source data, and claim QA all pass.",
            "claim_allowed_if_pass": "More precise simulator generalization estimate for the frozen selector.",
            "claim_prohibited": "Do not claim real-world robustness or safety certification.",
        },
        {
            "id": "CP3_traffic_density_ablation",
            "phase": "stress_ablation",
            "decision_role": "recommended_for_mechanistic_scope",
            "scope": "number and placement of non-target traffic cars",
            "pre_registered_action": "Evaluate fixed traffic-density settings while keeping selector, endpoints, and seed policy frozen.",
            "acceptance_criterion": "Report pass count and failure signatures separately for each density level.",
            "primary_metric": sap["primary_endpoint"]["name"],
            "analysis_plan": "Use stratified summaries rather than pooling density levels into one headline.",
            "stopping_rule": "Do not drop harder density levels after observing failures.",
            "evidence_to_generate": "tables/traffic_density_ablation_report.md; tables/traffic_density_failure_atlas.md",
            "frozen_design_elements": "same frozen selector/candidate/endpoint package generated by CP1",
            "seed_policy": "Use the same prespecified seeds within every density stratum so density effects are not confounded with seed selection.",
            "stress_factors": "traffic density strata: 2, 3, 4, and 5 total cars when supported by the simulator; target remains the last-starting car.",
            "leakage_controls": "No density level is removed after execution begins, and density-specific failures are reported even when harder settings reduce headline performance.",
            "minimum_reporting": "per-density pass count; Wilson interval; failure signatures; grass-rate and completion summaries; source CSV per stratum.",
            "command_template": "python scripts/run_multiseed_overtake_suite.py --root {root} --seeds {stress_seeds} --num-agents {density} --devices {cuda_devices}",
            "gpu_execution": "Use the same CUDA device policy for every density stratum; report if a density level cannot use parallel workers.",
            "pre_run_lock_artifacts": "configs/heldout5_frozen_selector.yaml; materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.json",
            "post_run_required_artifacts": "tables/traffic_density_ablation_report.csv; tables/traffic_density_failure_atlas.csv",
            "minimum_seed_count": 75,
            "preferred_seed_count": 100,
            "cuda_devices": preferred_devices,
            "parallelism_policy": "Run density strata independently but keep identical seed order within every stratum.",
            "failure_reporting": "Unsupported density settings must be reported as unsupported, not omitted from the preregistered grid.",
            "claim_upgrade_gate": "Only density-specific claims are allowed, and only for density strata with complete reports.",
            "claim_allowed_if_pass": "Density-specific simulator performance envelope.",
            "claim_prohibited": "Do not generalize beyond tested density and opponent-placement ranges.",
        },
        {
            "id": "CP4_opponent_diversity_ablation",
            "phase": "stress_ablation",
            "decision_role": "recommended_for_multi_agent_scope",
            "scope": "baseline-controller mix among opponent vehicles",
            "pre_registered_action": "Evaluate fixed opponent-controller mixtures, ideally one algorithm family per non-target car where the simulator supports it.",
            "acceptance_criterion": "Report per-mixture pass count, selector choices, and failure atlas rows.",
            "primary_metric": sap["primary_endpoint"]["name"],
            "analysis_plan": "Keep target car as the last-starting vehicle and separate opponent mix effects from seed effects.",
            "stopping_rule": "No opponent-mixture filtering after evaluation starts.",
            "evidence_to_generate": "tables/opponent_diversity_ablation_report.md; tables/opponent_diversity_failure_atlas.md",
            "frozen_design_elements": "same frozen selector/candidate/endpoint package generated by CP1",
            "seed_policy": "Use the same prespecified seeds for every opponent mixture and keep target start position fixed behind traffic.",
            "stress_factors": "opponent mixtures: cruise/yield/lane; cruise/yield/adaptive-conservative; lane/adaptive/recovery; one-controller-per-opponent when possible.",
            "leakage_controls": "Opponent mixtures are fixed before the first run; failed mixtures cannot be reclassified as exploratory after inspection.",
            "minimum_reporting": "per-mixture pass count; selected candidate distribution; failure atlas; opponent-policy list; all command lines.",
            "command_template": "python scripts/run_multiseed_overtake_suite.py --root {root} --seeds {stress_seeds} --baseline-policies {opponent_mix} --devices {cuda_devices}",
            "gpu_execution": "Use the same GPU allocation across opponent mixtures when possible; log fallback to CPU only as an error/review item.",
            "pre_run_lock_artifacts": "configs/heldout5_frozen_selector.yaml; materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.json",
            "post_run_required_artifacts": "tables/opponent_diversity_ablation_report.csv; tables/opponent_diversity_failure_atlas.csv",
            "minimum_seed_count": 75,
            "preferred_seed_count": 100,
            "cuda_devices": preferred_devices,
            "parallelism_policy": "Evaluate every opponent mixture over the same seed list; parallelize across GPUs but preserve mixture labels.",
            "failure_reporting": "Failed opponent mixtures remain in the table with their failure signatures and cannot be dropped from the headline scope.",
            "claim_upgrade_gate": "Only mixture-specific multi-agent claims are allowed, and only when every preregistered mixture is reported.",
            "claim_allowed_if_pass": "Opponent-diversity stress evidence inside the simulator.",
            "claim_prohibited": "Do not infer general multi-agent traffic robustness beyond tested opponent policies.",
        },
        {
            "id": "CP5_wallclock_and_resource_accounting",
            "phase": "reporting_completion",
            "decision_role": "recommended_for_reproducibility",
            "scope": "GPU utilization, wall-clock time, and probe cost",
            "pre_registered_action": "Record elapsed wall-clock time, device allocation, parallelism, and probe counts for confirmatory runs.",
            "acceptance_criterion": "Compute-cost tables include device, parallelism, wall-clock availability, probe count, and simulated steps.",
            "primary_metric": "compute and reproducibility reporting",
            "analysis_plan": "Report cost separately from accuracy and do not use resource accounting to change endpoint definitions.",
            "stopping_rule": "Timing failures are reported as missing timing fields rather than excluded from accuracy tables.",
            "evidence_to_generate": "tables/compute_cost_report.md; materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
            "frozen_design_elements": "timing logger; CUDA device list; process parallelism; probe count; rollout-step accounting",
            "seed_policy": "Record resource use for every confirmatory/stress seed rather than sampling only successful runs.",
            "stress_factors": "GPU device allocation and parallel worker count; accuracy endpoints remain unchanged.",
            "leakage_controls": "Timing/resource fields cannot be used to exclude failed accuracy runs.",
            "minimum_reporting": "device name; CUDA availability; wall-clock start/end; elapsed seconds; probes per seed; simulated steps; missing-timing flags.",
            "command_template": "/usr/bin/time -v python scripts/run_multiseed_overtake_suite.py --root {root} --seeds {seeds} --devices {cuda_devices}",
            "gpu_execution": "Record CUDA_VISIBLE_DEVICES, torch CUDA availability, nvidia-smi inventory, and per-run command line before each confirmatory batch.",
            "pre_run_lock_artifacts": "materials/GPU_RERUN_READINESS.json; materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.json",
            "post_run_required_artifacts": "tables/compute_cost_report.csv; materials/GPU_RERUN_READINESS.csv",
            "minimum_seed_count": 0,
            "preferred_seed_count": 0,
            "cuda_devices": preferred_devices,
            "parallelism_policy": "Use all available GPUs for expensive reruns when supported, but report the actual device allocation rather than assuming full utilization.",
            "failure_reporting": "Missing timing fields are explicit missingness rows; they do not remove seeds from accuracy denominators.",
            "claim_upgrade_gate": "Resource reporting can support reproducibility claims only, not accuracy or robustness upgrades.",
            "claim_allowed_if_pass": "Transparent computational reproducibility for confirmatory runs.",
            "claim_prohibited": "Do not imply all previous historical runs have complete wall-clock/utilization logs.",
        },
    ]

    return {
        "root": str(root),
        "title": "Confirmatory Experiment Preregistration Plan",
        "purpose": (
            "Convert remaining top-journal experimental gaps into a frozen, claim-safe confirmatory plan. "
            "This is a local preregistration-style protocol for future runs, not evidence that those runs have already been completed."
        ),
        "current_seed_sets": manifest["seed_sets"],
        "gap_snapshot": hard_numbers,
        "sample_size_snapshot": sample_summary,
        "seed_partition_snapshot": seed_audit_summary,
        "rows": rows,
        "summary": {
            "row_count": len(rows),
            "required_before_new_external_validation": sum(row["decision_role"] == "required_before_new_external_validation" for row in rows),
            "recommended_confirmatory_or_stress_rows": sum(row["decision_role"].startswith("recommended") for row in rows),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": artifact_provenance,
        },
        "interpretation": (
            "The saved package remains internally consistent, but broad robustness should wait for this frozen confirmatory ladder. "
            "The plan explicitly prevents heldout5-style data from becoming another tuning set."
        ),
    }


CSV_FIELDS = [
    "id",
    "phase",
    "decision_role",
    "scope",
    "pre_registered_action",
    "acceptance_criterion",
    "primary_metric",
    "analysis_plan",
    "stopping_rule",
    "evidence_to_generate",
    "frozen_design_elements",
    "seed_policy",
    "stress_factors",
    "leakage_controls",
    "minimum_reporting",
    "command_template",
    "gpu_execution",
    "pre_run_lock_artifacts",
    "post_run_required_artifacts",
    "minimum_seed_count",
    "preferred_seed_count",
    "cuda_devices",
    "parallelism_policy",
    "failure_reporting",
    "claim_upgrade_gate",
    "claim_allowed_if_pass",
    "claim_prohibited",
]


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({key: row[key] for key in CSV_FIELDS})


def write_markdown(report, path):
    lines = [
        "# Confirmatory Experiment Preregistration Plan",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Rows: {report['summary']['row_count']}",
        f"- Required before new external validation: {report['summary']['required_before_new_external_validation']}",
        f"- Recommended confirmatory/stress rows: {report['summary']['recommended_confirmatory_or_stress_rows']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        "",
        "## Current Evidence Snapshot",
        "",
        f"- Cross-heldout selector: {report['gap_snapshot']['cross_heldout_selector']}",
        f"- Cross-heldout oracle: {report['gap_snapshot']['cross_heldout_oracle']}",
        f"- Cross-heldout selector-oracle gap: {report['gap_snapshot']['cross_heldout_selector_oracle_gap']}",
        f"- Sample-size stages: {report['sample_size_snapshot']['stage_count']}",
        f"- Seed-partition audit status: {report['seed_partition_snapshot']['status']}",
        f"- Recommended larger-N planning target: n=75 minimum, n=100 preferred before broad robustness language",
        "",
        "## Preregistered Rows",
        "",
        "| id | phase | role | scope | action | acceptance criterion | claim boundary |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['id']} | {row['phase']} | {row['decision_role']} | {row['scope']} | "
            f"{row['pre_registered_action']} | {row['acceptance_criterion']} | {row['claim_prohibited']} |"
        )
    lines.extend(["", "## Evidence To Generate", ""])
    for row in report["rows"]:
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- Primary metric: {row['primary_metric']}",
                f"- Analysis plan: {row['analysis_plan']}",
                f"- Stopping rule: {row['stopping_rule']}",
                f"- Frozen design elements: {row['frozen_design_elements']}",
                f"- Seed policy: {row['seed_policy']}",
                f"- Stress factors: {row['stress_factors']}",
                f"- Leakage controls: {row['leakage_controls']}",
                f"- Minimum reporting: {row['minimum_reporting']}",
                f"- Command template: `{row['command_template']}`",
                f"- GPU execution: {row['gpu_execution']}",
                f"- Pre-run lock artifacts: `{row['pre_run_lock_artifacts']}`",
                f"- Post-run required artifacts: `{row['post_run_required_artifacts']}`",
                f"- Seed-count target: minimum {row['minimum_seed_count']}, preferred {row['preferred_seed_count']}",
                f"- CUDA devices: `{row['cuda_devices']}`",
                f"- Parallelism policy: {row['parallelism_policy']}",
                f"- Failure reporting: {row['failure_reporting']}",
                f"- Claim-upgrade gate: {row['claim_upgrade_gate']}",
                f"- Evidence to generate: `{row['evidence_to_generate']}`",
                f"- Claim allowed if pass: {row['claim_allowed_if_pass']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export confirmatory experiment preregistration plan.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "CONFIRMATORY_EXPERIMENT_PREREGISTRATION.json"
    out_md = materials / "CONFIRMATORY_EXPERIMENT_PREREGISTRATION.md"
    out_csv = materials / "CONFIRMATORY_EXPERIMENT_PREREGISTRATION.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
