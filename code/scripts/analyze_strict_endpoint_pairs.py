#!/usr/bin/env python
"""Paired inference for strict overtaking endpoints from an audit ledger."""

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


DEFAULT_ENDPOINTS = [
    "strict_completion", "physical_pass", "event_contact_free",
    "event_on_track", "sustained_lead", "post_pass_stable",
]


def truth(value):
    return str(value).strip().lower() in {"1", "true", "yes"}


def case_key(row):
    return (
        row.get("experiment_id", ""), row.get("track_id", ""),
        int(row["num_agents"]), int(row["seed"]), int(row.get("case_index", -1)),
    )


def bootstrap_difference(values, repeats, seed):
    values = np.asarray(values, dtype=np.float64)
    if not len(values):
        return None, None
    if len(values) == 1:
        return float(values[0]), float(values[0])
    rng = np.random.default_rng(seed)
    chunk = min(2000, repeats)
    means = []
    remaining = repeats
    while remaining:
        count = min(chunk, remaining)
        indices = rng.integers(0, len(values), size=(count, len(values)))
        means.append(values[indices].mean(axis=1))
        remaining -= count
    samples = np.concatenate(means)
    return float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))


def exact_mcnemar(b, c):
    n = int(b + c)
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(b, c) + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def holm_adjust(items, p_key, out_key, family_key):
    families = defaultdict(list)
    for index, item in enumerate(items):
        families[family_key(item)].append((index, float(item[p_key])))
    for members in families.values():
        ordered = sorted(members, key=lambda pair: pair[1])
        running = 0.0
        m = len(ordered)
        for rank, (index, p_value) in enumerate(ordered):
            adjusted = min(1.0, (m - rank) * p_value)
            running = max(running, adjusted)
            items[index][out_key] = running


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode-csv", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--comparators", default="", help="Comma-separated list; empty uses every other algorithm.")
    parser.add_argument("--endpoints", default=",".join(DEFAULT_ENDPOINTS))
    parser.add_argument("--bootstrap-repeats", type=int, default=20000)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    source = Path(args.episode_csv).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(source.open(encoding="utf-8")))
    endpoints = [item.strip() for item in args.endpoints.split(",") if item.strip()]
    algorithms = sorted({row["algorithm"] for row in rows})
    comparators = [item.strip() for item in args.comparators.split(",") if item.strip()]
    if not comparators:
        comparators = [name for name in algorithms if name != args.reference]
    unknown = set([args.reference] + comparators) - set(algorithms)
    if unknown:
        raise ValueError(f"algorithms absent from audit ledger: {sorted(unknown)}")

    scopes = ["ALL"] + sorted({row.get("experiment_id", "") for row in rows})
    results = []
    for scope in scopes:
        scoped = rows if scope == "ALL" else [row for row in rows if row.get("experiment_id") == scope]
        by_algorithm = {
            name: {case_key(row): row for row in scoped if row["algorithm"] == name}
            for name in [args.reference] + comparators
        }
        for comparator in comparators:
            keys = sorted(set(by_algorithm[args.reference]) & set(by_algorithm[comparator]))
            if not keys:
                continue
            for endpoint in endpoints:
                reference_values = [int(truth(by_algorithm[args.reference][key].get(endpoint, False))) for key in keys]
                comparator_values = [int(truth(by_algorithm[comparator][key].get(endpoint, False))) for key in keys]
                deltas = np.asarray(reference_values) - np.asarray(comparator_values)
                ref_only = int(np.sum(deltas == 1))
                comparator_only = int(np.sum(deltas == -1))
                stable_seed = int(hashlib.sha256(
                    f"{scope}|{endpoint}|{args.reference}|{comparator}".encode()
                ).hexdigest()[:8], 16)
                low, high = bootstrap_difference(deltas, args.bootstrap_repeats, stable_seed)
                results.append({
                    "scope": scope,
                    "endpoint": endpoint,
                    "reference": args.reference,
                    "comparator": comparator,
                    "paired_n": len(keys),
                    "reference_count": int(sum(reference_values)),
                    "comparator_count": int(sum(comparator_values)),
                    "reference_rate": float(np.mean(reference_values)),
                    "comparator_rate": float(np.mean(comparator_values)),
                    "paired_rate_difference": float(np.mean(deltas)),
                    "bootstrap_ci95_low": low,
                    "bootstrap_ci95_high": high,
                    "reference_only_success": ref_only,
                    "comparator_only_success": comparator_only,
                    "both_success": int(sum(a and b for a, b in zip(reference_values, comparator_values))),
                    "both_failure": int(sum(not a and not b for a, b in zip(reference_values, comparator_values))),
                    "mcnemar_exact_p": exact_mcnemar(ref_only, comparator_only),
                    "reference_planned_rows": len(by_algorithm[args.reference]),
                    "comparator_planned_rows": len(by_algorithm[comparator]),
                })

    holm_adjust(results, "mcnemar_exact_p", "mcnemar_holm_scope_endpoint",
                lambda item: (item["scope"], item["endpoint"]))
    strict_rows = [item for item in results if item["endpoint"] == "strict_completion"]
    holm_adjust(strict_rows, "mcnemar_exact_p", "mcnemar_holm_global_strict",
                lambda item: ("strict_completion",))
    strict_adjusted = {
        (item["scope"], item["comparator"]): item["mcnemar_holm_global_strict"]
        for item in strict_rows
    }
    for item in results:
        item["mcnemar_holm_global_strict"] = (
            strict_adjusted.get((item["scope"], item["comparator"]))
            if item["endpoint"] == "strict_completion" else ""
        )

    fields = list(results[0]) if results else []
    with (out / "paired_endpoint_tests.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    manifest = {
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "reference": args.reference,
        "comparators": comparators,
        "endpoints": endpoints,
        "bootstrap_repeats": args.bootstrap_repeats,
        "pairing": "experiment, track, vehicle count, seed, and frozen case index",
        "missing_policy": "The source audit retains planned missing/censored runs as endpoint failures.",
        "inference": "Percentile paired bootstrap CI; two-sided exact McNemar; Holm correction within each scope/endpoint and across all strict-completion tests.",
        "test_count": len(results),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Strict Endpoint Paired Analysis", "",
        f"Reference: `{args.reference}`. Paired bootstrap uses {args.bootstrap_repeats:,} resamples.", "",
        "| scope | comparator | n | reference | comparator | paired difference (95% CI) | McNemar p | Holm p |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in results:
        if item["endpoint"] != "strict_completion":
            continue
        lines.append(
            f"| {item['scope']} | {item['comparator']} | {item['paired_n']} | "
            f"{item['reference_rate']:.3f} | {item['comparator_rate']:.3f} | "
            f"{item['paired_rate_difference']:.3f} [{item['bootstrap_ci95_low']:.3f}, {item['bootstrap_ci95_high']:.3f}] | "
            f"{item['mcnemar_exact_p']:.4g} | {float(item['mcnemar_holm_scope_endpoint']):.4g} |"
        )
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "tests": len(results), "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
