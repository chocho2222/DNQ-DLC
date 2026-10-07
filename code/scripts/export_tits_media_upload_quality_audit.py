#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path

try:
    from PIL import Image
except Exception:  # pragma: no cover - handled at runtime
    Image = None


FIGURE_CHECKS = "outputs/tits_dynamic_graph/tits_figure_source_data_audit/tables/figure_source_data_checks.csv"
GIF_MANIFEST = "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.json"
FIGURE_FORMATS = ["pdf", "svg", "png", "tiff"]

WARNING_SIZE_BYTES = 100 * 1024 * 1024
BLOCKING_SIZE_BYTES = 500 * 1024 * 1024
MIN_RASTER_SIDE = 900
MIN_GIF_FRAMES = 8


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


def mb(size_bytes):
    try:
        return round(float(size_bytes) / (1024 * 1024), 3)
    except Exception:
        return 0.0


def safe_image_metadata(path):
    metadata = {
        "width_px": "",
        "height_px": "",
        "frame_count": "",
        "dpi_x": "",
        "dpi_y": "",
        "pil_readable": "",
        "pil_error": "",
    }
    if Image is None:
        metadata["pil_readable"] = "not_available"
        metadata["pil_error"] = "Pillow is not installed"
        return metadata
    try:
        with Image.open(path) as img:
            metadata["width_px"] = int(img.size[0])
            metadata["height_px"] = int(img.size[1])
            metadata["frame_count"] = int(getattr(img, "n_frames", 1))
            dpi = img.info.get("dpi")
            if isinstance(dpi, tuple) and len(dpi) >= 2:
                metadata["dpi_x"] = round(float(dpi[0]), 3)
                metadata["dpi_y"] = round(float(dpi[1]), 3)
            metadata["pil_readable"] = "yes"
    except Exception as exc:
        metadata["pil_readable"] = "no"
        metadata["pil_error"] = str(exc)[:240]
    return metadata


def svg_metadata(path):
    metadata = {
        "width_px": "",
        "height_px": "",
        "frame_count": "",
        "dpi_x": "",
        "dpi_y": "",
        "pil_readable": "not_applicable",
        "pil_error": "",
    }
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        viewbox = re.search(r"viewBox=['\"]([^'\"]+)['\"]", text)
        if viewbox:
            parts = [float(item) for item in re.split(r"[\s,]+", viewbox.group(1).strip()) if item]
            if len(parts) == 4:
                metadata["width_px"] = round(parts[2], 3)
                metadata["height_px"] = round(parts[3], 3)
    except Exception as exc:
        metadata["pil_error"] = str(exc)[:240]
    return metadata


def audit_media_file(root, media_id, role, rel_path, expected_kind):
    path = root / rel_path
    errors = []
    warnings = []
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    suffix = path.suffix.lower().lstrip(".")
    if not exists:
        errors.append("missing_file")
    if exists and size <= 0:
        errors.append("empty_file")
    if exists and size > BLOCKING_SIZE_BYTES:
        errors.append("file_exceeds_local_blocking_size_threshold")
    elif exists and size > WARNING_SIZE_BYTES:
        warnings.append("large_file_upload_risk")
    if expected_kind and suffix and suffix != expected_kind:
        warnings.append(f"unexpected_suffix:{suffix}")
    if suffix in {"png", "tif", "tiff", "gif"} and exists and size > 0:
        metadata = safe_image_metadata(path)
        if metadata["pil_readable"] == "no":
            errors.append("raster_not_readable_by_pillow")
        width = metadata.get("width_px") or 0
        height = metadata.get("height_px") or 0
        if width and height and min(int(width), int(height)) < MIN_RASTER_SIDE and suffix != "gif":
            warnings.append("small_raster_side_upload_risk")
        if suffix == "gif":
            frames = int(metadata.get("frame_count") or 0)
            if frames < MIN_GIF_FRAMES:
                warnings.append("short_gif_frame_count")
    elif suffix == "svg" and exists and size > 0:
        metadata = svg_metadata(path)
    else:
        metadata = {
            "width_px": "",
            "height_px": "",
            "frame_count": "",
            "dpi_x": "",
            "dpi_y": "",
            "pil_readable": "not_applicable",
            "pil_error": "",
        }
    return {
        "media_id": media_id,
        "role": role,
        "path": rel_path,
        "expected_kind": expected_kind,
        "exists": exists,
        "size_bytes": size,
        "size_mb": mb(size),
        **metadata,
        "status": "pass" if not errors else "error",
        "errors": ";".join(errors),
        "warnings": ";".join(warnings),
    }


def audit_figures(root):
    rows = []
    for item in read_csv(root / FIGURE_CHECKS):
        figure_id = item.get("figure_id", "")
        for fmt in FIGURE_FORMATS:
            rel = item.get(f"{fmt}_path", "")
            if rel:
                rows.append(audit_media_file(root, figure_id, f"figure_{fmt}", rel, fmt))
    return rows


def audit_gifs(root):
    manifest = read_json(root / GIF_MANIFEST)
    rows = []
    for item in manifest.get("rows", []):
        media_id = f"{item.get('scene', '')}:{item.get('algorithm', '')}"
        for key, role in [("topdown_gif", "gif_topdown"), ("first_person_gif", "gif_first_person")]:
            rel = item.get(key, "")
            if rel:
                rows.append(audit_media_file(root, media_id, role, rel, "gif"))
    return rows


def build_report(root):
    media_rows = audit_figures(root) + audit_gifs(root)
    error_rows = [row for row in media_rows if row["status"] != "pass"]
    warning_rows = [row for row in media_rows if row["warnings"]]
    figure_rows = [row for row in media_rows if row["role"].startswith("figure_")]
    gif_rows = [row for row in media_rows if row["role"].startswith("gif_")]
    summary = {
        "status": "pass" if not error_rows else "review_required",
        "media_file_count": len(media_rows),
        "figure_media_file_count": len(figure_rows),
        "gif_media_file_count": len(gif_rows),
        "error_count": len(error_rows),
        "warning_count": len(warning_rows),
        "large_file_warning_count": sum(1 for row in warning_rows if "large_file_upload_risk" in row["warnings"]),
        "pillow_available": Image is not None,
        "local_warning_size_mb": mb(WARNING_SIZE_BYTES),
        "local_blocking_size_mb": mb(BLOCKING_SIZE_BYTES),
        "min_raster_side_px": MIN_RASTER_SIDE,
        "min_gif_frames": MIN_GIF_FRAMES,
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "media_rows": media_rows,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Media Upload Quality Audit",
        "",
        "该审计检查正式主图/补充图和代表性 GIF 是否具备投稿前应关注的基本媒体属性：文件存在、非空、可读取、PNG/TIFF/GIF 像素尺寸、GIF 帧数、以及大文件上传风险。阈值是本地风险提示，不代表 IEEE 官方硬性文件大小限制。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Media Checks",
            "",
            "| Media ID | Role | Status | Size MB | Width | Height | Frames | DPI | Warnings | Errors |",
            "|---|---|---|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for row in report["media_rows"]:
        dpi = ""
        if row.get("dpi_x") or row.get("dpi_y"):
            dpi = f"{row.get('dpi_x')}/{row.get('dpi_y')}"
        lines.append(
            f"| {row['media_id']} | {row['role']} | {row['status']} | {row['size_mb']} | {row['width_px']} | {row['height_px']} | {row['frame_count']} | {dpi} | {row['warnings']} | {row['errors']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- PASS 表示所有注册媒体文件存在、非空，且可读取的 raster/GIF 文件能被 Pillow 打开。",
            "- `large_file_upload_risk` 是上传风险提示，不是阻塞错误；最终仍需按期刊门户的实时文件大小限制选择 PDF/SVG/TIFF/PNG/GIF 或压缩版本。",
            "- GIF 只作为代表性视觉材料；正式统计结论仍以 240-run source data 和 confirmatory evidence pack 为准。",
            "- 若重画图、压缩图片、替换 GIF 或改变补充材料选择，应重新运行本审计、figure source-data audit 和 final readiness dashboard。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_media_upload_quality_audit.py --out-dir outputs/tits_dynamic_graph/tits_media_upload_quality_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit media upload quality for T-ITS figures and visual supplements.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_media_upload_quality_audit")
    args = parser.parse_args()

    root = Path(".").resolve()
    out_dir = Path(args.out_dir)
    report = build_report(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "report_md": write_text(out_dir / "materials" / "MEDIA_UPLOAD_QUALITY_AUDIT.md", build_markdown(report)),
        "media_checks_csv": write_csv(
            out_dir / "tables" / "media_upload_quality_checks.csv",
            report["media_rows"],
            [
                "media_id",
                "role",
                "path",
                "expected_kind",
                "exists",
                "size_bytes",
                "size_mb",
                "width_px",
                "height_px",
                "frame_count",
                "dpi_x",
                "dpi_y",
                "pil_readable",
                "pil_error",
                "status",
                "errors",
                "warnings",
            ],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
        "boundary": "Local media-upload quality audit; final journal portal limits and production requirements must be checked by authors.",
    }
    manifest_path = write_json(out_dir / "tits_media_upload_quality_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
