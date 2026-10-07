#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


MB = 1024 * 1024


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fmt_mb(size_bytes):
    return round(size_bytes / MB, 3)


def split_paths(value):
    if isinstance(value, list):
        return value
    if not value:
        return []
    return [item.strip() for item in str(value).split(";") if item.strip()]


def classify_upload_package(path, bundle_rows, upload_rows):
    candidates = []
    if path in bundle_rows:
        candidates.extend(bundle_rows[path])
    if path in upload_rows:
        candidates.extend(upload_rows[path])
    if candidates:
        if any(item in {"journal_submission", "journal_submission_source", "journal_submission_upload"} for item in candidates):
            return "journal_submission_candidate"
        if any(item in {"source_data_upload", "supporting_upload"} for item in candidates):
            return "source_data_candidate"
        if any("supplement" in item for item in candidates):
            return "supplement_candidate"
        if any("archive" in item for item in candidates):
            return "archive_candidate"
        if any("internal" in item for item in candidates):
            return "internal_qc_candidate"
        return sorted(set(candidates))[0]
    if path.startswith("figures/"):
        return "figure_asset"
    if path.startswith("materials/"):
        return "materials_archive"
    if path.startswith("tables/"):
        return "tables_archive"
    if path.startswith("evaluations/"):
        return "evaluation_archive"
    if path.startswith("models/"):
        return "model_archive"
    return "archive_other"


def build_path_maps(bundle, upload_plan):
    bundle_rows = {}
    for row in bundle.get("files", bundle.get("rows", [])):
        path = row.get("path")
        if path:
            bundle_rows.setdefault(path, []).append(row.get("upload_package", "unspecified"))

    upload_rows = {}
    for row in upload_plan.get("rows", []):
        for path in split_paths(row.get("path") or row.get("local_files") or row.get("files")):
            upload_rows.setdefault(path, []).append(row.get("upload_package") or row.get("destination") or row.get("package_role") or "unspecified")
    return bundle_rows, upload_rows


def budget_status(size_bytes, soft_mb, hard_mb):
    size_mb = size_bytes / MB
    if size_mb > hard_mb:
        return "exceeds_hard_budget"
    if size_mb > soft_mb:
        return "exceeds_soft_budget"
    return "within_budget"


def build_report(root):
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    upload_plan = load_json(root / "materials" / "SUBMISSION_UPLOAD_SELECTION_PLAN.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    freeze = load_json(root / "materials" / "FINAL_CHECKSUM_FREEZE_RECORD.json")
    bundle_rows, upload_rows = build_path_maps(bundle, upload_plan)

    files = release["files"]
    total_size = sum(row["size_bytes"] for row in files)

    category_rows = []
    by_category = {}
    for row in files:
        item = by_category.setdefault(row["category"], {"category": row["category"], "file_count": 0, "size_bytes": 0})
        item["file_count"] += 1
        item["size_bytes"] += row["size_bytes"]
    for item in sorted(by_category.values(), key=lambda row: (-row["size_bytes"], row["category"])):
        category_rows.append(
            {
                **item,
                "size_mb": fmt_mb(item["size_bytes"]),
                "fraction_of_release": round(item["size_bytes"] / total_size, 6) if total_size else 0,
            }
        )

    upload_rows_budget = {}
    for row in files:
        package = classify_upload_package(row["path"], bundle_rows, upload_rows)
        item = upload_rows_budget.setdefault(package, {"upload_partition": package, "file_count": 0, "size_bytes": 0})
        item["file_count"] += 1
        item["size_bytes"] += row["size_bytes"]
    upload_partition_rows = []
    for item in sorted(upload_rows_budget.values(), key=lambda row: (-row["size_bytes"], row["upload_partition"])):
        upload_partition_rows.append(
            {
                **item,
                "size_mb": fmt_mb(item["size_bytes"]),
                "budget_status_100mb_soft_500mb_hard": budget_status(item["size_bytes"], 100, 500),
            }
        )

    largest_files = []
    for row in sorted(files, key=lambda item: item["size_bytes"], reverse=True)[:25]:
        largest_files.append(
            {
                "path": row["path"],
                "category": row["category"],
                "upload_partition": classify_upload_package(row["path"], bundle_rows, upload_rows),
                "size_bytes": row["size_bytes"],
                "size_mb": fmt_mb(row["size_bytes"]),
                "sha256": row["sha256"],
                "budget_status_50mb_soft_250mb_hard": budget_status(row["size_bytes"], 50, 250),
            }
        )

    budget_rows = [
        {
            "budget": "single_file_50mb_soft",
            "threshold_mb": 50,
            "observed_count": sum(1 for row in files if row["size_bytes"] > 50 * MB),
            "status": "review_required" if any(row["size_bytes"] > 50 * MB for row in files) else "pass",
            "action": "Large single files should be routed to archive or journal-specific large-file upload rather than ordinary portal fields.",
        },
        {
            "budget": "single_file_250mb_hard",
            "threshold_mb": 250,
            "observed_count": sum(1 for row in files if row["size_bytes"] > 250 * MB),
            "status": "review_required" if any(row["size_bytes"] > 250 * MB for row in files) else "pass",
            "action": "Files above this conservative hard threshold should be split, compressed differently, or deposited only in a repository that supports them.",
        },
        {
            "budget": "release_archive_500mb_soft",
            "threshold_mb": 500,
            "observed_count": 1 if total_size > 500 * MB else 0,
            "status": "review_required" if total_size > 500 * MB else "pass",
            "action": "If exceeded, provide a slim journal upload plus full public archive.",
        },
        {
            "budget": "release_archive_2gb_hard",
            "threshold_mb": 2048,
            "observed_count": 1 if total_size > 2048 * MB else 0,
            "status": "review_required" if total_size > 2048 * MB else "pass",
            "action": "If exceeded, use repository-native multipart deposition and document checksums per part.",
        },
    ]

    recommendations = [
        "Keep PDF/SVG/CSV source-data files as the journal-facing lightweight upload set when allowed.",
        "Keep TIFF figures available for production, but route them according to the selected journal's figure-upload limits.",
        "Deposit the full release package in the public archive, with RELEASE_ARCHIVE_MANIFEST.csv as the checksum index.",
        "Use the largest-file table to decide whether optional GIF/trace material should remain archive-only.",
        "Regenerate this report after adding a final PDF, compressed archive, or public-deposition files.",
    ]

    review_required_budget = sum(1 for row in budget_rows if row["status"] == "review_required")
    return {
        "root": str(root),
        "title": "Archive Size and Upload Budget Report",
        "purpose": (
            "Quantify release-package size, largest files, category budgets, and likely journal/archive upload routing "
            "before public deposition or final journal upload."
        ),
        "summary": {
            "status": "pass" if review_required_budget == 0 else "ready_with_size_review",
            "release_file_count": release["summary"]["file_count"],
            "release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "release_size_mb": fmt_mb(total_size),
            "category_count": len(category_rows),
            "upload_partition_count": len(upload_partition_rows),
            "largest_file_count": len(largest_files),
            "single_file_over_50mb_count": sum(1 for row in files if row["size_bytes"] > 50 * MB),
            "single_file_over_250mb_count": sum(1 for row in files if row["size_bytes"] > 250 * MB),
            "budget_review_required_count": review_required_budget,
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "submission_dashboard_review_required": dashboard["summary"]["review_required_row_count"],
            "freeze_status": freeze["summary"]["status"],
        },
        "category_rows": category_rows,
        "upload_partition_rows": upload_partition_rows,
        "largest_files": largest_files,
        "budget_rows": budget_rows,
        "recommendations": recommendations,
        "interpretation": (
            "Budget flags are conservative operational checks, not journal-specific requirements. "
            "They help authors decide which files should be journal-facing, source-data-facing, supplement-facing, "
            "or archive-only after selecting the target journal and repository."
        ),
    }


def write_csv(rows, path, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# Archive Size and Upload Budget Report",
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
            "## Budget Checks",
            "",
            "| budget | threshold MB | observed count | status | action |",
            "|---|---:|---:|---|---|",
        ]
    )
    for row in report["budget_rows"]:
        lines.append(f"| {row['budget']} | {row['threshold_mb']} | {row['observed_count']} | {row['status']} | {row['action']} |")
    lines.extend(
        [
            "",
            "## Release Categories",
            "",
            "| category | files | size MB | fraction |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in report["category_rows"]:
        lines.append(f"| {row['category']} | {row['file_count']} | {row['size_mb']} | {row['fraction_of_release']} |")
    lines.extend(
        [
            "",
            "## Upload Partitions",
            "",
            "| partition | files | size MB | budget status |",
            "|---|---:|---:|---|",
        ]
    )
    for row in report["upload_partition_rows"]:
        lines.append(f"| {row['upload_partition']} | {row['file_count']} | {row['size_mb']} | {row['budget_status_100mb_soft_500mb_hard']} |")
    lines.extend(
        [
            "",
            "## Largest Files",
            "",
            "| path | category | partition | size MB | budget status |",
            "|---|---|---|---:|---|",
        ]
    )
    for row in report["largest_files"]:
        lines.append(
            f"| `{row['path']}` | {row['category']} | {row['upload_partition']} | "
            f"{row['size_mb']} | {row['budget_status_50mb_soft_250mb_hard']} |"
        )
    lines.extend(["", "## Recommendations", ""])
    for item in report["recommendations"]:
        lines.append(f"- {item}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export archive size and upload budget report.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "ARCHIVE_SIZE_BUDGET_REPORT.json"
    out_md = materials / "ARCHIVE_SIZE_BUDGET_REPORT.md"
    category_csv = materials / "ARCHIVE_SIZE_BUDGET_CATEGORIES.csv"
    partition_csv = materials / "ARCHIVE_SIZE_BUDGET_UPLOAD_PARTITIONS.csv"
    largest_csv = materials / "ARCHIVE_SIZE_BUDGET_LARGEST_FILES.csv"
    budget_csv = materials / "ARCHIVE_SIZE_BUDGET_CHECKS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report["category_rows"], category_csv, ["category", "file_count", "size_bytes", "size_mb", "fraction_of_release"])
    write_csv(report["upload_partition_rows"], partition_csv, ["upload_partition", "file_count", "size_bytes", "size_mb", "budget_status_100mb_soft_500mb_hard"])
    write_csv(report["largest_files"], largest_csv, ["path", "category", "upload_partition", "size_bytes", "size_mb", "sha256", "budget_status_50mb_soft_250mb_hard"])
    write_csv(report["budget_rows"], budget_csv, ["budget", "threshold_mb", "observed_count", "status", "action"])
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "category_csv": str(category_csv),
                "partition_csv": str(partition_csv),
                "largest_csv": str(largest_csv),
                "budget_csv": str(budget_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
