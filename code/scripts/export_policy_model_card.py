#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


MODEL_SPECS = [
    {
        "id": "graph_bc",
        "artifact_type": "neural_policy",
        "summary_path": "models/graph_bc/train_summary.json",
        "training_source": "behavior cloning from locked multi-car telemetry demonstrations",
        "intended_use": "graph actor component for simulator-only multi-car overtaking policy evaluations",
        "evaluation_evidence": [
            "tables/main_multiseed_suite_report.md",
            "tables/full_statistical_report.md",
            "materials/CLAIM_EVIDENCE_MATRIX.md",
        ],
        "known_limitations": (
            "Standalone learned control is not the final supported claim; results depend on shielded or "
            "selector-composed policies and strict simulator validation."
        ),
    },
    {
        "id": "graph_dagger_recovery",
        "artifact_type": "neural_policy",
        "summary_path": "models/graph_dagger_recovery/train_summary.json",
        "training_source": "DAgger-style hard-state recovery labels from held-out failure seeds and support seeds",
        "intended_use": "diagnostic recovery actor candidate for hard held-out simulator states",
        "evaluation_evidence": [
            "tables/heldout_graph_dagger_recovery_smoke_report.md",
            "tables/dagger_failure_diagnosis.md",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
        ],
        "known_limitations": (
            "First recovery actor failed strict hard-smoke validation and is retained mainly as a negative "
            "control and design diagnostic."
        ),
    },
    {
        "id": "graph_dagger_recovery_v2",
        "artifact_type": "neural_policy",
        "summary_path": "models/graph_dagger_recovery_v2/train_summary.json",
        "training_source": "second DAgger-style recovery iteration initialized from the first recovery actor",
        "intended_use": "complementary candidate inside shielded and selector-composed simulator policies",
        "evaluation_evidence": [
            "tables/heldout_graph_dagger_recovery_v2_suite_report.md",
            "tables/heldout_v2_portfolio.md",
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2.md",
        ],
        "known_limitations": (
            "Complementary rather than standalone robust: complete held-out suite performance supports its "
            "portfolio value, not a single-policy breakthrough claim."
        ),
    },
    {
        "id": "heldout3_targeted_recovery",
        "artifact_type": "neural_policy",
        "summary_path": "models/heldout3_targeted_recovery/train_summary.json",
        "training_source": "targeted repair data from heldout3 hard seeds",
        "intended_use": "targeted diagnostic repair candidate for heldout3 analysis",
        "evaluation_evidence": [
            "tables/heldout3_targeted_recovery_suite_report.md",
            "tables/heldout3_targeted_selector_generalization.md",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
        ],
        "known_limitations": (
            "Targeted heldout3 repair is not external validation; it is reported as a diagnostic showing "
            "where additional hard-state data can help."
        ),
    },
]


NON_NEURAL_COMPONENTS = [
    {
        "id": "locked_rule_baselines",
        "artifact_type": "rule_policy_family",
        "model_path": "baselines/",
        "training_source": "hand-coded telemetry policies and locked baseline summaries",
        "training_samples": "",
        "agent_samples": "",
        "obs_shape": "",
        "action_shape": "",
        "training_status": "not_applicable",
        "intended_use": "baseline comparators: lane, cruise, yield, overtake, expert-gate, and related rule controls",
        "evaluation_evidence": "tables/full_statistical_report.md; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
        "known_limitations": "Rule baselines expose useful behavior and failure modes but do not establish learned robustness.",
    },
    {
        "id": "online_probe_selector_1200",
        "artifact_type": "online_selector",
        "model_path": "scripts/run_portfolio_probe_selector.py",
        "training_source": "short simulator probe rollouts scored against candidate-policy telemetry",
        "training_samples": "",
        "agent_samples": "",
        "obs_shape": "probe telemetry features",
        "action_shape": "candidate policy id",
        "training_status": "deterministic selector",
        "intended_use": "online simulator-loop selector that chooses among candidate policies after probe rollouts",
        "evaluation_evidence": (
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2.md; "
            "tables/portfolio_probe_selector_1200_heldout2_expanded.md; "
            "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.md"
        ),
        "known_limitations": "Requires multiple short probe rollouts per seed and drops on harder held-out batches.",
    },
    {
        "id": "learned_selector_diagnostic",
        "artifact_type": "selector_diagnostic",
        "model_path": "tables/learned_selector_report.json",
        "training_source": "offline diagnostic classifier over saved probe telemetry",
        "training_samples": "see tables/learned_selector_report.json",
        "agent_samples": "",
        "obs_shape": "probe telemetry feature vector",
        "action_shape": "candidate policy id",
        "training_status": "diagnostic only",
        "intended_use": "analysis of selector feature transfer and calibration limits",
        "evaluation_evidence": "tables/learned_selector_report.md; materials/CLAIM_EVIDENCE_MATRIX.md",
        "known_limitations": "Exploratory diagnostic, not the accepted replacement selector for claims.",
    },
    {
        "id": "oracle_portfolio",
        "artifact_type": "diagnostic_upper_bound",
        "model_path": "tables/portfolio_oracle.json",
        "training_source": "post hoc best-candidate selection from full rollout outcomes",
        "training_samples": "",
        "agent_samples": "",
        "obs_shape": "full rollout outcomes",
        "action_shape": "best candidate policy id",
        "training_status": "not_deployable",
        "intended_use": "upper-bound diagnostic for candidate-policy coverage",
        "evaluation_evidence": "tables/portfolio_oracle.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
        "known_limitations": "Not deployable because it uses full-rollout outcomes unavailable before policy choice.",
    },
]


COMMON = {
    "input_modality": "simulator state/telemetry only; no images, VLM, camera, LiDAR, or real-world sensor input",
    "output_action": "continuous simulator control action or candidate-policy selection",
    "not_intended_for": (
        "real-road deployment, safety certification, perception benchmarking, closed-loop vehicle control outside "
        "this simulator, or claims of broad robustness"
    ),
    "failure_modes": (
        "off-track grass contact, incomplete lap, failure to overtake, selector miss, candidate-policy gap, and "
        "seed-specific transfer failure"
    ),
    "deployment_boundary": (
        "Use only inside the saved multi-car racing simulator protocol and with the claim boundaries in the "
        "evidence package."
    ),
    "provenance": "materials/POLICY_MODEL_CARD.json plus train summaries, evaluation tables, and artifact provenance",
}


def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def compact_shape(value):
    if value in (None, ""):
        return ""
    return "x".join(str(item) for item in value)


def evidence_status(root, evidence):
    paths = evidence if isinstance(evidence, list) else [p.strip() for p in str(evidence).split(";") if p.strip()]
    return {path: (root / path).exists() for path in paths}


def build_model_row(root, spec):
    summary = load_json(root / spec["summary_path"])
    row = {
        "id": spec["id"],
        "artifact_type": spec["artifact_type"],
        "model_path": summary.get("model_path", ""),
        "training_source": spec["training_source"],
        "training_samples": summary.get("transitions", summary.get("episodes", "")),
        "agent_samples": summary.get("agent_samples", ""),
        "obs_shape": compact_shape(summary.get("obs_shape", "")),
        "action_shape": compact_shape(summary.get("action_shape", "")),
        "training_status": summary.get("status", "missing_summary"),
        "intended_use": spec["intended_use"],
        "evaluation_evidence": "; ".join(spec["evaluation_evidence"]),
        "known_limitations": spec["known_limitations"],
        **COMMON,
    }
    row["evidence_complete"] = all(evidence_status(root, spec["evaluation_evidence"]).values())
    row["model_file_exists"] = bool(row["model_path"]) and (root / row["model_path"].replace(str(root) + "/", "")).exists()
    if row["model_path"].startswith("outputs/"):
        row["model_file_exists"] = Path(row["model_path"]).exists() or (Path.cwd() / row["model_path"]).exists()
    row["summary_path"] = spec["summary_path"]
    row["summary_exists"] = (root / spec["summary_path"]).exists()
    row["loss_final"] = summary.get("loss_final", "")
    row["loss_mean_last_100"] = summary.get("loss_mean_last_100", "")
    row["reason_totals"] = summary.get("reason_totals", {})
    return row


def build_report(root):
    cards = [build_model_row(root, spec) for spec in MODEL_SPECS]
    for component in NON_NEURAL_COMPONENTS:
        row = {**component, **COMMON}
        row["evidence_complete"] = all(evidence_status(root, row["evaluation_evidence"]).values())
        row["model_file_exists"] = (root / row["model_path"]).exists() or Path(row["model_path"]).exists()
        row["summary_path"] = ""
        row["summary_exists"] = ""
        row["loss_final"] = ""
        row["loss_mean_last_100"] = ""
        row["reason_totals"] = {}
        cards.append(row)
    missing = [
        {
            "id": row["id"],
            "summary_exists": row["summary_exists"],
            "model_file_exists": row["model_file_exists"],
            "evidence_complete": row["evidence_complete"],
        }
        for row in cards
        if row["summary_exists"] is False or not row["model_file_exists"] or not row["evidence_complete"]
    ]
    return {
        "root": str(root),
        "cards": cards,
        "summary": {
            "card_count": len(cards),
            "neural_policy_count": sum(row["artifact_type"] == "neural_policy" for row in cards),
            "non_neural_component_count": sum(row["artifact_type"] != "neural_policy" for row in cards),
            "complete": not missing,
            "missing_or_incomplete": missing,
        },
        "interpretation": (
            "This policy/model card records trained neural policies, rule-policy comparators, selector components, "
            "intended uses, limitations, and deployment boundaries for the simulator-only overtaking package."
        ),
    }


CSV_FIELDS = [
    "id",
    "artifact_type",
    "model_path",
    "summary_path",
    "training_source",
    "training_samples",
    "agent_samples",
    "obs_shape",
    "action_shape",
    "training_status",
    "intended_use",
    "not_intended_for",
    "input_modality",
    "output_action",
    "evaluation_evidence",
    "known_limitations",
    "failure_modes",
    "deployment_boundary",
    "provenance",
    "summary_exists",
    "model_file_exists",
    "evidence_complete",
    "loss_final",
    "loss_mean_last_100",
]


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in report["cards"]:
            writer.writerow({key: row.get(key, "") for key in CSV_FIELDS})


def write_markdown(report, path):
    lines = [
        "# Policy and Model Card",
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Cards: {report['summary']['card_count']}",
        f"- Neural policies: {report['summary']['neural_policy_count']}",
        f"- Non-neural policy/selector components: {report['summary']['non_neural_component_count']}",
        f"- Complete: {report['summary']['complete']}",
        "",
        "## Cross-Cutting Boundary",
        "",
        f"- Input modality: {COMMON['input_modality']}",
        f"- Not intended for: {COMMON['not_intended_for']}",
        f"- Failure modes: {COMMON['failure_modes']}",
        "",
        "## Cards",
        "",
    ]
    for row in report["cards"]:
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- Artifact type: `{row['artifact_type']}`",
                f"- Model/path: `{row['model_path']}`",
                f"- Summary/path: `{row['summary_path']}`",
                f"- Training source: {row['training_source']}",
                f"- Training samples: {row['training_samples']}",
                f"- Agent samples: {row['agent_samples']}",
                f"- Observation shape: `{row['obs_shape']}`",
                f"- Action shape: `{row['action_shape']}`",
                f"- Training status: `{row['training_status']}`",
                f"- Intended use: {row['intended_use']}",
                f"- Known limitations: {row['known_limitations']}",
                f"- Evaluation evidence: {row['evaluation_evidence']}",
                f"- Evidence complete: `{row['evidence_complete']}`",
                f"- Model/path exists: `{row['model_file_exists']}`",
                "",
            ]
        )
    if report["summary"]["missing_or_incomplete"]:
        lines.extend(["## Missing or Incomplete", "", "```json", json.dumps(report["summary"]["missing_or_incomplete"], indent=2), "```", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export policy/model card for simulator overtaking package.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "POLICY_MODEL_CARD.json"
    out_md = materials / "POLICY_MODEL_CARD.md"
    out_csv = materials / "POLICY_MODEL_CARD.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "complete": report["summary"]["complete"]}, indent=2))


if __name__ == "__main__":
    main()
