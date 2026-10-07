#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


LIMITATIONS_DRAFT = "outputs/tits_dynamic_graph/tits_manuscript_package/materials/LIMITATIONS_DRAFT.md"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"


def read_text(path):
    path = Path(path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def source_facts(root):
    rows = read_csv(root / SOURCE_DATA)
    cases = {
        (
            row.get("_benchmark"),
            row.get("seed"),
            row.get("num_agents"),
            row.get("track_path"),
            row.get("traffic_profile"),
        )
        for row in rows
    }
    vehicle_counts = sorted({int(row.get("num_agents", 0) or 0) for row in rows})
    tracks = sorted({row.get("track_path", "") for row in rows})
    algorithms = sorted({row.get("algorithm", "") for row in rows})
    return {
        "source_rows": len(rows),
        "matched_case_count": len(cases),
        "algorithm_count": len(algorithms),
        "vehicle_counts": vehicle_counts,
        "max_vehicle_count": max(vehicle_counts) if vehicle_counts else 0,
        "has_monza_external_track": "tracks/monza_scaled.npz" in tracks,
        "tracks": tracks,
    }


def limitation_specs():
    return [
        {
            "limitation_id": "L01_simulation_only",
            "limitation": "The evidence is simulation-only and does not certify real-vehicle safety or deployment readiness.",
            "required_phrases": ["limited to simulation", "does not establish real-vehicle safety"],
            "evidence": "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md; outputs/tits_dynamic_graph/tits_claim_language_audit/materials/CLAIM_LANGUAGE_AUDIT.md",
            "manuscript_use": "Discussion / Limitations / Data and Code Availability",
            "forbidden_claim": "Do not claim real-road safety, legal compliance, deployment readiness or certified collision-free behavior.",
        },
        {
            "limitation_id": "L02_track_and_vehicle_scope",
            "limitation": "External validity is bounded by procedural tracks, one Monza CSV-derived external track and vehicle-count extrapolation up to 8 vehicles.",
            "required_phrases": ["procedural track family", "8-vehicle extrapolation", "Monza external CSV-derived track"],
            "evidence": "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv; outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "manuscript_use": "Experiments / Discussion",
            "forbidden_claim": "Do not claim arbitrary road geometry, unlimited density or untested vehicle-count generalization.",
        },
        {
            "limitation_id": "L03_residual_quality_failures",
            "limitation": "The optimized controller improves quality but still has high-grass, off-track and tail cases that do not satisfy desirable overtaking behavior criteria.",
            "required_phrases": ["does not eliminate all quality failures", "high grass-rate cases", "overtakes that do not satisfy desirable overtaking behavior criteria"],
            "evidence": "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/materials/SAFETY_PROXY_AUDIT_PACK.md; outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/materials/CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md",
            "manuscript_use": "Results / Discussion / Supplementary failure atlas",
            "forbidden_claim": "Do not report success-rate gains as always-on-track or always desirable overtaking.",
        },
        {
            "limitation_id": "L04_tail_case_transparency",
            "limitation": "Worst-case cards and long overtake windows should be discussed as tail-case evidence rather than hidden by aggregate means.",
            "required_phrases": ["worst-case cards", "long overtake windows", "not as replacements for the 240-run aggregate statistics"],
            "evidence": "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_worst_case_cards.csv; outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/materials/ONLINE_DECISION_CASE_STUDY_PACK.md",
            "manuscript_use": "Discussion / Reviewer response",
            "forbidden_claim": "Do not replace confirmatory aggregate evidence with selected qualitative cases.",
        },
        {
            "limitation_id": "L05_rule_expert_strength",
            "limitation": "The rule expert remains a strong hand-coded baseline in selected settings and should not be dismissed.",
            "required_phrases": ["rule expert remains a strong baseline", "hand-coded traffic rules"],
            "evidence": "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/materials/BASELINE_FAIRNESS_AUDIT.md; outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_REPORT.md",
            "manuscript_use": "Baselines / Discussion",
            "forbidden_claim": "Do not imply that learned world models dominate all rule-based behavior in every scenario.",
        },
        {
            "limitation_id": "L06_metric_threshold_sensitivity",
            "limitation": "On-track and desirable-overtaking-behavior labels depend on post-hoc threshold choices and must be paired with sensitivity evidence.",
            "required_phrases": ["post-hoc analysis boundary", "threshold choices", "sensitivity evidence"],
            "evidence": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md; outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/materials/BENCHMARK_METRIC_PROTOCOL_CARD.md",
            "manuscript_use": "Methods / Results / Discussion",
            "forbidden_claim": "Do not present thresholded quality metrics as universal driving-quality guarantees.",
        },
        {
            "limitation_id": "L07_quality_proposal_role",
            "limitation": "The quality-proposal branch is a proposal mechanism inside the DLC-style world-model family, not a standalone optimal controller.",
            "required_phrases": ["quality-proposal branch", "not an independently optimal controller", "candidate actions"],
            "evidence": "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials/INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md; outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_REPORT.md",
            "manuscript_use": "Methods / Ablation",
            "forbidden_claim": "Do not claim the proposal branch replaces world-model planning or proves optimal control.",
        },
        {
            "limitation_id": "L08_compute_timing_boundary",
            "limitation": "The compute ledger partially records wall-clock timing because the matrix includes repair runs; report scale using run counts and simulated steps.",
            "required_phrases": ["not a complete historical wall-clock trace", "repair runs", "240 algorithm-runs"],
            "evidence": "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/materials/COMPUTE_TIMING_BOUNDARY_AUDIT.md; outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/materials/REVIEWER_REPRODUCTION_TIME_BUDGET_AUDIT.md",
            "manuscript_use": "Reproducibility / Compute resources",
            "forbidden_claim": "Do not report partially recorded wall-clock time as a complete historical runtime trace.",
        },
        {
            "limitation_id": "L09_future_validation",
            "limitation": "Future work should add more tracks, denser traffic, diverse background drivers, contact modeling, deployment profiling and sim-to-real validation.",
            "required_phrases": ["Future work", "more external tracks", "higher-density traffic", "sim-to-real validation"],
            "evidence": "outputs/tits_dynamic_graph/tits_threats_validity_pack/materials/THREATS_TO_VALIDITY_DOSSIER.md; outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/materials/REVIEWER_REBUTTAL_READINESS_PACK.md",
            "manuscript_use": "Discussion / Future work",
            "forbidden_claim": "Do not frame these future validation items as already solved by the present simulator benchmark.",
        },
    ]


def evidence_status(root, evidence):
    paths = [item.strip() for item in evidence.split(";") if item.strip()]
    missing = [path for path in paths if not (root / path).exists()]
    return paths, missing


def build_rows(root, limitations_text):
    rows = []
    for spec in limitation_specs():
        phrase_hits = [phrase for phrase in spec["required_phrases"] if phrase in limitations_text]
        paths, missing = evidence_status(root, spec["evidence"])
        status = "pass" if len(phrase_hits) == len(spec["required_phrases"]) and not missing else "review_required"
        rows.append(
            {
                "limitation_id": spec["limitation_id"],
                "status": status,
                "limitation": spec["limitation"],
                "required_phrase_count": len(spec["required_phrases"]),
                "phrase_hit_count": len(phrase_hits),
                "missing_phrases": "; ".join(phrase for phrase in spec["required_phrases"] if phrase not in phrase_hits),
                "evidence_paths": "; ".join(paths),
                "missing_evidence_paths": "; ".join(missing),
                "manuscript_use": spec["manuscript_use"],
                "forbidden_claim": spec["forbidden_claim"],
            }
        )
    return rows


def build_checks(root, facts, rows):
    manifests = {
        "external_validity": read_json(root / "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/tits_external_validity_boundary_audit_manifest.json"),
        "threats_validity": read_json(root / "outputs/tits_dynamic_graph/tits_threats_validity_pack/tits_threats_validity_pack_manifest.json"),
        "claim_language": read_json(root / "outputs/tits_dynamic_graph/tits_claim_language_audit/tits_claim_language_audit_manifest.json"),
        "safety_proxy": read_json(root / "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/tits_safety_proxy_audit_pack_manifest.json"),
        "casewise": read_json(root / "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tits_casewise_diagnostic_pack_manifest.json"),
        "metric_sensitivity": read_json(root / "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tits_metric_sensitivity_audit_manifest.json"),
        "compute_timing": read_json(root / "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/tits_compute_timing_boundary_audit_manifest.json"),
        "reviewer_rebuttal": read_json(root / "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/tits_reviewer_rebuttal_readiness_pack_manifest.json"),
    }
    expected = {
        "external_validity": "pass",
        "threats_validity": "complete",
        "claim_language": "pass",
        "safety_proxy": "pass",
        "casewise": "pass",
        "metric_sensitivity": "pass",
        "compute_timing": "pass",
        "reviewer_rebuttal": "pass",
    }
    checks = []
    for name, expected_status in expected.items():
        observed = manifests[name].get("status")
        checks.append(
            {
                "check_id": f"manifest_{name}",
                "dimension": "upstream_evidence_status",
                "observed": str(observed),
                "expected": expected_status,
                "status": "pass" if observed == expected_status else "review_required",
                "note": "Upstream evidence package required for limitation wording.",
            }
        )
    checks.extend(
        [
            {
                "check_id": "formal_source_rows",
                "dimension": "formal_matrix_scope",
                "observed": str(facts["source_rows"]),
                "expected": "240",
                "status": "pass" if facts["source_rows"] == 240 else "review_required",
                "note": "Limitations should refer to the frozen confirmatory matrix scale.",
            },
            {
                "check_id": "formal_algorithm_count",
                "dimension": "formal_matrix_scope",
                "observed": str(facts["algorithm_count"]),
                "expected": "8",
                "status": "pass" if facts["algorithm_count"] == 8 else "review_required",
                "note": "Baseline and method-scope wording depends on the formal comparison set.",
            },
            {
                "check_id": "max_vehicle_count",
                "dimension": "external_validity_boundary",
                "observed": str(facts["max_vehicle_count"]),
                "expected": "8",
                "status": "pass" if facts["max_vehicle_count"] == 8 else "review_required",
                "note": "Do not claim beyond the evaluated vehicle-count extrapolation boundary.",
            },
            {
                "check_id": "monza_track_present",
                "dimension": "external_validity_boundary",
                "observed": str(facts["has_monza_external_track"]),
                "expected": "True",
                "status": "pass" if facts["has_monza_external_track"] else "review_required",
                "note": "The only external CSV-derived track currently represented in the formal matrix is Monza.",
            },
            {
                "check_id": "limitations_all_covered",
                "dimension": "draft_coverage",
                "observed": f"{sum(row['status'] == 'pass' for row in rows)}/{len(rows)}",
                "expected": f"{len(rows)}/{len(rows)}",
                "status": "pass" if all(row["status"] == "pass" for row in rows) else "review_required",
                "note": "Each required limitation must have draft wording and evidence paths.",
            },
        ]
    )
    return checks


def build_markdown(summary, rows, checks):
    lines = [
        "# Limitations Evidence Audit",
        "",
        "This audit checks whether the manuscript limitation wording covers the main evidence boundaries that a T-ITS reviewer is likely to inspect. It does not create new experiments; it links each limitation to existing formal source data, statistical/diagnostic packs and claim guardrails.",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Limitation-to-Evidence Map",
            "",
            "| ID | Status | Limitation | Phrase coverage | Evidence | Manuscript use | Forbidden claim |",
            "|---|---|---|---:|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['limitation_id']} | {row['status']} | {row['limitation']} | "
            f"{row['phrase_hit_count']}/{row['required_phrase_count']} | `{row['evidence_paths']}` | "
            f"{row['manuscript_use']} | {row['forbidden_claim']} |"
        )
    lines.extend(
        [
            "",
            "## Audit Checks",
            "",
            "| Check | Dimension | Observed | Expected | Status | Note |",
            "|---|---|---:|---:|---|---|",
        ]
    )
    for check in checks:
        lines.append(
            f"| {check['check_id']} | {check['dimension']} | {check['observed']} | "
            f"{check['expected']} | {check['status']} | {check['note']} |"
        )
    lines.extend(
        [
            "",
            "## Writing Guidance",
            "",
            "- Keep the limitation section visible in the final Discussion rather than moving all negative evidence to supplementary material.",
            "- Pair the main improvement claims with residual grass/off-track and tail-case statements for behavior that does not satisfy desirable overtaking behavior criteria.",
            "- Use the rule expert as a strong reference baseline, not as a weak strawman.",
            "- Treat metric-threshold sensitivity as a post-hoc robustness analysis, not as a prespecified primary endpoint.",
            "- Maintain the simulation-only, Monza-single-external-track and 8-vehicle extrapolation boundaries in Abstract, Discussion and Conclusion.",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export a limitation-to-evidence audit for the T-ITS dynamic graph manuscript package.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_limitations_evidence_audit")
    args = parser.parse_args()

    root = Path(args.root)
    out_dir = Path(args.out_dir)
    limitations_text = read_text(root / LIMITATIONS_DRAFT)
    facts = source_facts(root)
    rows = build_rows(root, limitations_text)
    checks = build_checks(root, facts, rows)
    issue_count = sum(row["status"] != "pass" for row in rows) + sum(check["status"] != "pass" for check in checks)
    status = "pass" if issue_count == 0 else "review_required"
    summary = {
        "status": status,
        "limitation_count": len(rows),
        "limitation_issue_count": sum(row["status"] != "pass" for row in rows),
        "check_count": len(checks),
        "check_issue_count": sum(check["status"] != "pass" for check in checks),
        "source_rows": facts["source_rows"],
        "matched_case_count": facts["matched_case_count"],
        "algorithm_count": facts["algorithm_count"],
        "vehicle_counts": facts["vehicle_counts"],
        "max_vehicle_count": facts["max_vehicle_count"],
        "has_monza_external_track": facts["has_monza_external_track"],
    }
    paths = {
        "markdown": write_text(out_dir / "materials" / "LIMITATIONS_EVIDENCE_AUDIT.md", build_markdown(summary, rows, checks)),
        "limitation_map_csv": write_csv(
            out_dir / "tables" / "limitations_evidence_map.csv",
            rows,
            [
                "limitation_id",
                "status",
                "limitation",
                "required_phrase_count",
                "phrase_hit_count",
                "missing_phrases",
                "evidence_paths",
                "missing_evidence_paths",
                "manuscript_use",
                "forbidden_claim",
            ],
        ),
        "checks_csv": write_csv(
            out_dir / "tables" / "limitations_evidence_checks.csv",
            checks,
            ["check_id", "dimension", "observed", "expected", "status", "note"],
        ),
    }
    manifest = {
        "status": status,
        "out_dir": str(out_dir),
        "summary": summary,
        "paths": paths,
        "source_inputs": [
            LIMITATIONS_DRAFT,
            SOURCE_DATA,
            "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/tits_external_validity_boundary_audit_manifest.json",
            "outputs/tits_dynamic_graph/tits_threats_validity_pack/tits_threats_validity_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_claim_language_audit/tits_claim_language_audit_manifest.json",
            "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/tits_safety_proxy_audit_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tits_casewise_diagnostic_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tits_metric_sensitivity_audit_manifest.json",
            "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/tits_compute_timing_boundary_audit_manifest.json",
            "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/tits_reviewer_rebuttal_readiness_pack_manifest.json",
        ],
    }
    manifest_path = write_json(out_dir / "tits_limitations_evidence_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
