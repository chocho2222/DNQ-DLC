#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


SUBMISSION_METADATA = "outputs/tits_dynamic_graph/tits_submission_metadata_pack/tits_submission_metadata_pack_manifest.json"
DECLARATIONS_MD = "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/AUTHOR_DECLARATIONS_AND_AI_DISCLOSURE_DRAFT.md"
SUBMISSION_DRY_RUN = "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/tits_submission_dry_run_checklist_manifest.json"
AUTHOR_CLOSURE = "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tits_author_submission_closure_pack_manifest.json"
AUTHOR_OWNED = "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/tits_author_owned_submission_integrity_audit_manifest.json"
CLAIM_LANGUAGE = "outputs/tits_dynamic_graph/tits_claim_language_audit/tits_claim_language_audit_manifest.json"
CLAIM_EVIDENCE = "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/tits_claim_evidence_completeness_audit_manifest.json"
EXTERNAL_VALIDITY = "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/tits_external_validity_boundary_audit_manifest.json"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"

SCAN_FILES = [
    "README.md",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/AUTHOR_DECLARATIONS_AND_AI_DISCLOSURE_DRAFT.md",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/IEEE_TITS_SUBMISSION_METADATA_PACK.md",
    "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/materials/SUBMISSION_DRY_RUN_CHECKLIST.md",
    "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/materials/AUTHOR_SUBMISSION_CLOSURE_PACK.md",
    "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.md",
    "outputs/tits_dynamic_graph/tits_claim_language_audit/materials/CLAIM_LANGUAGE_AUDIT.md",
    "outputs/tits_dynamic_graph/reviewer_replication_packet/SUBMISSION_READINESS_CHECKLIST.md",
]

PATTERNS = [
    ("ai_term", re.compile(r"\bAI\b|artificial intelligence|AI-tool|AI tools?", re.IGNORECASE)),
    ("tool_term", re.compile(r"tool-use|tools?|software|script|programmatic", re.IGNORECASE)),
    ("author_action", re.compile(r"author-side|authors? must|authors? should|作者|待确认|placeholder", re.IGNORECASE)),
    ("unsupported_ai_scope", re.compile(r"\bVLM\b|vision[- ]language|camera|LiDAR|real[- ]road|deployment|safety certification", re.IGNORECASE)),
    ("prohibited_overclaim", re.compile(r"AI[- ]?driven proof|autonomous deployment ready|certified safe|real[- ]world guaranteed", re.IGNORECASE)),
]

OFFICIAL_SOURCES = [
    {
        "source_id": "IEEE_AI",
        "title": "IEEE Author Guidelines for Artificial Intelligence (AI)-Generated Text",
        "url": "https://open.ieee.org/author-guidelines-for-artificial-intelligence-ai-generated-text/",
        "local_use": "AI-generated text/content disclosure wording and author-side declaration checklist.",
        "audit_boundary": "The package records a draft and checklist only; final authors must identify exact tools, affected sections and level of use.",
    },
    {
        "source_id": "IEEE_AUTHOR_CENTER_AI",
        "title": "IEEE Author Center submission and peer-review policies",
        "url": "https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/",
        "local_use": "Cross-checks that AI-generated content disclosure is treated as a submission-ethics item.",
        "audit_boundary": "The audit does not replace current portal fields or final IEEE production checks.",
    },
    {
        "source_id": "TITS_AUTHOR_INFO",
        "title": "IEEE Transactions on Intelligent Transportation Systems author information",
        "url": "https://ieee-itss.org/pub/t-its/",
        "local_use": "T-ITS target-journal scope and author-material routing.",
        "audit_boundary": "T-ITS page/portal details and editor metadata must still be checked by authors at submission time.",
    },
]


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path):
    path = Path(path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


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


def clean(text):
    return " ".join(str(text).split())


def scan_files(root):
    hits = []
    missing = []
    for rel in SCAN_FILES:
        path = root / rel
        if not path.exists():
            missing.append(rel)
            continue
        for line_no, line in enumerate(read_text(path).splitlines(), start=1):
            for pattern_id, pattern in PATTERNS:
                if pattern.search(line):
                    hits.append(
                        {
                            "file": rel,
                            "line": line_no,
                            "pattern_id": pattern_id,
                            "snippet": clean(line)[:260],
                        }
                    )
    return hits, missing


def build_rows(root, manifests, declarations_text):
    metadata = manifests["submission_metadata"]
    dry_run = manifests["submission_dry_run"]
    author_closure = manifests["author_closure"]
    author_owned = manifests["author_owned"]
    claim_language = manifests["claim_language"]
    claim_evidence = manifests["claim_evidence"]
    external_validity = manifests["external_validity"]
    has_declaration = bool(declarations_text.strip())
    has_placeholder = "exact AI systems used" in declarations_text or "AI-tool disclosure" in declarations_text
    has_author_boundary = "Author-side action before submission" in declarations_text
    final = manifests["final_readiness"]
    final_has_dashboard_shape = bool(final.get("status") and final.get("pass_count") is not None and final.get("gate_count") is not None)
    return [
        {
            "check_id": "AI01_official_sources_registered",
            "status": "pass" if len(OFFICIAL_SOURCES) == 3 else "review_required",
            "owner": "package",
            "evidence": "official_source_rows.csv",
            "observation": f"{len(OFFICIAL_SOURCES)} official/source rows recorded",
            "author_action": "Before final submission, authors should verify portal wording against the live IEEE/T-ITS pages.",
            "boundary": "Official URLs are evidence-routing aids, not proof that portal fields have been completed.",
        },
        {
            "check_id": "AI02_declaration_draft_exists",
            "status": "pass" if has_declaration and has_placeholder else "review_required",
            "owner": "authors",
            "evidence": DECLARATIONS_MD,
            "observation": f"declaration_file_exists={(root / DECLARATIONS_MD).exists()}; placeholder_detected={has_placeholder}",
            "author_action": "Replace the placeholder with exact AI systems, affected sections and level of use after all authors confirm.",
            "boundary": "The local draft does not certify private author tool use.",
        },
        {
            "check_id": "AI03_author_action_visible",
            "status": "pass" if has_author_boundary and author_closure.get("status") == "pass" and author_owned.get("status") == "pass" else "review_required",
            "owner": "authors",
            "evidence": f"{AUTHOR_CLOSURE}; {AUTHOR_OWNED}; {DECLARATIONS_MD}",
            "observation": f"author_closure={author_closure.get('status')}; author_owned={author_owned.get('status')}; declaration_author_boundary={has_author_boundary}",
            "author_action": "Keep AI disclosure as an author-owned finalization task until real submission fields are completed.",
            "boundary": "PASS means the task is visible, not that the final declaration is completed.",
        },
        {
            "check_id": "AI04_no_ai_scope_overclaim",
            "status": "pass" if claim_language.get("status") == "pass" and external_validity.get("status") == "pass" else "review_required",
            "owner": "package",
            "evidence": f"{CLAIM_LANGUAGE}; {EXTERNAL_VALIDITY}",
            "observation": f"claim_language={claim_language.get('status')}; external_validity={external_validity.get('status')}",
            "author_action": "When editing the final manuscript, keep non-VLM, simulator-only and no-real-road-safety-certification boundaries.",
            "boundary": "This controller is not validated as a VLM, perception stack or real-road deployment system.",
        },
        {
            "check_id": "AI05_submission_readiness_crosswalk",
            "status": "pass" if metadata.get("status") == "pass" and dry_run.get("status") == "pass" and final_has_dashboard_shape else "review_required",
            "owner": "authors_and_package",
            "evidence": f"{SUBMISSION_METADATA}; {SUBMISSION_DRY_RUN}; {FINAL_READINESS}",
            "observation": f"metadata={metadata.get('status')}; dry_run={dry_run.get('status')}; final={final.get('status')} {final.get('pass_count')}/{final.get('gate_count')}",
            "author_action": "Complete ScholarOne/IEEE portal fields, conflict/funding/ORCID metadata and AI-tool disclosure immediately before submission.",
            "boundary": "Final dashboard status is recorded as context only to avoid a circular readiness dependency; local readiness does not create a journal receipt or author-certified disclosure.",
        },
        {
            "check_id": "AI06_claim_evidence_alignment",
            "status": "pass" if claim_evidence.get("status") == "pass" else "review_required",
            "owner": "package",
            "evidence": CLAIM_EVIDENCE,
            "observation": f"claim_evidence={claim_evidence.get('status')}",
            "author_action": "Do not use AI disclosure language to imply additional experimental evidence beyond the frozen source data.",
            "boundary": "AI/tool-use disclosure is a publication-ethics item, not an algorithmic result.",
        },
    ]


def build_report(root):
    manifests = {
        "submission_metadata": read_json(root / SUBMISSION_METADATA),
        "submission_dry_run": read_json(root / SUBMISSION_DRY_RUN),
        "author_closure": read_json(root / AUTHOR_CLOSURE),
        "author_owned": read_json(root / AUTHOR_OWNED),
        "claim_language": read_json(root / CLAIM_LANGUAGE),
        "claim_evidence": read_json(root / CLAIM_EVIDENCE),
        "external_validity": read_json(root / EXTERNAL_VALIDITY),
        "final_readiness": read_json(root / FINAL_READINESS),
    }
    declarations_text = read_text(root / DECLARATIONS_MD)
    scan_hits, missing_scan_files = scan_files(root)
    rows = build_rows(root, manifests, declarations_text)
    prohibited_hits = [hit for hit in scan_hits if hit["pattern_id"] == "prohibited_overclaim"]
    if prohibited_hits:
        rows.append(
            {
                "check_id": "AI07_prohibited_overclaim_scan",
                "status": "review_required",
                "owner": "package",
                "evidence": "tables/ai_tool_use_scan_hits.csv",
                "observation": f"prohibited_hits={len(prohibited_hits)}",
                "author_action": "Remove prohibited AI/deployment overclaims or add explicit boundary context.",
                "boundary": "No AI/tool disclosure may enlarge the experimental claim scope.",
            }
        )
    else:
        rows.append(
            {
                "check_id": "AI07_prohibited_overclaim_scan",
                "status": "pass",
                "owner": "package",
                "evidence": "tables/ai_tool_use_scan_hits.csv",
                "observation": "prohibited_hits=0",
                "author_action": "Re-run after editing submission-facing text.",
                "boundary": "Absence of these exact strings is not a substitute for author review.",
            }
        )
    failed = [row for row in rows if row["status"] != "pass"]
    pattern_counts = {}
    for hit in scan_hits:
        pattern_counts[hit["pattern_id"]] = pattern_counts.get(hit["pattern_id"], 0) + 1
    summary = {
        "status": "pass" if not failed and not missing_scan_files else "review_required",
        "check_count": len(rows),
        "pass_count": sum(1 for row in rows if row["status"] == "pass"),
        "review_required_count": len(failed),
        "official_source_count": len(OFFICIAL_SOURCES),
        "scan_file_count": len(SCAN_FILES) - len(missing_scan_files),
        "missing_scan_file_count": len(missing_scan_files),
        "scan_hit_count": len(scan_hits),
        "pattern_counts": pattern_counts,
        "author_owned_checks": sum(1 for row in rows if "author" in row["owner"]),
        "final_readiness": f"{manifests['final_readiness'].get('pass_count')}/{manifests['final_readiness'].get('gate_count')}",
        "boundary": "This audit prepares an IEEE/T-ITS AI/tool-use disclosure route; final exact tool-use statements remain author-certified.",
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "official_sources": OFFICIAL_SOURCES,
        "rows": rows,
        "scan_hits": scan_hits,
        "missing_scan_files": missing_scan_files,
    }


def build_markdown(report):
    s = report["summary"]
    lines = [
        "# T-ITS AI/Tool-Use Disclosure Audit",
        "",
        "该审计用于把 IEEE/T-ITS 投稿中的 AI/工具使用披露准备工作从算法证据中分离出来：本地包可以证明披露草稿、作者侧动作、claim 边界和禁止表述检查均已纳入证据链；但最终使用了哪些 AI 系统、涉及哪些 manuscript sections、使用程度如何，必须由作者在投稿前确认。",
        "",
        "## Summary",
        "",
    ]
    for key, value in s.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Official/Policy Sources", "", "| source | title | url | local use | boundary |", "|---|---|---|---|---|"])
    for row in report["official_sources"]:
        lines.append(f"| {row['source_id']} | {row['title']} | {row['url']} | {row['local_use']} | {row['audit_boundary']} |")
    lines.extend(["", "## Audit Checks", "", "| check | status | owner | evidence | observation | author action | boundary |", "|---|---|---|---|---|---|---|"])
    for row in report["rows"]:
        lines.append(
            f"| {row['check_id']} | {row['status']} | {row['owner']} | `{row['evidence']}` | {row['observation']} | {row['author_action']} | {row['boundary']} |"
        )
    lines.extend(["", "## Safe Wording", ""])
    lines.append("- 可以写：AI/tool-use disclosure is author-owned and must be finalized with exact tools, affected sections, and level of use before submission.")
    lines.append("- 可以写：Programmatic scripts generated figures, manifests, QA tables, and audit reports from saved source data.")
    lines.append("- 不应写：AI tools generated or validated experimental results, or the method is VLM/perception/real-road ready.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export T-ITS AI/tool-use disclosure audit.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit")
    args = parser.parse_args()
    root = Path.cwd()
    out_dir = Path(args.out_dir)
    (out_dir / "materials").mkdir(parents=True, exist_ok=True)
    (out_dir / "tables").mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    paths = {
        "audit_md": write_text(out_dir / "materials" / "AI_TOOL_USE_DISCLOSURE_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(out_dir / "materials" / "AI_TOOL_USE_DISCLOSURE_AUDIT.json", report),
        "checks_csv": write_csv(
            out_dir / "tables" / "ai_tool_use_disclosure_checks.csv",
            report["rows"],
            ["check_id", "status", "owner", "evidence", "observation", "author_action", "boundary"],
        ),
        "official_sources_csv": write_csv(
            out_dir / "tables" / "ai_tool_use_official_sources.csv",
            report["official_sources"],
            ["source_id", "title", "url", "local_use", "audit_boundary"],
        ),
        "scan_hits_csv": write_csv(
            out_dir / "tables" / "ai_tool_use_scan_hits.csv",
            report["scan_hits"],
            ["file", "line", "pattern_id", "snippet"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_ai_tool_use_disclosure_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
