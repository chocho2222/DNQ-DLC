#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


GIF_MANIFEST = "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.json"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"

NUMERIC_FIELDS = [
    "rank_gain",
    "overtake_success_rate",
    "overtake_count",
    "on_track_overtake_rate",
    "elegant_overtake_rate",
    "time_to_first_overtake",
    "overtake_start_to_complete_time",
    "target_grass_rate",
    "compute_latency_ms",
]


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


def blank(value):
    return value is None or str(value).strip() == ""


def to_float(value):
    if blank(value):
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return 1.0 if value.strip().lower() == "true" else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def close(a, b, tol=1e-6):
    af = to_float(a)
    bf = to_float(b)
    if af is None and bf is None:
        return True
    if af is None or bf is None:
        return False
    return abs(af - bf) <= tol


def infer_benchmark(item):
    track_path = str(item.get("track_path", ""))
    num_agents = int(item.get("num_agents") or 0)
    if track_path == "tracks/monza_scaled.npz":
        return "monza_external_track"
    if num_agents == 8:
        return "vehicle_count_extrapolation"
    return "in_distribution_procedural"


def source_index(rows):
    out = {}
    for row in rows:
        key = (
            row.get("_benchmark", ""),
            row.get("algorithm", ""),
            row.get("seed", ""),
            row.get("num_agents", ""),
            row.get("track_path", ""),
            row.get("traffic_profile", ""),
        )
        out[key] = row
    return out


def summary_key(item):
    return (
        infer_benchmark(item),
        item.get("algorithm", ""),
        str(item.get("seed", "")),
        str(item.get("num_agents", "")),
        item.get("track_path", ""),
        item.get("traffic_profile", ""),
    )


def find_metrics_row(root, item):
    scene = item.get("scene", "")
    metrics_path = root / "outputs/tits_dynamic_graph/publication_gifs" / scene / "tables" / f"online_metrics_n{item.get('num_agents')}_seed{item.get('seed')}.csv"
    rows = read_csv(metrics_path)
    for row in rows:
        if row.get("algorithm") == item.get("algorithm"):
            return metrics_path.as_posix(), row
    return metrics_path.as_posix(), None


def compare_summary_to_manifest(summary, item):
    mismatches = []
    for field in NUMERIC_FIELDS:
        if field not in item:
            continue
        if not close(summary.get(field), item.get(field)):
            mismatches.append(field)
    return mismatches


def compare_metrics_to_manifest(metrics, item):
    mismatches = []
    if metrics is None:
        return ["missing_metrics_row"]
    field_map = {
        "overtake_success_rate": "overtake_success",
    }
    for field in NUMERIC_FIELDS:
        if field not in item:
            continue
        metric_field = field_map.get(field, field)
        if metric_field not in metrics:
            continue
        if not close(metrics.get(metric_field), item.get(field)):
            mismatches.append(field)
    return mismatches


def build_report(root):
    manifest = read_json(root / GIF_MANIFEST)
    source_rows = read_csv(root / SOURCE_DATA)
    source = source_index(source_rows)
    rows = []
    issue_rows = []
    for idx, item in enumerate(manifest.get("rows", []), start=1):
        key = summary_key(item)
        formal_row = source.get(key)
        summary_path = root / item.get("summary_path", "")
        trace_path = root / item.get("trace_path", "")
        topdown_path = root / item.get("topdown_gif", "")
        first_person_path = root / item.get("first_person_gif", "")
        metrics_path, metrics_row = find_metrics_row(root, item)
        summary = read_json(summary_path)
        trace = read_json(trace_path)
        trace_steps = len(trace) if isinstance(trace, list) else ""
        errors = []
        warnings = []
        for label, path in [
            ("topdown_gif", topdown_path),
            ("first_person_gif", first_person_path),
            ("summary_path", summary_path),
            ("trace_path", trace_path),
            ("metrics_csv", root / metrics_path),
        ]:
            if not path.exists() or path.stat().st_size <= 0:
                errors.append(f"missing_or_empty_{label}")
        if formal_row is None:
            errors.append("missing_formal_matrix_row")
        if not isinstance(trace, list):
            errors.append("trace_not_list")
        elif summary and int(summary.get("steps_run") or summary.get("finish_step") or -1) != len(trace):
            errors.append("trace_step_count_mismatch")
        manifest_summary_mismatches = compare_summary_to_manifest(summary, item)
        metrics_mismatches = compare_metrics_to_manifest(metrics_row, item)
        if manifest_summary_mismatches:
            errors.append("summary_manifest_metric_mismatch")
        if metrics_mismatches:
            errors.append("metrics_manifest_metric_mismatch")
        if formal_row is not None:
            formal_summary = formal_row.get("_summary_file", "")
            if not formal_summary:
                errors.append("formal_summary_missing")
            formal_finish = int(float(formal_row.get("finish_step") or 0))
            gif_finish = int(summary.get("finish_step") or 0) if summary else 0
            if formal_finish != gif_finish:
                warnings.append("representative_gif_run_length_differs_from_formal_matrix")
        if item.get("scene", "").startswith("n8") and item.get("target_grass_rate", 0) and float(item.get("target_grass_rate")) > 0.5:
            warnings.append("representative_case_high_target_grass_rate_limit")
        row = {
            "gif_row": idx,
            "scene": item.get("scene", ""),
            "algorithm": item.get("algorithm", ""),
            "benchmark": key[0],
            "seed": key[2],
            "num_agents": key[3],
            "track_path": key[4],
            "traffic_profile": key[5],
            "formal_matrix_row_found": formal_row is not None,
            "formal_summary_file": formal_row.get("_summary_file", "") if formal_row else "",
            "topdown_exists": topdown_path.exists(),
            "first_person_exists": first_person_path.exists(),
            "summary_exists": summary_path.exists(),
            "trace_exists": trace_path.exists(),
            "metrics_exists": (root / metrics_path).exists(),
            "trace_steps": trace_steps,
            "summary_finish_step": summary.get("finish_step", "") if summary else "",
            "summary_manifest_mismatches": ";".join(manifest_summary_mismatches),
            "metrics_manifest_mismatches": ";".join(metrics_mismatches),
            "warnings": ";".join(warnings),
            "errors": ";".join(errors),
            "status": "pass" if not errors else "review_required",
        }
        rows.append(row)
        for error in errors:
            issue_rows.append({**row, "severity": "error", "issue": error})
        for warning in warnings:
            issue_rows.append({**row, "severity": "warning", "issue": warning})
    status = "pass" if not [row for row in rows if row["status"] != "pass"] else "review_required"
    summary = {
        "status": status,
        "gif_manifest_status": manifest.get("status"),
        "manifest_rows": manifest.get("row_count"),
        "audited_rows": len(rows),
        "pass_rows": sum(1 for row in rows if row["status"] == "pass"),
        "issue_count": len(issue_rows),
        "error_count": sum(1 for row in issue_rows if row["severity"] == "error"),
        "warning_count": sum(1 for row in issue_rows if row["severity"] == "warning"),
        "formal_matrix_rows_found": sum(1 for row in rows if row["formal_matrix_row_found"]),
        "topdown_gif_count": sum(1 for row in rows if row["topdown_exists"]),
        "first_person_gif_count": sum(1 for row in rows if row["first_person_exists"]),
        "source_rows": len(source_rows),
    }
    return {"status": status, "summary": summary, "rows": rows, "issue_rows": issue_rows}


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Publication GIF Provenance Audit",
        "",
        "This audit checks whether representative top-down and first-person GIF rows are internally traceable to GIF files, online summaries, trace JSON files, per-scene metrics CSV files, and matched formal-matrix cases. GIFs remain qualitative visual evidence and do not replace the 240-run confirmatory statistics.",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Row Checks",
            "",
            "| Scene | Algorithm | Formal row | Top-down | First-person | Summary | Trace | Metrics | Trace steps | Warnings | Status |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['scene']} | {row['algorithm']} | {row['formal_matrix_row_found']} | {row['topdown_exists']} | {row['first_person_exists']} | {row['summary_exists']} | {row['trace_exists']} | {row['metrics_exists']} | {row['trace_steps']} | {row['warnings']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- PASS means each representative GIF row is file-complete and traceable to a matched formal-matrix case with the same benchmark, algorithm, seed, vehicle count, track and traffic profile.",
            "- Warnings identify expected representativeness boundaries, such as GIF runs using shorter visual rollouts than the formal 2200-step matrix.",
            "- The formal claims must still cite `outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv` and the confirmatory evidence pack.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_publication_gif_provenance_audit.py --out-dir outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit provenance of publication GIF visual evidence.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit")
    args = parser.parse_args()
    root = Path(args.root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    paths = {
        "audit_rows": str(out_dir / "tables" / "publication_gif_provenance_rows.csv"),
        "issue_rows": str(out_dir / "tables" / "publication_gif_provenance_issues.csv"),
        "audit_json": str(out_dir / "materials" / "PUBLICATION_GIF_PROVENANCE_AUDIT.json"),
        "audit_md": str(out_dir / "materials" / "PUBLICATION_GIF_PROVENANCE_AUDIT.md"),
        "manifest_json": str(out_dir / "tits_publication_gif_provenance_audit_manifest.json"),
    }
    report["paths"] = paths
    fields = [
        "gif_row",
        "scene",
        "algorithm",
        "benchmark",
        "seed",
        "num_agents",
        "track_path",
        "traffic_profile",
        "formal_matrix_row_found",
        "formal_summary_file",
        "topdown_exists",
        "first_person_exists",
        "summary_exists",
        "trace_exists",
        "metrics_exists",
        "trace_steps",
        "summary_finish_step",
        "summary_manifest_mismatches",
        "metrics_manifest_mismatches",
        "warnings",
        "errors",
        "status",
    ]
    write_csv(paths["audit_rows"], report["rows"], fields)
    write_csv(paths["issue_rows"], report["issue_rows"], fields + ["severity", "issue"])
    write_json(paths["audit_json"], {k: v for k, v in report.items() if k not in {"rows", "issue_rows"}})
    write_text(paths["audit_md"], build_markdown(report))
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
    }
    write_json(paths["manifest_json"], manifest)
    print(json.dumps({"manifest": paths["manifest_json"], "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
