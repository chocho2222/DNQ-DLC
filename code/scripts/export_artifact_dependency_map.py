#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def categorize_artifact(name):
    if any(token in name for token in ["multiseed", "suite", "smoke", "ablation", "selector_1200", "online_probe"]):
        return "rollout_or_selector_evaluation"
    if any(token in name for token in ["statistical", "ledger", "atlas", "synthesis", "generalization", "calibration"]):
        return "analysis_table"
    if any(token in name for token in ["figure", "legends"]):
        return "figure_or_legend"
    if any(token in name for token in ["manifest", "availability", "fair", "release", "dictionary", "verification", "audit", "provenance"]):
        return "reproducibility_or_archive"
    if any(token in name for token in ["manuscript", "claim", "reviewer", "submission", "reporting", "risk", "significance"]):
        return "manuscript_or_submission"
    if "training" in name or "dagger" in name:
        return "model_training_or_diagnostic"
    return "other"


def infer_review_use(name, category):
    if category == "rollout_or_selector_evaluation":
        return "Source evidence for strict validation outcomes and selector/oracle comparisons."
    if category == "analysis_table":
        return "Derived tables for statistics, failure decomposition, and held-out synthesis."
    if category == "figure_or_legend":
        return "Submission-facing visual evidence and source-data traceability."
    if category == "reproducibility_or_archive":
        return "Reproduction, audit, archive, metadata, and package-integrity checks."
    if category == "manuscript_or_submission":
        return "Claim wording, manuscript preparation, reviewer response, and editorial-submission checks."
    if category == "model_training_or_diagnostic":
        return "Model-development or diagnostic evidence retained for method context."
    return "Supporting package artifact."


def build_map(root):
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    manifest = load_json(root / "manifest.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    exclusion_audit_path = root / "materials" / "ARCHIVE_MANIFEST_EXCLUSION_AUDIT.json"
    excluded_release_outputs = set()
    if exclusion_audit_path.exists():
        exclusion_audit = load_json(exclusion_audit_path)
        excluded_release_outputs = {
            row["path"]
            for row in exclusion_audit.get("rows", [])
            if row.get("status") == "pass" and not row.get("in_release_manifest")
        }

    artifact_rows = []
    file_rows = []
    category_counts = {}
    file_to_artifacts = {}

    for index, artifact in enumerate(provenance["artifacts"], start=1):
        category = categorize_artifact(artifact["name"])
        category_counts[category] = category_counts.get(category, 0) + 1
        outputs = artifact["outputs"]
        inputs = artifact["inputs"]
        scripts = artifact["scripts"]
        artifact_rows.append(
            {
                "artifact": artifact["name"],
                "category": category,
                "complete": artifact["complete"],
                "input_count": len(inputs),
                "output_count": len(outputs),
                "script_count": len(scripts),
                "primary_output": outputs[0] if outputs else "",
                "review_use": infer_review_use(artifact["name"], category),
                "command": artifact["command"],
                "topological_index": index,
            }
        )
        for role, paths in [("input", inputs), ("output", outputs), ("script", scripts)]:
            for path in paths:
                file_rows.append(
                    {
                        "artifact": artifact["name"],
                        "category": category,
                        "role": role,
                        "path": path,
                        "exists": (
                            artifact["inputs_status"].get(path)
                            if role == "input"
                            else artifact["outputs_status"].get(path)
                            if role == "output"
                            else artifact["scripts_status"].get(path)
                        ),
                    }
                )
                file_to_artifacts.setdefault(path, {"as_input": [], "as_output": [], "as_script": []})
                file_to_artifacts[path][f"as_{role}"].append(artifact["name"])

    key_paths = {
        "manifest": "manifest.json",
        "artifact_provenance": "tables/artifact_provenance.json",
        "publication_verification": "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        "claim_matrix": "materials/CLAIM_EVIDENCE_MATRIX.json",
        "seed_ledger": "tables/seed_outcome_ledger.json",
        "figure3_source": "figures/figure_3_source_data.csv",
        "significance_briefing": "materials/SIGNIFICANCE_BRIEFING.json",
        "editorial_checklist": "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
        "release_manifest": "materials/RELEASE_ARCHIVE_MANIFEST.json",
    }
    key_lineage = {}
    for label, path in key_paths.items():
        entry = file_to_artifacts.get(path, {"as_input": [], "as_output": [], "as_script": []})
        key_lineage[label] = {"path": path, **entry}

    release_paths = {row["path"] for row in release["files"]}
    self_describing_manifest_outputs = (
        "materials/RELEASE_ARCHIVE_MANIFEST",
        "materials/FAIR_ARCHIVE_METADATA",
    )
    def release_covers_output(output):
        if output in release_paths:
            return True
        if output in excluded_release_outputs:
            return True
        if output.startswith(self_describing_manifest_outputs):
            return True
        return (root / output).is_dir() and any(
            path.startswith(f"{output}/") for path in release_paths
        )

    unlisted_outputs = sorted(
        {
            output
            for artifact in provenance["artifacts"]
            for output in artifact["outputs"]
            if not release_covers_output(output)
        }
    )
    excluded_artifact_outputs = sorted(
        {
            output
            for artifact in provenance["artifacts"]
            for output in artifact["outputs"]
            if output in excluded_release_outputs
        }
    )

    return {
        "root": str(root),
        "title": "Artifact dependency map",
        "purpose": "Trace package artifacts from saved inputs and scripts to reviewer-facing outputs.",
        "artifact_rows": artifact_rows,
        "file_rows": file_rows,
        "key_lineage": key_lineage,
        "summary": {
            "artifact_count": len(provenance["artifacts"]),
            "complete_count": provenance["complete_count"],
            "category_counts": category_counts,
            "file_edge_count": len(file_rows),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
            "release_file_count": release["summary"]["file_count"],
            "unlisted_release_outputs_after_exclusions": unlisted_outputs,
            "excluded_release_outputs_documented": excluded_artifact_outputs,
            "excluded_release_output_count": len(excluded_artifact_outputs),
            "manifest_primary_material_count": len(manifest.get("primary_materials", {})),
        },
        "interpretation": (
            "This map is a reviewer-facing dependency overview. The authoritative reproduction commands remain "
            "tables/artifact_provenance.md; this file summarizes the same provenance in analysis- and archive-oriented views."
        ),
    }


def write_artifact_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "artifact",
            "category",
            "complete",
            "input_count",
            "output_count",
            "script_count",
            "primary_output",
            "review_use",
            "command",
            "topological_index",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["artifact_rows"]:
            writer.writerow(row)


def write_file_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["artifact", "category", "role", "path", "exists"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["file_rows"]:
            writer.writerow(row)


def write_markdown(report, path):
    lines = [
        "# Artifact Dependency Map",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Artifacts: {report['summary']['complete_count']}/{report['summary']['artifact_count']}",
        f"- File dependency edges: {report['summary']['file_edge_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Release file count: {report['summary']['release_file_count']}",
        f"- Unlisted release outputs after documented exclusions: {len(report['summary']['unlisted_release_outputs_after_exclusions'])}",
        f"- Documented self-referential release exclusions: {report['summary']['excluded_release_output_count']}",
        "",
        "## Category Counts",
        "",
        "| category | artifacts |",
        "|---|---:|",
    ]
    for category, count in sorted(report["summary"]["category_counts"].items()):
        lines.append(f"| {category} | {count} |")
    lines.extend(
        [
            "",
            "## Reviewer Entry Lineage",
            "",
            "| label | path | produced by | consumed by |",
            "|---|---|---|---|",
        ]
    )
    for label, row in report["key_lineage"].items():
        lines.append(
            f"| {label} | `{row['path']}` | {', '.join(row['as_output']) or 'external/root'} | {', '.join(row['as_input']) or 'not recorded'} |"
        )
    lines.extend(
        [
            "",
            "## Artifact Overview",
            "",
            "| artifact | category | complete | outputs | inputs | scripts | primary output | review use |",
            "|---|---|---|---:|---:|---:|---|---|",
        ]
    )
    for row in report["artifact_rows"]:
        lines.append(
            f"| {row['artifact']} | {row['category']} | {row['complete']} | {row['output_count']} | "
            f"{row['input_count']} | {row['script_count']} | `{row['primary_output']}` | {row['review_use']} |"
        )
    lines.extend(
        [
            "",
            "CSV detail files:",
            "",
            "- `materials/ARTIFACT_DEPENDENCY_MAP.csv`",
            "- `materials/ARTIFACT_DEPENDENCY_FILE_EDGES.csv`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export artifact dependency map from provenance.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_map(root)
    out_json = materials / "ARTIFACT_DEPENDENCY_MAP.json"
    out_md = materials / "ARTIFACT_DEPENDENCY_MAP.md"
    out_csv = materials / "ARTIFACT_DEPENDENCY_MAP.csv"
    out_edges = materials / "ARTIFACT_DEPENDENCY_FILE_EDGES.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_artifact_csv(report, out_csv)
    write_file_csv(report, out_edges)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "file_edges": str(out_edges)}, indent=2))


if __name__ == "__main__":
    main()
