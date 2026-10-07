#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def method_passes(report):
    return {
        int(row["seed"]): row["validation_status"] == "PASS"
        for row in report["rows"]
    }


def build_report(root):
    atlas = load_json(root / "tables" / "heldout2_failure_atlas.json")
    conservative = load_json(root / "tables" / "heldout2_overtake_conservative_traffic_targeted_report.json")
    recovery = load_json(root / "tables" / "heldout2_dagger_v2_recovery_conservative_suite_report.json")
    more_graph = load_json(root / "tables" / "heldout2_dagger_v2_expert_more_graph_suite_report.json")

    existing_pass = {
        int(row["seed"])
        for row in atlas["seed_rows"]
        if row["passing_methods"]
    }
    original_candidate_gap = set(atlas["summary"]["candidate_gap_seeds"])
    recovery_pass = {seed for seed, ok in method_passes(load_json(root / "evaluations" / "heldout2_dagger_v2_recovery_conservative_suite" / "multiseed_suite_summary.json")).items() if ok}
    conservative_pass = {
        seed
        for seed, ok in method_passes(
            load_json(root / "evaluations" / "heldout2_overtake_conservative_traffic_targeted" / "multiseed_suite_summary.json")
        ).items()
        if ok
    }
    more_graph_pass = {
        seed
        for seed, ok in method_passes(
            load_json(root / "evaluations" / "heldout2_dagger_v2_expert_more_graph_suite" / "multiseed_suite_summary.json")
        ).items()
        if ok
    }
    expanded_pass = existing_pass | recovery_pass | conservative_pass | more_graph_pass
    all_seeds = sorted({row["seed"] for row in atlas["seed_rows"]})
    remaining_candidate_gap = sorted(set(all_seeds) - expanded_pass)
    newly_covered = sorted(expanded_pass - existing_pass)

    rows = []
    recovery_suite = load_json(root / "evaluations" / "heldout2_dagger_v2_recovery_conservative_suite" / "multiseed_suite_summary.json")
    conservative_suite = load_json(root / "evaluations" / "heldout2_overtake_conservative_traffic_targeted" / "multiseed_suite_summary.json")
    more_graph_suite = load_json(root / "evaluations" / "heldout2_dagger_v2_expert_more_graph_suite" / "multiseed_suite_summary.json")
    existing_by_seed = {row["seed"]: row for row in atlas["seed_rows"]}
    recovery_by_seed = {int(row["seed"]): row for row in recovery_suite["rows"]}
    conservative_by_seed = {int(row["seed"]): row for row in conservative_suite["rows"]}
    more_graph_by_seed = {int(row["seed"]): row for row in more_graph_suite["rows"]}
    for seed in all_seeds:
        recovery_row = recovery_by_seed.get(seed)
        conservative_row = conservative_by_seed.get(seed)
        more_graph_row = more_graph_by_seed.get(seed)
        rows.append(
            {
                "seed": seed,
                "original_error_type": existing_by_seed[seed]["error_type"],
                "original_passing_methods": ", ".join(existing_by_seed[seed]["passing_methods"]),
                "recovery_conservative_status": recovery_row["validation_status"] if recovery_row else "not_run",
                "recovery_conservative_target_progress": recovery_row.get("target_tile_progress") if recovery_row else None,
                "recovery_conservative_target_grass": recovery_row.get("target_grass_rate") if recovery_row else None,
                "overtake_conservative_status": conservative_row["validation_status"] if conservative_row else "not_run",
                "expert_more_graph_status": more_graph_row["validation_status"] if more_graph_row else "not_run",
                "expert_more_graph_target_progress": more_graph_row.get("target_tile_progress") if more_graph_row else None,
                "expert_more_graph_target_grass": more_graph_row.get("target_grass_rate") if more_graph_row else None,
                "expanded_oracle_status": "PASS" if seed in expanded_pass else "FAIL",
            }
        )

    return {
        "root": str(root),
        "original_oracle": {
            "pass_count": atlas["summary"]["heldout2_selector"]["oracle_pass_count"],
            "n": atlas["summary"]["n"],
            "candidate_gap_seeds": sorted(original_candidate_gap),
        },
        "new_candidates": {
            "dagger_v2_recovery_conservative": {
                "suite": "evaluations/heldout2_dagger_v2_recovery_conservative_suite/multiseed_suite_summary.json",
                "pass_count": recovery["method_summaries"]["graph_recovery_adaptive_conservative_traffic"]["pass_count"],
                "n": recovery["method_summaries"]["graph_recovery_adaptive_conservative_traffic"]["n"],
                "pass_seeds": sorted(recovery_pass),
            },
            "overtake_conservative_traffic_targeted": {
                "suite": "evaluations/heldout2_overtake_conservative_traffic_targeted/multiseed_suite_summary.json",
                "pass_count": conservative["method_summaries"]["overtake_conservative_traffic"]["pass_count"],
                "n": conservative["method_summaries"]["overtake_conservative_traffic"]["n"],
                "pass_seeds": sorted(conservative_pass),
            },
            "dagger_v2_expert_more_graph": {
                "suite": "evaluations/heldout2_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
                "pass_count": more_graph["method_summaries"]["graph_expert_gate_shield_more_graph"]["pass_count"],
                "n": more_graph["method_summaries"]["graph_expert_gate_shield_more_graph"]["n"],
                "pass_seeds": sorted(more_graph_pass),
            },
        },
        "expanded_oracle": {
            "pass_count": len(expanded_pass),
            "n": len(all_seeds),
            "pass_seeds": sorted(expanded_pass),
            "newly_covered_seeds": newly_covered,
            "remaining_candidate_gap_seeds": remaining_candidate_gap,
        },
        "rows": rows,
        "interpretation": (
            "Adding the DAgger-v2 recovery-conservative and expert-more-graph candidates raises the "
            "heldout2 candidate oracle from 7/10 to 10/10. This is candidate-policy coverage progress, "
            "not an online selector result: the online selector remains unrerun with this expanded candidate "
            "pool, and the expert-more-graph candidate is complementary rather than strong as a standalone policy."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "seed",
            "original_error_type",
            "original_passing_methods",
            "recovery_conservative_status",
            "recovery_conservative_target_progress",
            "recovery_conservative_target_grass",
            "overtake_conservative_status",
            "expert_more_graph_status",
            "expert_more_graph_target_progress",
            "expert_more_graph_target_grass",
            "expanded_oracle_status",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow(row)


def fmt_float(value):
    if isinstance(value, (float, int)):
        return f"{float(value):.3f}"
    if value is None:
        return ""
    return str(value)


def write_markdown(report, path):
    original = report["original_oracle"]
    expanded = report["expanded_oracle"]
    recovery = report["new_candidates"]["dagger_v2_recovery_conservative"]
    conservative = report["new_candidates"]["overtake_conservative_traffic_targeted"]
    more_graph = report["new_candidates"]["dagger_v2_expert_more_graph"]
    lines = [
        "# Heldout2 Candidate Expansion",
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Original heldout2 candidate oracle: {original['pass_count']}/{original['n']}",
        f"- Expanded heldout2 candidate oracle: {expanded['pass_count']}/{expanded['n']}",
        f"- Newly covered seeds: {', '.join(str(seed) for seed in expanded['newly_covered_seeds']) or 'none'}",
        f"- Remaining candidate-gap seeds: {', '.join(str(seed) for seed in expanded['remaining_candidate_gap_seeds']) or 'none'}",
        "",
        "## New Candidate Results",
        "",
        f"- DAgger-v2 recovery-conservative suite: {recovery['pass_count']}/{recovery['n']} "
        f"(pass seeds: {', '.join(str(seed) for seed in recovery['pass_seeds'])})",
        f"- Overtake conservative-traffic targeted control: {conservative['pass_count']}/{conservative['n']} "
        f"(pass seeds: {', '.join(str(seed) for seed in conservative['pass_seeds']) or 'none'})",
        f"- DAgger-v2 expert-more-graph suite: {more_graph['pass_count']}/{more_graph['n']} "
        f"(pass seeds: {', '.join(str(seed) for seed in more_graph['pass_seeds']) or 'none'})",
        "",
        "## Seed-level Matrix",
        "",
        "| seed | original error | original passing methods | recovery-conservative | recovery progress | recovery grass | overtake-conservative | expert-more-graph | more-graph progress | more-graph grass | expanded oracle |",
        "|---:|---|---|---|---:|---:|---|---|---:|---:|---|",
    ]
    for row in report["rows"]:
        progress = row["recovery_conservative_target_progress"]
        grass = row["recovery_conservative_target_grass"]
        more_graph_progress = row["expert_more_graph_target_progress"]
        more_graph_grass = row["expert_more_graph_target_grass"]
        lines.append(
            f"| {row['seed']} | {row['original_error_type']} | {row['original_passing_methods'] or 'none'} | "
            f"{row['recovery_conservative_status']} | "
            f"{fmt_float(progress)} | "
            f"{fmt_float(grass)} | "
            f"{row['overtake_conservative_status']} | "
            f"{row['expert_more_graph_status']} | "
            f"{fmt_float(more_graph_progress)} | "
            f"{fmt_float(more_graph_grass)} | "
            f"{row['expanded_oracle_status']} |"
        )
    lines.extend(
        [
            "",
            "## Reporting Boundary",
            "",
            "- This report updates candidate-policy coverage, not online selector performance.",
            "- The expanded oracle is still an upper bound because it uses full validation outcomes.",
            "- The next policy target is selector evaluation/training with the expanded candidate pool, plus larger-N stress testing.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export heldout2 candidate expansion report.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    out_json = root / "tables" / "heldout2_candidate_expansion.json"
    out_md = root / "tables" / "heldout2_candidate_expansion.md"
    out_csv = root / "tables" / "heldout2_candidate_expansion_rows.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
