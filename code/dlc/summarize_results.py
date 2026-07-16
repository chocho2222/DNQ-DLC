import argparse
import csv
import json
from pathlib import Path


def split_pairing(pairing):
    left, right = pairing.split("_vs_")
    return left, right


def format_float(value):
    return f"{float(value):.6g}"


def flatten_rows(summary):
    rows = []
    for stage_name, stage_results in summary["aggregate"].items():
        for pairing, metrics in stage_results.items():
            left, right = split_pairing(pairing)
            rows.append(
                {
                    "stage": stage_name,
                    "pairing": pairing,
                    "method_a": left,
                    "method_b": right,
                    "win_ratio_a_mean": metrics["win_ratio_mean"][0],
                    "win_ratio_a_std": metrics["win_ratio_std"][0],
                    "win_ratio_b_mean": metrics["win_ratio_mean"][1],
                    "win_ratio_b_std": metrics["win_ratio_std"][1],
                    "score_a_mean": metrics["mean_score_mean"][0],
                    "score_a_std": metrics["mean_score_std"][0],
                    "score_b_mean": metrics["mean_score_mean"][1],
                    "score_b_std": metrics["mean_score_std"][1],
                }
            )
    return rows


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "stage",
        "pairing",
        "method_a",
        "method_b",
        "win_ratio_a_mean",
        "win_ratio_a_std",
        "win_ratio_b_mean",
        "win_ratio_b_std",
        "score_a_mean",
        "score_a_std",
        "score_b_mean",
        "score_b_std",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_markdown(path, rows, summary):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# DLC Telemetry Experiment Summary",
        "",
        f"- Seeds: {summary.get('seeds', [])}",
        f"- Training races per seed: {summary.get('train_episodes')}",
        f"- Evaluation races per pairing: {summary.get('eval_episodes')}",
        "",
        "| Stage | Pairing | Win A | Win B | Score A | Score B |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {stage} | {method_a} vs {method_b} | {wa} +/- {wsa} | {wb} +/- {wsb} | {sa} +/- {ssa} | {sb} +/- {ssb} |".format(
                stage=row["stage"],
                method_a=row["method_a"],
                method_b=row["method_b"],
                wa=format_float(row["win_ratio_a_mean"]),
                wsa=format_float(row["win_ratio_a_std"]),
                wb=format_float(row["win_ratio_b_mean"]),
                wsb=format_float(row["win_ratio_b_std"]),
                sa=format_float(row["score_a_mean"]),
                ssa=format_float(row["score_a_std"]),
                sb=format_float(row["score_b_mean"]),
                ssb=format_float(row["score_b_std"]),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Export DLC telemetry aggregate_summary.json to CSV and Markdown."
    )
    parser.add_argument("summary_json")
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    summary_path = Path(args.summary_json)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir) if args.out_dir else summary_path.parent
    rows = flatten_rows(summary)
    write_csv(out_dir / "summary.csv", rows)
    write_markdown(out_dir / "summary.md", rows, summary)
    print(json.dumps({
        "rows": len(rows),
        "csv": str(out_dir / "summary.csv"),
        "markdown": str(out_dir / "summary.md"),
    }, indent=2))


if __name__ == "__main__":
    main()

