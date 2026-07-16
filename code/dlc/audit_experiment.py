import argparse
import json
from pathlib import Path


MODEL_NAMES = [
    "individual_transition",
    "joint_transition",
    "joint_transition_observer",
]

PAIRINGS = [
    "individual_transition_vs_joint_transition",
    "individual_transition_vs_joint_transition_observer",
    "joint_transition_vs_joint_transition_observer",
]

EXPORT_FILES = [
    "exported/summary.csv",
    "exported/summary.md",
    "figures/win_ratio.svg",
    "figures/mean_score.svg",
    "validation/validation_report.json",
    "validation/validation_report.md",
]


def model_dir_for_stage(seed_dir, stage):
    if stage == "final":
        return seed_dir / "models"
    return seed_dir / "models" / stage


def add_check(checks, name, passed, detail):
    checks.append(
        {
            "name": name,
            "passed": bool(passed),
            "detail": detail,
        }
    )


def audit(summary_path):
    summary_path = Path(summary_path)
    root = summary_path.parent
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    checks = []

    add_check(
        checks,
        "summary_exists",
        summary_path.exists(),
        str(summary_path),
    )
    seeds = summary.get("seeds", [])
    stages = list(summary.get("aggregate", {}).keys())
    add_check(checks, "has_seeds", len(seeds) > 0, {"seeds": seeds})
    add_check(checks, "has_stages", len(stages) > 0, {"stages": stages})

    for seed in seeds:
        seed_dir = root / f"seed_{seed}"
        add_check(
            checks,
            f"seed_{seed}_train_summary",
            (seed_dir / "models" / "train_summary.json").exists(),
            str(seed_dir / "models" / "train_summary.json"),
        )
        for stage in stages:
            model_dir = model_dir_for_stage(seed_dir, stage)
            for model_name in MODEL_NAMES:
                model_path = model_dir / f"{model_name}.pt"
                add_check(
                    checks,
                    f"seed_{seed}_{stage}_{model_name}_model",
                    model_path.exists(),
                    str(model_path),
                )

            round_robin_path = seed_dir / f"round_robin_{stage}.json"
            round_robin_ok = False
            round_robin_detail = str(round_robin_path)
            if round_robin_path.exists():
                result = json.loads(round_robin_path.read_text(encoding="utf-8"))
                pairings = result.get("pairings", {})
                round_robin_ok = all(pairing in pairings for pairing in PAIRINGS)
                round_robin_detail = {
                    "path": str(round_robin_path),
                    "pairings": sorted(pairings.keys()),
                }
            add_check(
                checks,
                f"seed_{seed}_{stage}_round_robin",
                round_robin_ok,
                round_robin_detail,
            )

    aggregate = summary.get("aggregate", {})
    for stage in stages:
        stage_results = aggregate.get(stage, {})
        add_check(
            checks,
            f"{stage}_aggregate_pairings",
            all(pairing in stage_results for pairing in PAIRINGS),
            {"pairings": sorted(stage_results.keys())},
        )

    for relative_path in EXPORT_FILES:
        path = root / relative_path
        add_check(
            checks,
            f"export_{relative_path}",
            path.exists() and path.stat().st_size > 0,
            str(path),
        )

    validation_path = root / "validation" / "validation_report.json"
    if validation_path.exists():
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        add_check(
            checks,
            "validation_status",
            validation.get("status") == "PASS",
            {
                "path": str(validation_path),
                "status": validation.get("status"),
            },
        )
    else:
        add_check(
            checks,
            "validation_status",
            False,
            str(validation_path),
        )

    status = "PASS" if all(check["passed"] for check in checks) else "FAIL"
    return {
        "status": status,
        "summary": str(summary_path),
        "root": str(root),
        "seeds": seeds,
        "stages": stages,
        "checks": checks,
    }


def write_markdown(path, report):
    lines = [
        "# DLC Telemetry Experiment Audit",
        "",
        f"- Status: {report['status']}",
        f"- Summary: `{report['summary']}`",
        f"- Seeds: {report['seeds']}",
        f"- Stages: {report['stages']}",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in report["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        detail = check["detail"]
        if not isinstance(detail, str):
            detail = json.dumps(detail, sort_keys=True)
        lines.append(f"| {check['name']} | {status} | `{detail}` |")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Audit telemetry DLC experiment artifacts for completeness."
    )
    parser.add_argument("summary_json")
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    report = audit(args.summary_json)
    summary_path = Path(args.summary_json)
    out_dir = Path(args.out_dir) if args.out_dir else summary_path.parent / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "audit_report.json"
    md_path = out_dir / "audit_report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(md_path, report)
    print(json.dumps({
        "status": report["status"],
        "json": str(json_path),
        "markdown": str(md_path),
    }, indent=2))


if __name__ == "__main__":
    main()
