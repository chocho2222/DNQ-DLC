#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.tits_experiment_registry import PAPER_DLC_MODEL_PATHS, write_csv, write_json


MODEL_NAMES = [
    "joint_transition_observer",
    "joint_transition",
    "individual_transition",
]


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def stage_model_dir(seed_dir, stage):
    if stage == "final":
        return seed_dir / "models"
    return seed_dir / "models" / stage


def round_robin_path(seed_dir, stage):
    return seed_dir / f"round_robin_{stage}.json"


def model_path(seed_dir, stage, model_name):
    return stage_model_dir(seed_dir, stage) / f"{model_name}.pt"


def seed_score(seed_dir, stage):
    rr = read_json(round_robin_path(seed_dir, stage))
    if not rr:
        return None
    values = []
    for pairing in rr.get("pairings", {}).values():
        values.extend(float(item) for item in pairing.get("mean_score", []) if item is not None)
    if not values:
        return None
    return sum(values) / len(values)


def discover_candidates(experiment_dir, stage):
    rows = []
    for seed_dir in sorted(Path(experiment_dir).glob("seed_*")):
        if not seed_dir.is_dir():
            continue
        try:
            seed = int(seed_dir.name.split("_", 1)[1])
        except Exception:
            seed = seed_dir.name
        paths = {name: model_path(seed_dir, stage, name) for name in MODEL_NAMES}
        present = {name: paths[name].exists() for name in MODEL_NAMES}
        rows.append(
            {
                "seed": seed,
                "seed_dir": str(seed_dir),
                "stage": stage,
                "complete_model_set": all(present.values()),
                "present_count": sum(1 for value in present.values() if value),
                "round_robin_exists": round_robin_path(seed_dir, stage).exists(),
                "selection_score": seed_score(seed_dir, stage),
                "joint_transition_observer": str(paths["joint_transition_observer"]),
                "joint_transition": str(paths["joint_transition"]),
                "individual_transition": str(paths["individual_transition"]),
            }
        )
    return rows


def choose_candidate(rows, select_seed=None):
    complete = [row for row in rows if row["complete_model_set"]]
    if select_seed is not None:
        for row in complete:
            if str(row["seed"]) == str(select_seed):
                return row
        return None
    if not complete:
        return None
    return sorted(
        complete,
        key=lambda row: (
            row["selection_score"] is not None,
            float(row["selection_score"] or -1e12),
            -int(row["seed"]) if isinstance(row["seed"], int) else 0,
        ),
        reverse=True,
    )[0]


def freeze_candidate(candidate, frozen_dir):
    frozen_dir = Path(frozen_dir)
    frozen_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for model_name in MODEL_NAMES:
        src = Path(candidate[model_name])
        dst = frozen_dir / f"{model_name}.pt"
        shutil.copy2(src, dst)
        copied.append({"model_name": model_name, "source": str(src), "frozen_path": str(dst), "size_bytes": dst.stat().st_size})
    return copied


def registry_alignment_rows(frozen_dir):
    rows = []
    frozen_dir = Path(frozen_dir)
    mapping = {
        "dlc_joint_transition_observer": "joint_transition_observer.pt",
        "dlc_joint_transition": "joint_transition.pt",
        "dlc_individual_transition": "individual_transition.pt",
    }
    for algorithm, filename in mapping.items():
        expected = Path(PAPER_DLC_MODEL_PATHS[algorithm])
        actual = frozen_dir / filename
        rows.append(
            {
                "algorithm": algorithm,
                "registry_expected_path": str(expected),
                "frozen_path": str(actual),
                "path_matches_registry": expected == actual,
                "exists": actual.exists(),
                "size_bytes": actual.stat().st_size if actual.exists() else 0,
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description="Freeze paper-style DLC baseline checkpoints for T-ITS expanded experiments.")
    parser.add_argument("--experiment-dir", default="outputs/tits_dynamic_graph_expanded/paper_dlc_baselines_training")
    parser.add_argument("--frozen-dir", default="outputs/tits_dynamic_graph_expanded/paper_dlc_baselines")
    parser.add_argument("--stage", default="final")
    parser.add_argument("--select-seed", default="")
    parser.add_argument("--mode", choices=["dry-run", "freeze"], default="dry-run")
    args = parser.parse_args()

    out_dir = Path(args.frozen_dir)
    tables = out_dir / "tables"
    materials = out_dir / "materials"
    tables.mkdir(parents=True, exist_ok=True)
    materials.mkdir(parents=True, exist_ok=True)

    rows = discover_candidates(args.experiment_dir, args.stage)
    selected = choose_candidate(rows, args.select_seed or None)
    copied = freeze_candidate(selected, out_dir) if args.mode == "freeze" and selected else []
    registry_rows = registry_alignment_rows(out_dir)
    candidate_csv = write_csv(
        tables / "paper_dlc_candidate_checkpoints.csv",
        rows,
        [
            "seed",
            "seed_dir",
            "stage",
            "complete_model_set",
            "present_count",
            "round_robin_exists",
            "selection_score",
            "joint_transition_observer",
            "joint_transition",
            "individual_transition",
        ],
    )
    copied_csv = write_csv(
        tables / "paper_dlc_frozen_checkpoints.csv",
        copied,
        ["model_name", "source", "frozen_path", "size_bytes"],
    )
    registry_csv = write_csv(
        tables / "paper_dlc_registry_alignment.csv",
        registry_rows,
        ["algorithm", "registry_expected_path", "frozen_path", "path_matches_registry", "exists", "size_bytes"],
    )
    status = "pass" if all(row["exists"] and row["path_matches_registry"] for row in registry_rows) else "needs_training_or_freeze"
    if args.mode == "freeze" and selected and copied:
        status = "pass"
    if args.mode == "freeze" and not selected:
        status = "blocked_no_complete_candidate"
    report = {
        "status": status,
        "mode": args.mode,
        "experiment_dir": args.experiment_dir,
        "frozen_dir": args.frozen_dir,
        "stage": args.stage,
        "candidate_count": len(rows),
        "complete_candidate_count": sum(1 for row in rows if row["complete_model_set"]),
        "selected_candidate": selected,
        "copied_count": len(copied),
        "paths": {
            "candidate_checkpoints": candidate_csv,
            "frozen_checkpoints": copied_csv,
            "registry_alignment": registry_csv,
        },
        "selection_rule": "Use --select-seed if specified; otherwise choose the complete candidate with the highest per-seed round-robin mean-score average for the requested stage. If no round-robin exists, choose a complete model set deterministically.",
        "claim_boundary": "This script only freezes trained paper-DLC baseline checkpoints. It does not train them and does not make performance claims until online evaluation is run.",
    }
    manifest_path = write_json(out_dir / "paper_dlc_baseline_freeze_manifest.json", report)
    print(json.dumps({"manifest": manifest_path, "status": status, "candidate_count": len(rows), "complete_candidate_count": report["complete_candidate_count"]}, ensure_ascii=False, indent=2))
    if args.mode == "freeze" and status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

