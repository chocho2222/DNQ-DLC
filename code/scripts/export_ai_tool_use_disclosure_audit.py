#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


SCAN_FILES = [
    "manuscript/main.md",
    "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
    "materials/COVER_LETTER_DRAFT_PACKAGE.md",
    "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
    "materials/RESEARCH_RISK_AND_SAFETY.md",
    "materials/SIMULATION_TO_REAL_APPLICABILITY.md",
    "materials/POLICY_MODEL_CARD.md",
    "materials/FIGURE_PRODUCTION_HANDOFF.md",
    "materials/REPRODUCTION_GUIDE.md",
    "materials/DATA_CODE_AVAILABILITY.md",
]

PATTERNS = [
    ("ai_general", re.compile(r"\bAI\b|\bartificial intelligence\b", re.IGNORECASE)),
    ("vlm_term", re.compile(r"\bVLM\b|vision[- ]language", re.IGNORECASE)),
    ("generated_term", re.compile(r"\bgenerated\b|\bgenerative\b", re.IGNORECASE)),
    ("automated_term", re.compile(r"\bautomated\b|\bautomation\b|\bprogrammatic\b", re.IGNORECASE)),
    ("script_term", re.compile(r"\bscript(s)?\b|\bexporter(s)?\b", re.IGNORECASE)),
    ("tool_term", re.compile(r"\btool(s)?\b|\bsoftware\b|\bpackage\b", re.IGNORECASE)),
    ("chatgpt_openai_codex", re.compile(r"\bChatGPT\b|\bOpenAI\b|\bCodex\b", re.IGNORECASE)),
]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def clean(text):
    return " ".join(str(text).split())


def scan_file(root, rel):
    path = root / rel
    if not path.exists():
        return [], rel
    hits = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
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
    return hits, None


def row(
    row_id,
    area,
    status,
    files,
    evidence,
    author_action,
    boundary,
    disclosure_relevance,
    disclosure_owner,
    portal_instruction,
    prohibited_wording,
):
    return {
        "id": row_id,
        "area": area,
        "status": status,
        "files": files,
        "evidence": evidence,
        "author_action": author_action,
        "boundary": boundary,
        "disclosure_relevance": disclosure_relevance,
        "disclosure_owner": disclosure_owner,
        "portal_instruction": portal_instruction,
        "prohibited_wording": prohibited_wording,
    }


def build_report(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    script_audit = load_json(root / "materials" / "SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json")
    policy_card = load_json(root / "materials" / "POLICY_MODEL_CARD.json")
    figure_qc = load_json(root / "materials" / "FIGURE_TECHNICAL_QC.json")
    figure_handoff = load_json(root / "materials" / "FIGURE_PRODUCTION_HANDOFF.json")
    metadata = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    sim2real = load_json(root / "materials" / "SIMULATION_TO_REAL_APPLICABILITY.json")

    hits = []
    missing = []
    for rel in SCAN_FILES:
        rel_hits, missing_rel = scan_file(root, rel)
        hits.extend(rel_hits)
        if missing_rel:
            missing.append(missing_rel)

    hit_counts = {}
    for hit in hits:
        hit_counts[hit["pattern_id"]] = hit_counts.get(hit["pattern_id"], 0) + 1

    provenance_ratio = f"{provenance['complete_count']}/{len(provenance['artifacts'])}"
    script_ratio = f"{script_audit['summary']['passing_script_count']}/{script_audit['summary']['registered_script_count']}"
    model_rows = policy_card["summary"]["card_count"]
    figure_count = figure_qc["summary"]["figure_count"]
    author_required = metadata["summary"]["author_required_count"] + portal["summary"]["author_required_count"]

    rows = [
        row(
            "AI01_author_ai_assistance_declaration",
            "author_declaration",
            "author_required",
            "materials/SUBMISSION_METADATA_DISCLOSURES.csv; materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            "materials/SUBMISSION_METADATA_DRAFT.json; materials/ETHICS_DISCLOSURE_READINESS_PACK.md",
            "Authors must certify whether any AI-assisted writing, code generation, translation, or editing tools were used, and add the exact journal-required statement if applicable.",
            "The local package cannot infer private author tool use or certify author declarations.",
            "high",
            "authors",
            "Complete this row in the journal portal or cover letter only after authors certify any AI-assisted writing, editing, code, translation, or analysis support.",
            "Do not write that no AI/tool assistance was used unless all authors have explicitly certified it.",
        ),
        row(
            "AI02_non_vlm_policy_scope",
            "model_scope",
            "package_supported",
            "materials/POLICY_MODEL_CARD.md; materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "materials/POLICY_MODEL_CARD.json; materials/CLAIM_BOUNDARY_COMMUNICATION_PACK.json",
            f"The saved policy/model card covers {model_rows} simulator-state policies and explicitly excludes image, VLM, camera, LiDAR, and real-world sensor evidence.",
            "Do not describe the controller as VLM-based, perception-robust, or real-road ready.",
            "high",
            "package",
            "Use this row to state what the saved controllers are not: no VLM, no image-policy, no camera/LiDAR perception, and no real-road evidence.",
            "Do not label the method as VLM, vision-language autonomous driving, perception robust, or road deployable.",
        ),
        row(
            "AI03_automated_analysis_scripts",
            "analysis_automation",
            "package_supported",
            "tables/artifact_provenance.md; materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.md",
            "tables/artifact_provenance.json; materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json",
            f"Report that analyses, figures, manifests, and QC materials are generated by registered scripts when needed; provenance is {provenance_ratio} and script snapshots are {script_ratio}.",
            "Programmatic analysis is reproducibility infrastructure, not an AI-authorship claim.",
            "medium",
            "package",
            "If the journal asks about computational tools, describe registered scripts as reproducibility and QC infrastructure with provenance and script snapshots.",
            "Do not equate scripted analysis, manifest generation, or figure export with author-certified generative AI use.",
        ),
        row(
            "AI04_programmatic_figures_and_gifs",
            "visual_materials",
            "package_supported",
            "materials/FIGURE_PRODUCTION_HANDOFF.md; materials/FIGURE_TECHNICAL_QC.md; figures/",
            "materials/FIGURE_PRODUCTION_HANDOFF.json; materials/FIGURE_TECHNICAL_QC.json",
            f"Describe {figure_count} figures and rollout GIFs as programmatic exports from simulator rollouts and saved source data.",
            "Do not call qualitative GIFs quantitative evidence, and do not imply generative-image evidence unless authors separately add such assets.",
            "medium",
            "package",
            "Describe figures and GIFs as exports from simulator rollouts and source data; reserve any generative-media disclosure for author-added assets.",
            "Do not imply that GIFs prove pass rates or that generated visual assets are part of the evidence package.",
        ),
        row(
            "AI05_risk_and_scope_wording",
            "risk_scope",
            "package_supported",
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "materials/RESEARCH_RISK_AND_SAFETY.json; materials/SIMULATION_TO_REAL_APPLICABILITY.json",
            "Use simulator-only, non-VLM, no-public-road, and no-safety-certification wording in manuscript, portal, and cover-letter text.",
            "Risk/scope wording limits claims; it does not certify deployment safety.",
            "high",
            "package",
            "Copy simulator-only, non-VLM, no-public-road, and no-safety-certification language into any AI/safety/risk portal fields.",
            "Do not imply safety certification, real-world deployment readiness, or perception-stack validation.",
        ),
        row(
            "AI06_portal_and_cover_letter_copy",
            "submission_copy",
            "ready_with_author_completion",
            "materials/COVER_LETTER_DRAFT_PACKAGE.md; materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            "materials/PORTAL_COPYEDIT_LOCK_AUDIT.md; materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.md",
            "Before submission, authors should add any required AI/tool-use declaration to the portal or cover letter without weakening the claim boundaries.",
            "No tool-use statement should imply evidence that is absent from the simulator package.",
            "high",
            "authors_and_package",
            "Combine author-certified tool-use disclosure with the package-supported simulator boundary; keep private tool-use declarations separate from experimental evidence claims.",
            "Do not add broad autonomy, VLM, real-road, or public-deployment claims while completing disclosure text.",
        ),
    ]

    status_counts = {}
    for item in rows:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1

    return {
        "root": str(root),
        "title": "AI and Tool-Use Disclosure Audit",
        "purpose": (
            "Separate package-supported automation facts from author-certified AI/tool-use declarations for journal submission, "
            "while preserving the non-VLM, simulator-only claim boundary."
        ),
        "summary": {
            "status": "pass" if not missing else "review_required",
            "row_count": len(rows),
            "status_counts": status_counts,
            "scan_file_count": len(SCAN_FILES) - len(missing),
            "missing_scan_file_count": len(missing),
            "scan_hit_count": len(hits),
            "scan_hit_counts": hit_counts,
            "author_required_count": author_required,
            "artifact_provenance": provenance_ratio,
            "script_snapshot_status": script_audit["summary"]["status"],
            "figure_production_status": figure_handoff["summary"]["status"],
            "policy_model_card_complete": policy_card["summary"]["complete"],
            "risk_statement_available": bool(risk.get("risk_items")),
            "simulation_to_real_dimensions": len(sim2real.get("dimensions", [])),
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
        },
        "rows": rows,
        "scan_hits": hits,
        "missing_scan_files": missing,
        "interpretation": (
            "This audit is not a journal-specific AI policy statement and does not certify private author tool use. "
            "It gives authors a conservative checklist for completing AI/tool-use disclosures without adding unsupported claims."
        ),
    }


def write_csv(report, path):
    fields = [
        "id",
        "area",
        "status",
        "files",
        "evidence",
        "author_action",
        "boundary",
        "disclosure_relevance",
        "disclosure_owner",
        "portal_instruction",
        "prohibited_wording",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow({field: item.get(field, "") for field in fields})


def write_hits_csv(report, path):
    fields = ["file", "line", "pattern_id", "snippet"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["scan_hits"]:
            writer.writerow({field: item.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# AI and Tool-Use Disclosure Audit",
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
            "## Disclosure Rows",
            "",
            "| id | area | status | owner | files | author action | portal instruction | prohibited wording | boundary |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['id']} | {item['area']} | {item['status']} | {item['disclosure_owner']} | "
            f"`{item['files']}` | {item['author_action']} | {item['portal_instruction']} | "
            f"{item['prohibited_wording']} | {item['boundary']} |"
        )
    lines.extend(["", "## Scan Hit Summary", "", "| pattern | count |", "|---|---:|"])
    for key, value in sorted(report["summary"]["scan_hit_counts"].items()):
        lines.append(f"| {key} | {value} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export AI and tool-use disclosure audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "AI_TOOL_USE_DISCLOSURE_AUDIT.json"
    out_md = materials / "AI_TOOL_USE_DISCLOSURE_AUDIT.md"
    out_csv = materials / "AI_TOOL_USE_DISCLOSURE_AUDIT.csv"
    hits_csv = materials / "AI_TOOL_USE_DISCLOSURE_SCAN_HITS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    write_hits_csv(report, hits_csv)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "hits_csv": str(hits_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
