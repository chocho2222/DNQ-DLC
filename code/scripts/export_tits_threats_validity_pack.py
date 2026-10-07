#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def top_failure(failure_rows, algorithm, tag=None):
    rows = [row for row in failure_rows if row["algorithm"] == algorithm]
    if tag:
        rows = [row for row in rows if row["failure_or_quality_tag"] == tag]
    rows = sorted(rows, key=lambda row: f(row.get("tag_rate_per_case")), reverse=True)
    return rows[0] if rows else {}


def build_risk_register(failure_rows, claim_rows, protocol_qa, stats_qa, final_manifest):
    safe_grass = top_failure(failure_rows, "v6_runtime_dynamic_neighborhood_safe", "high_grass_rate_gt_0.60")
    safe_nonelegant = top_failure(failure_rows, "v6_runtime_dynamic_neighborhood_safe", "success_but_no_elegant_overtake")
    original_grass = top_failure(failure_rows, "dlc_world_original", "high_grass_rate_gt_0.60")
    rule_grass = top_failure(failure_rows, "rule_expert_gate", "high_grass_rate_gt_0.60")
    protocol_checks = protocol_qa.get("checks", {})
    stats = stats_qa.get("statistics", {})
    final_items = ", ".join(final_manifest.get("author_owned_items", []))
    claim_by_id = {row.get("claim_id"): row for row in claim_rows}
    rows = [
        {
            "risk_id": "V01",
            "validity_class": "external validity",
            "risk": "Evidence is limited to simulation and does not establish real-vehicle deployment safety.",
            "evidence": "Benchmark protocol covers procedural tracks, 8-car extrapolation and one Monza CSV-derived track.",
            "severity": "high",
            "likelihood": "high",
            "mitigation": "State simulation-only scope; frame real-vehicle or high-fidelity simulator transfer as future work.",
            "safe_claim": "The method improves online overtaking in the evaluated multi-car simulation benchmarks.",
            "avoid_claim": "The method is safe for real-world autonomous overtaking.",
            "source": "LIMITATIONS_DRAFT.md; BENCHMARK_METRIC_PROTOCOL_CARD.md",
        },
        {
            "risk_id": "V02",
            "validity_class": "external validity",
            "risk": "External-track evidence uses a single Monza CSV-derived track.",
            "evidence": claim_by_id.get("C2", {}).get("boundary", "Monza is a single external CSV-derived track."),
            "severity": "medium",
            "likelihood": "high",
            "mitigation": "Describe Monza as an external-track stress test, not broad road-geometry proof.",
            "safe_claim": "The method outperforms original DLC on the included Monza external-track setting.",
            "avoid_claim": "The method generalizes to arbitrary tracks.",
            "source": "confirmatory_claim_evidence_matrix.csv; benchmark_cards.csv",
        },
        {
            "risk_id": "V03",
            "validity_class": "external validity",
            "risk": "Vehicle-count generalization is tested up to 8 vehicles only.",
            "evidence": claim_by_id.get("C1", {}).get("boundary", "Evidence covers 4/5/6 and 8 vehicles."),
            "severity": "medium",
            "likelihood": "high",
            "mitigation": "Report 8-car extrapolation as bounded evidence; reserve denser traffic for future work.",
            "safe_claim": "Runtime dynamic neighborhoods support online evaluation at the included 8-car extrapolation setting without retraining for that vehicle count.",
            "avoid_claim": "The graph policy supports unlimited traffic density.",
            "source": "confirmatory_claim_evidence_matrix.csv; BENCHMARK_METRIC_PROTOCOL_CARD.md",
        },
        {
            "risk_id": "V04",
            "validity_class": "construct validity",
            "risk": "Desirable/on-track overtaking metrics are simulator-defined proxies.",
            "evidence": f"Metric protocol records {protocol_checks.get('source_metric_fields')} source-data fields and notes that evaluator thresholds define the metric.",
            "severity": "medium",
            "likelihood": "medium",
            "mitigation": "Keep metric dictionary with the release; do not equate desirable-overtaking-behavior proxy with human comfort or certified safety.",
            "safe_claim": "The method improves benchmark-defined desirable and on-track overtaking rates.",
            "avoid_claim": "The method guarantees human-like or legally safe overtaking.",
            "source": "metric_dictionary.csv; BENCHMARK_METRIC_PROTOCOL_QA.json",
        },
        {
            "risk_id": "V05",
            "validity_class": "construct validity",
            "risk": "Close-contact proxy is not a certified collision or safety metric.",
            "evidence": "Metric dictionary explicitly labels collision_or_contact_proxy as a lightweight close-contact proxy.",
            "severity": "medium",
            "likelihood": "medium",
            "mitigation": "Use collision/contact language cautiously and keep certified collision modeling as future work.",
            "safe_claim": "The benchmark includes a close-contact proxy as supplementary safety evidence.",
            "avoid_claim": "The experiments prove collision-free operation.",
            "source": "metric_dictionary.csv",
        },
        {
            "risk_id": "V06",
            "validity_class": "internal validity",
            "risk": "The primary method still has high grass-rate cases.",
            "evidence": f"v6-safe high grass rate tag: {safe_grass.get('tag_count', 'NA')}/{safe_grass.get('case_count', 'NA')} cases; examples: {safe_grass.get('example_cases', 'NA')}.",
            "severity": "high",
            "likelihood": "medium",
            "mitigation": "Report failure atlas and discuss grass/off-track behavior as a remaining limitation.",
            "safe_claim": "v6-safe reduces grass exposure relative to original DLC but does not eliminate all off-track behavior.",
            "avoid_claim": "v6-safe always stays on track.",
            "source": "confirmatory_failure_atlas.csv; STATISTICAL_RESULTS_BRIEF.md",
        },
        {
            "risk_id": "V07",
            "validity_class": "internal validity",
            "risk": "Some successful passes are not desirable/on-track passes.",
            "evidence": f"v6-safe success-but-no-desirable-behavior tag: {safe_nonelegant.get('tag_count', 'NA')}/{safe_nonelegant.get('case_count', 'NA')} cases.",
            "severity": "medium",
            "likelihood": "medium",
            "mitigation": "Report success and desirable/on-track metrics together; avoid headline success-only claims.",
            "safe_claim": "The method improves both success and quality metrics, with remaining cases that do not satisfy desirable overtaking behavior criteria disclosed.",
            "avoid_claim": "All successful overtakes satisfy desirable overtaking behavior criteria.",
            "source": "confirmatory_failure_atlas.csv; manuscript English figures",
        },
        {
            "risk_id": "V08",
            "validity_class": "baseline fairness",
            "risk": "Rule expert can be strong in selected settings and should not be dismissed.",
            "evidence": f"Rule expert high grass-rate tag: {rule_grass.get('tag_count', 'NA')}/{rule_grass.get('case_count', 'NA')} cases; claim matrix marks it as a strong hand-coded baseline.",
            "severity": "medium",
            "likelihood": "medium",
            "mitigation": "Frame rule expert as a strong hand-engineered reference with failure-mode trade-offs.",
            "safe_claim": "The learned world-model method improves over original DLC while rule expert remains an informative strong baseline.",
            "avoid_claim": "Rules are uniformly weak or irrelevant.",
            "source": "confirmatory_claim_evidence_matrix.csv; confirmatory_failure_atlas.csv",
        },
        {
            "risk_id": "V09",
            "validity_class": "statistical validity",
            "risk": "Multiple endpoints and baselines can inflate isolated p-value interpretation.",
            "evidence": f"Statistical pack applies Holm-Bonferroni to {stats.get('primary_family_size')} primary metrics and reports {stats.get('exploratory_family_size')} exploratory comparisons separately.",
            "severity": "medium",
            "likelihood": "medium",
            "mitigation": "Lead with effect sizes and CIs; describe adjusted p values as support for frozen simulation claims only.",
            "safe_claim": "The five pre-specified v6-safe primary metrics remain supported after Holm correction.",
            "avoid_claim": "Every exploratory p value is an independent confirmatory discovery.",
            "source": "STATISTICAL_ANALYSIS_PLAN.md; STATISTICAL_ANALYSIS_QA.json",
        },
        {
            "risk_id": "V10",
            "validity_class": "reproducibility",
            "risk": "Author-owned publication metadata remain outside local automation.",
            "evidence": f"Final readiness dashboard lists author-owned items: {final_items}.",
            "severity": "medium",
            "likelihood": "high",
            "mitigation": "Assign DOI/accession, confirm license, finalize IEEE template and declarations before submission.",
            "safe_claim": "Local files support reproducibility and release routing.",
            "avoid_claim": "The package is publicly archived and DOI-backed before deposition.",
            "source": "FINAL_READINESS_DASHBOARD.md; PUBLIC_RELEASE_PLAN.md",
        },
        {
            "risk_id": "V11",
            "validity_class": "compute/provenance",
            "risk": "Complete historical wall-clock and GPU-utilization traces are not archived for every confirmatory run.",
            "evidence": "The compute reproducibility cost pack records 240 algorithm-runs, 528000 simulated finish steps, CUDA availability and 4 GPUs, while explicitly marking full wall-clock timing as unavailable.",
            "severity": "low",
            "likelihood": "medium",
            "mitigation": "Report complete algorithm-run scale, simulated steps, decision latency and GPU/environment snapshot; avoid overstating wall-clock accounting.",
            "safe_claim": "The compute evidence records decision latency, complete run scale and GPU/environment snapshot, with wall-clock timing disclosed as unavailable.",
            "avoid_claim": "Every historical wall-clock minute and GPU-utilization trace is fully audited.",
            "source": "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/materials/COMPUTE_REPRODUCIBILITY_COST_REPORT.md; outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_cost_by_algorithm.csv",
        },
        {
            "risk_id": "V12",
            "validity_class": "baseline limitation",
            "risk": "Original DLC and its tuning variants can fail because they are not overtake-aware planners.",
            "evidence": f"Original DLC high grass-rate tag: {original_grass.get('tag_count', 'NA')}/{original_grass.get('case_count', 'NA')} cases.",
            "severity": "medium",
            "likelihood": "medium",
            "mitigation": "State that baselines are DLC world-model variants by design; include rule expert and quality-proposal branch to broaden comparison.",
            "safe_claim": "Compared with original DLC world-model variants and rule baseline, dynamic-neighborhood DLC improves benchmark-defined overtaking quality.",
            "avoid_claim": "The method beats all possible modern autonomous driving planners.",
            "source": "ablation_contribution_pack; confirmatory_failure_atlas.csv",
        },
    ]
    return rows


def build_guardrails(risk_rows):
    fields = ["risk_id", "safe_claim", "avoid_claim", "source"]
    return [{field: row[field] for field in fields} for row in risk_rows]


def build_reviewer_response_map(risk_rows):
    rows = []
    templates = {
        "external validity": "We agree that this is bounded simulation evidence. We now state the benchmark scope explicitly and limit the claim to the evaluated procedural, 8-car extrapolation, and Monza CSV-derived settings.",
        "construct validity": "We agree that these are benchmark-defined proxies. We provide a metric dictionary and avoid equating the proxy with certified safety or human comfort.",
        "internal validity": "We agree that aggregate success can hide quality failures. We therefore report desirable/on-track metrics, grass exposure, and a failure atlas rather than success alone.",
        "baseline fairness": "We treat the rule expert as a strong hand-engineered reference and discuss its trade-offs rather than dismissing it.",
        "statistical validity": "We report paired effect sizes and confidence intervals first, apply Holm correction to the primary family, and keep exploratory p values separate.",
        "reproducibility": "We provide frozen commands, source data, checksums and release routing; DOI/license/template items remain explicitly author-owned before submission.",
        "compute/provenance": "We report complete run scale and latency evidence while disclosing the partial historical wall-clock ledger.",
        "baseline limitation": "We compare against the original DLC world model and its variants while acknowledging that this is not an exhaustive comparison to every possible planner.",
    }
    for row in risk_rows:
        rows.append(
            {
                "risk_id": row["risk_id"],
                "likely_reviewer_question": reviewer_question(row),
                "short_response": templates.get(row["validity_class"], row["mitigation"]),
                "evidence_to_cite": row["source"],
                "manuscript_location": suggested_location(row["validity_class"]),
            }
        )
    return rows


def reviewer_question(row):
    if row["risk_id"] == "V01":
        return "Does this prove real-world autonomous overtaking safety?"
    if row["risk_id"] == "V02":
        return "Is one Monza track enough for external validity?"
    if row["risk_id"] == "V03":
        return "Can the method scale to arbitrary traffic density?"
    if row["risk_id"] == "V06":
        return "Why does the proposed method still go off track in some cases?"
    if row["risk_id"] == "V09":
        return "How are multiple metrics and p values controlled?"
    return row["risk"]


def suggested_location(validity_class):
    mapping = {
        "external validity": "Discussion / Limitations",
        "construct validity": "Methods / Metrics / Limitations",
        "internal validity": "Results / Failure analysis / Limitations",
        "baseline fairness": "Experiments / Baselines / Discussion",
        "statistical validity": "Methods / Statistical analysis",
        "reproducibility": "Data and Code Availability / Supplement",
        "compute/provenance": "Supplement / Reproducibility",
        "baseline limitation": "Experiments / Baselines",
    }
    return mapping.get(validity_class, "Discussion")


def build_threats_md(risk_rows):
    by_class = {}
    for row in risk_rows:
        by_class.setdefault(row["validity_class"], []).append(row)
    lines = [
        "# Threats to Validity and Reviewer-Risk Dossier",
        "",
        "This dossier converts the current frozen evidence package into reviewer-facing validity risks, claim boundaries, and response material. It does not add new simulator runs.",
        "",
        "## Executive Summary",
        "",
        "- The strongest claim is limited to the evaluated simulation benchmark: procedural tracks, 8-car extrapolation, and one Monza CSV-derived external track.",
        "- The proposed method improves benchmark-defined success, desirable/on-track overtaking, completion time, and grass exposure relative to original DLC, but still has high-grass and cases that do not satisfy desirable overtaking behavior criteria.",
        "- Statistics should be reported as effect sizes and confidence intervals first; Holm-adjusted p values are support for the frozen matrix, not a real-world safety certificate.",
        "- DOI/accession, license, final IEEE formatting and declarations remain author-owned actions before submission.",
        "",
        "## Validity Risk Register",
        "",
    ]
    for validity_class, rows in sorted(by_class.items()):
        lines.extend([f"### {validity_class.title()}", ""])
        for row in rows:
            lines.extend(
                [
                    f"**{row['risk_id']} — {row['risk']}**",
                    "",
                    f"- Evidence: {row['evidence']}",
                    f"- Severity / likelihood: {row['severity']} / {row['likelihood']}",
                    f"- Mitigation: {row['mitigation']}",
                    f"- Safe claim: {row['safe_claim']}",
                    f"- Avoid claim: {row['avoid_claim']}",
                    f"- Source: `{row['source']}`",
                    "",
                ]
            )
    return "\n".join(lines)


def build_response_md(response_rows):
    lines = [
        "# Reviewer Risk Response Map",
        "",
        "| Risk ID | Likely reviewer question | Short response | Evidence to cite | Manuscript location |",
        "|---|---|---|---|---|",
    ]
    for row in response_rows:
        lines.append(
            f"| {row['risk_id']} | {row['likely_reviewer_question']} | {row['short_response']} | `{row['evidence_to_cite']}` | {row['manuscript_location']} |"
        )
    return "\n".join(lines)


def build_qa(paths, risk_rows):
    export_paths = [Path(path) for path in paths.values()]
    classes = sorted({row["validity_class"] for row in risk_rows})
    high_risks = [row for row in risk_rows if row["severity"] == "high"]
    return {
        "status": "pass" if all(path.exists() and path.stat().st_size > 0 for path in export_paths) and len(risk_rows) >= 10 else "check",
        "risk_count": len(risk_rows),
        "validity_classes": classes,
        "high_risk_count": len(high_risks),
        "checks": {
            "all_exports_nonempty": all(path.exists() and path.stat().st_size > 0 for path in export_paths),
            "has_external_validity_risk": "external validity" in classes,
            "has_statistical_validity_risk": "statistical validity" in classes,
            "has_reproducibility_risk": "reproducibility" in classes,
            "has_claim_guardrails": True,
        },
        "reviewer_risks": [
            "This is a risk-response dossier, not new empirical evidence.",
            "The risk register should be used to constrain claims rather than to imply all risks are solved.",
            "Author-owned DOI, license, template and declaration items remain unresolved until submission preparation.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Export T-ITS threats-to-validity and reviewer-risk response materials.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_threats_validity_pack")
    parser.add_argument("--failure-atlas", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_failure_atlas.csv")
    parser.add_argument("--claim-matrix", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_claim_evidence_matrix.csv")
    parser.add_argument("--protocol-qa", default="outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/materials/BENCHMARK_METRIC_PROTOCOL_QA.json")
    parser.add_argument("--statistics-qa", default="outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/STATISTICAL_ANALYSIS_QA.json")
    parser.add_argument("--final-readiness", default="outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    tables_dir = out_dir / "tables"
    materials_dir = out_dir / "materials"
    tables_dir.mkdir(parents=True, exist_ok=True)
    materials_dir.mkdir(parents=True, exist_ok=True)

    failure_rows = read_csv(args.failure_atlas)
    claim_rows = read_csv(args.claim_matrix)
    protocol_qa = load_json(args.protocol_qa)
    statistics_qa = load_json(args.statistics_qa)
    final_readiness = load_json(args.final_readiness)

    risk_rows = build_risk_register(failure_rows, claim_rows, protocol_qa, statistics_qa, final_readiness)
    guardrails = build_guardrails(risk_rows)
    response_rows = build_reviewer_response_map(risk_rows)

    risk_fields = [
        "risk_id",
        "validity_class",
        "risk",
        "evidence",
        "severity",
        "likelihood",
        "mitigation",
        "safe_claim",
        "avoid_claim",
        "source",
    ]
    response_fields = ["risk_id", "likely_reviewer_question", "short_response", "evidence_to_cite", "manuscript_location"]
    guardrail_fields = ["risk_id", "safe_claim", "avoid_claim", "source"]
    paths = {}
    paths["risk_register_csv"] = write_csv(tables_dir / "threats_validity_risk_register.csv", risk_rows, risk_fields)
    paths["reviewer_response_csv"] = write_csv(tables_dir / "reviewer_risk_response_map.csv", response_rows, response_fields)
    paths["claim_guardrails_csv"] = write_csv(tables_dir / "claim_language_guardrails.csv", guardrails, guardrail_fields)
    paths["threats_md"] = write_text(materials_dir / "THREATS_TO_VALIDITY_DOSSIER.md", build_threats_md(risk_rows))
    paths["response_md"] = write_text(materials_dir / "REVIEWER_RISK_RESPONSE_MAP.md", build_response_md(response_rows))
    qa = build_qa(paths, risk_rows)
    paths["qa_json"] = write_json(materials_dir / "THREATS_VALIDITY_QA.json", qa)

    manifest = {
        "status": "complete" if qa["status"] == "pass" else "check",
        "out_dir": str(out_dir),
        "paths": paths,
        "summary": {
            "risk_count": len(risk_rows),
            "validity_class_count": len(set(row["validity_class"] for row in risk_rows)),
            "high_risk_count": sum(1 for row in risk_rows if row["severity"] == "high"),
            "response_count": len(response_rows),
            "claim_guardrail_count": len(guardrails),
        },
        "inputs": {
            "failure_atlas": args.failure_atlas,
            "claim_matrix": args.claim_matrix,
            "protocol_qa": args.protocol_qa,
            "statistics_qa": args.statistics_qa,
            "final_readiness": args.final_readiness,
        },
    }
    manifest_path = write_json(out_dir / "tits_threats_validity_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
