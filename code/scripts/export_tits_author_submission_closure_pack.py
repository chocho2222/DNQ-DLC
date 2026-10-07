#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
IEEE_COMPLIANCE = "outputs/tits_dynamic_graph/ieee_tits_compliance/ieee_tits_compliance_matrix.csv"
SUBMISSION_CHECKLIST = "outputs/tits_dynamic_graph/tits_submission_metadata_pack/tables/submission_portal_checklist.csv"
GITHUB_ACTIONS = "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tables/github_release_author_actions.csv"
PUBLIC_RELEASE = "outputs/tits_dynamic_graph/public_release_plan/public_release_plan_manifest.json"

PLACEHOLDER_SCAN_FILES = [
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/TITLE_ABSTRACT_KEYWORDS_DRAFT.md",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/COVER_LETTER_DRAFT.md",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/AUTHOR_DECLARATIONS_AND_AI_DISCLOSURE_DRAFT.md",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/DATA_CODE_AVAILABILITY_FINALIZATION.md",
    "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/CITATION_cff_DRAFT.md",
    "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_README_DRAFT.md",
    "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/MODEL_CARD_md_DRAFT.md",
    "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/DATA_CARD_md_DRAFT.md",
    "outputs/tits_dynamic_graph/reviewer_replication_packet/DATA_CODE_AVAILABILITY_DRAFT.md",
    "outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md",
]


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


def exists(path):
    return Path(path).exists()


def action_rows():
    return [
        {
            "action_id": "A01",
            "category": "data_archive",
            "author_action": "Create the public data archive and obtain DOI/accession.",
            "why_required": "Formal source data, model artifacts, figures/GIFs and checksums need a stable citation target.",
            "local_evidence_ready": "yes",
            "local_evidence_paths": "outputs/tits_dynamic_graph/public_release_plan/PUBLIC_RELEASE_PLAN.md; outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.md; outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md",
            "fields_or_files_to_update": "DATA_CODE_AVAILABILITY_FINALIZATION.md; DATA_CODE_AVAILABILITY_DRAFT.md; CITATION_cff_DRAFT.md; GITHUB_README_DRAFT.md",
            "completion_evidence": "Final DOI/accession and archive landing page URL.",
            "after_completion_rerun": "export_tits_submission_metadata_pack.py; export_tits_github_release_readiness_pack.py; export_tits_cross_reference_audit.py; export_tits_dynamic_graph_artifact_manifest.py; export_tits_final_readiness_dashboard.py",
            "status": "author_action_required",
        },
        {
            "action_id": "A02",
            "category": "code_release",
            "author_action": "Create the public code repository or release tag and record URL/commit.",
            "why_required": "Reviewers/readers need a stable route to scripts, configs, environment and minimal reproduction instructions.",
            "local_evidence_ready": "yes",
            "local_evidence_paths": "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_RELEASE_READINESS_PACK.md; outputs/tits_dynamic_graph/public_release_plan/public_release_file_plan.csv",
            "fields_or_files_to_update": "GITHUB_README_DRAFT.md; CITATION_cff_DRAFT.md; DATA_CODE_AVAILABILITY_FINALIZATION.md; REVIEWER_REPLICATION_README.md",
            "completion_evidence": "Repository URL, release tag, commit hash and access policy.",
            "after_completion_rerun": "export_tits_github_release_readiness_pack.py; export_tits_public_release_plan.py; export_tits_cross_reference_audit.py; export_tits_reproducibility_capsule.py",
            "status": "author_action_required",
        },
        {
            "action_id": "A03",
            "category": "license",
            "author_action": "Confirm code, model, GIF, track and data license choices.",
            "why_required": "Local files can route artifacts, but legal permission and final license text are author-owned.",
            "local_evidence_ready": "partial",
            "local_evidence_paths": "LICENSE; outputs/tits_dynamic_graph/public_release_plan/PUBLIC_RELEASE_PLAN.md; outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/MODEL_CARD_md_DRAFT.md; outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/DATA_CARD_md_DRAFT.md",
            "fields_or_files_to_update": "LICENSE; CITATION.cff; MODEL_CARD; DATA_CARD; README; archive metadata",
            "completion_evidence": "Approved license identifiers and any third-party track/data notices.",
            "after_completion_rerun": "export_tits_github_release_readiness_pack.py; export_tits_public_release_plan.py; export_tits_claim_language_audit.py",
            "status": "author_action_required",
        },
        {
            "action_id": "A04",
            "category": "ieee_template",
            "author_action": "Convert drafts into the current IEEE T-ITS manuscript template and check page/figure/table formatting.",
            "why_required": "Local drafts are evidence-driven text, not final IEEE double-column submission files.",
            "local_evidence_ready": "yes",
            "local_evidence_paths": "outputs/tits_dynamic_graph/tits_manuscript_package/materials/METHODS_DRAFT.md; outputs/tits_dynamic_graph/tits_manuscript_package/materials/RESULTS_DRAFT.md; outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/MANUSCRIPT_SUPPLEMENT_NAVIGATOR.md",
            "fields_or_files_to_update": "Final manuscript PDF/LaTeX/Word; figure captions; supplementary numbering",
            "completion_evidence": "Compiled manuscript PDF and supplement files matching the live IEEE/T-ITS portal requirements.",
            "after_completion_rerun": "export_tits_manuscript_numeric_trace_audit.py; export_tits_claim_evidence_completeness_audit.py; export_tits_claim_language_audit.py; export_tits_cross_reference_audit.py",
            "status": "author_action_required",
        },
        {
            "action_id": "A05",
            "category": "author_metadata",
            "author_action": "Finalize author names, affiliations, ORCID, corresponding author and contributions.",
            "why_required": "No final author metadata are stored in the technical package.",
            "local_evidence_ready": "no",
            "local_evidence_paths": "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/AUTHOR_DECLARATIONS_AND_AI_DISCLOSURE_DRAFT.md",
            "fields_or_files_to_update": "ScholarOne author fields; manuscript front matter; cover letter; author declarations",
            "completion_evidence": "Author-approved metadata and ORCID entries.",
            "after_completion_rerun": "export_tits_submission_metadata_pack.py; export_tits_claim_language_audit.py",
            "status": "author_action_required",
        },
        {
            "action_id": "A06",
            "category": "funding_conflict_ethics",
            "author_action": "Finalize funding, conflicts of interest, ethics/safety and AI-tool disclosure statements.",
            "why_required": "Draft disclosure text exists, but exact author/project details must be confirmed by authors.",
            "local_evidence_ready": "partial",
            "local_evidence_paths": "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/AUTHOR_DECLARATIONS_AND_AI_DISCLOSURE_DRAFT.md; outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/COVER_LETTER_DRAFT.md",
            "fields_or_files_to_update": "Author declarations; cover letter; ScholarOne declarations; manuscript acknowledgements",
            "completion_evidence": "Author-approved declarations and portal entries.",
            "after_completion_rerun": "export_tits_submission_metadata_pack.py; export_tits_claim_language_audit.py; export_tits_final_readiness_dashboard.py",
            "status": "author_action_required",
        },
        {
            "action_id": "A07",
            "category": "portal_metadata",
            "author_action": "Enter final title, abstract, keywords, classifications and suggested/excluded reviewers in the live portal.",
            "why_required": "Local metadata drafts cannot prove portal completion.",
            "local_evidence_ready": "yes",
            "local_evidence_paths": "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/TITLE_ABSTRACT_KEYWORDS_DRAFT.md; outputs/tits_dynamic_graph/tits_submission_metadata_pack/tables/keyword_plan.csv; outputs/tits_dynamic_graph/tits_submission_metadata_pack/tables/submission_portal_checklist.csv",
            "fields_or_files_to_update": "ScholarOne portal fields; cover letter; final metadata pack",
            "completion_evidence": "Portal preview/export or author confirmation.",
            "after_completion_rerun": "export_tits_submission_metadata_pack.py; export_tits_claim_evidence_completeness_audit.py",
            "status": "author_action_required",
        },
        {
            "action_id": "A08",
            "category": "supplement_selection",
            "author_action": "Select final supplementary tables, GIFs and source-data files for upload.",
            "why_required": "Local package contains all evidence; authors must choose final upload bundle size and journal-compliant supplement structure.",
            "local_evidence_ready": "yes",
            "local_evidence_paths": "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/MANUSCRIPT_SUPPLEMENT_NAVIGATOR.md; outputs/tits_dynamic_graph/tits_figure_source_data_audit/materials/FIGURE_SOURCE_DATA_AUDIT.md; outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.md",
            "fields_or_files_to_update": "Supplementary file list; data archive file list; final manuscript citations",
            "completion_evidence": "Final supplement upload map and archive bundle manifest.",
            "after_completion_rerun": "export_tits_manuscript_supplement_navigator.py; export_tits_figure_source_data_audit.py; export_tits_cross_reference_audit.py",
            "status": "author_action_required",
        },
        {
            "action_id": "A09",
            "category": "final_freeze",
            "author_action": "After all author edits and uploads, rerun final checksums and freeze the submission evidence state.",
            "why_required": "Any DOI, URL, template or author-text edit changes the final evidence package.",
            "local_evidence_ready": "yes",
            "local_evidence_paths": "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.md; outputs/tits_dynamic_graph/final_readiness_dashboard/FINAL_READINESS_DASHBOARD.md",
            "fields_or_files_to_update": "Artifact manifest; public release plan; final readiness dashboard; final archive README",
            "completion_evidence": "Fresh checksum manifest, public release audit PASS and final readiness dashboard after author edits.",
            "after_completion_rerun": "export_tits_dynamic_graph_artifact_manifest.py; export_tits_public_release_plan.py; export_tits_cross_reference_audit.py; export_tits_final_readiness_dashboard.py",
            "status": "author_action_required",
        },
    ]


def scan_placeholders(root):
    patterns = [
        re.compile(r"\[[^\]\n]*(?:DOI|URL|author|Author|ORCID|license|License|repository|archive|accession|funding|conflict|affiliation|release tag)[^\]\n]*\]"),
        re.compile(r"\b(?:TBD|TODO|PLACEHOLDER|INSERT|Insert)\b[^\n]*"),
        re.compile(r"(?:Author-side action before submission:|Replace all|replace TODO)[^\n]*"),
    ]
    rows = []
    for rel in PLACEHOLDER_SCAN_FILES:
        path = root / rel
        if not path.exists():
            rows.append(
                {
                    "source_file": rel,
                    "line": "",
                    "placeholder": "",
                    "status": "missing_scan_file",
                    "context": "",
                }
            )
            continue
        text = path.read_text(encoding="utf-8")
        for idx, line in enumerate(text.splitlines(), start=1):
            for pattern in patterns:
                for match in pattern.finditer(line):
                    rows.append(
                        {
                            "source_file": rel,
                            "line": idx,
                            "placeholder": match.group(0),
                            "status": "author_fill_required",
                            "context": line.strip()[:500],
                        }
                    )
    return rows


def evidence_rows(root, rows):
    out = []
    for row in rows:
        for rel in [item.strip() for item in row["local_evidence_paths"].split(";") if item.strip()]:
            out.append(
                {
                    "action_id": row["action_id"],
                    "evidence_path": rel,
                    "exists": (root / rel).exists(),
                }
            )
    return out


def regeneration_rows():
    commands = [
        ("submission_metadata", "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_submission_metadata_pack.py --out-dir outputs/tits_dynamic_graph/tits_submission_metadata_pack"),
        ("github_release_readiness", "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_github_release_readiness_pack.py --out-dir outputs/tits_dynamic_graph/tits_github_release_readiness_pack"),
        ("claim_evidence", "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_claim_evidence_completeness_audit.py --out-dir outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit"),
        ("claim_language", "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_claim_language_audit.py --out-dir outputs/tits_dynamic_graph/tits_claim_language_audit"),
        ("cross_reference", "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_cross_reference_audit.py --out-dir outputs/tits_dynamic_graph/tits_cross_reference_audit"),
        ("artifact_manifest", "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_dynamic_graph_artifact_manifest.py --root . --out-dir outputs/tits_dynamic_graph/artifact_manifest"),
        ("public_release", "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_public_release_plan.py --out-dir outputs/tits_dynamic_graph/public_release_plan"),
        ("final_readiness", "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_final_readiness_dashboard.py --out-dir outputs/tits_dynamic_graph/final_readiness_dashboard"),
    ]
    return [{"step_order": i + 1, "command_id": name, "command": command} for i, (name, command) in enumerate(commands)]


def build_report(root):
    actions = action_rows()
    placeholders = scan_placeholders(root)
    evidence = evidence_rows(root, actions)
    regeneration = regeneration_rows()
    final_readiness = read_json(root / FINAL_READINESS)
    ieee = read_csv(root / IEEE_COMPLIANCE)
    submission = read_csv(root / SUBMISSION_CHECKLIST)
    github = read_csv(root / GITHUB_ACTIONS)
    release = read_json(root / PUBLIC_RELEASE)
    missing_evidence = [row for row in evidence if not row["exists"]]
    summary = {
        "status": "pass" if not missing_evidence else "review_required",
        "author_action_count": len(actions),
        "placeholder_count": len([row for row in placeholders if row["status"] == "author_fill_required"]),
        "missing_scan_file_count": len([row for row in placeholders if row["status"] == "missing_scan_file"]),
        "missing_evidence_count": len(missing_evidence),
        "final_readiness": f"{final_readiness.get('pass_count', 'NA')}/{final_readiness.get('gate_count', 'NA')}",
        "ieee_compliance_rows": len(ieee),
        "submission_checklist_rows": len(submission),
        "github_author_action_rows": len(github),
        "public_release_status": release.get("status", ""),
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "author_actions": actions,
        "placeholder_inventory": placeholders,
        "evidence_rows": evidence,
        "regeneration_rows": regeneration,
        "note": "This pack tracks author-owned closure actions. Open author actions are expected and do not contradict local reproducibility readiness.",
    }


def build_markdown(report):
    lines = [
        "# T-ITS Author-Owned Submission Closure Pack",
        "",
        "该包把本地无法自动完成、但投稿前必须由作者确认的事项集中成闭环表。它不表示这些事项已完成；它证明当前技术材料已经准备好支撑作者完成 DOI、license、模板、声明和上传动作。",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Author-Owned Actions",
            "",
            "| ID | Category | Action | Local evidence | Completion evidence | Rerun after completion |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["author_actions"]:
        lines.append(
            f"| {row['action_id']} | {row['category']} | {row['author_action']} | {row['local_evidence_ready']} | {row['completion_evidence']} | {row['after_completion_rerun']} |"
        )
    lines.extend(
        [
            "",
            "## Placeholder Inventory",
            "",
            "| File | Line | Placeholder | Status |",
            "|---|---:|---|---|",
        ]
    )
    for row in report["placeholder_inventory"][:80]:
        lines.append(f"| `{row['source_file']}` | {row['line']} | `{row['placeholder']}` | {row['status']} |")
    if len(report["placeholder_inventory"]) > 80:
        lines.append(f"| ... | ... | ... | {len(report['placeholder_inventory']) - 80} additional rows in CSV |")
    lines.extend(
        [
            "",
            "## Recommended Closure Order",
            "",
            "1. Confirm authorship, funding, conflicts, AI disclosure and license.",
            "2. Create public code release and data archive DOI/accession.",
            "3. Replace placeholders in submission metadata, data/code availability, citation and README drafts.",
            "4. Convert manuscript into the current IEEE T-ITS template and finalize figures/supplementary files.",
            "5. Rerun the regeneration commands table, then freeze checksums and final readiness.",
            "",
            "## Boundary",
            "",
            "本包是作者侧闭环索引，不替代法律/license 审查、ScholarOne 实际提交、IEEE 当前模板检查或最终通讯作者确认。",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export author-owned submission closure pack for T-ITS package.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_author_submission_closure_pack")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    paths = {
        "pack_md": write_text(materials / "AUTHOR_SUBMISSION_CLOSURE_PACK.md", build_markdown(report)),
        "pack_json": write_json(materials / "AUTHOR_SUBMISSION_CLOSURE_PACK.json", report),
        "author_actions_csv": write_csv(
            tables / "author_owned_action_matrix.csv",
            report["author_actions"],
            [
                "action_id",
                "category",
                "author_action",
                "why_required",
                "local_evidence_ready",
                "local_evidence_paths",
                "fields_or_files_to_update",
                "completion_evidence",
                "after_completion_rerun",
                "status",
            ],
        ),
        "placeholder_inventory_csv": write_csv(
            tables / "author_placeholder_inventory.csv",
            report["placeholder_inventory"],
            ["source_file", "line", "placeholder", "status", "context"],
        ),
        "evidence_csv": write_csv(
            tables / "author_action_evidence_checks.csv",
            report["evidence_rows"],
            ["action_id", "evidence_path", "exists"],
        ),
        "regeneration_csv": write_csv(
            tables / "post_author_action_regeneration_commands.csv",
            report["regeneration_rows"],
            ["step_order", "command_id", "command"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_author_submission_closure_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
