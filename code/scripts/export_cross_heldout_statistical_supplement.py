#!/usr/bin/env python
import argparse
import csv
import json
import math
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def wilson_ci(successes, n, z=1.959963984540054):
    if n == 0:
        return [None, None]
    p = successes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def sign_test_pvalue(successes, n, null_p=0.5):
    if n == 0:
        return None
    lower = sum(math.comb(n, k) * (null_p**k) * ((1.0 - null_p) ** (n - k)) for k in range(0, successes + 1))
    upper = sum(math.comb(n, k) * (null_p**k) * ((1.0 - null_p) ** (n - k)) for k in range(successes, n + 1))
    return min(1.0, 2.0 * min(lower, upper))


def exact_mcnemar_pvalue(b, c):
    discordant = b + c
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, k) for k in range(0, min(b, c) + 1)) / (2**discordant)
    return min(1.0, 2.0 * tail)


def entry_stats(row):
    n = row["n"]
    selector = row["selector_pass_count"]
    oracle = row["oracle_pass_count"]
    selector_miss = len(row["selector_miss_seeds"])
    candidate_gap = len(row["candidate_gap_seeds"])
    selector_only_success = 0
    oracle_only_success = max(0, oracle - selector)
    return {
        "heldout": row["heldout"],
        "stage": row["stage"],
        "status": row["status"],
        "n": n,
        "selector_pass_count": selector,
        "oracle_pass_count": oracle,
        "selector_pass_rate": selector / n,
        "oracle_pass_rate": oracle / n,
        "selector_ci95_low": wilson_ci(selector, n)[0],
        "selector_ci95_high": wilson_ci(selector, n)[1],
        "oracle_ci95_low": wilson_ci(oracle, n)[0],
        "oracle_ci95_high": wilson_ci(oracle, n)[1],
        "selector_oracle_gap_count": oracle - selector,
        "selector_oracle_gap_rate": (oracle - selector) / n,
        "selector_miss_count": selector_miss,
        "candidate_gap_count": candidate_gap,
        "failed_count": len(row["failed_seeds"]),
        "selector_miss_seeds": row["selector_miss_seeds"],
        "candidate_gap_seeds": row["candidate_gap_seeds"],
        "oracle_only_successes": oracle_only_success,
        "selector_only_successes": selector_only_success,
        "mcnemar_exact_p_selector_vs_oracle": exact_mcnemar_pvalue(selector_only_success, oracle_only_success),
        "selector_sign_test_p_vs_half": sign_test_pvalue(selector, n),
        "oracle_sign_test_p_vs_half": sign_test_pvalue(oracle, n),
    }


def aggregate_stats(report):
    agg = report["aggregate_expanded_or_later"]
    n = agg["n"]
    selector = agg["selector_pass_count"]
    oracle = agg["oracle_pass_count"]
    gap = agg["selector_oracle_gap"]
    return {
        "label": "expanded_or_later",
        "n": n,
        "selector_pass_count": selector,
        "oracle_pass_count": oracle,
        "selector_pass_rate": selector / n,
        "oracle_pass_rate": oracle / n,
        "selector_ci95_low": wilson_ci(selector, n)[0],
        "selector_ci95_high": wilson_ci(selector, n)[1],
        "oracle_ci95_low": wilson_ci(oracle, n)[0],
        "oracle_ci95_high": wilson_ci(oracle, n)[1],
        "selector_oracle_gap_count": gap,
        "selector_oracle_gap_rate": gap / n,
        "mcnemar_exact_p_selector_vs_oracle": exact_mcnemar_pvalue(0, gap),
        "selector_sign_test_p_vs_half": sign_test_pvalue(selector, n),
        "oracle_sign_test_p_vs_half": sign_test_pvalue(oracle, n),
    }


def source_data_dictionary():
    return [
        {"field": "panel", "meaning": "Figure panel in which the row is used."},
        {"field": "heldout", "meaning": "Held-out seed batch label."},
        {"field": "stage", "meaning": "Candidate-pool or validation stage."},
        {"field": "status", "meaning": "Interpretation label for the held-out stage."},
        {"field": "n", "meaning": "Number of seeds in the row."},
        {"field": "selector_pass_count", "meaning": "Strict PASS count for the online simulator-loop selector."},
        {"field": "oracle_pass_count", "meaning": "Strict PASS count for the diagnostic candidate oracle."},
        {"field": "selector_pass_rate", "meaning": "selector_pass_count divided by n."},
        {"field": "oracle_pass_rate", "meaning": "oracle_pass_count divided by n."},
        {"field": "selector_miss_count", "meaning": "Failed seeds where at least one candidate passed but the selector chose a failing one."},
        {"field": "candidate_gap_count", "meaning": "Failed seeds where no tested candidate achieved strict PASS."},
        {"field": "failed_count", "meaning": "Number of selector failed seeds."},
        {"field": "selector_miss_seeds", "meaning": "Semicolon-separated selector miss seed list."},
        {"field": "candidate_gap_seeds", "meaning": "Semicolon-separated candidate gap seed list."},
    ]


def build_report(root):
    synthesis = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")
    heldout4 = load_json(root / "tables" / "heldout4_external_validation.json")
    rows = [entry_stats(row) for row in synthesis["entries"]]
    aggregate = aggregate_stats(synthesis)
    heldout4_entry = next(row for row in rows if row["heldout"] == "heldout4")
    return {
        "root": str(root),
        "sources": [
            "tables/cross_heldout_validation_synthesis.json",
            "tables/heldout4_external_validation.json",
            "figures/figure_3_source_data.csv",
        ],
        "stage_statistics": rows,
        "aggregate_expanded_or_later": aggregate,
        "heldout4_statistical_summary": {
            "selector_pass_count": heldout4["selector"]["pass_count"],
            "selector_n": heldout4["selector"]["n"],
            "selector_ci95": wilson_ci(heldout4["selector"]["pass_count"], heldout4["selector"]["n"]),
            "oracle_pass_count": heldout4["oracle"]["pass_count"],
            "oracle_n": heldout4["oracle"]["n"],
            "oracle_ci95": wilson_ci(heldout4["oracle"]["pass_count"], heldout4["oracle"]["n"]),
            "selector_miss_count": len(heldout4["selector"]["selector_miss_seeds"]),
            "candidate_gap_count": len(heldout4["oracle"]["candidate_gap_seeds"]),
            "selector_miss_seeds": heldout4["selector"]["selector_miss_seeds"],
            "candidate_gap_seeds": heldout4["oracle"]["candidate_gap_seeds"],
            "mcnemar_exact_p_selector_vs_oracle": heldout4_entry["mcnemar_exact_p_selector_vs_oracle"],
        },
        "figure_3_source_data_dictionary": source_data_dictionary(),
        "interpretation": (
            "The supplement adds uncertainty intervals and exact paired selector-oracle gap tests to Figure 3. "
            "Because each held-out stage has only 10 seeds and the aggregate mixes development stages, these "
            "statistics are descriptive and should not be used as confirmatory evidence for a broad robustness claim."
        ),
    }


def write_csv(report, root):
    stage_csv = root / "tables" / "cross_heldout_statistical_supplement_rows.csv"
    fields = [
        "heldout",
        "stage",
        "status",
        "n",
        "selector_pass_count",
        "oracle_pass_count",
        "selector_pass_rate",
        "oracle_pass_rate",
        "selector_ci95_low",
        "selector_ci95_high",
        "oracle_ci95_low",
        "oracle_ci95_high",
        "selector_oracle_gap_count",
        "selector_oracle_gap_rate",
        "selector_miss_count",
        "candidate_gap_count",
        "failed_count",
        "selector_miss_seeds",
        "candidate_gap_seeds",
        "mcnemar_exact_p_selector_vs_oracle",
        "selector_sign_test_p_vs_half",
        "oracle_sign_test_p_vs_half",
    ]
    with stage_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["stage_statistics"]:
            writer.writerow(
                {
                    key: (
                        ";".join(map(str, row[key]))
                        if key in {"selector_miss_seeds", "candidate_gap_seeds"}
                        else row.get(key)
                    )
                    for key in fields
                }
            )

    dict_csv = root / "figures" / "figure_3_source_data_dictionary.csv"
    with dict_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["field", "meaning"])
        writer.writeheader()
        writer.writerows(report["figure_3_source_data_dictionary"])
    return stage_csv, dict_csv


def write_markdown(report, path):
    lines = [
        "# Cross-heldout Statistical Supplement",
        "",
        report["interpretation"],
        "",
        "## Stage Statistics",
        "",
        "| heldout | stage | selector | selector Wilson 95% CI | oracle | oracle Wilson 95% CI | gap | selector misses | candidate gaps | McNemar p |",
        "|---|---|---:|---|---:|---|---:|---|---|---:|",
    ]
    for row in report["stage_statistics"]:
        lines.append(
            f"| {row['heldout']} | {row['stage']} | {row['selector_pass_count']}/{row['n']} | "
            f"[{row['selector_ci95_low']:.3f}, {row['selector_ci95_high']:.3f}] | "
            f"{row['oracle_pass_count']}/{row['n']} | "
            f"[{row['oracle_ci95_low']:.3f}, {row['oracle_ci95_high']:.3f}] | "
            f"{row['selector_oracle_gap_count']} | "
            f"{', '.join(map(str, row['selector_miss_seeds'])) or 'none'} | "
            f"{', '.join(map(str, row['candidate_gap_seeds'])) or 'none'} | "
            f"{row['mcnemar_exact_p_selector_vs_oracle']:.3f} |"
        )
    agg = report["aggregate_expanded_or_later"]
    lines.extend(
        [
            "",
            "## Expanded-or-later Aggregate",
            "",
            f"- Selector: {agg['selector_pass_count']}/{agg['n']} "
            f"(Wilson 95% CI [{agg['selector_ci95_low']:.3f}, {agg['selector_ci95_high']:.3f}])",
            f"- Diagnostic oracle: {agg['oracle_pass_count']}/{agg['n']} "
            f"(Wilson 95% CI [{agg['oracle_ci95_low']:.3f}, {agg['oracle_ci95_high']:.3f}])",
            f"- Selector-oracle gap: {agg['selector_oracle_gap_count']} seeds "
            f"({agg['selector_oracle_gap_rate']:.3f} of evaluated seeds)",
            f"- Exact McNemar p for selector-vs-oracle discordance: {agg['mcnemar_exact_p_selector_vs_oracle']:.6f}",
            "",
            "## Heldout4 Focus",
            "",
        ]
    )
    h4 = report["heldout4_statistical_summary"]
    lines.extend(
        [
            f"- Selector: {h4['selector_pass_count']}/{h4['selector_n']} "
            f"(Wilson 95% CI [{h4['selector_ci95'][0]:.3f}, {h4['selector_ci95'][1]:.3f}])",
            f"- Diagnostic oracle: {h4['oracle_pass_count']}/{h4['oracle_n']} "
            f"(Wilson 95% CI [{h4['oracle_ci95'][0]:.3f}, {h4['oracle_ci95'][1]:.3f}])",
            f"- Selector misses: {h4['selector_miss_count']} ({', '.join(map(str, h4['selector_miss_seeds']))})",
            f"- Candidate gaps: {h4['candidate_gap_count']} ({', '.join(map(str, h4['candidate_gap_seeds']))})",
            f"- Exact McNemar p for selector-vs-oracle discordance: {h4['mcnemar_exact_p_selector_vs_oracle']:.3f}",
            "",
            "## Figure 3 Source-data Dictionary",
            "",
            "| field | meaning |",
            "|---|---|",
        ]
    )
    for row in report["figure_3_source_data_dictionary"]:
        lines.append(f"| {row['field']} | {row['meaning']} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export cross-heldout statistical supplement.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    out_json = root / "tables" / "cross_heldout_statistical_supplement.json"
    out_md = root / "tables" / "cross_heldout_statistical_supplement.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    stage_csv, dict_csv = write_csv(report, root)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "stage_csv": str(stage_csv),
                "figure3_dictionary_csv": str(dict_csv),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
