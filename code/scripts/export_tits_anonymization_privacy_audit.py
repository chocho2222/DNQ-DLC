#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


SCAN_DIRS = [
    "outputs/tits_dynamic_graph/tits_manuscript_package",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack",
    "outputs/tits_dynamic_graph/tits_github_release_readiness_pack",
    "outputs/tits_dynamic_graph/reviewer_replication_packet",
    "outputs/tits_dynamic_graph/tits_author_submission_closure_pack",
    "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist",
    "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack",
    "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack",
    "outputs/tits_dynamic_graph/public_release_plan",
    "outputs/tits_dynamic_graph/final_readiness_dashboard",
]
SCAN_SUFFIXES = {".md", ".csv", ".json", ".sh", ".draft"}
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
AUTHOR_CLOSURE = "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tits_author_submission_closure_pack_manifest.json"
DRY_RUN = "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/tits_submission_dry_run_checklist_manifest.json"

PATTERNS = [
    {
        "risk_id": "A01",
        "pattern": r"/home/itrc/VLM/racing/overtake/multi_car_racing",
        "risk_type": "absolute_workspace_path",
        "severity": "review",
        "recommended_action": "For public/reviewer release, replace with repository-relative paths or a documented project root placeholder.",
    },
    {
        "risk_id": "A02",
        "pattern": r"/home/itrc/\.conda/envs/vlm_planner/bin/python",
        "risk_type": "local_python_interpreter_path",
        "severity": "review",
        "recommended_action": "For public commands, prefer `python` after activating the released environment, or document this as a local server command.",
    },
    {
        "risk_id": "A03",
        "pattern": r"/tmp/[A-Za-z0-9_./-]+",
        "risk_type": "temporary_output_path",
        "severity": "low",
        "recommended_action": "Temporary smoke-test paths are acceptable if clearly marked as disposable outputs.",
    },
    {
        "risk_id": "A04",
        "pattern": r"\bTODO(?:/[A-Z0-9_ -]+)?\b",
        "risk_type": "author_placeholder",
        "severity": "author_action",
        "recommended_action": "Replace before real repository, DOI, license or author metadata publication.",
    },
    {
        "risk_id": "A05",
        "pattern": r"\[[^\]\n]*(?:Author|author|ORCID|DOI|URL|license|License|repository|funding|affiliation|accession)[^\]\n]*\]",
        "risk_type": "author_placeholder",
        "severity": "author_action",
        "recommended_action": "Replace before final submission or public data/code deposition.",
    },
    {
        "risk_id": "A06",
        "pattern": r"https://github\.com/TODO/TODO|https://doi\.org/TODO",
        "risk_type": "unresolved_public_identifier",
        "severity": "author_action",
        "recommended_action": "Replace with final repository URL or DOI/accession after release/deposition.",
    },
]

MANUSCRIPT_TEXT_SEGMENTS = (
    "tits_manuscript_package/materials/ABSTRACT",
    "tits_manuscript_package/materials/METHODS",
    "tits_manuscript_package/materials/RESULTS",
    "tits_manuscript_package/materials/LIMITATIONS",
    "tits_submission_metadata_pack/materials/COVER_LETTER",
    "tits_submission_metadata_pack/materials/TITLE_ABSTRACT_KEYWORDS",
)

BOUNDARY_MARKERS = [
    "command",
    "regeneration",
    "rerun",
    "run ",
    "python",
    "expected output",
    "manifest",
    "json",
    "csv",
    "md",
    "qa_json",
    "audit_json",
    "readme_md",
    "troubleshooting_csv",
    "file-level plan",
    "directory-level plan",
    "path",
    "local",
    "placeholder",
    "author-side",
    "author_fill_required",
    "replace",
    "fill ",
    "family-names",
    "given-names",
    "repository-code",
    "current_value",
    "publisher",
    "rights",
    "identifier",
    "creators",
    "doi_or_accession",
    "repository_url",
    "draft",
    "not a",
    "not evidence",
    "boundary",
    "local-only",
    "本地",
    "占位",
    "作者",
    "替换",
    "草案",
    "边界",
]


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def discover_files(root):
    files = []
    for rel in SCAN_DIRS:
        base = root / rel
        if not base.exists():
            continue
        if base.is_file():
            candidates = [base]
        else:
            candidates = sorted(path for path in base.rglob("*") if path.is_file())
        for path in candidates:
            if path.suffix.lower() in SCAN_SUFFIXES and path.stat().st_size < 10_000_000:
                files.append(path)
    return files


def line_context(text, start):
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end].strip()
    line_no = text.count("\n", 0, start) + 1
    return line, line_no


def context_window(text, start, radius=220):
    begin = max(0, start - radius)
    end = min(len(text), start + radius)
    return text[begin:end].replace("\n", " ").strip()


def is_boundary_context(line, window):
    lowered = f"{line} {window}".lower()
    return any(marker in lowered for marker in BOUNDARY_MARKERS)


def is_manuscript_text(rel):
    return any(segment in rel for segment in MANUSCRIPT_TEXT_SEGMENTS)


def classify_status(rel, risk_type, severity, line, window):
    boundary = is_boundary_context(line, window)
    if risk_type == "temporary_output_path":
        return "boundary_reference"
    if severity == "author_action":
        return "author_action_tracked"
    if is_manuscript_text(rel) and not boundary:
        return "blocking_unlabeled_identity_trace"
    if boundary:
        return "boundary_reference"
    return "review_required_unlabeled_trace"


def scan_file(root, path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    rel = path.relative_to(root).as_posix()
    rows = []
    seen = set()
    for item in PATTERNS:
        regex = re.compile(item["pattern"], re.IGNORECASE)
        for match in regex.finditer(text):
            line, line_no = line_context(text, match.start())
            window = context_window(text, match.start())
            status = classify_status(rel, item["risk_type"], item["severity"], line, window)
            key = (rel, line_no, item["risk_id"], match.group(0), line)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "source_file": rel,
                    "line": line_no,
                    "risk_id": item["risk_id"],
                    "risk_type": item["risk_type"],
                    "severity": item["severity"],
                    "status": status,
                    "matched_text": match.group(0)[:240],
                    "line_text": line[:600],
                    "context_window": window[:700],
                    "recommended_action": item["recommended_action"],
                }
            )
    return rows


def action_rows(scan_rows):
    rows = [
        {
            "action_id": "P01",
            "issue": "Absolute local command paths may be useful for local reproduction but should not be copied verbatim into final public instructions without context.",
            "recommended_action": "For public release, provide environment-agnostic commands such as `python ...` after `conda activate`, while keeping local commands only in internal provenance.",
            "blocking": "no_if_boundary_labeled",
        },
        {
            "action_id": "P02",
            "issue": "Author names, ORCID, repository URL, DOI/accession, license and funding placeholders remain unresolved by design.",
            "recommended_action": "Authors must replace these placeholders after repository release, data deposition and final author declaration approval.",
            "blocking": "author_side_before_submission",
        },
        {
            "action_id": "P03",
            "issue": "If the journal or review process requires anonymization, manuscript/front-matter files must be checked after author edits.",
            "recommended_action": "Rerun this audit after converting markdown drafts to the final IEEE template and before uploading reviewer-facing files.",
            "blocking": "author_side_policy_dependent",
        },
    ]
    blocking_count = sum(1 for row in scan_rows if row["status"] == "blocking_unlabeled_identity_trace")
    review_count = sum(1 for row in scan_rows if row["status"] == "review_required_unlabeled_trace")
    rows.append(
        {
            "action_id": "P04",
            "issue": f"Current scan found {blocking_count} blocking unlabeled identity traces and {review_count} unlabeled review-required traces.",
            "recommended_action": "Treat zero blocking traces as local readiness; still review boundary-labeled command paths before public release.",
            "blocking": "yes_if_counts_nonzero",
        }
    )
    return rows


def build_report(root):
    files = discover_files(root)
    scan_rows = []
    for path in files:
        scan_rows.extend(scan_file(root, path))
    status_counts = {}
    for row in scan_rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    blocking_count = status_counts.get("blocking_unlabeled_identity_trace", 0)
    review_unlabeled_count = status_counts.get("review_required_unlabeled_trace", 0)
    author_unlabeled_count = status_counts.get("author_action_unlabeled", 0)
    final = read_json(root / FINAL_READINESS)
    author = read_json(root / AUTHOR_CLOSURE)
    dry_run = read_json(root / DRY_RUN)
    status = "pass" if blocking_count == 0 and review_unlabeled_count == 0 and author_unlabeled_count == 0 else "review_required"
    summary = {
        "status": status,
        "scanned_file_count": len(files),
        "trace_row_count": len(scan_rows),
        "blocking_unlabeled_identity_trace_count": blocking_count,
        "review_required_unlabeled_trace_count": review_unlabeled_count,
        "author_action_unlabeled_count": author_unlabeled_count,
        "boundary_reference_count": status_counts.get("boundary_reference", 0),
        "author_action_tracked_count": status_counts.get("author_action_tracked", 0),
        "final_readiness": f"{final.get('pass_count', 'NA')}/{final.get('gate_count', 'NA')}",
        "author_closure_status": author.get("status", ""),
        "author_placeholder_count": author.get("summary", {}).get("placeholder_count"),
        "submission_dry_run_status": dry_run.get("status", ""),
    }
    return {
        "status": status,
        "summary": summary,
        "scan_rows": scan_rows,
        "action_rows": action_rows(scan_rows),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Anonymization, Privacy and Local-Trace Audit",
        "",
        "该审计检查投稿/复现/开源材料中是否残留本机绝对路径、用户名、临时路径、未替换 DOI/URL/license/作者占位符等痕迹。它的目的不是删除所有本地复现命令，而是把可接受的本地命令、manifest 路径和作者占位符明确归类，防止它们误进入最终主文或匿名审稿材料。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Trace Categories",
            "",
            "- `boundary_reference`: 位于命令、manifest、regeneration、local path 或边界说明上下文中；不阻塞当前本地证据链。",
            "- `author_action_tracked`: DOI、URL、license、作者、ORCID、funding 等占位符，已由作者闭环包跟踪。",
            "- `review_required_unlabeled_trace`: 本地痕迹未处于明确边界上下文，公开前需要处理。",
            "- `blocking_unlabeled_identity_trace`: 主文/摘要/cover letter 等候选投稿文本中出现未标注身份或本机路径痕迹。",
            "",
            "## Author Actions",
            "",
            "| ID | Issue | Recommended action | Blocking boundary |",
            "|---|---|---|---|",
        ]
    )
    for row in report["action_rows"]:
        lines.append(f"| {row['action_id']} | {row['issue']} | {row['recommended_action']} | {row['blocking']} |")
    lines.extend(
        [
            "",
            "## Detected Trace Summary",
            "",
            "| File | Line | Risk type | Status | Matched text | Recommended action |",
            "|---|---:|---|---|---|---|",
        ]
    )
    for row in report["scan_rows"][:80]:
        lines.append(
            f"| {row['source_file']} | {row['line']} | {row['risk_type']} | {row['status']} | `{row['matched_text']}` | {row['recommended_action']} |"
        )
    if len(report["scan_rows"]) > 80:
        lines.append(f"| ... | ... | ... | ... | {len(report['scan_rows']) - 80} additional rows in CSV | ... |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- 当前 PASS 只表示没有未标注的阻塞身份痕迹；它不代表匿名投稿政策已经由期刊确认。",
            "- 如果最终采用双盲或匿名评审路线，作者必须在最终 Word/LaTeX/PDF、补充材料和 reviewer-facing README 上重新运行该审计。",
            "- 绝对路径和本机 Python 路径可作为内部 provenance，但公开 README 中应优先改为环境无关命令。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_anonymization_privacy_audit.py --out-dir outputs/tits_dynamic_graph/tits_anonymization_privacy_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit local identity, privacy and anonymization traces in T-ITS submission materials.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_anonymization_privacy_audit")
    args = parser.parse_args()

    root = Path(".").resolve()
    out_dir = Path(args.out_dir)
    report = build_report(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "report_md": write_text(out_dir / "materials" / "ANONYMIZATION_PRIVACY_AUDIT.md", build_markdown(report)),
        "scan_csv": write_csv(
            out_dir / "tables" / "anonymization_privacy_scan_rows.csv",
            report["scan_rows"],
            [
                "source_file",
                "line",
                "risk_id",
                "risk_type",
                "severity",
                "status",
                "matched_text",
                "line_text",
                "context_window",
                "recommended_action",
            ],
        ),
        "action_csv": write_csv(
            out_dir / "tables" / "anonymization_privacy_author_actions.csv",
            report["action_rows"],
            ["action_id", "issue", "recommended_action", "blocking"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
        "boundary": "Local audit of privacy/anonymization traces; not a journal policy determination and not a legal/privacy review.",
    }
    manifest_path = write_json(out_dir / "tits_anonymization_privacy_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
