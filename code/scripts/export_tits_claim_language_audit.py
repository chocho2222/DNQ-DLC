#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


SCAN_DIRS = [
    "outputs/tits_dynamic_graph/tits_manuscript_package/materials",
    "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials",
    "outputs/tits_dynamic_graph/reviewer_replication_packet",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials",
    "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials",
    "outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials",
    "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials",
    "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials",
    "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials",
]

SCAN_SUFFIXES = {".md"}

GUARDRAIL_CSV = "outputs/tits_dynamic_graph/tits_threats_validity_pack/tables/claim_language_guardrails.csv"

HIGH_RISK_PATTERNS = [
    {
        "risk_id": "L01",
        "pattern": r"\b(real[- ]world|real vehicle|real-vehicle|on-road|public road)\b.{0,80}\b(safe|safety|deploy|deployment|certif)",
        "risk": "real_world_safety_or_deployment_overclaim",
        "safe_rewrite": "Limit the statement to evaluated simulation benchmarks and describe real-world deployment as future work.",
    },
    {
        "risk_id": "L02",
        "pattern": r"\b(arbitrary|any|all|unlimited|limitless)\b.{0,80}\b(track|road|traffic|density|scenario|vehicle)",
        "risk": "unbounded_generalization_overclaim",
        "safe_rewrite": "State the evaluated procedural, Monza-derived and 8-vehicle extrapolation settings explicitly.",
    },
    {
        "risk_id": "L03",
        "pattern": r"\b(guarantee|guaranteed|prove|proved|certified|certify)\b.{0,80}\b(collision[- ]free|safe|safety|success|overtak)",
        "risk": "guarantee_or_certification_overclaim",
        "safe_rewrite": "Use empirical benchmark evidence language rather than certification or guarantee language.",
    },
    {
        "risk_id": "L04",
        "pattern": r"\b(solves|solved)\b.{0,80}\b(overtak|autonomous driving|multi[- ]car)",
        "risk": "solved_problem_overclaim",
        "safe_rewrite": "Use improves/supports/outperforms under evaluated benchmark instead of solves.",
    },
    {
        "risk_id": "L05",
        "pattern": r"\b(human[- ]like|legally safe|legal)\b.{0,80}\b(overtak|driv|maneuver)",
        "risk": "human_or_legal_safety_overclaim",
        "safe_rewrite": "Report benchmark-defined desirable/on-track overtaking rather than human or legal safety.",
    },
]

BOUNDARY_MARKERS = [
    "not ",
    "does not",
    "do not",
    "cannot",
    "should not",
    "avoid",
    "boundary",
    "limitation",
    "limitations",
    "future work",
    "risk",
    "guardrail",
    "recommended claim wording",
    "not intended for",
    "不",
    "不能",
    "不证明",
    "不代表",
    "不声称",
    "避免",
    "边界",
    "限制",
    "风险",
]


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


def discover_files(root):
    out = []
    for rel in SCAN_DIRS:
        base = root / rel
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in SCAN_SUFFIXES:
                out.append(path)
    return out


def line_context(text, start):
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end].strip()
    line_no = text.count("\n", 0, start) + 1
    return line, line_no


def context_window(text, start, radius=260):
    begin = max(0, start - radius)
    end = min(len(text), start + radius)
    return text[begin:end].replace("\n", " ").strip()


def is_boundary_context(line, window=""):
    lowered = f"{window} {line}".lower()
    return any(marker in lowered for marker in BOUNDARY_MARKERS)


def build_exact_avoid_patterns(guardrail_rows):
    patterns = []
    for row in guardrail_rows:
        avoid = (row.get("avoid_claim") or "").strip()
        if not avoid:
            continue
        compact = re.escape(avoid)
        compact = compact.replace(r"\ ", r"\s+")
        patterns.append(
            {
                "risk_id": row.get("risk_id", "guardrail"),
                "pattern": compact,
                "risk": "exact_avoid_claim_text",
                "safe_rewrite": row.get("safe_claim", ""),
                "avoid_claim": avoid,
                "source": row.get("source", ""),
            }
        )
    return patterns


def scan_file(root, path, patterns):
    text = path.read_text(encoding="utf-8", errors="ignore")
    rel = path.relative_to(root).as_posix()
    rows = []
    seen = set()
    for item in patterns:
        regex = re.compile(item["pattern"], flags=re.IGNORECASE | re.DOTALL)
        for match in regex.finditer(text):
            line, line_no = line_context(text, match.start())
            window = context_window(text, match.start())
            boundary = is_boundary_context(line, window)
            key = (rel, line_no, item["risk_id"], item["risk"], line)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "source_file": rel,
                    "line": line_no,
                    "risk_id": item["risk_id"],
                    "risk": item["risk"],
                    "status": "boundary_reference" if boundary else "risky_claim_language",
                    "boundary_context": boundary,
                    "matched_text": " ".join(match.group(0).split())[:240],
                    "line_text": line[:500],
                    "context_window": window[:700],
                    "safe_rewrite": item.get("safe_rewrite", ""),
                    "source": item.get("source", ""),
                }
            )
    return rows


def build_guardrail_trace_rows(guardrail_rows):
    rows = []
    for row in guardrail_rows:
        rows.append(
            {
                "risk_id": row.get("risk_id", ""),
                "safe_claim": row.get("safe_claim", ""),
                "avoid_claim": row.get("avoid_claim", ""),
                "source": row.get("source", ""),
                "audit_use": "safe_claim_allowed; avoid_claim_scanned_as_risky_unless_boundary_context",
            }
        )
    return rows


def summarize(rows, scanned_files, guardrail_rows):
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    risky = [row for row in rows if row["status"] == "risky_claim_language"]
    return {
        "status": "pass" if not risky else "review_required",
        "scanned_file_count": len(scanned_files),
        "guardrail_count": len(guardrail_rows),
        "match_count": len(rows),
        "risky_claim_language_count": len(risky),
        "boundary_reference_count": counts.get("boundary_reference", 0),
        "status_counts": dict(sorted(counts.items())),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Claim-Language Audit",
        "",
        "该审计检查正式写作材料中是否出现超出当前仿真证据边界的 claim，例如真实道路部署安全、任意交通密度泛化、保证无碰撞或已解决自动超车问题。它复用 threats-to-validity pack 的 claim guardrails，不新增实验结果。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `pass`: 未发现未加边界说明的高风险 claim 表述。",
            "- `boundary_reference`: 高风险短语只出现在“不证明/不能/avoid/limitations/future work”等边界上下文中。",
            "- `risky_claim_language`: 高风险短语出现在普通论断中，投稿前应改写。",
            "",
            "## Risky Rows",
            "",
        ]
    )
    risky = [row for row in report["rows"] if row["status"] == "risky_claim_language"]
    if not risky:
        lines.append("No unbounded or unsafe claim-language rows were found.")
    else:
        lines.extend(["| Source | Line | Risk | Text | Suggested rewrite |", "|---|---:|---|---|---|"])
        for row in risky:
            lines.append(
                f"| `{row['source_file']}` | {row['line']} | {row['risk']} | {row['line_text']} | {row['safe_rewrite']} |"
            )
    lines.extend(
        [
            "",
            "## Boundary Rows",
            "",
        ]
    )
    boundary = [row for row in report["rows"] if row["status"] == "boundary_reference"]
    if not boundary:
        lines.append("No boundary-only high-risk phrases were found.")
    else:
        lines.extend(["| Source | Line | Risk | Boundary text |", "|---|---:|---|---|"])
        for row in boundary[:80]:
            lines.append(f"| `{row['source_file']}` | {row['line']} | {row['risk']} | {row['line_text']} |")
        if len(boundary) > 80:
            lines.append(f"| ... | ... | ... | {len(boundary) - 80} additional boundary rows omitted from markdown; see CSV. |")
    lines.extend(
        [
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_claim_language_audit.py --out-dir outputs/tits_dynamic_graph/tits_claim_language_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit manuscript-facing claim language against T-ITS claim guardrails.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_claim_language_audit")
    parser.add_argument("--guardrails", default=GUARDRAIL_CSV)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    guardrails = read_csv(root / args.guardrails)
    patterns = HIGH_RISK_PATTERNS + build_exact_avoid_patterns(guardrails)
    scanned_files = discover_files(root)
    rows = []
    for path in scanned_files:
        rows.extend(scan_file(root, path, patterns))
    scanned_rel = [path.relative_to(root).as_posix() for path in scanned_files]
    report = {
        "status": "pending",
        "out_dir": args.out_dir,
        "scan_dirs": SCAN_DIRS,
        "scanned_files": scanned_rel,
        "guardrail_source": args.guardrails,
        "summary": {},
        "rows": rows,
        "note": "This audit checks manuscript-facing language boundaries. It is a writing-risk screen, not a scientific correctness proof.",
    }
    report["summary"] = summarize(rows, scanned_rel, guardrails)
    report["status"] = report["summary"]["status"]
    paths = {
        "audit_md": write_text(materials / "CLAIM_LANGUAGE_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "CLAIM_LANGUAGE_AUDIT.json", report),
        "qa_json": write_json(
            materials / "CLAIM_LANGUAGE_QA.json",
            {
                "status": report["status"],
                "checks": {
                    "guardrails_loaded": bool(guardrails),
                    "files_scanned": bool(scanned_files),
                    "no_risky_claim_language": report["summary"]["risky_claim_language_count"] == 0,
                },
                "summary": report["summary"],
            },
        ),
        "scan_rows_csv": write_csv(
            tables / "claim_language_scan_rows.csv",
            rows,
            [
                "source_file",
                "line",
                "risk_id",
                "risk",
                "status",
                "boundary_context",
                "matched_text",
                "line_text",
                "context_window",
                "safe_rewrite",
                "source",
            ],
        ),
        "guardrail_trace_csv": write_csv(
            tables / "claim_guardrail_trace.csv",
            build_guardrail_trace_rows(guardrails),
            ["risk_id", "safe_claim", "avoid_claim", "source", "audit_use"],
        ),
        "scanned_files_csv": write_csv(
            tables / "claim_language_scanned_files.csv",
            [{"source_file": rel} for rel in scanned_rel],
            ["source_file"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_claim_language_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
