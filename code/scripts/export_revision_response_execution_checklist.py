#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


SECTION_MAP = {
    "RQ1_main_claim_strength": ("title_abstract_highlights", "Abstract, highlights, limitations"),
    "RQ2_baseline_strength": ("results_baselines", "Results baseline comparison"),
    "RQ3_oracle_deployability": ("results_oracle_boundary", "Results and figure legends"),
    "RQ4_heldout3_reuse": ("methods_seed_partitions", "Methods seed partitions"),
    "RQ5_failure_visibility": ("results_failure_analysis", "Failure analysis and limitations"),
    "RQ6_sample_size": ("statistics_limitations", "Statistical reporting and limitations"),
    "RQ7_selector_rule": ("methods_selector", "Online selector methods"),
    "RQ8_endpoint_dependence": ("methods_endpoint", "Endpoint definition and sensitivity"),
    "RQ9_visual_evidence": ("figures_visual_evidence", "Figure legends and qualitative examples"),
    "RQ10_reproducibility": ("data_code_reproducibility", "Data/code availability and Methods"),
    "RQ11_response_scope": ("response_letter_guardrail", "Response letter and revised cover letter"),
    "RQ12_quick_review_route": ("reviewer_navigation", "Supplementary navigator or cover-letter note"),
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def split_paths(value):
    return [item.strip() for item in str(value).split(";") if item.strip()]


def evidence_complete(root, value):
    paths = split_paths(value)
    return all((root / path).exists() for path in paths), paths


def action_status(seed_status, complete):
    if seed_status != "ready":
        return "review_required"
    return "ready_for_author_revision" if complete else "evidence_missing"


def build_report(root):
    seeds = load_json(root / "materials" / "REVIEWER_RESPONSE_SEED_PACK.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    frontmatter = load_json(root / "materials" / "EDITORIAL_FRONTMATTER_CLAIM_AUDIT.json")
    boundary = load_json(root / "materials" / "CLAIM_BOUNDARY_COMMUNICATION_PACK.json")

    rows = []
    for index, seed in enumerate(seeds["rows"], start=1):
        section_key, section_label = SECTION_MAP.get(seed["id"], ("author_revision", "Author-selected manuscript section"))
        complete, paths = evidence_complete(root, seed["evidence"])
        rows.append(
            {
                "order": index,
                "id": seed["id"],
                "revision_target": section_key,
                "manuscript_section_placeholder": section_label,
                "line_reference_placeholder": "author_to_fill_after_revision",
                "likely_critique": seed["likely_critique"],
                "revision_action": seed["escalation_or_revision_action"],
                "response_seed": seed["response_seed"],
                "evidence": seed["evidence"],
                "evidence_complete": complete,
                "evidence_paths": paths,
                "claim_boundary": seed["claim_boundary"],
                "author_completion_required": (
                    "Insert final manuscript line numbers after revision; adapt response tone; "
                    "verify no claim is strengthened beyond the boundary."
                ),
                "post_edit_check": (
                    "Rerun claim/front-matter audits and smoke tests after manuscript, cover-letter, "
                    "portal, or response-letter edits."
                ),
                "status": action_status(seed["status"], complete),
            }
        )

    status_counts = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    return {
        "root": str(root),
        "title": "Revision Response Execution Checklist",
        "purpose": (
            "Convert likely reviewer/editor critiques into a conservative revision-execution checklist "
            "with evidence routes, line-reference placeholders, and claim-boundary locks."
        ),
        "summary": {
            "status": "pass" if all(row["status"] == "ready_for_author_revision" for row in rows) else "review_required",
            "row_count": len(rows),
            "status_counts": status_counts,
            "evidence_incomplete_count": sum(1 for row in rows if not row["evidence_complete"]),
            "line_references_pending_count": len(rows),
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "frontmatter_claim_audit_status": frontmatter["summary"]["status"],
            "claim_boundary_status": boundary["summary"]["status"],
        },
        "rows": rows,
        "interpretation": (
            "This is not a finished rebuttal letter. Authors must add real manuscript line references "
            "after revision and keep all response wording within the listed simulator-only and diagnostic boundaries."
        ),
    }


def write_csv(report, path):
    fields = [
        "order",
        "id",
        "revision_target",
        "manuscript_section_placeholder",
        "line_reference_placeholder",
        "likely_critique",
        "revision_action",
        "response_seed",
        "evidence",
        "evidence_complete",
        "claim_boundary",
        "author_completion_required",
        "post_edit_check",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# Revision Response Execution Checklist",
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
            "## Checklist",
            "",
            "| id | target | status | line placeholder | action | evidence | boundary |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['id']} | {row['manuscript_section_placeholder']} | {row['status']} | "
            f"{row['line_reference_placeholder']} | {row['revision_action']} | "
            f"`{row['evidence']}` | {row['claim_boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export revision response execution checklist.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "REVISION_RESPONSE_EXECUTION_CHECKLIST.json"
    out_md = materials / "REVISION_RESPONSE_EXECUTION_CHECKLIST.md"
    out_csv = materials / "REVISION_RESPONSE_EXECUTION_CHECKLIST.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
