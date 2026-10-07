#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


TEXT_FILES = [
    "manuscript/main.md",
    "materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md",
    "materials/MANUSCRIPT_OUTLINE.md",
    "materials/PUBLICATION_PACKAGE_SUMMARY.md",
    "materials/TOP_JOURNAL_READINESS_CHECKLIST.md",
]


RULES = [
    {
        "id": "R1_distributional_robustness",
        "pattern": r"\b(distributionally robust|distributional robustness|robust autonomous|robust-overtaking|robust overtaking|robust generalization)\b",
        "severity": "blocker",
        "allowed_if": [
            "not yet",
            "not ",
            "does not support",
            "do not claim",
            "prevents",
            "proof of",
            "rather than using",
            "barriers to",
            "before making",
            "before stronger",
            "limits",
            "limited",
        ],
        "evidence_boundary": "The expanded heldout2 selector is 7/10 against a 10/10 oracle; broad robustness claims are not supported.",
    },
    {
        "id": "R2_learned_surpasses_baseline",
        "pattern": r"\b(surpass(?:es|ed)?|outperform(?:s|ed)?|superior to|beats?)\b",
        "severity": "blocker",
        "allowed_if": [
            "does not",
            "do not",
            "not standalone",
            "rather than standalone",
            "not yet",
        ],
        "evidence_boundary": "The strongest locked single method is the rule overtake baseline at 8/10; graph-adaptive shield is 7/10.",
    },
    {
        "id": "R3_oracle_as_deployable",
        "pattern": r"\boracle\b.*\b(deployable|deployed|controller|policy|decision rule)\b|\b(deployable|deployed)\b.*\boracle\b",
        "severity": "blocker",
        "allowed_if": [
            "not",
            "only as diagnostic",
            "upper bound",
            "do not",
            "rather than",
            "not a deployable",
            "selector",
            "candidate-policy",
            "candidate policy",
            "separated from deployable",
            "matches oracle",
        ],
        "evidence_boundary": "Oracle portfolios use full-rollout outcomes and are diagnostic upper bounds, not online selector outputs.",
    },
    {
        "id": "R4_heldout1_without_heldout2",
        "pattern": r"\b10/10\b",
        "severity": "warning",
        "allowed_if": [
            "5/10",
            "heldout2",
            "second held-out",
            "second disjoint",
            "7/10",
            "10/10 oracle",
            "do not report",
            "locked",
        ],
        "evidence_boundary": "Heldout1 10/10 must be paired with the heldout2 5/10 original selector, 7/10 expanded selector, and 10/10 expanded oracle boundary.",
    },
    {
        "id": "R5_score_calibration_solves",
        "pattern": r"\b(calibration|score-only|linear score|retuning)\b.*\b(solve|solves|close|closes|fix|fixes)\b|\b(solve|solves|close|closes|fix|fixes)\b.*\b(calibration|score-only|linear score|retuning)\b",
        "severity": "blocker",
        "allowed_if": [
            "does not",
            "do not",
            "not",
            "insufficient",
            "remain",
        ],
        "evidence_boundary": "Offline score calibration does not improve heldout2 beyond 5/10.",
    },
    {
        "id": "R6_state_of_the_art",
        "pattern": r"\b(state[- ]of[- ]the[- ]art|sota|breakthrough|guarantee(?:d|s)?|solved|all scenarios|all seeds)\b",
        "severity": "blocker",
        "allowed_if": [
            "do not",
            "not",
            "no ",
            "before",
        ],
        "evidence_boundary": "The package is a conservative reproducible study with clear heldout2 limits, not a SOTA or solved claim.",
    },
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sentence_window(text, start, end):
    left = max(text.rfind("\n", 0, start), text.rfind(". ", 0, start), text.rfind("; ", 0, start))
    right_candidates = [idx for idx in [text.find("\n", end), text.find(". ", end), text.find("; ", end)] if idx != -1]
    right = min(right_candidates) if right_candidates else len(text)
    snippet = text[left + 1 : right].strip()
    return re.sub(r"\s+", " ", snippet)


def line_no(text, start):
    return text.count("\n", 0, start) + 1


def is_allowed(snippet, rule):
    lower = snippet.lower()
    return any(token in lower for token in rule["allowed_if"])


def scan_file(root, rel_path):
    path = root / rel_path
    text = path.read_text(encoding="utf-8")
    findings = []
    for rule in RULES:
        regex = re.compile(rule["pattern"], re.IGNORECASE)
        for match in regex.finditer(text):
            snippet = sentence_window(text, match.start(), match.end())
            allowed = is_allowed(snippet, rule)
            severity = "reviewed" if allowed else rule["severity"]
            findings.append(
                {
                    "file": rel_path,
                    "line": line_no(text, match.start()),
                    "rule_id": rule["id"],
                    "severity": severity,
                    "matched_text": match.group(0),
                    "snippet": snippet,
                    "evidence_boundary": rule["evidence_boundary"],
                }
            )
    return findings


def build_report(root):
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    findings = []
    missing_files = []
    for rel_path in TEXT_FILES:
        if not (root / rel_path).exists():
            missing_files.append(rel_path)
            continue
        findings.extend(scan_file(root, rel_path))

    counts = {}
    for finding in findings:
        counts[finding["severity"]] = counts.get(finding["severity"], 0) + 1
    counts.setdefault("blocker", 0)
    counts.setdefault("warning", 0)
    counts.setdefault("reviewed", 0)

    blockers = [row for row in findings if row["severity"] == "blocker"]
    warnings = [row for row in findings if row["severity"] == "warning"]
    return {
        "root": str(root),
        "scanned_files": TEXT_FILES,
        "missing_files": missing_files,
        "rules": RULES,
        "claim_matrix_count": len(claims["claims"]),
        "summary": {
            "status": "pass" if not blockers and not missing_files else "fail",
            "blockers": len(blockers),
            "warnings": len(warnings),
            "reviewed": counts["reviewed"],
            "total_findings": len(findings),
        },
        "findings": findings,
        "interpretation": (
            "This QA report checks manuscript-facing text against the claim evidence matrix. "
            "Blockers indicate overclaims that should be rewritten before submission. Reviewed findings are "
            "sensitive terms used in limiting or guardrail contexts."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["file", "line", "rule_id", "severity", "matched_text", "snippet", "evidence_boundary"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["findings"]:
            writer.writerow({key: row[key] for key in fieldnames})


def write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# Manuscript Claim QA",
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Status: `{summary['status']}`",
        f"- Blockers: {summary['blockers']}",
        f"- Warnings: {summary['warnings']}",
        f"- Reviewed guardrail uses: {summary['reviewed']}",
        f"- Claim evidence entries loaded: {report['claim_matrix_count']}",
        "",
        "## Scanned Files",
        "",
    ]
    lines.extend(f"- `{item}`" for item in report["scanned_files"])
    if report["missing_files"]:
        lines.extend(["", "## Missing Files", ""])
        lines.extend(f"- `{item}`" for item in report["missing_files"])

    for label, severity in [("Blockers", "blocker"), ("Warnings", "warning"), ("Reviewed Guardrail Uses", "reviewed")]:
        rows = [row for row in report["findings"] if row["severity"] == severity]
        lines.extend(["", f"## {label}", ""])
        if not rows:
            lines.append("- None")
            continue
        lines.extend(["| file | line | rule | match | evidence boundary |", "|---|---:|---|---|---|"])
        for row in rows:
            lines.append(
                f"| `{row['file']}` | {row['line']} | {row['rule_id']} | "
                f"{row['matched_text']} | {row['evidence_boundary']} |"
            )

    lines.extend(
        [
            "",
            "## Rule Set",
            "",
            "| rule | default severity | evidence boundary |",
            "|---|---|---|",
        ]
    )
    for rule in report["rules"]:
        lines.append(f"| {rule['id']} | {rule['severity']} | {rule['evidence_boundary']} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Scan manuscript-facing text for claim overstatements.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--prefix", default="MANUSCRIPT_CLAIM_QA")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    out_json = root / "materials" / f"{args.prefix}.json"
    out_md = root / "materials" / f"{args.prefix}.md"
    out_csv = root / "materials" / f"{args.prefix}.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), **report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
