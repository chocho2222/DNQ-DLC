import argparse
import json
import os
from pathlib import Path


MODEL_NAMES = [
    "individual_transition",
    "joint_transition",
    "joint_transition_observer",
]


def process_alive(pid):
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def expected_stages(train_steps, eval_at_steps):
    stages = [
        f"step_{step}"
        for step in eval_at_steps
        if 0 < int(step) <= int(train_steps)
    ]
    stages.append("final")
    return stages


def stage_model_dir(seed_dir, stage):
    if stage == "final":
        return seed_dir / "models"
    return seed_dir / "models" / stage


def count_models(model_dir):
    return sum((model_dir / f"{name}.pt").exists() for name in MODEL_NAMES)


def load_summary(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def status(out_dir):
    out_dir = Path(out_dir)
    pid_path = out_dir / "paper_scale.pid"
    pid = None
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except ValueError:
            pid = None

    summary = load_summary(out_dir / "aggregate_summary.json")
    if summary:
        seeds = summary.get("seeds", [])
        train_steps = summary.get("train_steps")
        eval_at_steps = summary.get("eval_at_steps", [])
        stages = list(summary.get("aggregate", {}).keys())
    else:
        seeds = [0, 1, 2, 3, 4]
        train_steps = 200
        eval_at_steps = [50, 100, 150, 200]
        stages = expected_stages(train_steps, eval_at_steps)

    seed_status = {}
    for seed in seeds:
        seed_dir = out_dir / f"seed_{seed}"
        train_summary_path = seed_dir / "models" / "train_summary.json"
        progress_path = seed_dir / "models" / "progress.json"
        train_summary = load_summary(train_summary_path)
        progress = load_summary(progress_path)
        stage_status = {}
        for stage in stages:
            model_dir = stage_model_dir(seed_dir, stage)
            round_robin_path = seed_dir / f"round_robin_{stage}.json"
            stage_status[stage] = {
                "models_present": count_models(model_dir),
                "models_expected": len(MODEL_NAMES),
                "round_robin": round_robin_path.exists(),
            }
        seed_status[str(seed)] = {
            "train_summary": train_summary_path.exists(),
            "progress": progress,
            "transitions": train_summary.get("transitions") if train_summary else None,
            "stages": stage_status,
        }

    exports = {
        "aggregate_summary": (out_dir / "aggregate_summary.json").exists(),
        "summary_csv": (out_dir / "exported" / "summary.csv").exists(),
        "summary_md": (out_dir / "exported" / "summary.md").exists(),
        "win_ratio_svg": (out_dir / "figures" / "win_ratio.svg").exists(),
        "mean_score_svg": (out_dir / "figures" / "mean_score.svg").exists(),
        "validation_report": (out_dir / "validation" / "validation_report.json").exists(),
        "audit_report": (out_dir / "audit" / "audit_report.json").exists(),
    }

    return {
        "out_dir": str(out_dir),
        "pid": pid,
        "running": process_alive(pid),
        "log_bytes": (out_dir / "paper_scale.log").stat().st_size
        if (out_dir / "paper_scale.log").exists()
        else 0,
        "seeds": seeds,
        "train_steps": train_steps,
        "eval_at_steps": eval_at_steps,
        "stages": stages,
        "seed_status": seed_status,
        "exports": exports,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Show progress for a telemetry DLC experiment directory."
    )
    parser.add_argument("out_dir", nargs="?", default="outputs/torch_dlc_experiment")
    args = parser.parse_args()
    print(json.dumps(status(args.out_dir), indent=2))


if __name__ == "__main__":
    main()
