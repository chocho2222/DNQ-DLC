#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
BENCHMARK_CARDS = "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/benchmark_cards.csv"
THREATS_REGISTER = "outputs/tits_dynamic_graph/tits_threats_validity_pack/tables/threats_validity_risk_register.csv"


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


def to_float(value, default=0.0):
    try:
        if value in {"", None}:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def fmt(value):
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def source_facts(rows):
    case_keys = {
        (
            row.get("_benchmark", ""),
            row.get("seed", ""),
            row.get("num_agents", ""),
            row.get("track_path", ""),
            row.get("traffic_profile", ""),
        )
        for row in rows
    }
    benchmark_case_counts = Counter(
        (
            row.get("_benchmark", ""),
            row.get("seed", ""),
            row.get("num_agents", ""),
            row.get("track_path", ""),
            row.get("traffic_profile", ""),
        )
        for row in rows
    )
    cases_by_benchmark = defaultdict(set)
    for benchmark, seed, num_agents, track_path, traffic_profile in benchmark_case_counts:
        cases_by_benchmark[benchmark].add((seed, num_agents, track_path, traffic_profile))
    return {
        "source_rows": len(rows),
        "matched_case_count": len(case_keys),
        "algorithm_count": len({row.get("algorithm", "") for row in rows if row.get("algorithm", "")}),
        "benchmarks": sorted({row.get("_benchmark", "") for row in rows if row.get("_benchmark", "")}),
        "tracks": sorted({row.get("track_path", "") for row in rows if row.get("track_path", "")}),
        "vehicle_counts": sorted({row.get("num_agents", "") for row in rows if row.get("num_agents", "")}, key=lambda item: int(item or 0)),
        "traffic_profiles": sorted({row.get("traffic_profile", "") for row in rows if row.get("traffic_profile", "")}),
        "cases_by_benchmark": {key: len(value) for key, value in sorted(cases_by_benchmark.items())},
        "seeds_by_benchmark": {
            key: sorted({case[0] for case in value}, key=lambda item: int(item or 0))
            for key, value in sorted(cases_by_benchmark.items())
        },
    }


def algorithm_metric_summary(rows, algorithm):
    subset = [row for row in rows if row.get("algorithm") == algorithm]
    return {
        "algorithm": algorithm,
        "runs": len(subset),
        "success_mean": mean(to_float(row.get("overtake_success_rate")) for row in subset),
        "elegant_mean": mean(to_float(row.get("elegant_overtake_rate")) for row in subset),
        "on_track_mean": mean(to_float(row.get("on_track_overtake_rate")) for row in subset),
        "grass_mean": mean(to_float(row.get("target_grass_rate")) for row in subset),
        "latency_mean_ms": mean(to_float(row.get("compute_latency_ms")) for row in subset),
    }


def benchmark_metric_rows(rows, primary_algorithm):
    out = []
    for key in sorted({(row.get("_benchmark", ""), row.get("num_agents", ""), row.get("track_path", "")) for row in rows}):
        benchmark, num_agents, track_path = key
        subset = [
            row
            for row in rows
            if row.get("_benchmark") == benchmark
            and row.get("num_agents") == num_agents
            and row.get("track_path") == track_path
            and row.get("algorithm") == primary_algorithm
        ]
        if not subset:
            continue
        out.append(
            {
                "benchmark": benchmark,
                "num_agents": num_agents,
                "track_path": track_path,
                "runs": len(subset),
                "success_mean": fmt(mean(to_float(row.get("overtake_success_rate")) for row in subset)),
                "elegant_mean": fmt(mean(to_float(row.get("elegant_overtake_rate")) for row in subset)),
                "on_track_mean": fmt(mean(to_float(row.get("on_track_overtake_rate")) for row in subset)),
                "grass_mean": fmt(mean(to_float(row.get("target_grass_rate")) for row in subset)),
                "latency_mean_ms": fmt(mean(to_float(row.get("compute_latency_ms")) for row in subset)),
            }
        )
    return out


def build_boundary_rows(facts, rows, benchmark_cards, threat_rows):
    risk_by_id = {row.get("risk_id"): row for row in threat_rows}
    primary = algorithm_metric_summary(rows, "v6_runtime_dynamic_neighborhood_safe")
    monza_cases = facts["cases_by_benchmark"].get("monza_external_track", 0)
    extrap_cases = facts["cases_by_benchmark"].get("vehicle_count_extrapolation", 0)
    procedural_cases = facts["cases_by_benchmark"].get("in_distribution_procedural", 0)
    monza_tracks = sorted({row.get("track_path", "") for row in rows if row.get("_benchmark") == "monza_external_track"})
    rows_out = [
        {
            "boundary_id": "B01_simulation_only",
            "evidence_basis": f"{facts['source_rows']} source rows; {facts['matched_case_count']} matched simulation cases; traffic profiles={','.join(facts['traffic_profiles'])}",
            "supported_claim": "The optimized DLC-style world-model controller improves benchmark-defined online overtaking in the evaluated simulation matrix.",
            "unsupported_claim": "The method is certified safe or ready for real-world autonomous overtaking deployment.",
            "risk_link": risk_by_id.get("V01", {}).get("risk", "simulation-only external validity"),
            "recommended_text": "Report the contribution as simulation benchmark evidence and reserve real-vehicle/high-fidelity transfer for future validation.",
            "status": "pass" if facts["source_rows"] == 240 and facts["matched_case_count"] == 30 else "review_required",
        },
        {
            "boundary_id": "B02_single_external_track",
            "evidence_basis": f"Monza external-track cases={monza_cases}; tracks={','.join(monza_tracks)}; seeds={','.join(facts['seeds_by_benchmark'].get('monza_external_track', []))}",
            "supported_claim": "The method is evaluated on the included Monza CSV-derived external-track setting.",
            "unsupported_claim": "The method generalizes to arbitrary road geometries or all racing circuits.",
            "risk_link": risk_by_id.get("V02", {}).get("risk", "single external track"),
            "recommended_text": "Describe Monza as an external-track stress test, not as broad road-geometry proof.",
            "status": "pass" if monza_cases == 10 and monza_tracks == ["tracks/monza_scaled.npz"] else "review_required",
        },
        {
            "boundary_id": "B03_vehicle_count_limit",
            "evidence_basis": f"Vehicle counts={','.join(facts['vehicle_counts'])}; 8-car extrapolation cases={extrap_cases}",
            "supported_claim": "Runtime dynamic neighborhoods support online evaluation up to the included 8-car extrapolation setting without retraining for that vehicle count.",
            "unsupported_claim": "The graph policy supports unlimited traffic density or arbitrary numbers of surrounding vehicles.",
            "risk_link": risk_by_id.get("V03", {}).get("risk", "vehicle-count extrapolation limit"),
            "recommended_text": "State the maximum demonstrated traffic size explicitly: 8 vehicles in this benchmark.",
            "status": "pass" if "8" in facts["vehicle_counts"] and extrap_cases == 5 else "review_required",
        },
        {
            "boundary_id": "B04_metric_proxy_limit",
            "evidence_basis": "Source data includes simulator-defined desirable/on-track/grass/contact-proxy metrics; metric dictionary defines their directions and scope.",
            "supported_claim": f"Primary method aggregate success={fmt(primary['success_mean'])}, elegant={fmt(primary['elegant_mean'])}, on-track={fmt(primary['on_track_mean'])}, grass={fmt(primary['grass_mean'])}.",
            "unsupported_claim": "Desirable/on-track proxy metrics prove human comfort, legal compliance, or certified collision-free behavior.",
            "risk_link": "construct-validity proxy metrics",
            "recommended_text": "Report success, desirable/on-track and grass/contact proxy metrics together, with metric definitions.",
            "status": "pass" if primary["runs"] == 30 else "review_required",
        },
        {
            "boundary_id": "B05_baseline_scope",
            "evidence_basis": f"Algorithms={facts['algorithm_count']}; DLC variants plus quality proposal and rule expert; procedural cases={procedural_cases}",
            "supported_claim": "The comparison covers original DLC-style world-model variants and a strong rule-based reference within matched cases.",
            "unsupported_claim": "The method beats all possible modern autonomous driving planners or all model-based RL methods.",
            "risk_link": risk_by_id.get("V12", {}).get("risk", "baseline family scope"),
            "recommended_text": "Name the baseline family precisely: DLC world-model variants and rule expert, not the full autonomous-driving literature.",
            "status": "pass" if facts["algorithm_count"] == 8 else "review_required",
        },
    ]
    return rows_out


def build_report(root):
    source_rows = read_csv(root / SOURCE_DATA)
    benchmark_cards = read_csv(root / BENCHMARK_CARDS)
    threat_rows = read_csv(root / THREATS_REGISTER)
    facts = source_facts(source_rows)
    boundary_rows = build_boundary_rows(facts, source_rows, benchmark_cards, threat_rows)
    benchmark_rows = benchmark_metric_rows(source_rows, "v6_runtime_dynamic_neighborhood_safe")
    status = "pass" if boundary_rows and all(row["status"] == "pass" for row in boundary_rows) else "review_required"
    return {
        "status": status,
        "summary": {
            "status": status,
            "boundary_count": len(boundary_rows),
            "passing_boundary_count": sum(1 for row in boundary_rows if row["status"] == "pass"),
            "source_rows": facts["source_rows"],
            "matched_case_count": facts["matched_case_count"],
            "algorithm_count": facts["algorithm_count"],
            "benchmark_count": len(facts["benchmarks"]),
            "track_count": len(facts["tracks"]),
            "max_vehicle_count": max([int(item) for item in facts["vehicle_counts"]]) if facts["vehicle_counts"] else 0,
            "monza_case_count": facts["cases_by_benchmark"].get("monza_external_track", 0),
            "vehicle_extrapolation_case_count": facts["cases_by_benchmark"].get("vehicle_count_extrapolation", 0),
        },
        "facts": facts,
        "boundary_rows": boundary_rows,
        "benchmark_metric_rows": benchmark_rows,
        "inputs": {
            "source_data": SOURCE_DATA,
            "benchmark_cards": BENCHMARK_CARDS,
            "threats_register": THREATS_REGISTER,
        },
        "note": "This audit constrains external-validity wording from the frozen 240-run simulation source data. It does not add new experiments or certify real-road deployment.",
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS External Validity Boundary Audit",
        "",
        "该审计从正式 240-run source data、benchmark protocol 和 threats-to-validity register 复算当前证据覆盖范围，明确哪些泛化表述被支持，哪些必须写成限制或未来工作。它不新增实验，只约束论文写作边界。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Boundary Matrix",
            "",
            "| ID | Evidence basis | Supported claim | Unsupported claim | Recommended wording | Status |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["boundary_rows"]:
        lines.append(
            f"| {row['boundary_id']} | {row['evidence_basis']} | {row['supported_claim']} | "
            f"{row['unsupported_claim']} | {row['recommended_text']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Primary Method by Benchmark",
            "",
            "| Benchmark | Vehicles | Track | Runs | Success | Desirable | On-track | Grass | Latency ms |",
            "|---|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report["benchmark_metric_rows"]:
        lines.append(
            f"| {row['benchmark']} | {row['num_agents']} | `{row['track_path']}` | {row['runs']} | "
            f"{row['success_mean']} | {row['elegant_mean']} | {row['on_track_mean']} | "
            f"{row['grass_mean']} | {row['latency_mean_ms']} |"
        )
    lines.extend(
        [
            "",
            "## Manuscript Guardrails",
            "",
            "- 在 Abstract/Conclusion 中使用 `evaluated simulation benchmarks`，不要写成 real-world safety。",
            "- Monza 只能写作 `CSV-derived external-track stress test`，不要写成 arbitrary-track generalization。",
            "- 车辆数只能写作 `up to 8 vehicles in the evaluated matrix`，不要写成 unlimited traffic density。",
            "- 质量指标必须与 simulator-defined proxy/metric dictionary 绑定。",
            "- 对比算法必须写清楚是 DLC world-model variants、quality-proposal variant 和 rule expert。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_external_validity_boundary_audit.py --out-dir outputs/tits_dynamic_graph/tits_external_validity_boundary_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export external-validity boundary audit for the T-ITS dynamic graph package.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_external_validity_boundary_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    report = build_report(root)
    paths = {
        "audit_md": write_text(materials / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json", report),
        "boundary_csv": write_csv(
            tables / "external_validity_boundary_matrix.csv",
            report["boundary_rows"],
            [
                "boundary_id",
                "evidence_basis",
                "supported_claim",
                "unsupported_claim",
                "risk_link",
                "recommended_text",
                "status",
            ],
        ),
        "benchmark_metrics_csv": write_csv(
            tables / "external_validity_primary_by_benchmark.csv",
            report["benchmark_metric_rows"],
            [
                "benchmark",
                "num_agents",
                "track_path",
                "runs",
                "success_mean",
                "elegant_mean",
                "on_track_mean",
                "grass_mean",
                "latency_mean_ms",
            ],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
        "boundary": report["note"],
    }
    manifest_path = write_json(out_dir / "tits_external_validity_boundary_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
