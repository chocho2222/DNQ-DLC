#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image


FIGURES = [
    {
        "figure": "figure_1",
        "manifest": "figures/figure_manifest.json",
        "base": "figures/figure_1_multicar_overtake_results",
        "source_data": "figures/figure_1_source_data.csv",
    },
    {
        "figure": "figure_2",
        "manifest": "figures/figure_2_manifest.json",
        "base": "figures/figure_2_portfolio_selector_summary",
        "source_data": "figures/figure_2_source_data.csv",
    },
    {
        "figure": "figure_3",
        "manifest": "figures/figure_3_manifest.json",
        "base": "figures/figure_3_cross_heldout_validation",
        "source_data": "figures/figure_3_source_data.csv",
    },
]

REQUIRED_FORMATS = [".pdf", ".tiff", ".png", ".svg"]
MIN_RASTER_DPI = 300
MIN_TIFF_DPI = 300
MIN_RASTER_WIDTH_PX = 1800
MIN_RASTER_HEIGHT_PX = 1200
DPI_TOLERANCE = 0.5
HEX_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def csv_shape(path):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return 0, 0
    return max(0, len(rows) - 1), len(rows[0])


def raster_info(path):
    with Image.open(path) as image:
        dpi = image.info.get("dpi") or (None, None)
        x_dpi = float(dpi[0]) if dpi and dpi[0] else None
        y_dpi = float(dpi[1]) if dpi and len(dpi) > 1 and dpi[1] else None
        return {
            "width_px": image.size[0],
            "height_px": image.size[1],
            "mode": image.mode,
            "x_dpi": x_dpi,
            "y_dpi": y_dpi,
        }


def svg_info(path):
    root = ElementTree.parse(path).getroot()
    view_box = root.attrib.get("viewBox", "")
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "width_px": parse_svg_length(root.attrib.get("width")),
        "height_px": parse_svg_length(root.attrib.get("height")),
        "mode": "vector",
        "x_dpi": None,
        "y_dpi": None,
        "view_box": view_box,
        "svg_text_element_count": text.count("<text"),
        "svg_image_element_count": text.count("<image"),
        "svg_has_font_family": "font-family" in text,
        "svg_has_glyph_defs": "<glyph" in text,
    }


def parse_svg_length(value):
    if not value:
        return None
    match = re.match(r"^([0-9.]+)", value)
    return float(match.group(1)) if match else None


def pdf_info(path):
    text = path.read_bytes()[:4096].decode("latin-1", errors="ignore")
    match = re.search(r"/MediaBox\s*\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]", text)
    if not match:
        return {"width_px": None, "height_px": None, "mode": "pdf", "x_dpi": None, "y_dpi": None}
    return {
        "width_px": round(float(match.group(1)), 2),
        "height_px": round(float(match.group(2)), 2),
        "mode": "pdf_points",
        "x_dpi": None,
        "y_dpi": None,
    }


def file_info(path):
    suffix = path.suffix.lower()
    base = {
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "width_px": None,
        "height_px": None,
        "mode": "",
        "x_dpi": None,
        "y_dpi": None,
        "view_box": "",
        "svg_text_element_count": None,
        "svg_image_element_count": None,
        "svg_has_font_family": None,
        "svg_has_glyph_defs": None,
        "technical_status": "missing",
        "notes": "",
    }
    if not path.exists():
        return base
    try:
        if suffix in {".png", ".tif", ".tiff"}:
            base.update(raster_info(path))
        elif suffix == ".svg":
            base.update(svg_info(path))
        elif suffix == ".pdf":
            base.update(pdf_info(path))
        else:
            base["mode"] = "unknown"
    except Exception as exc:
        base["technical_status"] = "review_required"
        base["notes"] = f"metadata read failed: {type(exc).__name__}: {exc}"
        return base

    checks = []
    if suffix in {".png", ".tif", ".tiff"}:
        checks.append(base["width_px"] is not None and base["width_px"] >= MIN_RASTER_WIDTH_PX)
        checks.append(base["height_px"] is not None and base["height_px"] >= MIN_RASTER_HEIGHT_PX)
        if suffix in {".tif", ".tiff"}:
            checks.append(base["x_dpi"] is not None and base["x_dpi"] + DPI_TOLERANCE >= MIN_TIFF_DPI)
            checks.append(base["y_dpi"] is not None and base["y_dpi"] + DPI_TOLERANCE >= MIN_TIFF_DPI)
        else:
            dpi_missing = base["x_dpi"] is None or base["y_dpi"] is None
            if dpi_missing:
                base["notes"] = "PNG DPI metadata absent; TIFF is the archival raster submission format."
            else:
                checks.append(
                    base["x_dpi"] + DPI_TOLERANCE >= MIN_RASTER_DPI
                    and base["y_dpi"] + DPI_TOLERANCE >= MIN_RASTER_DPI
                )
    elif suffix == ".svg":
        checks.append(bool(base["view_box"]) or (base["width_px"] is not None and base["height_px"] is not None))
    elif suffix == ".pdf":
        checks.append(base["size_bytes"] > 0)
    base["technical_status"] = "pass" if all(checks) else "review_required"
    return base


def build_report(root):
    source_audit = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    release_paths = {item["path"] for item in release["files"]}
    source_by_path = {row["source_data"]: row for row in source_audit["figures"]}

    figure_rows = []
    file_rows = []
    accessibility_rows = []
    for spec in FIGURES:
        manifest_path = root / spec["manifest"]
        source_path = root / spec["source_data"]
        source_rows, source_columns = csv_shape(source_path) if source_path.exists() else (0, 0)
        manifest = load_json(manifest_path) if manifest_path.exists() else {}
        panels = manifest.get("panels", {})
        expected_files = [f"{spec['base']}{ext}" for ext in REQUIRED_FORMATS]
        figure_file_rows = []
        for rel_path in expected_files:
            path = root / rel_path
            info = file_info(path)
            row = {
                "figure": spec["figure"],
                "path": rel_path,
                "format": path.suffix.lower().lstrip("."),
                "in_release_manifest": rel_path in release_paths,
                **info,
            }
            figure_file_rows.append(row)
            file_rows.append(row)

        missing_format_count = sum(1 for row in figure_file_rows if not row["exists"])
        review_required_count = sum(1 for row in figure_file_rows if row["technical_status"] != "pass")
        source_complete = bool(source_by_path.get(spec["source_data"], {}).get("complete"))
        figure_status = (
            "pass"
            if missing_format_count == 0
            and review_required_count == 0
            and source_complete
            and source_rows > 0
            and source_columns > 0
            else "review_required"
        )
        tiff = next(row for row in figure_file_rows if row["format"] == "tiff")
        svg_row = next(row for row in figure_file_rows if row["format"] == "svg")
        svg_path = root / f"{spec['base']}.svg"
        svg_text = svg_path.read_text(encoding="utf-8", errors="replace") if svg_path.exists() else ""
        figure_script = {
            "figure_1": Path("scripts/export_paper_figures.py"),
            "figure_2": Path("scripts/export_supplementary_figure.py"),
            "figure_3": Path("scripts/export_cross_heldout_validation_figure.py"),
        }.get(spec["figure"])
        script_text = figure_script.read_text(encoding="utf-8", errors="replace") if figure_script and figure_script.exists() else ""
        palette_colors = sorted(set(HEX_COLOR_RE.findall(script_text)))
        panel_labels = sorted(panels)
        panel_label_hits = [
            panel
            for panel in panel_labels
            if f">{panel}" in svg_text or f"{panel}  " in svg_text or f"{panel} " in svg_text
        ]
        status_text_hits = [word for word in ["PASS", "FAIL", "pass rate", "diagnostic oracle", "selector miss", "candidate gap"] if word in svg_text]
        accessibility_checks = {
            "svg_editable_text": svg_row["svg_text_element_count"] is not None and svg_row["svg_text_element_count"] > 0,
            "svg_no_embedded_raster": svg_row["svg_image_element_count"] == 0,
            "svg_font_family_declared": bool(svg_row["svg_has_font_family"]),
            "svg_no_glyph_outlines": svg_row["svg_has_glyph_defs"] is False,
            "panel_labels_present": len(panel_label_hits) == len(panel_labels),
            "multi_hue_palette_declared": len(palette_colors) >= 4,
            "non_color_status_cues_present": bool(status_text_hits),
        }
        missing_accessibility = [key for key, value in accessibility_checks.items() if not value]
        accessibility_rows.append(
            {
                "figure": spec["figure"],
                "status": "pass" if not missing_accessibility else "review_required",
                "svg": f"{spec['base']}.svg",
                "panel_count": len(panel_labels),
                "panel_labels_detected": ";".join(panel_label_hits),
                "svg_text_element_count": svg_row["svg_text_element_count"],
                "svg_image_element_count": svg_row["svg_image_element_count"],
                "svg_has_font_family": svg_row["svg_has_font_family"],
                "svg_has_glyph_defs": svg_row["svg_has_glyph_defs"],
                "palette_color_count": len(palette_colors),
                "palette_colors": ";".join(palette_colors),
                "status_text_cues": ";".join(status_text_hits),
                "missing_checks": ";".join(missing_accessibility),
                "interpretation": (
                    "Automated accessibility and editability screen only; final journal-specific color, font, and "
                    "layout review remains an author production step."
                ),
            }
        )
        figure_rows.append(
            {
                "figure": spec["figure"],
                "status": figure_status,
                "manifest": spec["manifest"],
                "source_data": spec["source_data"],
                "source_rows": source_rows,
                "source_columns": source_columns,
                "panel_count": len(panels),
                "format_count": len(figure_file_rows),
                "missing_format_count": missing_format_count,
                "review_required_file_count": review_required_count,
                "tiff_width_px": tiff["width_px"],
                "tiff_height_px": tiff["height_px"],
                "tiff_x_dpi": tiff["x_dpi"],
                "tiff_y_dpi": tiff["y_dpi"],
                "source_data_audit_complete": source_complete,
                "accessibility_status": accessibility_rows[-1]["status"],
            }
        )

    failed = [row for row in figure_rows if row["status"] != "pass"]
    accessibility_failed = [row for row in accessibility_rows if row["status"] != "pass"]
    return {
        "root": str(root),
        "title": "Figure technical QC audit",
        "purpose": (
            "Check publication figure exports for reviewer-facing technical readiness: required formats, "
            "raster dimensions, TIFF DPI metadata, vector/PDF presence, release-manifest inclusion, and source-data linkage."
        ),
        "summary": {
            "figure_count": len(figure_rows),
            "pass_count": len(figure_rows) - len(failed),
            "review_required_count": len(failed),
            "file_row_count": len(file_rows),
            "accessibility_row_count": len(accessibility_rows),
            "accessibility_review_required_count": len(accessibility_failed),
            "required_formats": ",".join(REQUIRED_FORMATS),
            "minimum_tiff_dpi": MIN_TIFF_DPI,
            "minimum_raster_width_px": MIN_RASTER_WIDTH_PX,
            "minimum_raster_height_px": MIN_RASTER_HEIGHT_PX,
            "dpi_tolerance": DPI_TOLERANCE,
            "status": "pass" if not failed else "review_required",
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
        },
        "figures": figure_rows,
        "files": file_rows,
        "accessibility": accessibility_rows,
        "interpretation": (
            "This is a technical packaging QC, not a scientific-result validation. It should be rerun after any "
            "figure regeneration, journal-specific resizing, color conversion, or source-data relabeling."
        ),
    }


def write_csv(report, materials):
    summary_csv = materials / "FIGURE_TECHNICAL_QC.csv"
    file_csv = materials / "FIGURE_TECHNICAL_QC_FILE_ROWS.csv"
    accessibility_csv = materials / "FIGURE_ACCESSIBILITY_QC.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "figure",
            "status",
            "manifest",
            "source_data",
            "source_rows",
            "source_columns",
            "panel_count",
            "format_count",
            "missing_format_count",
            "review_required_file_count",
            "tiff_width_px",
            "tiff_height_px",
            "tiff_x_dpi",
            "tiff_y_dpi",
            "source_data_audit_complete",
            "accessibility_status",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["figures"])
    with file_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "figure",
            "path",
            "format",
            "exists",
            "size_bytes",
            "width_px",
            "height_px",
            "mode",
            "x_dpi",
            "y_dpi",
            "view_box",
            "svg_text_element_count",
            "svg_image_element_count",
            "svg_has_font_family",
            "svg_has_glyph_defs",
            "in_release_manifest",
            "technical_status",
            "notes",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["files"])
    with accessibility_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "figure",
            "status",
            "svg",
            "panel_count",
            "panel_labels_detected",
            "svg_text_element_count",
            "svg_image_element_count",
            "svg_has_font_family",
            "svg_has_glyph_defs",
            "palette_color_count",
            "palette_colors",
            "status_text_cues",
            "missing_checks",
            "interpretation",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["accessibility"])
    return summary_csv, file_csv, accessibility_csv


def write_markdown(report, path):
    lines = [
        "# Figure Technical QC Audit",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "| figure | status | source data | panels | formats | TIFF pixels | TIFF dpi | source-data complete | accessibility |",
            "|---|---|---|---:|---:|---|---|---|---|",
        ]
    )
    for row in report["figures"]:
        lines.append(
            f"| {row['figure']} | {row['status']} | `{row['source_data']}` | {row['panel_count']} | "
            f"{row['format_count']} | {row['tiff_width_px']} x {row['tiff_height_px']} | "
            f"{row['tiff_x_dpi']} x {row['tiff_y_dpi']} | {row['source_data_audit_complete']} | "
            f"{row['accessibility_status']} |"
        )
    lines.extend(
        [
            "",
            "## Accessibility And Editability",
            "",
            "| figure | status | panel labels | SVG text | SVG images | font family | glyph outlines | palette colors | status text cues | missing checks |",
            "|---|---|---|---:|---:|---|---|---:|---|---|",
        ]
    )
    for row in report["accessibility"]:
        lines.append(
            f"| {row['figure']} | {row['status']} | {row['panel_labels_detected']} | "
            f"{row['svg_text_element_count']} | {row['svg_image_element_count']} | "
            f"{row['svg_has_font_family']} | {row['svg_has_glyph_defs']} | "
            f"{row['palette_color_count']} | {row['status_text_cues']} | {row['missing_checks']} |"
        )
    lines.extend(
        [
            "",
            "## File Rows",
            "",
            "| figure | format | path | size bytes | dimensions | dpi | release manifest | status | notes |",
            "|---|---|---|---:|---|---|---|---|---|",
        ]
    )
    for row in report["files"]:
        dimensions = (
            f"{row['width_px']} x {row['height_px']}"
            if row["width_px"] is not None or row["height_px"] is not None
            else ""
        )
        dpi = f"{row['x_dpi']} x {row['y_dpi']}" if row["x_dpi"] is not None or row["y_dpi"] is not None else ""
        lines.append(
            f"| {row['figure']} | {row['format']} | `{row['path']}` | {row['size_bytes']} | "
            f"{dimensions} | {dpi} | {row['in_release_manifest']} | {row['technical_status']} | {row['notes']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export figure technical QC audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "FIGURE_TECHNICAL_QC.json"
    out_md = materials / "FIGURE_TECHNICAL_QC.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    summary_csv, file_csv, accessibility_csv = write_csv(report, materials)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(summary_csv),
                "file_csv": str(file_csv),
                "accessibility_csv": str(accessibility_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
