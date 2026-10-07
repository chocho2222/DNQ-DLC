#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


FINAL_DASHBOARD_SCRIPT = "scripts/export_tits_final_readiness_dashboard.py"
MAKEFILE = "Makefile"
EVIDENCE_COMMAND_LEDGER = "outputs/tits_dynamic_graph/tits_evidence_ledger/tables/evidence_command_ledger.csv"
REVIEWER_README = "outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md"


def read_text(path):
    path = Path(path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


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


def final_input_paths():
    text = read_text(FINAL_DASHBOARD_SCRIPT)
    paths = re.findall(r'load_json\("([^"]+)"\)', text)
    return sorted(dict.fromkeys(paths))


def top_artifact_dir(path):
    parts = Path(path).parts
    if len(parts) >= 3 and parts[0] == "outputs" and parts[1] == "tits_dynamic_graph":
        if len(parts) == 3:
            return str(Path(*parts[:2]))
        return str(Path(*parts[:3]))
    return str(Path(path).parent)


def refresh_body():
    text = read_text(MAKEFILE)
    match = re.search(r"^tits-refresh-gates:\n(?P<body>(?:\t.*\n)+)", text, flags=re.MULTILINE)
    body = match.group("body") if match else ""
    return body.replace("$(TITS_OUT)", "outputs/tits_dynamic_graph").replace("${TITS_OUT}", "outputs/tits_dynamic_graph")


def script_refs():
    refs = {}
    for script in sorted(Path("scripts").glob("*.py")):
        text = read_text(script)
        for path in final_input_paths():
            top_dir = top_artifact_dir(path)
            if path in text or top_dir in text:
                refs.setdefault(top_dir, set()).add(str(script))
    return refs


def command_ledger_text():
    rows = read_csv(EVIDENCE_COMMAND_LEDGER)
    return "\n".join(
        " ".join(str(row.get(field, "")) for field in row.keys())
        for row in rows
    )


def build_rows(root):
    refresh = refresh_body()
    reviewer = read_text(REVIEWER_README)
    command_ledger = command_ledger_text()
    scripts_by_top_dir = script_refs()
    rows = []
    for rel in final_input_paths():
        top_dir = top_artifact_dir(rel)
        exists = (root / rel).exists()
        refresh_covered = top_dir in refresh or rel in refresh
        command_ledger_covered = top_dir in command_ledger or rel in command_ledger
        reviewer_readme_covered = top_dir in reviewer or rel in reviewer
        script_candidates = sorted(scripts_by_top_dir.get(top_dir, []))
        script_available = bool(script_candidates)
        route_count = sum(
            [
                bool(refresh_covered),
                bool(command_ledger_covered),
                bool(reviewer_readme_covered),
                bool(script_available),
            ]
        )
        status = "pass" if exists and route_count > 0 else "missing_or_unrouted"
        rows.append(
            {
                "final_input_path": rel,
                "top_artifact_dir": top_dir,
                "exists": exists,
                "refresh_gates": refresh_covered,
                "evidence_command_ledger": command_ledger_covered,
                "reviewer_readme": reviewer_readme_covered,
                "script_available": script_available,
                "script_candidates": ";".join(script_candidates[:5]),
                "route_count": route_count,
                "status": status,
            }
        )
    return rows


def build_report(rows):
    total = len(rows)
    missing = [row for row in rows if not row["exists"]]
    unrouted = [row for row in rows if row["exists"] and row["route_count"] == 0]
    refresh_count = sum(bool(row["refresh_gates"]) for row in rows)
    command_count = sum(bool(row["evidence_command_ledger"]) for row in rows)
    reviewer_count = sum(bool(row["reviewer_readme"]) for row in rows)
    script_count = sum(bool(row["script_available"]) for row in rows)
    status = "pass" if not missing and not unrouted else "review_required"
    summary = {
        "status": status,
        "final_input_count": total,
        "existing_input_count": total - len(missing),
        "missing_input_count": len(missing),
        "unrouted_existing_input_count": len(unrouted),
        "refresh_gates_covered_count": refresh_count,
        "evidence_command_ledger_covered_count": command_count,
        "reviewer_readme_covered_count": reviewer_count,
        "script_available_count": script_count,
    }
    return status, summary


def build_markdown(summary, rows):
    lines = [
        "# T-ITS Refresh Coverage Audit",
        "",
        "该审计检查 final readiness dashboard 读取的每个输入产物是否存在，以及是否至少能从 `make tits-refresh-gates`、evidence command ledger、reviewer README 或本地生成脚本中找到再生成路线。它不重跑实验，用于发现顶刊复现包中“有结果但无入口”的风险。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Coverage Table",
            "",
            "| Final input | Exists | Refresh | Ledger | Reviewer | Script | Routes | Status |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| `{row['final_input_path']}` | {row['exists']} | {row['refresh_gates']} | "
            f"{row['evidence_command_ledger']} | {row['reviewer_readme']} | {row['script_available']} | "
            f"{row['route_count']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- PASS 表示 final-readiness 输入均存在且至少有一种本地再生成/追溯路线；不表示所有产物都由 `make tits-refresh-gates` 每次重算。",
            "- `script_available=True` 表示本地脚本文本中引用了该产物或顶层输出目录；最终公开仓库仍应保留 reviewer README 和 evidence ledger 作为优先路线。",
            "- 如果新增 final dashboard 输入、移动输出目录或删改 evidence ledger，需要重新运行该审计。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_refresh_coverage_audit.py --out-dir outputs/tits_dynamic_graph/tits_refresh_coverage_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit regeneration coverage for final-readiness inputs.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_refresh_coverage_audit")
    args = parser.parse_args()

    root = Path(".").resolve()
    rows = build_rows(root)
    status, summary = build_report(rows)
    out_dir = Path(args.out_dir)
    paths = {
        "report_md": write_text(out_dir / "materials" / "TITS_REFRESH_COVERAGE_AUDIT.md", build_markdown(summary, rows)),
        "coverage_csv": write_csv(
            out_dir / "tables" / "final_readiness_input_refresh_coverage.csv",
            rows,
            [
                "final_input_path",
                "top_artifact_dir",
                "exists",
                "refresh_gates",
                "evidence_command_ledger",
                "reviewer_readme",
                "script_available",
                "script_candidates",
                "route_count",
                "status",
            ],
        ),
    }
    manifest = {
        "status": status,
        "out_dir": str(out_dir),
        "summary": summary,
        "paths": paths,
        "boundary": "Static coverage audit only; it checks regeneration routes but does not rerun simulations.",
    }
    manifest_path = write_json(out_dir / "tits_refresh_coverage_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
