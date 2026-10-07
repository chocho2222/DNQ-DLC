#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


def read_case_rows(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def split_algorithms(value):
    marker = "--algorithms "
    text = str(value)
    if marker not in text:
        return []
    tail = text.split(marker, 1)[1]
    algs = tail.split()[0]
    return [item.strip() for item in algs.split(",") if item.strip()]


def expected_summary_path(case, algorithm):
    return Path(case["out_dir"]) / "summaries" / f"{algorithm}_n{case['num_agents']}_seed{case['seed']}.summary.json"


def inspect_summary(path):
    if not path.exists():
        return {
            "exists": False,
            "valid_json": False,
            "target_completed_lap": "",
            "overtake_success_rate": "",
            "elegant_overtake_rate": "",
            "target_grass_rate": "",
            "compute_latency_ms": "",
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "valid_json": False,
            "json_error": repr(exc),
            "target_completed_lap": "",
            "overtake_success_rate": "",
            "elegant_overtake_rate": "",
            "target_grass_rate": "",
            "compute_latency_ms": "",
        }
    return {
        "exists": True,
        "valid_json": True,
        "target_completed_lap": data.get("target_completed_lap"),
        "overtake_success_rate": data.get("overtake_success_rate"),
        "elegant_overtake_rate": data.get("elegant_overtake_rate"),
        "target_grass_rate": data.get("target_grass_rate"),
        "compute_latency_ms": data.get("compute_latency_ms"),
    }


def write_csv(rows, path, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# v6 Confirmatory Matrix Audit",
        "",
        "## Summary",
        "",
        f"- Status: `{summary['status']}`",
        f"- Expected algorithm-runs: {summary['expected_algorithm_runs']}",
        f"- Existing summaries: {summary['existing_summaries']}",
        f"- Missing summaries: {summary['missing_summaries']}",
        f"- Invalid summaries: {summary['invalid_summaries']}",
        "",
        "## Missing Commands",
        "",
    ]
    if report["missing_case_commands"]:
        lines.append("Run or rerun these case commands:")
        lines.append("")
        for command in report["missing_case_commands"][:20]:
            lines.append(f"- `{command}`")
        if len(report["missing_case_commands"]) > 20:
            lines.append(f"- ... {len(report['missing_case_commands']) - 20} more")
    else:
        lines.append("No missing case commands.")
    lines.extend(
        [
            "",
            "## Output Files",
            "",
            "- `tables/v6_confirmatory_matrix_audit_rows.csv`",
            "- `tables/v6_confirmatory_missing_case_commands.csv`",
            "- `v6_confirmatory_matrix_audit.json`",
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Audit v6 confirmatory matrix completion.")
    parser.add_argument(
        "--case-commands",
        default="outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv",
    )
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/v6_confirmatory_preflight")
    args = parser.parse_args()

    cases = read_case_rows(args.case_commands)
    rows = []
    missing_case_commands = []
    for case in cases:
        algorithms = split_algorithms(case["command"])
        case_missing = False
        for algorithm in algorithms:
            path = expected_summary_path(case, algorithm)
            inspected = inspect_summary(path)
            status = "complete" if inspected["exists"] and inspected["valid_json"] else "missing" if not inspected["exists"] else "invalid"
            case_missing = case_missing or status != "complete"
            rows.append(
                {
                    "benchmark": case["benchmark"],
                    "num_agents": case["num_agents"],
                    "seed": case["seed"],
                    "algorithm": algorithm,
                    "status": status,
                    "summary_path": str(path),
                    **inspected,
                }
            )
        if case_missing:
            missing_case_commands.append({"case_id": case["case_id"], "command": case["command"]})

    expected = len(rows)
    existing = sum(row["status"] == "complete" for row in rows)
    missing = sum(row["status"] == "missing" for row in rows)
    invalid = sum(row["status"] == "invalid" for row in rows)
    status = "complete" if expected and existing == expected else "incomplete"
    report = {
        "case_commands": args.case_commands,
        "summary": {
            "status": status,
            "expected_algorithm_runs": expected,
            "existing_summaries": existing,
            "missing_summaries": missing,
            "invalid_summaries": invalid,
            "missing_case_command_count": len(missing_case_commands),
        },
        "missing_case_commands": [row["command"] for row in missing_case_commands],
    }

    out_dir = Path(args.out_dir)
    tables = out_dir / "tables"
    write_csv(
        rows,
        tables / "v6_confirmatory_matrix_audit_rows.csv",
        [
            "benchmark",
            "num_agents",
            "seed",
            "algorithm",
            "status",
            "summary_path",
            "exists",
            "valid_json",
            "target_completed_lap",
            "overtake_success_rate",
            "elegant_overtake_rate",
            "target_grass_rate",
            "compute_latency_ms",
        ],
    )
    write_csv(missing_case_commands, tables / "v6_confirmatory_missing_case_commands.csv", ["case_id", "command"])
    (out_dir / "v6_confirmatory_matrix_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(report, out_dir / "v6_confirmatory_matrix_audit.md")
    print(json.dumps({"audit": str(out_dir / "v6_confirmatory_matrix_audit.json"), **report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
