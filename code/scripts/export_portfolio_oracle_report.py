#!/usr/bin/env python
import argparse
import csv
import itertools
import json
from pathlib import Path


DEFAULT_SUITES = [
    {
        "name": "main",
        "path": "evaluations/multiseed_suite/multiseed_suite_summary.json",
        "targeted": False,
    },
    {
        "name": "adaptive",
        "path": "evaluations/adaptive_gate_suite/multiseed_suite_summary.json",
        "targeted": False,
    },
    {
        "name": "recovery",
        "path": "evaluations/recovery_adaptive_suite/multiseed_suite_summary.json",
        "targeted": False,
    },
    {
        "name": "expert_targeted",
        "path": "evaluations/expert_gate_targeted/multiseed_suite_summary.json",
        "targeted": True,
    },
]


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
    parser = argparse.ArgumentParser(description="Export method portfolio and oracle upper-bound report.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--out-prefix", default="portfolio_oracle")
    parser.add_argument("--include-targeted", action="store_true")
    parser.add_argument("--portfolio-sizes", default="2,3")
    args = parser.parse_args()

    root = Path(args.root)
    rows = []
    included_suites = []
    targeted_appendix = []
    for suite_def in DEFAULT_SUITES:
        suite_name = suite_def["name"]
        rel_path = suite_def["path"]
        is_targeted = suite_def["targeted"]
        if is_targeted and not args.include_targeted:
            path = root / rel_path
            if path.exists():
                suite = load_json(path)
                targeted_appendix.append(
                    {
                        "suite": suite_name,
                        "path": str(path),
                        "seeds": suite.get("seeds", []),
                        "by_method": suite.get("by_method", {}),
                    }
                )
            continue
        path = root / rel_path
        if not path.exists():
            continue
        included_suites.append({"suite": suite_name, "path": str(path), "targeted": is_targeted})
        suite = load_json(path)
        for row in suite["rows"]:
            item = dict(row)
            item["suite"] = suite_name
            item["method_key"] = f"{suite_name}:{row['method']}"
            rows.append(item)

    seeds = sorted({row["seed"] for row in rows})
    methods = sorted({row["method_key"] for row in rows})
    by_method_seed = {
        (row["method_key"], row["seed"]): row
        for row in rows
    }

    method_summaries = {}
    for method in methods:
        method_rows = [by_method_seed[(method, seed)] for seed in seeds if (method, seed) in by_method_seed]
        if not method_rows:
            continue
        passes = sum(row["validation_status"] == "PASS" for row in method_rows)
        method_summaries[method] = {
            "n": len(method_rows),
            "pass_count": passes,
            "pass_rate": passes / len(method_rows),
        }

    portfolio_sizes = [int(item.strip()) for item in args.portfolio_sizes.split(",") if item.strip()]
    portfolio_results = {}
    for size in portfolio_sizes:
        portfolios = []
        for combination in itertools.combinations(methods, size):
            covered = []
            seed_choices = {}
            for seed in seeds:
                candidates = [
                    by_method_seed[(method, seed)]
                    for method in combination
                    if (method, seed) in by_method_seed
                ]
                if not candidates:
                    continue
                best = max(candidates, key=row_score)
                covered.append(best["validation_status"] == "PASS")
                seed_choices[str(seed)] = {
                    "method": best["method_key"],
                    "status": best["validation_status"],
                    "target_progress": best["target_tile_progress"],
                    "target_grass_rate": best["target_grass_rate"],
                    "rank": best["target_final_rank_by_tiles"],
                }
            if len(covered) == len(seeds):
                portfolios.append(
                    {
                        "methods": list(combination),
                        "n": len(covered),
                        "pass_count": sum(covered),
                        "pass_rate": sum(covered) / len(covered),
                        "seed_choices": seed_choices,
                    }
                )
        portfolios.sort(key=lambda item: (item["pass_rate"], item["pass_count"]), reverse=True)
        portfolio_results[str(size)] = portfolios[:10]

    portfolio_pairs = portfolio_results.get("2", [])

    oracle_choices = {}
    oracle_pass_count = 0
    for seed in seeds:
        candidates = [row for row in rows if row["seed"] == seed]
        best = max(candidates, key=row_score)
        oracle_choices[str(seed)] = {
            "method": best["method_key"],
            "status": best["validation_status"],
            "target_progress": best["target_tile_progress"],
            "target_grass_rate": best["target_grass_rate"],
            "rank": best["target_final_rank_by_tiles"],
            "target_completed_lap": best["target_completed_lap"],
        }
        oracle_pass_count += int(best["validation_status"] == "PASS")

    report = {
        "root": str(root),
        "included_suites": included_suites,
        "targeted_appendix": targeted_appendix,
        "seeds": seeds,
        "method_summaries": method_summaries,
        "best_pair_portfolios": portfolio_pairs,
        "best_portfolios": portfolio_results,
        "oracle": {
            "n": len(seeds),
            "pass_count": oracle_pass_count,
            "pass_rate": oracle_pass_count / len(seeds) if seeds else None,
            "seed_choices": oracle_choices,
        },
        "interpretation": (
            "The methods are complementary across seeds. The strongest single method is "
            "the rule-based overtake controller. Two-method portfolios improve coverage "
            "but do not cover every current seed; three-method and full-oracle upper "
            "bounds motivate a learned, seed-agnostic portfolio selector."
        ),
    }

    table_dir = root / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    out_json = table_dir / f"{args.out_prefix}.json"
    out_md = table_dir / f"{args.out_prefix}.md"
    out_csv = table_dir / f"{args.out_prefix}_rows.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["section", "methods", "n", "pass_count", "pass_rate"],
        )
        writer.writeheader()
        for method, item in sorted(method_summaries.items(), key=lambda kv: kv[1]["pass_rate"], reverse=True):
            writer.writerow(
                {
                    "section": "single_method",
                    "methods": method,
                    "n": item["n"],
                    "pass_count": item["pass_count"],
                    "pass_rate": f"{item['pass_rate']:.6f}",
                }
            )
        for size, portfolios in portfolio_results.items():
            for item in portfolios:
                writer.writerow(
                    {
                        "section": f"portfolio_{size}",
                        "methods": " + ".join(item["methods"]),
                        "n": item["n"],
                        "pass_count": item["pass_count"],
                        "pass_rate": f"{item['pass_rate']:.6f}",
                    }
                )
        writer.writerow(
            {
                "section": "oracle",
                "methods": "all_available_full_suite_methods",
                "n": len(seeds),
                "pass_count": oracle_pass_count,
                "pass_rate": f"{oracle_pass_count / len(seeds):.6f}" if seeds else "",
            }
        )

    lines = [
        "# Portfolio Oracle Report",
        "",
        f"- Included suites: {', '.join(item['suite'] for item in included_suites)}",
        f"- Seeds: {', '.join(str(seed) for seed in seeds)}",
        f"- Oracle pass rate: {oracle_pass_count}/{len(seeds)}",
        "",
        "## Single Methods",
        "",
        "| method | n | pass | pass rate |",
        "|---|---:|---:|---:|",
    ]
    for method, item in sorted(method_summaries.items(), key=lambda kv: kv[1]["pass_rate"], reverse=True):
        lines.append(f"| {method} | {item['n']} | {item['pass_count']} | {item['pass_rate']:.3f} |")
    lines.extend(["", "## Best Two-method Portfolios", "", "| methods | n | pass | pass rate |", "|---|---:|---:|---:|"])
    for item in portfolio_pairs:
        lines.append(
            f"| {' + '.join(item['methods'])} | {item['n']} | {item['pass_count']} | {item['pass_rate']:.3f} |"
        )
    if "3" in portfolio_results:
        lines.extend(
            [
                "",
                "## Best Three-method Portfolios",
                "",
                "| methods | n | pass | pass rate |",
                "|---|---:|---:|---:|",
            ]
        )
        for item in portfolio_results["3"]:
            lines.append(
                f"| {' + '.join(item['methods'])} | {item['n']} | {item['pass_count']} | {item['pass_rate']:.3f} |"
            )
    lines.extend(["", "## Oracle Seed Choices", "", "| seed | method | status | progress | grass | rank |", "|---:|---|---|---:|---:|---:|"])
    for seed in seeds:
        item = oracle_choices[str(seed)]
        lines.append(
            f"| {seed} | {item['method']} | {item['status']} | {item['target_progress']:.3f} | "
            f"{item['target_grass_rate']:.3f} | {item['rank']} |"
        )
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    if targeted_appendix:
        lines.extend(["", "## Targeted Appendix Excluded From Main Portfolio", ""])
        for item in targeted_appendix:
            lines.append(f"- {item['suite']}: seeds={item['seeds']}, path={item['path']}")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
