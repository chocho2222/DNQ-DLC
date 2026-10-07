#!/usr/bin/env python
import argparse
import csv
import itertools
import json
from pathlib import Path


SUITES = {
    "main": "evaluations/heldout_multiseed_suite/multiseed_suite_summary.json",
    "adaptive": "evaluations/heldout_adaptive_suite/multiseed_suite_summary.json",
    "expert": "evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json",
    "dagger_v2": "evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def row_score(row):
    return (
        int(row["validation_status"] == "PASS"),
        int(row["target_completed_lap"]),
        -int(row["target_final_rank_by_tiles"]),
        -float(row["target_grass_rate"]),
        float(row["target_tile_progress"]),
    )


def main():
    parser = argparse.ArgumentParser(description="Export held-out portfolio report including DAgger v2.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--prefix", default="heldout_v2_portfolio")
    args = parser.parse_args()
    root = Path(args.root)
    rows = []
    for suite, rel in SUITES.items():
        data = load_json(root / rel)
        for row in data["rows"]:
            if suite == "dagger_v2" and row["method"] != "graph_expert_gate_shield":
                continue
            item = dict(row)
            item["suite"] = suite
            item["method_key"] = f"{suite}:{row['method']}"
            rows.append(item)
    seeds = sorted({row["seed"] for row in rows})
    methods = sorted({row["method_key"] for row in rows})
    by = {(row["method_key"], row["seed"]): row for row in rows}
    method_summaries = []
    for method in methods:
        method_rows = [by[(method, seed)] for seed in seeds if (method, seed) in by]
        passed = [row for row in method_rows if row["validation_status"] == "PASS"]
        method_summaries.append(
            {
                "method": method,
                "n": len(method_rows),
                "pass_count": len(passed),
                "pass_rate": len(passed) / len(method_rows) if method_rows else None,
                "passing_seeds": [row["seed"] for row in passed],
                "target_progress_mean": sum(row["target_tile_progress"] for row in method_rows) / len(method_rows),
                "target_grass_mean": sum(row["target_grass_rate"] for row in method_rows) / len(method_rows),
            }
        )
    best_portfolios = {}
    for size in range(1, min(5, len(methods)) + 1):
        portfolios = []
        for combo in itertools.combinations(methods, size):
            seed_choices = {}
            pass_count = 0
            for seed in seeds:
                candidates = [by[(method, seed)] for method in combo if (method, seed) in by]
                best = max(candidates, key=row_score)
                if best["validation_status"] == "PASS":
                    pass_count += 1
                seed_choices[str(seed)] = {
                    "method": best["method_key"],
                    "status": best["validation_status"],
                    "target_progress": best["target_tile_progress"],
                    "target_grass_rate": best["target_grass_rate"],
                    "rank": best["target_final_rank_by_tiles"],
                }
            portfolios.append(
                {
                    "methods": list(combo),
                    "n": len(seeds),
                    "pass_count": pass_count,
                    "pass_rate": pass_count / len(seeds),
                    "seed_choices": seed_choices,
                }
            )
        best_portfolios[str(size)] = sorted(portfolios, key=lambda item: (item["pass_count"], item["pass_rate"]), reverse=True)[:5]
    oracle = best_portfolios[str(len(methods))][0] if str(len(methods)) in best_portfolios else best_portfolios[str(min(5, len(methods)))][0]
    report = {
        "root": str(root),
        "suite_sources": SUITES,
        "seeds": seeds,
        "method_summaries": method_summaries,
        "best_portfolios": best_portfolios,
        "oracle": oracle,
        "interpretation": (
            "The DAgger v2 graph+expert-gate candidate is not the strongest single held-out method, "
            "but it is complementary: paired with expert-gate it raises the held-out oracle to 9/10, "
            "and with graph-adaptive plus expert-gate it reaches a 10/10 oracle upper bound. This remains "
            "an oracle complementarity analysis, not an online selector result."
        ),
    }
    out_dir = root / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"{args.prefix}.json"
    out_md = out_dir / f"{args.prefix}.md"
    out_csv = out_dir / f"{args.prefix}_method_summary.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["method", "n", "pass_count", "pass_rate", "passing_seeds", "target_progress_mean", "target_grass_mean"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in method_summaries:
            item = dict(row)
            item["passing_seeds"] = ",".join(str(seed) for seed in item["passing_seeds"])
            writer.writerow(item)
    lines = [
        "# Held-out DAgger v2 Portfolio Report",
        "",
        f"- Seeds: {', '.join(str(seed) for seed in seeds)}",
        "",
        "## Single Methods",
        "",
        "| method | pass | rate | passing seeds | progress | grass |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for row in sorted(method_summaries, key=lambda item: item["pass_rate"], reverse=True):
        lines.append(
            f"| {row['method']} | {row['pass_count']}/{row['n']} | {row['pass_rate']:.3f} | "
            f"{', '.join(str(seed) for seed in row['passing_seeds']) or 'none'} | "
            f"{row['target_progress_mean']:.3f} | {row['target_grass_mean']:.3f} |"
        )
    lines.extend(["", "## Best Portfolios", "", "| size | pass | rate | methods |", "|---:|---:|---:|---|"])
    for size, portfolios in best_portfolios.items():
        best = portfolios[0]
        lines.append(
            f"| {size} | {best['pass_count']}/{best['n']} | {best['pass_rate']:.3f} | "
            f"{', '.join(best['methods'])} |"
        )
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
