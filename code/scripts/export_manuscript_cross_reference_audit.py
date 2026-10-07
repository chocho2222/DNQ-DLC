#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


TEXT_FILES = [
    "manuscript/main.md",
    "manuscript/README.md",
    "manuscript/figures/README.md",
    "materials/MANUSCRIPT_OUTLINE.md",
    "materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md",
    "materials/PUBLICATION_PACKAGE_SUMMARY.md",
    "materials/SUPPLEMENTARY_INDEX.md",
]

SELF_OUTPUTS = {
    "materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.md",
    "materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.json",
    "materials/MANUSCRIPT_CROSS_REFERENCE_PATHS.csv",
    "materials/MANUSCRIPT_CROSS_REFERENCE_NUMERIC_CHECKS.csv",
    "materials/REFERENCE_READINESS_AUDIT.md",
    "materials/REFERENCE_READINESS_AUDIT.json",
    "materials/REFERENCE_READINESS_CITATIONS.csv",
    "materials/REFERENCE_READINESS_TOPICS.csv",
}

PATH_PATTERN = re.compile(r"`([^`]+)`")
COMPUTE_PATTERN = re.compile(r"summarizes\s+(\d+)\s+full-rollout rows and\s+(\d+)\s+selector probe rows")
ARCHIVE_NUMBER_PATTERN = re.compile(r"release archive manifest currently lists\s+(\d+)\s+files and\s+(\d+)\s+bytes")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def line_no(text, index):
    return text.count("\n", 0, index) + 1


def candidate_path_tokens(text):
    for match in PATH_PATTERN.finditer(text):
        token = match.group(1).strip()
        if not token:
            continue
        if token.startswith(("http://", "https://", "../")):
            continue
        if token.startswith("../../"):
            yield match, token
            continue
        if token.startswith(("tables/", "materials/", "figures/", "manuscript/")):
            yield match, token


def resolve_token(root, source_rel, token):
    if token.startswith("../../"):
        source_dir = (root / source_rel).parent
        return (source_dir / token).resolve()
    source_relative = (root / source_rel).parent / token
    if source_relative.exists():
        return source_relative
    return root / token


def token_exists(root, source_rel, token):
    if token in SELF_OUTPUTS:
        return True, [token]
    if "*" in token:
        base = resolve_token(root, source_rel, token)
        matches = sorted(base.parent.glob(base.name))
        return bool(matches), [str(path.relative_to(root)) for path in matches if path.is_file()]
    path = resolve_token(root, source_rel, token)
    if path.exists():
        try:
            return True, [str(path.relative_to(root))]
        except ValueError:
            return True, [str(path)]
    return False, []


def scan_paths(root):
    rows = []
    for rel in TEXT_FILES:
        path = root / rel
        if not path.exists():
            rows.append(
                {
                    "source_file": rel,
                    "line": "",
                    "reference": "",
                    "reference_type": "source_file",
                    "status": "missing_source",
                    "resolved_paths": "",
                    "matched_count": 0,
                    "note": "Configured source text file is missing.",
                }
            )
            continue
        text = path.read_text(encoding="utf-8")
        for match, token in candidate_path_tokens(text):
            ok, matches = token_exists(root, rel, token)
            rows.append(
                {
                    "source_file": rel,
                    "line": line_no(text, match.start()),
                    "reference": token,
                    "reference_type": "glob" if "*" in token else "path",
                    "status": "pass" if ok else "missing_reference",
                    "resolved_paths": ";".join(matches),
                    "matched_count": len(matches),
                    "note": "Referenced package artifact found." if ok else "Referenced package artifact was not found.",
                }
            )
    return rows


def scan_numeric_consistency(root):
    rows = []
    manuscript_path = root / "manuscript" / "main.md"
    if not manuscript_path.exists():
        return [
            {
                "check_id": "manuscript_present",
                "source_file": "manuscript/main.md",
                "line": "",
                "expected": "exists",
                "observed": "missing",
                "status": "fail",
                "note": "Cannot scan numeric consistency without manuscript/main.md.",
            }
        ]

    text = manuscript_path.read_text(encoding="utf-8")
    compute = load_json(root / "tables" / "compute_cost_report.json")
    expected_full = int(compute["summary"]["full_rollout_rows"])
    expected_probe = int(compute["summary"]["selector_probe_rows"])
    compute_match = COMPUTE_PATTERN.search(text)
    if compute_match:
        observed_full = int(compute_match.group(1))
        observed_probe = int(compute_match.group(2))
        passed = observed_full == expected_full and observed_probe == expected_probe
        line = line_no(text, compute_match.start())
        observed = f"{observed_full} full-rollout rows; {observed_probe} selector probe rows"
    else:
        passed = False
        line = ""
        observed = "missing compute sentence"
    rows.append(
        {
            "check_id": "manuscript_compute_rows_match_report",
            "source_file": "manuscript/main.md",
            "line": line,
            "expected": f"{expected_full} full-rollout rows; {expected_probe} selector probe rows",
            "observed": observed,
            "status": "pass" if passed else "fail",
            "note": "Manuscript compute sentence must match tables/compute_cost_report.json.",
        }
    )

    archive_match = ARCHIVE_NUMBER_PATTERN.search(text)
    rows.append(
        {
            "check_id": "manuscript_avoids_archive_self_reference_counts",
            "source_file": "manuscript/main.md",
            "line": line_no(text, archive_match.start()) if archive_match else "",
            "expected": "no hard-coded release file count or byte count",
            "observed": archive_match.group(0) if archive_match else "no hard-coded archive count sentence",
            "status": "fail" if archive_match else "pass",
            "note": (
                "Release manifest counts drift when manuscript/reports are regenerated; manuscript should point to the manifest instead."
            ),
        }
    )
    return rows


def build_report(root):
    path_rows = scan_paths(root)
    numeric_rows = scan_numeric_consistency(root)
    missing_refs = [row for row in path_rows if row["status"] != "pass"]
    failed_numeric = [row for row in numeric_rows if row["status"] != "pass"]
    verification_path = root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json"
    verification = load_json(verification_path) if verification_path.exists() else {"summary": {}}
    return {
        "root": str(root),
        "title": "Manuscript Cross-reference Audit",
        "purpose": (
            "Check manuscript-facing references to figures, tables, and materials, and verify key manuscript numbers "
            "against authoritative machine-readable reports."
        ),
        "summary": {
            "source_file_count": len(TEXT_FILES),
            "reference_count": len(path_rows),
            "missing_reference_count": len(missing_refs),
            "numeric_check_count": len(numeric_rows),
            "failed_numeric_check_count": len(failed_numeric),
            "status": "pass" if not missing_refs and not failed_numeric else "fail",
            "publication_verification_status": verification.get("summary", {}).get("status", "unknown"),
            "artifact_provenance": verification.get("summary", {}).get("artifact_provenance", "unknown"),
        },
        "path_references": path_rows,
        "numeric_checks": numeric_rows,
        "interpretation": (
            "This audit is a static manuscript-readiness check. It verifies that cited local artifacts exist and that "
            "selected manuscript numbers match saved reports; it does not judge scientific adequacy or rerun simulations."
        ),
    }


def write_csv(report, materials):
    path_csv = materials / "MANUSCRIPT_CROSS_REFERENCE_PATHS.csv"
    numeric_csv = materials / "MANUSCRIPT_CROSS_REFERENCE_NUMERIC_CHECKS.csv"
    with path_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "source_file",
            "line",
            "reference",
            "reference_type",
            "status",
            "resolved_paths",
            "matched_count",
            "note",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["path_references"])
    with numeric_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = ["check_id", "source_file", "line", "expected", "observed", "status", "note"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["numeric_checks"])
    return path_csv, numeric_csv


def write_markdown(report, path):
    lines = [
        "# Manuscript Cross-reference Audit",
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
            "## Numeric Checks",
            "",
            "| check | status | expected | observed |",
            "|---|---|---|---|",
        ]
    )
    for row in report["numeric_checks"]:
        lines.append(f"| {row['check_id']} | {row['status']} | {row['expected']} | {row['observed']} |")
    lines.extend(
        [
            "",
            "## Missing References",
            "",
        ]
    )
    missing = [row for row in report["path_references"] if row["status"] != "pass"]
    if missing:
        for row in missing:
            lines.append(f"- `{row['source_file']}` line {row['line']}: `{row['reference']}`")
    else:
        lines.append("None.")
    lines.extend(
        [
            "",
            "## Reference Table",
            "",
            "Full path-reference rows are available in `materials/MANUSCRIPT_CROSS_REFERENCE_PATHS.csv`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export manuscript cross-reference and numeric consistency audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "MANUSCRIPT_CROSS_REFERENCE_AUDIT.json"
    out_md = materials / "MANUSCRIPT_CROSS_REFERENCE_AUDIT.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    path_csv, numeric_csv = write_csv(report, materials)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "path_csv": str(path_csv),
                "numeric_csv": str(numeric_csv),
                "status": report["summary"]["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
