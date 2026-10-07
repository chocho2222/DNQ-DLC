#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_report(root):
    technical = load_json(root / "materials" / "FIGURE_TECHNICAL_QC.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    source_audit_path = root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json"
    source_audit = load_json(source_audit_path) if source_audit_path.exists() else {}

    rows = technical.get("accessibility", [])
    failed = [row for row in rows if row.get("status") != "pass"]
    svg_text_total = sum(int(row.get("svg_text_element_count") or 0) for row in rows)
    embedded_raster_count = sum(int(row.get("svg_image_element_count") or 0) for row in rows)
    glyph_outline_count = sum(1 for row in rows if row.get("svg_has_glyph_defs") is True)
    panel_label_complete_count = sum(
        1
        for row in rows
        if len([item for item in str(row.get("panel_labels_detected", "")).split(";") if item])
        == int(row.get("panel_count") or 0)
    )
    non_color_cue_complete_count = sum(1 for row in rows if row.get("status_text_cues"))
    source_complete_count = sum(1 for row in source_audit.get("figures", []) if row.get("complete"))

    return {
        "root": str(root),
        "title": "Figure accessibility and editability QC",
        "purpose": (
            "Provide an independent, reviewer-facing entry point for figure accessibility and editability checks: "
            "editable SVG text, absence of embedded SVG rasters and glyph outlines, panel-label detection, palette "
            "metadata, and non-colour status cues."
        ),
        "summary": {
            "status": "pass" if not failed else "review_required",
            "figure_count": len(rows),
            "pass_count": len(rows) - len(failed),
            "review_required_count": len(failed),
            "svg_text_total": svg_text_total,
            "embedded_raster_count": embedded_raster_count,
            "glyph_outline_count": glyph_outline_count,
            "panel_label_complete_count": panel_label_complete_count,
            "non_color_cue_complete_count": non_color_cue_complete_count,
            "source_data_complete_count": source_complete_count,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
        },
        "figures": rows,
        "interpretation": (
            "This automated screen supports journal-production review but does not replace author visual inspection, "
            "journal-specific accessibility checks, or production-editor requirements after resizing, colour conversion, "
            "font substitution, or layout edits."
        ),
    }


def write_csv(report, path):
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
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["figures"])


def write_markdown(report, path):
    lines = [
        "# Figure Accessibility And Editability QC",
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
            "## Per-Figure Checks",
            "",
            "| figure | status | panel labels | SVG text | SVG images | font family | glyph outlines | palette colors | status text cues | missing checks |",
            "|---|---|---|---:|---:|---|---|---:|---|---|",
        ]
    )
    for row in report["figures"]:
        lines.append(
            f"| {row['figure']} | {row['status']} | {row['panel_labels_detected']} | "
            f"{row['svg_text_element_count']} | {row['svg_image_element_count']} | "
            f"{row['svg_has_font_family']} | {row['svg_has_glyph_defs']} | "
            f"{row['palette_color_count']} | {row['status_text_cues']} | {row['missing_checks']} |"
        )
    lines.extend(
        [
            "",
            "## Review Boundary",
            "",
            (
                "The pass status means the exported SVG files retain editable text and the expected automated cues. "
                "It is not a substitute for colour-vision simulation, journal-specific font licensing review, or "
                "manual inspection of final production proofs."
            ),
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export independent figure accessibility/editability QC.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "FIGURE_ACCESSIBILITY_QC.json"
    out_md = materials / "FIGURE_ACCESSIBILITY_QC.md"
    out_csv = materials / "FIGURE_ACCESSIBILITY_QC.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
