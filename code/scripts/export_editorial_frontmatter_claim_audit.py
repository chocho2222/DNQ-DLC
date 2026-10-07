#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


TEXT_FILES = [
    "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
    "materials/COVER_LETTER_DRAFT_PACKAGE.md",
    "materials/SIGNIFICANCE_BRIEFING.md",
    "materials/EDITORIAL_NARRATIVE_PACKAGE.md",
    "materials/EDITORIAL_DECISION_BRIEF.md",
    "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
]


RULES = [
    {
        "id": "F1_broad_robustness",
        "pattern": r"\b(broad robustness|broadly robust|robust autonomous|robust-overtaking|robust overtaking|robust generalization|solved overtaking|overtaking is solved)\b",
        "severity": "blocker",
        "allowed_if": [
            "not",
            "no ",
            "do not",
            "prohibit",
            "unsupported",
            "risk",
            "avoid",
            "limitation",
            "boundary",
            "not supported",
            "before",
            "prevents",
            "guardrail",
            "rather than",
            "cannot",
            "must not",
        ],
        "evidence_boundary": "Heldout3 is negative external validation, heldout4 is partial transfer, and cross-heldout selector-oracle gaps remain.",
    },
    {
        "id": "F2_real_world_or_deployment",
        "pattern": r"\b(real[- ]?world deployment|real[- ]?road|public[- ]?road|road[- ]?ready|deployment[- ]?ready|deployed autonomous-driving|safety[- ]?certification|safety[- ]?certified)\b",
        "severity": "blocker",
        "allowed_if": [
            "not",
            "no ",
            "do not",
            "prohibit",
            "pending",
            "boundary",
            "risk",
            "avoid",
            "limitation",
            "excluded",
            "not supported",
            "without",
            "must not",
            "not evidence",
        ],
        "evidence_boundary": "All driving evidence is simulator-only and no real-road, public-road, or safety-certification evidence is included.",
    },
    {
        "id": "F3_vlm_or_perception_readiness",
        "pattern": r"\b(VLM autonomy|vision[- ]language autonomy|perception[- ]stack readiness|perception readiness|sensor[- ]fusion readiness|camera[- ]based readiness)\b",
        "severity": "blocker",
        "allowed_if": [
            "not",
            "no ",
            "do not",
            "prohibit",
            "excluded",
            "boundary",
            "risk",
            "avoid",
            "limitation",
            "not supported",
            "without",
            "must not",
        ],
        "evidence_boundary": "The package is explicitly non-VLM and telemetry/state based; no perception stack is evaluated.",
    },
    {
        "id": "F4_oracle_as_deployable",
        "pattern": r"\boracle\b.*\b(deployable|deployed|controller|policy|decision rule)\b|\b(deployable|deployed)\b.*\boracle\b",
        "severity": "blocker",
        "allowed_if": [
            "not",
            "no ",
            "do not",
            "upper bound",
            "diagnostic",
            "separate",
            "rather than",
            "mistaken",
            "boundary",
            "not supported",
            "prohibit",
            "must not",
            "selector",
        ],
        "evidence_boundary": "Oracle portfolios use full-rollout outcomes and are diagnostic upper bounds only.",
    },
    {
        "id": "F5_targeted_repair_externalized",
        "pattern": r"\b(heldout3[- ]targeted repair|targeted repair|seed[- ]targeted diagnostic)\b.*\b(external validation|broad generalization|robustness)\b|\b(external validation|broad generalization|robustness)\b.*\b(heldout3[- ]targeted repair|targeted repair|seed[- ]targeted diagnostic)\b",
        "severity": "blocker",
        "allowed_if": [
            "not",
            "avoid",
            "rather than",
            "do not",
            "prohibit",
            "diagnostic",
            "boundary",
            "partial transfer",
            "negative external validation",
            "heldout4",
            "must not",
            "not external",
        ],
        "evidence_boundary": "Heldout3 targeted repair is diagnostic reuse, not external validation.",
    },
    {
        "id": "F6_heldout4_overgeneralized",
        "pattern": r"\bheldout4\b.*\b(broad robustness|broad generalization|robustness proof|proves robustness|complete transfer)\b|\b(broad robustness|broad generalization|robustness proof|proves robustness|complete transfer)\b.*\bheldout4\b",
        "severity": "blocker",
        "allowed_if": [
            "not",
            "do not",
            "prohibit",
            "partial",
            "limitation",
            "boundary",
            "must not",
            "still",
            "leaves",
        ],
        "evidence_boundary": "Heldout4 is post-repair external validation with partial transfer, leaving selector misses and candidate gaps.",
    },
    {
        "id": "F7_sota_or_guarantee",
        "pattern": r"\b(state[- ]of[- ]the[- ]art|SOTA|breakthrough|guarantee(?:d|s)?|all scenarios|all seed distributions)\b",
        "severity": "blocker",
        "allowed_if": [
            "not",
            "no ",
            "do not",
            "prohibit",
            "before",
            "without",
            "cannot",
            "limitation",
        ],
        "evidence_boundary": "The evidence package is conservative and seed-bounded; it does not support SOTA, solved, or guarantee claims.",
    },
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def line_no(text, index):
    return text.count("\n", 0, index) + 1


def context_window(text, start, end):
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end].strip()
    if line.startswith("- ") or "|" in line:
        context_lines = []
        for prev in reversed(text[:line_start].splitlines()):
            stripped = prev.strip()
            if stripped.startswith("#") or stripped.lower().endswith(
                ("not supported:", "not yet supported:", "prohibited wording:", "excluded claims:")
            ):
                context_lines.append(stripped)
                break
        return re.sub(r"\s+", " ", " ".join(list(reversed(context_lines)) + [line]).strip())
    left = max(text.rfind("\n", 0, start), text.rfind(". ", 0, start), text.rfind("; ", 0, start))
    right_candidates = [idx for idx in (text.find("\n", end), text.find(". ", end), text.find("; ", end)) if idx != -1]
    right = min(right_candidates) if right_candidates else len(text)
    return re.sub(r"\s+", " ", text[left + 1 : right].strip())


def is_allowed(snippet, rule):
    lowered = snippet.lower()
    return any(token.lower() in lowered for token in rule["allowed_if"])


def scan_file(root, rel_path):
    path = root / rel_path
    text = path.read_text(encoding="utf-8")
    rows = []
    for rule in RULES:
        regex = re.compile(rule["pattern"], re.IGNORECASE)
        for match in regex.finditer(text):
            snippet = context_window(text, match.start(), match.end())
            allowed = is_allowed(snippet, rule)
            rows.append(
                {
                    "file": rel_path,
                    "line": line_no(text, match.start()),
                    "rule_id": rule["id"],
                    "severity": "reviewed" if allowed else rule["severity"],
                    "matched_text": match.group(0),
                    "snippet": snippet,
                    "evidence_boundary": rule["evidence_boundary"],
                }
            )
    return rows


def build_report(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    claim_qa = load_json(root / "materials" / "MANUSCRIPT_CLAIM_QA.json")
    local_author = load_json(root / "materials" / "LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json")
    findings = []
    missing = []
    for rel_path in TEXT_FILES:
        if not (root / rel_path).exists():
            missing.append(rel_path)
            continue
        findings.extend(scan_file(root, rel_path))

    blockers = [row for row in findings if row["severity"] == "blocker"]
    warnings = [row for row in findings if row["severity"] == "warning"]
    reviewed = [row for row in findings if row["severity"] == "reviewed"]
    return {
        "root": str(root),
        "title": "Editorial Front-matter Claim Audit",
        "purpose": (
            "Scan editor-facing title/abstract/highlight, cover-letter, significance, and triage materials for "
            "high-risk overclaims before journal upload."
        ),
        "scanned_files": TEXT_FILES,
        "missing_files": missing,
        "rules": RULES,
        "summary": {
            "status": "pass" if not blockers and not missing else "fail",
            "scanned_file_count": len(TEXT_FILES) - len(missing),
            "missing_file_count": len(missing),
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
            "reviewed_guardrail_count": len(reviewed),
            "finding_count": len(findings),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
            "manuscript_claim_qa_status": claim_qa["summary"]["status"],
            "local_author_readiness_status": local_author["summary"]["status"],
        },
        "findings": findings,
        "interpretation": (
            "A pass means high-risk phrases appear only in explicit limitation, prohibition, or boundary contexts. "
            "It does not replace author review of final journal-specific wording."
        ),
    }


def write_csv(report, path):
    fields = ["file", "line", "rule_id", "severity", "matched_text", "snippet", "evidence_boundary"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["findings"]:
            writer.writerow({key: row[key] for key in fields})


def write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# Editorial Front-matter Claim Audit",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Scanned Files", ""])
    lines.extend(f"- `{item}`" for item in report["scanned_files"])
    if report["missing_files"]:
        lines.extend(["", "## Missing Files", ""])
        lines.extend(f"- `{item}`" for item in report["missing_files"])
    for title, severity in [("Blockers", "blocker"), ("Warnings", "warning"), ("Reviewed Guardrail Uses", "reviewed")]:
        rows = [row for row in report["findings"] if row["severity"] == severity]
        lines.extend(["", f"## {title}", ""])
        if not rows:
            lines.append("- None")
            continue
        lines.extend(["| file | line | rule | match | evidence boundary |", "|---|---:|---|---|---|"])
        for row in rows:
            lines.append(
                f"| `{row['file']}` | {row['line']} | {row['rule_id']} | {row['matched_text']} | {row['evidence_boundary']} |"
            )
    lines.extend(["", "## Rules", "", "| rule | default severity | evidence boundary |", "|---|---|---|"])
    for rule in report["rules"]:
        lines.append(f"| {rule['id']} | {rule['severity']} | {rule['evidence_boundary']} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export editor-facing front-matter claim audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "EDITORIAL_FRONTMATTER_CLAIM_AUDIT.json"
    out_md = materials / "EDITORIAL_FRONTMATTER_CLAIM_AUDIT.md"
    out_csv = materials / "EDITORIAL_FRONTMATTER_CLAIM_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "status": report["summary"]["status"],
                "blockers": report["summary"]["blocker_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
