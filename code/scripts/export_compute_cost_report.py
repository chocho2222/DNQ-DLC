#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rel(root, path):
    return str(path.relative_to(root))


def summarize_suite(root, path):
    data = load_json(path)
    rows = data.get("rows", [])
    steps = [row.get("steps_run") for row in rows if row.get("steps_run") is not None]
    devices = sorted({row.get("device") for row in rows if row.get("device")})
    passes = sum(1 for row in rows if row.get("validation_status") == "PASS")
    return {
        "kind": "full_rollout_suite",
        "name": path.parent.name,
        "source": rel(root, path),
        "methods": len(data.get("methods", [])),
        "seeds": len(data.get("seeds", [])),
        "rows": len(rows),
        "pass_count": passes,
        "total_steps_run": sum(steps),
        "mean_steps_run": (sum(steps) / len(steps)) if steps else None,
        "max_steps_run": max(steps) if steps else None,
        "devices": ",".join(devices),
        "wall_clock_available": False,
        "notes": "Summary contains simulated steps and devices, but not wall-clock timing.",
    }


def summarize_selector(root, path):
    data = load_json(path)
    probe_rows = data.get("probe_rows", [])
    decisions = data.get("decisions", [])
    probe_steps = data.get("probe_steps")
    methods = data.get("methods", [])
    seeds = data.get("seeds", [])
    probe_steps_run = [row.get("probe_steps_run") for row in probe_rows if row.get("probe_steps_run") is not None]
    return {
        "kind": "online_probe_selector",
        "name": path.stem,
        "source": rel(root, path),
        "methods": len(methods),
        "seeds": len(seeds),
        "rows": len(probe_rows),
        "pass_count": data.get("pass_count"),
        "oracle_pass_count": data.get("oracle_pass_count"),
        "probe_steps": probe_steps,
        "total_probe_steps_run": sum(probe_steps_run),
        "mean_probe_steps_run": (sum(probe_steps_run) / len(probe_steps_run)) if probe_steps_run else None,
        "committed_runs": len(decisions),
        "probes_per_seed": (len(probe_rows) / len(seeds)) if seeds else None,
        "devices": "see probe/full rollout logs",
        "wall_clock_available": False,
        "notes": "Selector cost is reported in probe count and simulated probe steps; wall-clock timing is not recorded.",
    }


def build_report(root):
    manifest = load_json(root / "manifest.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    environment = load_json(root / "materials" / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.json")
    suite_paths = sorted((root / "evaluations").glob("*/multiseed_suite_summary.json"))
    suite_rows = [summarize_suite(root, path) for path in suite_paths]

    selector_paths = sorted((root / "tables").glob("portfolio_probe_selector*.json"))
    selector_rows = [summarize_selector(root, path) for path in selector_paths]

    total_full_rollout_rows = sum(row["rows"] for row in suite_rows)
    total_full_rollout_steps = sum(row["total_steps_run"] for row in suite_rows)
    total_selector_probe_rows = sum(row["rows"] for row in selector_rows)
    total_selector_probe_steps = sum(row["total_probe_steps_run"] for row in selector_rows)
    all_devices = sorted(
        {
            device
            for row in suite_rows
            for device in row["devices"].split(",")
            if device
        }
    )
    selector_reports_from_evaluations = sorted((root / "evaluations").glob("*/portfolio_probe_selector_summary.json"))
    selector_table_source_names = {row["name"] for row in selector_rows}
    evaluation_selector_names = {path.parent.name for path in selector_reports_from_evaluations}
    missing_selector_tables = sorted(evaluation_selector_names - selector_table_source_names)
    max_probes_per_seed = max((row["probes_per_seed"] or 0 for row in selector_rows), default=0)
    max_probe_steps = max((row["probe_steps"] or 0 for row in selector_rows), default=0)
    l20_gpu_count = environment["summary"].get("nvidia_smi_gpu_count")
    total_gpu_memory_mb = sum(gpu.get("memory_total_mb", 0) for gpu in environment.get("gpu", {}).get("gpus", []))

    return {
        "root": str(root),
        "device_record": manifest["device"],
        "summary": {
            "full_rollout_suite_count": len(suite_rows),
            "full_rollout_rows": total_full_rollout_rows,
            "full_rollout_simulated_steps": total_full_rollout_steps,
            "selector_report_count": len(selector_rows),
            "selector_probe_rows": total_selector_probe_rows,
            "selector_probe_simulated_steps": total_selector_probe_steps,
            "selector_evaluation_summary_count": len(selector_reports_from_evaluations),
            "missing_selector_table_count": len(missing_selector_tables),
            "max_probes_per_seed": max_probes_per_seed,
            "max_probe_steps": max_probe_steps,
            "devices_from_suites": all_devices,
            "environment_gpu_count": l20_gpu_count,
            "environment_total_gpu_memory_mb": total_gpu_memory_mb,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
            "wall_clock_available": False,
            "interpretation": (
                "The saved artifacts support simulated-step and device-count reporting. "
                "They do not provide reliable wall-clock timings, so wall-clock cost is listed as unavailable."
            ),
        },
        "suite_rows": suite_rows,
        "selector_rows": selector_rows,
        "coverage": {
            "suite_summary_files_found": len(suite_paths),
            "selector_table_reports_found": len(selector_rows),
            "selector_evaluation_summaries_found": len(selector_reports_from_evaluations),
            "missing_selector_table_reports": missing_selector_tables,
            "coverage_status": "complete" if not missing_selector_tables else "partial",
        },
        "limitations": [
            "Wall-clock timing is not consistently recorded in logs.",
            "GPU utilization and CPU utilization are not archived.",
            "Selector cost is reported as probe count and simulated steps rather than elapsed time.",
        ],
    }


def write_csv(report, root):
    suite_csv = root / "tables" / "compute_cost_suite_rows.csv"
    selector_csv = root / "tables" / "compute_cost_selector_rows.csv"
    suite_fields = [
        "kind",
        "name",
        "source",
        "methods",
        "seeds",
        "rows",
        "pass_count",
        "total_steps_run",
        "mean_steps_run",
        "max_steps_run",
        "devices",
        "wall_clock_available",
        "notes",
    ]
    with suite_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=suite_fields)
        writer.writeheader()
        for row in report["suite_rows"]:
            writer.writerow({key: row.get(key) for key in suite_fields})
    selector_fields = [
        "kind",
        "name",
        "source",
        "methods",
        "seeds",
        "rows",
        "pass_count",
        "oracle_pass_count",
        "probe_steps",
        "total_probe_steps_run",
        "mean_probe_steps_run",
        "committed_runs",
        "probes_per_seed",
        "devices",
        "wall_clock_available",
        "notes",
    ]
    with selector_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=selector_fields)
        writer.writeheader()
        for row in report["selector_rows"]:
            writer.writerow({key: row.get(key) for key in selector_fields})
    return suite_csv, selector_csv


def write_markdown(report, path):
    s = report["summary"]
    lines = [
        "# Compute Cost Report",
        "",
        "This report summarizes compute scale from saved rollout summaries and selector reports. It reports simulated steps and probe counts, not wall-clock time.",
        "",
        "## Summary",
        "",
        f"- Device record from manifest: `{report['device_record']}`",
        f"- Devices observed in suite rows: `{', '.join(s['devices_from_suites'])}`",
        f"- Full-rollout suite count: {s['full_rollout_suite_count']}",
        f"- Full-rollout rows: {s['full_rollout_rows']}",
        f"- Full-rollout simulated steps: {s['full_rollout_simulated_steps']}",
        f"- Selector report count: {s['selector_report_count']}",
        f"- Selector probe rows: {s['selector_probe_rows']}",
        f"- Selector probe simulated steps: {s['selector_probe_simulated_steps']}",
        f"- Selector evaluation summaries found: {s['selector_evaluation_summary_count']}",
        f"- Missing selector table reports: {s['missing_selector_table_count']}",
        f"- Max probes per seed: {s['max_probes_per_seed']}",
        f"- Max probe steps: {s['max_probe_steps']}",
        f"- Environment GPU count: {s['environment_gpu_count']}",
        f"- Environment total GPU memory MB: {s['environment_total_gpu_memory_mb']}",
        f"- Wall-clock available: {s['wall_clock_available']}",
        f"- Publication verification: {s['publication_verification_status']}",
        f"- Artifact provenance: {s['artifact_provenance']}",
        "",
        "Interpretation:",
        "",
        s["interpretation"],
        "",
        "## Full-rollout Suites",
        "",
        "| suite | methods | seeds | rows | pass | total steps | mean steps | max steps | devices |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report["suite_rows"]:
        lines.append(
            f"| {row['name']} | {row['methods']} | {row['seeds']} | {row['rows']} | "
            f"{row['pass_count']} | {row['total_steps_run']} | {row['mean_steps_run']:.1f} | "
            f"{row['max_steps_run']} | {row['devices']} |"
        )
    lines.extend(
        [
            "",
            "## Online Probe Selectors",
            "",
            "| selector | methods | seeds | probe rows | probe steps | total probe steps | committed runs | probes/seed | pass | oracle |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report["selector_rows"]:
        probes_per_seed = row["probes_per_seed"]
        lines.append(
            f"| {row['name']} | {row['methods']} | {row['seeds']} | {row['rows']} | "
            f"{row['probe_steps']} | {row['total_probe_steps_run']} | {row['committed_runs']} | "
            f"{probes_per_seed:.1f} | {row['pass_count']} | {row['oracle_pass_count']} |"
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.extend(
        [
            "",
            "## Coverage",
            "",
            f"- Suite summary files found: {report['coverage']['suite_summary_files_found']}",
            f"- Selector table reports found: {report['coverage']['selector_table_reports_found']}",
            f"- Selector evaluation summaries found: {report['coverage']['selector_evaluation_summaries_found']}",
            f"- Coverage status: {report['coverage']['coverage_status']}",
        ]
    )
    if report["coverage"]["missing_selector_table_reports"]:
        lines.append("- Missing selector table reports:")
        for item in report["coverage"]["missing_selector_table_reports"]:
            lines.append(f"  - `{item}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export compute cost report from saved summaries.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    out_json = root / "tables" / "compute_cost_report.json"
    out_md = root / "tables" / "compute_cost_report.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    suite_csv, selector_csv = write_csv(report, root)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "suite_csv": str(suite_csv),
                "selector_csv": str(selector_csv),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
