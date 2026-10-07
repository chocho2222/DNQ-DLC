#!/usr/bin/env python
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


REFERENCE_FILES = [
    "tables/main_results.csv",
    "tables/main_results.json",
    "tables/main_results.md",
    "tables/heldout4_failure_atlas_method_matrix.csv",
    "materials/README.md",
    "materials/SUPPLEMENTARY_INDEX.md",
    "materials/REPRODUCTION_GUIDE.md",
]


def normalize_rel(root, path):
    path = Path(path)
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def category_for(rel):
    first = Path(rel).parts[0] if Path(rel).parts else "other"
    if first in {"baselines", "evaluations", "ablations", "sweeps"}:
        return first[:-1] if first.endswith("s") else first
    return "other"


def seed_for(rel):
    match = re.search(r"seed[_-]?(\d+)", rel)
    return int(match.group(1)) if match else ""


def method_for(rel):
    parts = Path(rel).parts
    if not parts:
        return ""
    if parts[0] == "baselines" and len(parts) > 1:
        return parts[1]
    if parts[0] == "ablations" and len(parts) > 1:
        return parts[1]
    if parts[0] == "evaluations" and len(parts) > 1:
        return parts[1]
    if parts[0] == "sweeps" and len(parts) > 1:
        return parts[1]
    return parts[-2] if len(parts) > 1 else Path(rel).stem


def companion_paths(gif_path):
    stem = gif_path.with_suffix("")
    candidates = [
        gif_path.with_suffix(".json"),
        Path(str(gif_path) + ".json"),
        Path(str(stem) + ".json"),
    ]
    trace_candidates = [
        Path(str(stem) + ".trace.json"),
        Path(str(gif_path) + ".trace.json"),
    ]
    summary = next((path for path in candidates if path.exists()), None)
    trace = next((path for path in trace_candidates if path.exists()), None)
    return summary, trace


def referenced_paths(root):
    refs = {}
    for rel in REFERENCE_FILES:
        path = root / rel
        if path.exists():
            refs[rel] = path.read_text(encoding="utf-8", errors="replace")
    return refs


def build_audit(root):
    gifs = sorted(root.glob("**/*.gif"))
    references = referenced_paths(root)
    verification_path = root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json"
    verification = load_json(verification_path) if verification_path.exists() else {"summary": {}}

    rows = []
    for gif_path in gifs:
        rel = normalize_rel(root, gif_path)
        summary_path, trace_path = companion_paths(gif_path)
        linked_files = [ref for ref, text in references.items() if rel in text or Path(rel).name in text]
        rows.append(
            {
                "gif": rel,
                "category": category_for(rel),
                "method": method_for(rel),
                "seed": seed_for(rel),
                "size_bytes": gif_path.stat().st_size,
                "has_summary_json": summary_path is not None,
                "summary_json": normalize_rel(root, summary_path) if summary_path else "",
                "has_trace_json": trace_path is not None,
                "trace_json": normalize_rel(root, trace_path) if trace_path else "",
                "referenced_by": ";".join(linked_files),
                "referenced_by_count": len(linked_files),
                "linked_primary_table": any(ref.startswith("tables/") for ref in linked_files),
                "qualitative_only": True,
                "interpretation_boundary": (
                    "Qualitative rollout visualization only; strict PASS/FAIL claims must come from saved tables and validator reports."
                ),
            }
        )

    category_counts = Counter(row["category"] for row in rows)
    paired_summary_count = sum(1 for row in rows if row["has_summary_json"])
    paired_trace_count = sum(1 for row in rows if row["has_trace_json"])
    referenced_count = sum(1 for row in rows if row["referenced_by_count"])
    primary_linked_count = sum(1 for row in rows if row["linked_primary_table"])
    unreferenced = [row["gif"] for row in rows if not row["referenced_by_count"]]

    return {
        "root": str(root),
        "title": "Visual Evidence Audit",
        "purpose": (
            "Catalog saved GIF rollouts and separate qualitative visual evidence from strict quantitative validation tables."
        ),
        "summary": {
            "gif_count": len(rows),
            "paired_summary_json_count": paired_summary_count,
            "paired_trace_json_count": paired_trace_count,
            "referenced_gif_count": referenced_count,
            "unreferenced_gif_count": len(unreferenced),
            "primary_table_linked_gif_count": primary_linked_count,
            "category_counts": dict(sorted(category_counts.items())),
            "publication_verification_status": verification.get("summary", {}).get("status", "unknown"),
            "artifact_provenance": verification.get("summary", {}).get("artifact_provenance", "unknown"),
        },
        "reference_files": REFERENCE_FILES,
        "gifs": rows,
        "unreferenced_gifs": unreferenced,
        "interpretation": (
            "GIFs are retained for visual inspection and reviewer orientation. They are not used as primary evidence for "
            "success rates, overtaking claims, or robustness claims; those claims are controlled by strict validator tables, "
            "seed ledgers, sensitivity audits, and statistical reports."
        ),
    }


def write_csv(report, path):
    fields = [
        "gif",
        "category",
        "method",
        "seed",
        "size_bytes",
        "has_summary_json",
        "summary_json",
        "has_trace_json",
        "trace_json",
        "referenced_by",
        "referenced_by_count",
        "linked_primary_table",
        "qualitative_only",
        "interpretation_boundary",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["gifs"])


def write_markdown(report, path):
    lines = [
        "# Visual Evidence Audit",
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
            "## GIF Rollouts",
            "",
            "| gif | category | method | seed | summary json | trace json | referenced | qualitative only |",
            "|---|---|---|---:|---|---|---:|---|",
        ]
    )
    for row in report["gifs"]:
        lines.append(
            f"| `{row['gif']}` | {row['category']} | `{row['method']}` | {row['seed']} | "
            f"{row['has_summary_json']} | {row['has_trace_json']} | {row['referenced_by_count']} | {row['qualitative_only']} |"
        )
    if report["unreferenced_gifs"]:
        lines.extend(["", "## Unreferenced GIFs", ""])
        for item in report["unreferenced_gifs"]:
            lines.append(f"- `{item}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export visual evidence audit for saved GIF rollouts.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_audit(root)
    out_json = materials / "VISUAL_EVIDENCE_AUDIT.json"
    out_md = materials / "VISUAL_EVIDENCE_AUDIT.md"
    out_csv = materials / "VISUAL_EVIDENCE_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "gif_count": report["summary"]["gif_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
