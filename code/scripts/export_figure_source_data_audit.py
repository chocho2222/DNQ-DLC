#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_rel(root, path_value):
    path = Path(path_value)
    if path.is_absolute():
        try:
            return str(path.relative_to(root))
        except ValueError:
            return str(path)
    text = str(path)
    prefix = str(root) + "/"
    if text.startswith(prefix):
        return text[len(prefix) :]
    return text


def csv_shape(path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    if not rows:
        return [], 0, 0
    return rows[0], max(0, len(rows) - 1), len(rows[0])


def build_audit(root):
    manifest_specs = [
        ("figure_1", root / "figures" / "figure_manifest.json"),
        ("figure_2", root / "figures" / "figure_2_manifest.json"),
        ("figure_3", root / "figures" / "figure_3_manifest.json"),
    ]
    legends = load_json(root / "materials" / "FIGURE_LEGENDS.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    legend_by_figure = {row["figure"]: row for row in legends["legends"]}

    rows = []
    file_edges = []
    panel_rows = []
    required_panel_fields = [
        "conclusion",
        "source_data_filter",
        "statistical_support",
        "claim_boundary",
        "reviewer_risk",
        "production_note",
    ]
    for figure_id, manifest_path in manifest_specs:
        manifest = load_json(manifest_path)
        figure = manifest["figure"]
        source_rel = normalize_rel(root, manifest["source_data"])
        source_path = root / source_rel
        headers, row_count, column_count = csv_shape(source_path) if source_path.exists() else ([], 0, 0)
        expected_exports = [normalize_rel(root, item) for item in manifest["exports"]]
        missing_exports = [item for item in expected_exports if not (root / item).exists()]
        legend = legend_by_figure.get(figure, {})
        panel_review_matrix = legend.get("panel_review_matrix", {})
        legend_source = normalize_rel(root, legend.get("source_data", "")) if legend else ""
        legend_exports = [normalize_rel(root, item) for item in legend.get("exports", [])]
        legend_export_mismatch = sorted(set(expected_exports).symmetric_difference(set(legend_exports)))
        required_formats = [".svg", ".pdf", ".tiff", ".png"]
        available_formats = sorted(Path(item).suffix for item in expected_exports if (root / item).exists())
        missing_formats = [ext for ext in required_formats if ext not in available_formats]
        complete = (
            manifest_path.exists()
            and source_path.exists()
            and not missing_exports
            and not missing_formats
            and legend_source == source_rel
            and not legend_export_mismatch
            and row_count > 0
            and column_count > 0
        )
        rows.append(
            {
                "figure": figure,
                "manifest": normalize_rel(root, manifest_path),
                "source_data": source_rel,
                "source_rows": row_count,
                "source_columns": column_count,
                "panel_count": len(manifest.get("panels", {})),
                "export_count": len(expected_exports),
                "available_formats": ";".join(available_formats),
                "missing_formats": ";".join(missing_formats),
                "legend_source_matches": legend_source == source_rel,
                "legend_export_mismatch_count": len(legend_export_mismatch),
                "review_risk_count": len(manifest.get("review_risks", [])),
                "complete": complete,
            }
        )
        for panel, description in manifest.get("panels", {}).items():
            review = panel_review_matrix.get(panel, {})
            missing_review_fields = [field for field in required_panel_fields if not review.get(field)]
            source_filter_text = review.get("source_data_filter", "")
            panel_rows.append(
                {
                    "figure": figure,
                    "panel": panel,
                    "description": description,
                    "source_data": source_rel,
                    "has_panel_review": bool(review),
                    "missing_review_fields": ";".join(missing_review_fields),
                    "source_data_filter": source_filter_text,
                    "statistical_support": review.get("statistical_support", ""),
                    "claim_boundary": review.get("claim_boundary", ""),
                    "reviewer_risk": review.get("reviewer_risk", ""),
                    "production_note": review.get("production_note", ""),
                    "complete": bool(review) and not missing_review_fields and bool(source_filter_text),
                }
            )
        file_edges.append(
            {
                "figure": figure,
                "role": "manifest",
                "path": normalize_rel(root, manifest_path),
                "exists": manifest_path.exists(),
            }
        )
        file_edges.append({"figure": figure, "role": "source_data", "path": source_rel, "exists": source_path.exists()})
        for item in expected_exports:
            file_edges.append({"figure": figure, "role": "export", "path": item, "exists": (root / item).exists()})

    incomplete = [row for row in rows if not row["complete"]]
    incomplete_panels = [row for row in panel_rows if not row["complete"]]
    all_columns = sorted({column for row in rows for column in (csv_shape(root / row["source_data"])[0] if (root / row["source_data"]).exists() else [])})
    return {
        "root": str(root),
        "title": "Figure/source-data consistency audit",
        "purpose": (
            "Check that publication figures have source-data CSV files, complete export formats, manifest entries, "
            "figure legends, and review-risk statements."
        ),
        "summary": {
            "figure_count": len(rows),
            "complete_count": len(rows) - len(incomplete),
            "incomplete_count": len(incomplete),
            "file_edge_count": len(file_edges),
            "panel_review_row_count": len(panel_rows),
            "panel_review_complete_count": len(panel_rows) - len(incomplete_panels),
            "panel_review_incomplete_count": len(incomplete_panels),
            "unique_source_columns": len(all_columns),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
        },
        "figures": rows,
        "panel_review_rows": panel_rows,
        "file_edges": file_edges,
        "source_columns": all_columns,
        "interpretation": (
            "This audit verifies figure packaging and source-data traceability. It does not re-render figures or "
            "recompute simulation results; the source tables and figure-generation scripts remain the analytical sources of truth."
        ),
    }


def write_csv(report, materials):
    summary_csv = materials / "FIGURE_SOURCE_DATA_AUDIT.csv"
    edges_csv = materials / "FIGURE_SOURCE_DATA_FILE_EDGES.csv"
    panel_csv = materials / "FIGURE_PANEL_REVIEW_MATRIX.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "figure",
            "manifest",
            "source_data",
            "source_rows",
            "source_columns",
            "panel_count",
            "export_count",
            "available_formats",
            "missing_formats",
            "legend_source_matches",
            "legend_export_mismatch_count",
            "review_risk_count",
            "complete",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["figures"])
    with edges_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = ["figure", "role", "path", "exists"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["file_edges"])
    with panel_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "figure",
            "panel",
            "description",
            "source_data",
            "has_panel_review",
            "missing_review_fields",
            "source_data_filter",
            "statistical_support",
            "claim_boundary",
            "reviewer_risk",
            "production_note",
            "complete",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["panel_review_rows"])
    return summary_csv, edges_csv, panel_csv


def write_markdown(report, path):
    lines = [
        "# Figure/source-data Consistency Audit",
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
            "| figure | source data | rows | columns | panels | exports | formats | legend source matches | review risks | complete |",
            "|---|---|---:|---:|---:|---:|---|---|---:|---|",
        ]
    )
    for row in report["figures"]:
        lines.append(
            f"| {row['figure']} | `{row['source_data']}` | {row['source_rows']} | {row['source_columns']} | "
            f"{row['panel_count']} | {row['export_count']} | {row['available_formats']} | "
            f"{row['legend_source_matches']} | {row['review_risk_count']} | {row['complete']} |"
        )
    lines.extend(
        [
            "",
            "## Panel Review Matrix",
            "",
            "| figure | panel | source data | complete | statistical support | claim boundary | reviewer risk |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["panel_review_rows"]:
        lines.append(
            f"| {row['figure']} | {row['panel']} | `{row['source_data']}` | {row['complete']} | "
            f"{row['statistical_support']} | {row['claim_boundary']} | {row['reviewer_risk']} |"
        )
    lines.extend(
        [
            "",
            "## Source-data Columns",
            "",
            ", ".join(f"`{column}`" for column in report["source_columns"]),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export figure/source-data consistency audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_audit(root)
    out_json = materials / "FIGURE_SOURCE_DATA_AUDIT.json"
    out_md = materials / "FIGURE_SOURCE_DATA_AUDIT.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    summary_csv, edges_csv, panel_csv = write_csv(report, materials)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(summary_csv),
                "file_edges": str(edges_csv),
                "panel_review_matrix": str(panel_csv),
                "complete": report["summary"]["incomplete_count"] == 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
