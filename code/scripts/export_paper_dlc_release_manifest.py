#!/usr/bin/env python
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


MODEL_NAMES = (
    "individual_transition",
    "joint_transition",
    "joint_transition_observer",
)
STAGES = ("20", "40", "80", "final")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path, role, seed=None, stage=None, model_name=None):
    path = Path(path)
    return {
        "role": role,
        "seed": seed,
        "stage": stage,
        "model_name": model_name,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "license_status": "author_confirmation_required",
    }


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-dir", default="outputs/tits_dynamic_graph_expanded/paper_dlc_baselines_training")
    parser.add_argument("--frozen-dir", default="outputs/tits_dynamic_graph_expanded/paper_dlc_baselines")
    parser.add_argument("--e1-manifest", default="outputs/tits_dynamic_graph_expanded/e1_200_summary/online_benchmark_summary_manifest.json")
    parser.add_argument("--e1-statistics", default="outputs/tits_dynamic_graph_expanded/e1_200_summary/tables/online_benchmark_nature_direct_statistics.csv")
    parser.add_argument("--e1-table-source", default="outputs/tits_dynamic_graph_expanded/e1_200_summary/tables/retrained_dlc_table_source.csv")
    parser.add_argument("--e1-table-dictionary", default="outputs/tits_dynamic_graph_expanded/e1_200_summary/tables/retrained_dlc_table_data_dictionary.md")
    args = parser.parse_args()

    training_dir = Path(args.training_dir)
    frozen_dir = Path(args.frozen_dir)
    tables_dir = frozen_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    training_rows = []
    selection_rows = []
    artifacts = []

    for seed_dir in sorted(training_dir.glob("seed_*")):
        seed = int(seed_dir.name.split("_", 1)[1])
        summary_path = seed_dir / "models" / "train_summary.json"
        summary = read_json(summary_path)
        metrics = summary.get("metrics", {})
        update_counts = sorted({
            int(metrics.get(name, {}).get("actor_updates", 0))
            for name in MODEL_NAMES
        })
        training_rows.append({
            "seed": seed,
            "episodes": summary.get("episodes"),
            "max_steps": summary.get("max_steps"),
            "transitions_recorded": summary.get("transitions"),
            "actor_updates_by_model": ";".join(map(str, update_counts)),
            "behavior_policy": summary.get("behavior_policy"),
            "train_summary_path": str(summary_path),
            "train_summary_sha256": sha256_file(summary_path),
        })
        artifacts.append(file_record(summary_path, "training_summary", seed=seed))

        round_robin_path = seed_dir / "round_robin_final.json"
        round_robin = read_json(round_robin_path)
        values = []
        for pairing in round_robin.get("pairings", {}).values():
            values.extend(float(item) for item in pairing.get("mean_score", []) if item is not None)
        selection_rows.append({
            "seed": seed,
            "selection_score": sum(values) / len(values) if values else None,
            "round_robin_path": str(round_robin_path),
            "round_robin_sha256": sha256_file(round_robin_path),
        })
        artifacts.append(file_record(round_robin_path, "selection_validation", seed=seed, stage="final"))

        for stage in STAGES:
            model_dir = seed_dir / "models" if stage == "final" else seed_dir / "models" / f"step_{stage}"
            for model_name in MODEL_NAMES:
                model_path = model_dir / f"{model_name}.pt"
                if model_path.exists():
                    artifacts.append(file_record(
                        model_path,
                        "candidate_checkpoint",
                        seed=seed,
                        stage=stage,
                        model_name=model_name,
                    ))

    freeze_manifest_path = frozen_dir / "paper_dlc_baseline_freeze_manifest.json"
    freeze_manifest = read_json(freeze_manifest_path)
    selected_seed = freeze_manifest.get("selected_candidate", {}).get("seed")

    for model_name in MODEL_NAMES:
        model_path = frozen_dir / f"{model_name}.pt"
        artifacts.append(file_record(
            model_path,
            "frozen_checkpoint",
            seed=selected_seed,
            stage="final",
            model_name=model_name,
        ))

    benchmark_records = []
    for path in (
        Path(args.e1_manifest),
        Path(args.e1_statistics),
        Path(args.e1_table_source),
        Path(args.e1_table_dictionary),
    ):
        benchmark_records.append({
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    write_csv(
        tables_dir / "paper_dlc_training_summary.csv",
        training_rows,
        [
            "seed", "episodes", "max_steps", "transitions_recorded",
            "actor_updates_by_model", "behavior_policy",
            "train_summary_path", "train_summary_sha256",
        ],
    )
    write_csv(
        tables_dir / "paper_dlc_selection_scores.csv",
        selection_rows,
        ["seed", "selection_score", "round_robin_path", "round_robin_sha256"],
    )
    write_csv(
        tables_dir / "paper_dlc_artifact_checksums.csv",
        artifacts,
        [
            "role", "seed", "stage", "model_name", "path",
            "size_bytes", "sha256", "license_status",
        ],
    )

    report = {
        "status": "pass",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_seed": selected_seed,
        "selection_rule": freeze_manifest.get("selection_rule"),
        "training_seed_count": len(training_rows),
        "training_summaries": training_rows,
        "selection_scores": selection_rows,
        "artifact_count": len(artifacts),
        "benchmark_linkage": benchmark_records,
        "paths": {
            "training_summary_csv": str(tables_dir / "paper_dlc_training_summary.csv"),
            "selection_scores_csv": str(tables_dir / "paper_dlc_selection_scores.csv"),
            "artifact_checksums_csv": str(tables_dir / "paper_dlc_artifact_checksums.csv"),
        },
        "temporal_claim_boundary": (
            "This regenerated release manifest proves current artifact identity and "
            "the documented selection rule. It does not independently prove the "
            "wall-clock order of the original freeze relative to the E1 online run."
        ),
        "license_boundary": (
            "License status is author_confirmation_required for model/checkpoint "
            "artifacts until training-data, track, and third-party rights are confirmed."
        ),
    }
    out_path = frozen_dir / "paper_dlc_release_manifest.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "manifest": str(out_path),
        "artifact_count": len(artifacts),
        "training_seed_count": len(training_rows),
        "selected_seed": selected_seed,
    }, indent=2))


if __name__ == "__main__":
    main()
