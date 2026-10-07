#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


GIF_MANIFEST = "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.json"
GIF_PROVENANCE = "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/tables/publication_gif_provenance_rows.csv"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"


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


def fmt(value, digits=3, empty="NA"):
    if value is None or str(value).strip() == "":
        return empty
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def file_info(path):
    path = Path(path)
    if not path.exists():
        return {"exists": False, "size_bytes": 0, "size_mb": 0.0}
    size = path.stat().st_size
    return {"exists": True, "size_bytes": size, "size_mb": round(size / (1024 * 1024), 3)}


def provenance_index(rows):
    out = {}
    for row in rows:
        key = (row.get("scene", ""), row.get("algorithm", ""))
        out[key] = row
    return out


def source_case_count(rows):
    cases = {
        (
            row.get("_benchmark", ""),
            row.get("seed", ""),
            row.get("num_agents", ""),
            row.get("track_path", ""),
            row.get("traffic_profile", ""),
        )
        for row in rows
    }
    return len(rows), len(cases), len({row.get("algorithm", "") for row in rows})


def scene_label(item):
    if item.get("track_path") == "tracks/monza_scaled.npz":
        return "Monza CSV-derived external track"
    if str(item.get("num_agents")) == "8":
        return "eight-vehicle extrapolation"
    return "procedural benchmark"


def build_caption(item, view):
    algorithm = item.get("algorithm", "")
    method = "optimized dynamic-neighborhood DLC-safe controller" if "v6_runtime_dynamic_neighborhood_safe" in algorithm else "original DLC world-model baseline"
    view_text = "top-down" if view == "topdown" else "first-person"
    outcome = (
        f"rank gain {fmt(item.get('rank_gain'), 0)}, "
        f"{fmt(item.get('overtake_count'), 0)} overtakes, "
        f"on-track/desirable rate {fmt(item.get('on_track_overtake_rate'))}/{fmt(item.get('elegant_overtake_rate'))}, "
        f"target grass rate {fmt(item.get('target_grass_rate'))}"
    )
    return (
        f"{view_text.capitalize()} representative online rollout for the {method} in the "
        f"{scene_label(item)} setting (N={item.get('num_agents')}, seed={item.get('seed')}). "
        f"The visual clip is qualitative and linked to the formal matched case through the GIF provenance audit; "
        f"summary metrics for this visual run are {outcome}."
    )


def build_rows(root):
    manifest = read_json(root / GIF_MANIFEST)
    provenance = provenance_index(read_csv(root / GIF_PROVENANCE))
    source_rows = read_csv(root / SOURCE_DATA)
    source_row_count, source_case_count_value, source_algorithm_count = source_case_count(source_rows)
    rows = []
    issue_rows = []
    video_idx = 1
    for item in manifest.get("rows", []):
        prov = provenance.get((item.get("scene", ""), item.get("algorithm", "")), {})
        for view, field in [("topdown", "topdown_gif"), ("first_person", "first_person_gif")]:
            path = item.get(field, "")
            info = file_info(root / path)
            warnings = prov.get("warnings", "")
            errors = []
            if not info["exists"] or info["size_bytes"] <= 0:
                errors.append("missing_or_empty_gif")
            if prov.get("status") != "pass":
                errors.append("provenance_not_pass")
            if prov.get("formal_matrix_row_found") not in {"True", True}:
                errors.append("missing_formal_matrix_row")
            row = {
                "video_id": f"Video S{video_idx}",
                "scene": item.get("scene", ""),
                "view": view,
                "algorithm": item.get("algorithm", ""),
                "algorithm_label_cn": item.get("algorithm_label_cn", ""),
                "benchmark": prov.get("benchmark", ""),
                "num_agents": item.get("num_agents", ""),
                "seed": item.get("seed", ""),
                "track_path": item.get("track_path", ""),
                "traffic_profile": item.get("traffic_profile", ""),
                "gif_path": path,
                "exists": info["exists"],
                "size_bytes": info["size_bytes"],
                "size_mb": info["size_mb"],
                "summary_path": item.get("summary_path", ""),
                "trace_path": item.get("trace_path", ""),
                "formal_summary_file": prov.get("formal_summary_file", ""),
                "provenance_status": prov.get("status", ""),
                "provenance_warnings": warnings,
                "rank_gain": item.get("rank_gain", ""),
                "overtake_count": item.get("overtake_count", ""),
                "on_track_overtake_rate": item.get("on_track_overtake_rate", ""),
                "elegant_overtake_rate": item.get("elegant_overtake_rate", ""),
                "target_grass_rate": item.get("target_grass_rate", ""),
                "caption": build_caption(item, view),
                "submission_role": "supplementary_video_visual_evidence",
                "claim_boundary": "qualitative representative visual evidence; formal statistics come from the 240-run source data",
                "status": "pass" if not errors else "review_required",
                "errors": ";".join(errors),
            }
            rows.append(row)
            for error in errors:
                issue_rows.append({**row, "severity": "error", "issue": error})
            if warnings:
                for warning in warnings.split(";"):
                    issue_rows.append({**row, "severity": "warning", "issue": warning})
            video_idx += 1
    summary = {
        "status": "pass" if not any(row["status"] != "pass" for row in rows) else "review_required",
        "video_rows": len(rows),
        "pass_rows": sum(1 for row in rows if row["status"] == "pass"),
        "gif_manifest_status": manifest.get("status"),
        "gif_manifest_rows": manifest.get("row_count"),
        "source_rows": source_row_count,
        "source_cases": source_case_count_value,
        "source_algorithms": source_algorithm_count,
        "missing_gif_count": sum(1 for row in rows if not row["exists"]),
        "error_count": sum(1 for row in issue_rows if row["severity"] == "error"),
        "warning_count": sum(1 for row in issue_rows if row["severity"] == "warning"),
        "total_size_mb": round(sum(float(row["size_mb"]) for row in rows), 3),
    }
    return {"status": summary["status"], "summary": summary, "rows": rows, "issue_rows": issue_rows}


def build_markdown(report):
    s = report["summary"]
    lines = [
        "# Supplementary Video / GIF Index Pack",
        "",
        "This pack converts representative GIF evidence into a submission-facing supplementary video index. It does not create new simulator runs and does not replace the 240-run confirmatory statistics.",
        "",
        "## Summary",
        "",
        f"- status: {s['status']}",
        f"- supplementary video rows: {s['pass_rows']}/{s['video_rows']}",
        f"- GIF manifest status: {s['gif_manifest_status']}",
        f"- formal source data: {s['source_rows']} rows, {s['source_cases']} matched cases, {s['source_algorithms']} algorithms",
        f"- missing GIFs: {s['missing_gif_count']}",
        f"- errors: {s['error_count']}",
        f"- warnings: {s['warning_count']}",
        f"- total GIF size MB: {s['total_size_mb']}",
        "",
        "## Supplementary Video Table",
        "",
        "| Video | Scene | View | Algorithm | N | Seed | File | Size MB | Provenance | Caption |",
        "|---|---|---|---|---:|---:|---|---:|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['video_id']} | {row['scene']} | {row['view']} | {row['algorithm']} | "
            f"{row['num_agents']} | {row['seed']} | `{row['gif_path']}` | {row['size_mb']} | "
            f"{row['provenance_status']} | {row['caption']} |"
        )
    lines.extend(
        [
            "",
            "## Submission Boundary",
            "",
            "- Use these rows as a supplement/video-upload index, not as statistical evidence.",
            "- Cite `outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/materials/PUBLICATION_GIF_PROVENANCE_AUDIT.md` when describing traceability.",
            "- Cite `outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv` for all formal quantitative claims.",
            "- Warnings are expected representativeness limits, especially shorter visual rollouts and high-grass representative cases.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_supplementary_video_index_pack.py --out-dir outputs/tits_dynamic_graph/tits_supplementary_video_index_pack",
            "```",
        ]
    )
    return "\n".join(lines)


def export(root, out_dir):
    out_dir = Path(out_dir)
    tables_dir = out_dir / "tables"
    materials_dir = out_dir / "materials"
    report = build_rows(root)
    row_fields = [
        "video_id", "scene", "view", "algorithm", "algorithm_label_cn", "benchmark", "num_agents", "seed",
        "track_path", "traffic_profile", "gif_path", "exists", "size_bytes", "size_mb", "summary_path",
        "trace_path", "formal_summary_file", "provenance_status", "provenance_warnings", "rank_gain",
        "overtake_count", "on_track_overtake_rate", "elegant_overtake_rate", "target_grass_rate",
        "caption", "submission_role", "claim_boundary", "status", "errors",
    ]
    issue_fields = row_fields + ["severity", "issue"]
    paths = {
        "video_index_csv": write_csv(tables_dir / "supplementary_video_index.csv", report["rows"], row_fields),
        "video_issues_csv": write_csv(tables_dir / "supplementary_video_index_issues.csv", report["issue_rows"], issue_fields),
        "video_index_md": write_text(materials_dir / "SUPPLEMENTARY_VIDEO_INDEX.md", build_markdown(report)),
    }
    manifest = {
        "status": report["status"],
        "summary": report["summary"],
        "paths": paths,
        "inputs": {
            "gif_manifest": GIF_MANIFEST,
            "gif_provenance_rows": GIF_PROVENANCE,
            "source_data": SOURCE_DATA,
        },
    }
    paths["manifest_json"] = write_json(out_dir / "tits_supplementary_video_index_pack_manifest.json", manifest)
    return manifest, paths["manifest_json"]


def main():
    parser = argparse.ArgumentParser(description="Export a supplementary video/GIF index pack for T-ITS submission materials.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_supplementary_video_index_pack")
    args = parser.parse_args()
    manifest, manifest_path = export(Path(args.root), args.out_dir)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
