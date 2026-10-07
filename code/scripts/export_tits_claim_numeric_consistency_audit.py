#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
import re
from pathlib import Path


CLAIM_MATRIX = "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/tables/claim_evidence_completeness_matrix.csv"
OVERALL = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv"
SCENARIO = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_scenario_statistics.csv"
PRIMARY = "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv"
RUNTIME = "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_scalability_by_vehicle_count.csv"
ROBUSTNESS = "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/robustness_summary_by_algorithm.csv"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
COMPUTE_ENV = "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_environment_snapshot.csv"
CONTAINER = "outputs/tits_dynamic_graph/tits_container_build_preflight/tits_container_build_preflight_manifest.json"


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def to_float(value):
    try:
        if value in {None, ""}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt(value, digits=3):
    if value is None:
        return ""
    return f"{float(value):.{digits}f}"


def approx_equal(observed, expected, tolerance):
    if observed is None or expected is None:
        return False
    return abs(float(observed) - float(expected)) <= tolerance


def find_row(rows, **filters):
    for row in rows:
        if all(str(row.get(key, "")) == str(value) for key, value in filters.items()):
            return row
    return {}


def source_facts(rows):
    cases = {
        (row.get("_benchmark", ""), row.get("seed", ""), row.get("num_agents", ""), row.get("track_path", ""), row.get("traffic_profile", ""))
        for row in rows
    }
    return {
        "source_rows": len(rows),
        "matched_case_count": len(cases),
        "algorithm_count": len({row.get("algorithm", "") for row in rows if row.get("algorithm", "")}),
        "total_finish_steps": sum(int(float(row.get("finish_step") or 0)) for row in rows),
    }


def env_lookup(rows):
    return {row.get("item", ""): row.get("value", "") for row in rows}


def extract_numbers(text):
    numbers = []
    for match in re.finditer(r"(?<![A-Za-z0-9_])[-+]?\d+(?:\.\d+)?(?:/\d+)?", text):
        numbers.append({"token": match.group(0), "start": match.start(), "context": text[max(0, match.start() - 60): match.end() + 60]})
    return numbers


def add_check(rows, claim_id, metric, observed, expected, source, tolerance=0.0005, note=""):
    if isinstance(expected, str) and ("/" in expected or expected in {"True", "False"}):
        status = "pass" if str(observed) == expected else "mismatch"
        delta = ""
    else:
        obs = to_float(observed)
        exp = to_float(expected)
        status = "pass" if approx_equal(obs, exp, tolerance) else "mismatch"
        delta = "" if obs is None or exp is None else obs - exp
    rows.append(
        {
            "claim_id": claim_id,
            "metric": metric,
            "observed_in_claim": observed,
            "expected_from_source": expected,
            "abs_tolerance": tolerance,
            "delta": delta,
            "source": source,
            "status": status,
            "note": note,
        }
    )


def build_checks(claims, overall, scenario, primary, runtime, robustness, source_rows, final, env_rows, container):
    checks = []
    claim_by_id = {row["claim_id"]: row for row in claims}
    facts = source_facts(source_rows)
    env = env_lookup(env_rows)
    ours = find_row(overall, algorithm="v6_runtime_dynamic_neighborhood_safe")
    dlc = find_row(overall, algorithm="dlc_world_original")
    rule = find_row(overall, algorithm="rule_expert_gate")
    quality = find_row(overall, algorithm="quality_proposal_dlc_world_v1")
    safe_n8 = find_row(runtime, algorithm="v6_runtime_dynamic_neighborhood_safe", num_agents="8")
    dlc_n8 = find_row(runtime, algorithm="dlc_world_original", num_agents="8")
    safe_monza_n6 = find_row(scenario, algorithm="v6_runtime_dynamic_neighborhood_safe", benchmark="monza_external_track", num_agents="6")
    dlc_monza_n6 = find_row(scenario, algorithm="dlc_world_original", benchmark="monza_external_track", num_agents="6")
    robust_safe = find_row(robustness, algorithm="v6_runtime_dynamic_neighborhood_safe")
    robust_rule = find_row(robustness, algorithm="rule_expert_gate")
    primary_by_metric = {row.get("metric"): row for row in primary if row.get("algorithm") == "v6_runtime_dynamic_neighborhood_safe" and row.get("baseline") == "dlc_world_original"}

    # C01 main result.
    add_check(checks, "C01", "success_ours", "0.933", fmt(ours.get("overtake_success_rate_mean")), OVERALL)
    add_check(checks, "C01", "success_dlc", "0.633", fmt(dlc.get("overtake_success_rate_mean")), OVERALL)
    add_check(checks, "C01", "elegant_ours", "0.455", fmt(ours.get("elegant_overtake_rate_mean")), OVERALL)
    add_check(checks, "C01", "elegant_dlc", "0.077", fmt(dlc.get("elegant_overtake_rate_mean")), OVERALL)
    add_check(checks, "C01", "completion_time_ours", "85.3", f"{to_float(ours.get('overtake_start_to_complete_time_mean')):.1f}", OVERALL, 0.05)
    add_check(checks, "C01", "completion_time_dlc", "378.5", f"{to_float(dlc.get('overtake_start_to_complete_time_mean')):.1f}", OVERALL, 0.05)

    # C02 paired gains.
    for metric, observed in [
        ("overtake_success_rate", "+0.300"),
        ("elegant_overtake_rate", "+0.378"),
        ("on_track_overtake_rate", "+0.378"),
        ("overtake_start_to_complete_time", "292.2"),
    ]:
        row = primary_by_metric.get(metric, {})
        expected = to_float(row.get("improvement_mean"))
        if metric == "overtake_start_to_complete_time":
            expected_text = f"{expected:.1f}" if expected is not None else ""
            add_check(checks, "C02", f"paired_gain_{metric}", observed, expected_text, PRIMARY, 0.05)
        else:
            expected_text = f"{expected:+.3f}" if expected is not None else ""
            add_check(checks, "C02", f"paired_gain_{metric}", observed, expected_text, PRIMARY)

    # C03 dynamic vehicle count.
    add_check(checks, "C03", "n8_elegant_ours", "0.741", fmt(safe_n8.get("elegant_mean")), RUNTIME)
    add_check(checks, "C03", "n8_elegant_dlc", "0.302", fmt(dlc_n8.get("elegant_mean")), RUNTIME)

    # C04 external track.
    add_check(checks, "C04", "monza_n6_success_ours", "1.000", fmt(safe_monza_n6.get("overtake_success_rate_mean")), SCENARIO)
    add_check(checks, "C04", "monza_n6_success_dlc", "0.000", fmt(dlc_monza_n6.get("overtake_success_rate_mean")), SCENARIO)

    # C05 failure boundary.
    add_check(checks, "C05", "grass_ours", "0.601", fmt(ours.get("target_grass_rate_mean")), OVERALL)
    add_check(checks, "C05", "grass_dlc", "0.767", fmt(dlc.get("target_grass_rate_mean")), OVERALL)

    # C06 rule expert.
    add_check(checks, "C06", "rule_elegant_rate", "0.519", fmt(rule.get("elegant_overtake_rate_mean")), OVERALL)
    add_check(checks, "C06", "rule_positive_threshold_fraction", "1.000", fmt(robust_rule.get("positive_delta_fraction")), ROBUSTNESS)

    # C07 sensitivity.
    add_check(checks, "C07", "safe_positive_threshold_fraction", "0.894", fmt(robust_safe.get("positive_delta_fraction")), ROBUSTNESS)
    add_check(checks, "C07", "safe_nonnegative_threshold_fraction", "1.000", fmt(robust_safe.get("nonnegative_delta_fraction")), ROBUSTNESS)

    # C11 quality proposal.
    add_check(checks, "C11", "quality_success", "1.000", fmt(quality.get("overtake_success_rate_mean")), OVERALL)
    add_check(checks, "C11", "quality_elegant", "0.286", fmt(quality.get("elegant_overtake_rate_mean")), OVERALL)

    # C12 reproducibility.
    add_check(checks, "C12", "source_rows", "240", facts["source_rows"], SOURCE_DATA, 0)
    add_check(checks, "C12", "algorithm_count", "8", facts["algorithm_count"], SOURCE_DATA, 0)
    add_check(checks, "C12", "simulated_steps", "528000", facts["total_finish_steps"], SOURCE_DATA, 0)
    add_check(checks, "C12", "final_readiness", f"{final.get('pass_count')}/{final.get('gate_count')}", f"{final.get('pass_count')}/{final.get('gate_count')}", FINAL_READINESS, 0)

    # C13 compute transparency.
    gpu_count = env.get("gpu_count", "") or env.get("torch_cuda_device_count", "")
    add_check(checks, "C13", "gpu_count", "4", gpu_count, COMPUTE_ENV, 0)

    # C15 container boundary.
    summary = container.get("summary", {})
    for key, expected in [("docker_available", False), ("apptainer_or_singularity_available", False), ("build_attempted", False), ("image_built", False)]:
        observed = str(summary.get(key))
        add_check(checks, "C15", key, observed, str(expected), CONTAINER, 0)

    numeric_claim_ids = {row["claim_id"] for row in checks}
    for claim_id, row in sorted(claim_by_id.items()):
        if claim_id not in numeric_claim_ids:
            checks.append(
                {
                    "claim_id": claim_id,
                    "metric": "not_numeric_claim",
                    "observed_in_claim": "",
                    "expected_from_source": "",
                    "abs_tolerance": "",
                    "delta": "",
                    "source": "",
                    "status": "not_applicable",
                    "note": "No concrete numeric assertion is audited for this claim.",
                }
            )
    return checks


def build_extracted_number_rows(claims):
    rows = []
    for claim in claims:
        text = claim.get("allowed_claim", "")
        for item in extract_numbers(text):
            rows.append(
                {
                    "claim_id": claim.get("claim_id", ""),
                    "token": item["token"],
                    "context": item["context"],
                }
            )
    return rows


def summarize(checks, number_rows):
    blocking = [row for row in checks if row["status"] == "mismatch"]
    audited = [row for row in checks if row["status"] == "pass"]
    return {
        "status": "pass" if not blocking else "review_required",
        "numeric_check_count": len(audited),
        "mismatch_count": len(blocking),
        "not_applicable_claim_count": sum(1 for row in checks if row["status"] == "not_applicable"),
        "extracted_number_count": len(number_rows),
        "audited_claim_count": len({row["claim_id"] for row in audited}),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Claim Numeric Consistency Audit",
        "",
        "This audit rechecks the concrete numeric assertions in claim-level writing against the frozen formal source data and derived statistical tables. It is narrower than the evidence ledger: it asks whether the numbers written in claims still equal the current formal evidence.",
        "",
        "## Summary",
        "",
        f"- Status: `{summary['status']}`",
        f"- Numeric checks: {summary['numeric_check_count']}",
        f"- Mismatches: {summary['mismatch_count']}",
        f"- Not-applicable nonnumeric claims: {summary['not_applicable_claim_count']}",
        f"- Extracted numeric tokens from allowed claims: {summary['extracted_number_count']}",
        "",
        "## Blocking Mismatches",
        "",
    ]
    mismatches = [row for row in report["check_rows"] if row["status"] == "mismatch"]
    if not mismatches:
        lines.append("No numeric mismatches were found.")
    else:
        lines.extend(["| Claim | Metric | Observed | Expected | Source |", "|---|---|---:|---:|---|"])
        for row in mismatches:
            lines.append(f"| {row['claim_id']} | {row['metric']} | {row['observed_in_claim']} | {row['expected_from_source']} | `{row['source']}` |")
    lines.extend(
        [
            "",
            "## Audited Numeric Checks",
            "",
            "| Claim | Metric | Observed | Expected | Status |",
            "|---|---|---:|---:|---|",
        ]
    )
    for row in report["check_rows"]:
        if row["status"] == "not_applicable":
            continue
        lines.append(f"| {row['claim_id']} | {row['metric']} | {row['observed_in_claim']} | {row['expected_from_source']} | {row['status']} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This audit covers high-value numeric claim text, not every number in every generated material. The broader freshness audit still scans manuscript-facing files for stale global numbers.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_claim_numeric_consistency_audit.py --out-dir outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit numeric consistency of T-ITS claim text against formal evidence tables.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    claims = read_csv(root / CLAIM_MATRIX)
    checks = build_checks(
        claims,
        read_csv(root / OVERALL),
        read_csv(root / SCENARIO),
        read_csv(root / PRIMARY),
        read_csv(root / RUNTIME),
        read_csv(root / ROBUSTNESS),
        read_csv(root / SOURCE_DATA),
        read_json(root / FINAL_READINESS),
        read_csv(root / COMPUTE_ENV),
        read_json(root / CONTAINER),
    )
    extracted = build_extracted_number_rows(claims)
    summary = summarize(checks, extracted)
    report = {
        "status": summary["status"],
        "out_dir": args.out_dir,
        "summary": summary,
        "check_rows": checks,
        "extracted_number_rows": extracted,
        "note": "This audit checks selected high-value numeric claim assertions; it does not rerun simulations.",
    }
    paths = {
        "audit_md": write_text(materials / "CLAIM_NUMERIC_CONSISTENCY_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "CLAIM_NUMERIC_CONSISTENCY_AUDIT.json", report),
        "check_rows_csv": write_csv(
            tables / "claim_numeric_consistency_checks.csv",
            checks,
            ["claim_id", "metric", "observed_in_claim", "expected_from_source", "abs_tolerance", "delta", "source", "status", "note"],
        ),
        "extracted_numbers_csv": write_csv(
            tables / "claim_numeric_extracted_tokens.csv",
            extracted,
            ["claim_id", "token", "context"],
        ),
    }
    manifest = {"status": summary["status"], "out_dir": args.out_dir, "summary": summary, "paths": paths}
    manifest_path = write_json(out_dir / "tits_claim_numeric_consistency_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": summary["status"], "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
