#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_artifact(provenance, name):
    for artifact in provenance["artifacts"]:
        if artifact["name"] == name:
            return artifact
    raise KeyError(name)


def command_block(command):
    safe_command = command.replace("'", "'\"'\"'")
    return f"```bash\nPYTHONPATH=. conda run -n vlm_planner bash -lc '{safe_command}'\n```"


def build_guide(root):
    manifest = load_json(root / "manifest.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    audit = load_json(root / "tables" / "reproducibility_audit.json")

    quick_artifacts = [
        "heldout_generalization",
        "selector_calibration",
        "claim_evidence_matrix",
        "manuscript_results_discussion_draft",
        "package_manifest",
        "portfolio_selector_figure",
        "environment_reproducibility_audit",
        "experiment_registry",
        "seed_outcome_ledger",
        "data_dictionary",
        "fair_archive_metadata",
        "research_risk_and_safety",
        "top_journal_reporting_summary",
        "editorial_submission_checklist",
        "significance_briefing",
        "statistical_consistency_audit",
        "endpoint_sensitivity_audit",
        "selector_decision_audit",
        "seed_partition_audit",
        "artifact_dependency_map",
        "policy_model_card",
        "study_protocol_and_deviations",
        "baseline_fairness_audit",
        "software_dependency_license_audit",
        "publication_package_verification",
        "reproducibility_audit",
    ]
    quick_commands = [
        {
            "name": name,
            "command": find_artifact(provenance, name)["command"],
            "outputs": find_artifact(provenance, name)["outputs"],
        }
        for name in quick_artifacts
    ]

    full_eval_artifacts = [
        "heldout2_multiseed_suite",
        "heldout2_adaptive_suite",
        "heldout2_expert_gate_suite",
        "heldout2_graph_dagger_recovery_v2_suite",
        "online_probe_selector_1200_heldout2_dagger_v2",
    ]

    lines = [
        "# Reproduction Guide",
        "",
        "This guide is the reviewer-facing entry point for reproducing and auditing the current non-VLM multi-car overtaking package.",
        "",
        "## Environment",
        "",
        "Use the repository root `multi_car_racing` and the provided conda environment.",
        "",
        "```bash",
        "conda env create -f environment.yml",
        "conda run -n vlm_planner python -m pip install -e . --no-deps",
        "```",
        "",
        "All paper-package commands should be run from the repository root with `PYTHONPATH=.`.",
        "",
        "## Package Root",
        "",
        f"- Root: `{manifest['root']}`",
        f"- Task: {manifest['scope']['task']}",
        f"- Excluded components: {manifest['scope']['excluded']}",
        f"- Devices used in recorded runs: `{manifest['device']}`",
        "",
        "## Seed Sets",
        "",
    ]
    for name, seeds in manifest["seed_sets"].items():
        lines.append(f"- `{name}`: {', '.join(str(seed) for seed in seeds)}")
    lines.extend(
        [
            "",
            "## Key Expected Results",
            "",
            f"- Locked overtake baseline: {manifest['key_results']['locked_single_methods']['overtake_base_only']['pass_count']}/10.",
            f"- Locked graph-adaptive shield: {manifest['key_results']['locked_single_methods']['graph_adaptive_shield']['pass_count']}/10.",
            f"- Heldout1 five-candidate selector: {manifest['key_results']['heldout1_five_candidate_selector']['pass_count']}/10, oracle {manifest['key_results']['heldout1_five_candidate_selector']['oracle_pass_count']}/10.",
            f"- Heldout2 five-candidate selector: {manifest['key_results']['heldout2_five_candidate_selector']['pass_count']}/10, oracle {manifest['key_results']['heldout2_five_candidate_selector']['oracle_pass_count']}/10.",
            f"- Heldout2 calibration decomposition: {manifest['key_results']['selector_calibration_heldout2']['candidate_gap_count']} candidate gaps and {manifest['key_results']['selector_calibration_heldout2']['selector_miss_count']} selector misses.",
            "",
            "## Fast Audit Path",
            "",
            "These commands regenerate reports, figures, metadata, and audit files from saved JSON summaries without rerunning expensive Box2D rollouts.",
            "",
        ]
    )
    for item in quick_commands:
        lines.extend(
            [
                f"### {item['name']}",
                "",
                command_block(item["command"]),
                "",
                "Expected outputs:",
                "",
            ]
        )
        for output in item["outputs"]:
            lines.append(f"- `{output}`")
        lines.append("")

    lines.extend(
        [
            "## Expensive Full-rollout Reproduction",
            "",
            "The following artifacts rerun simulation rollouts and can take substantially longer. They are listed here for completeness; reviewers can first inspect the saved summaries and logs.",
            "",
        ]
    )
    for name in full_eval_artifacts:
        artifact = find_artifact(provenance, name)
        lines.extend(
            [
                f"### {name}",
                "",
                command_block(artifact["command"]),
                "",
            ]
        )

    lines.extend(
        [
            "## One-command Integrity Checks",
            "",
            "After regenerating reports, run:",
            "",
            "```bash",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_artifact_provenance.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_environment_reproducibility_audit.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_experiment_registry.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_seed_outcome_ledger.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_data_dictionary.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_fair_archive_metadata.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_research_risk_and_safety_statement.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_top_journal_reporting_summary.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_editorial_submission_checklist.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_significance_briefing.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_statistical_consistency_audit.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_endpoint_sensitivity_audit.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_selector_decision_audit.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_seed_partition_audit.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_artifact_dependency_map.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_publication_package_verification.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_reproducibility_audit.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_package_manifest.py --root outputs/paper_multicar_overtake_20260618",
            "```",
            "",
            "Expected integrity status:",
            "",
            f"- Artifact provenance: {provenance['complete_count']}/{len(provenance['artifacts'])} complete.",
            f"- Reproducibility audit missing/weak items: {len(audit['missing_or_weak_items'])}.",
            f"- Current audit timestamp: {audit['timestamp_utc']}",
            "",
            "## Reporting Boundary",
            "",
            f"- Positive claim: {manifest['reporting_boundary']['main_positive']}",
            f"- Limitation: {manifest['reporting_boundary']['main_limitation']}",
            f"- Oracle policy: {manifest['reporting_boundary']['oracle_policy']}",
            "",
            "## Reviewer Navigation",
            "",
            "- Start with `manifest.json` for current package metadata.",
            "- Use `materials/CLAIM_EVIDENCE_MATRIX.md` before writing or checking claims.",
            "- Use `materials/PUBLICATION_PACKAGE_VERIFICATION.md` for the local preflight gate before submission or archiving.",
            "- Use `materials/DATA_DICTIONARY.md` for machine-readable table fields, units, sources, and intended use.",
            "- Use `materials/FAIR_ARCHIVE_METADATA.md` for DataCite/Zenodo-oriented archive metadata before external deposition.",
            "- Use `materials/RESEARCH_RISK_AND_SAFETY.md` for simulation-only, oracle-boundary, and responsible-reporting risks.",
            "- Use `materials/TOP_JOURNAL_REPORTING_SUMMARY.md` for editor-facing method, statistics, data/code, and safety reporting items.",
            "- Use `materials/EDITORIAL_SUBMISSION_CHECKLIST.md` for submission-system material checks and author-provided metadata gaps.",
            "- Use `materials/SIGNIFICANCE_BRIEFING.md` for evidence-bound cover-letter and editor-facing significance wording.",
            "- Use `materials/STATISTICAL_CONSISTENCY_AUDIT.md` for static cross-checks of manuscript-facing numerical summaries, Figure 3 source data, and package verification status.",
            "- Use `materials/ENDPOINT_SENSITIVITY_AUDIT.md` to inspect how saved rollout PASS counts change under nearby endpoint thresholds and gate ablations.",
            "- Use `materials/SELECTOR_DECISION_AUDIT.md` to verify that online selector decisions are recomputable from probe telemetry and registered tie-breaks.",
            "- Use `materials/SEED_PARTITION_AUDIT.md` to check seed-set disjointness, diagnostic seed reuse, and targeted-repair claim boundaries.",
            "- Use `materials/ARTIFACT_DEPENDENCY_MAP.md` to trace key reviewer-facing outputs back to inputs, scripts, and provenance rows.",
            "- Use `materials/POLICY_MODEL_CARD.md` for trained policy, rule-policy, selector, intended-use, and simulator-boundary metadata.",
            "- Use `materials/STUDY_PROTOCOL_AND_DEVIATIONS.md` to separate locked analyses, held-out validation, diagnostic follow-ups, targeted repair, and post-repair external validation.",
            "- Use `materials/BASELINE_FAIRNESS_AUDIT.md` to check baseline strength, shared seeds, strict validator use, oracle boundaries, negative controls, and compute-budget caveats.",
            "- Use `materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md` to check repository license, authorship metadata, environment dependencies, third-party-license boundaries, checksums, and archive DOI status.",
            "- Use `materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md` for the conservative Results/Discussion scaffold.",
            "- Use `materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md` for Python, package, CUDA, GPU, and lockfile records.",
            "- Use `materials/EXPERIMENT_REGISTRY.md` for experiment roles, seed sets, endpoints, evidence files, and claim boundaries.",
            "- Use `tables/seed_outcome_ledger.md` for per-seed selector/oracle outcomes and failure-type labels.",
            "- Use `tables/artifact_provenance.md` for every artifact-level reproduction command.",
            "- Use `tables/reproducibility_audit.md` for checklist-style completeness.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export reviewer-facing reproduction guide.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--out", default="materials/REPRODUCTION_GUIDE.md")
    args = parser.parse_args()
    root = Path(args.root)
    out = root / args.out
    out.write_text(build_guide(root), encoding="utf-8")
    print(json.dumps({"markdown": str(out)}, indent=2))


if __name__ == "__main__":
    main()
