import argparse
import json
from pathlib import Path


CHECKS = [
    {
        "name": "joint_beats_individual",
        "pairing": "individual_transition_vs_joint_transition",
        "winner_index": 1,
    },
    {
        "name": "observer_beats_individual",
        "pairing": "individual_transition_vs_joint_transition_observer",
        "winner_index": 1,
    },
]


def latest_stage(summary):
    if "final" in summary["aggregate"]:
        return "final"
    stages = list(summary["aggregate"].keys())
    return stages[-1]


def evaluate_checks(summary, stage, threshold):
    stage_results = summary["aggregate"][stage]
    checks = []
    for check in CHECKS:
        metrics = stage_results[check["pairing"]]
        win_ratio = float(metrics["win_ratio_mean"][check["winner_index"]])
        score = float(metrics["mean_score_mean"][check["winner_index"]])
        opponent_score = float(metrics["mean_score_mean"][1 - check["winner_index"]])
        checks.append(
            {
                "name": check["name"],
                "stage": stage,
                "pairing": check["pairing"],
                "winner_index": check["winner_index"],
                "win_ratio": win_ratio,
                "win_ratio_threshold": threshold,
                "score_margin": score - opponent_score,
                "passed": win_ratio >= threshold,
            }
        )
    return checks


def write_markdown(path, report):
    lines = [
        "# DLC Telemetry Validation Report",
        "",
        f"- Stage: {report['stage']}",
        f"- Overall status: {report['status']}",
        f"- Win-ratio threshold: {report['win_ratio_threshold']}",
        "",
        "| Check | Pairing | Win Ratio | Score Margin | Status |",
        "|---|---|---:|---:|---|",
    ]
    for check in report["checks"]:
        lines.append(
            "| {name} | {pairing} | {win:.6g} | {margin:.6g} | {status} |".format(
                name=check["name"],
                pairing=check["pairing"],
                win=check["win_ratio"],
                margin=check["score_margin"],
                status="PASS" if check["passed"] else "WARN",
            )
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Validate telemetry DLC aggregate results against baseline expectations."
    )
    parser.add_argument("summary_json")
    parser.add_argument("--stage", default=None)
    parser.add_argument("--win-ratio-threshold", type=float, default=0.5)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    summary_path = Path(args.summary_json)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    stage = args.stage or latest_stage(summary)
    checks = evaluate_checks(summary, stage, args.win_ratio_threshold)
    status = "PASS" if all(check["passed"] for check in checks) else "WARN"
    out_dir = Path(args.out_dir) if args.out_dir else summary_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "status": status,
        "stage": stage,
        "win_ratio_threshold": args.win_ratio_threshold,
        "checks": checks,
    }
    json_path = out_dir / "validation_report.json"
    md_path = out_dir / "validation_report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(md_path, report)
    print(json.dumps({
        "status": status,
        "json": str(json_path),
        "markdown": str(md_path),
    }, indent=2))


if __name__ == "__main__":
    main()

