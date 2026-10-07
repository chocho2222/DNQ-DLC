#!/usr/bin/env python
"""Every main-comparison number the manuscript quotes, in one JSON.

The manuscript reports one trained instance per learned method, and every
learned method is the output of a stochastic recipe. This script reads the
draw-level audits of the proposed controller and of the three DLC variants, the
single run of each rule and continuous-control reference, and prints, per
family, the per-draw endpoint counts, their mean and range, the whole-episode
containment, and the paired comparison against the rule expert.

Usage:
    python3 scripts/report_paper_table.py --out /tmp/paper_table.json
"""
import argparse, csv, json, math, os, statistics as stats

Z = 1.959963984540054
ENDPOINTS = ("P", "E_pass", "E_valid", "E_full", "E_race")


def wilson(k, n, z=Z):
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    cen = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, cen - half), min(1.0, cen + half))


def mcnemar_exact(wins, losses):
    n = wins + losses
    if n == 0:
        return float("nan")
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2.0 ** n
    return min(1.0, 2.0 * tail)


def read_csv(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def number(value):
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def mean_of(rows, column):
    values = [number(r.get(column)) for r in rows]
    values = [v for v in values if v is not None]
    return stats.mean(values) if values else None


def counts(rows):
    rows = [r for r in rows if r.get("status") in (None, "", "ok")]
    out = {"n": len(rows)}
    for key in ENDPOINTS:
        out[key] = sum(1 for r in rows if str(r.get(key)) == "True")
    for key in ("rank_gain", "target_progress", "latency_ms", "mean_speed",
                "time_to_pass_steps", "mean_abs_lat", "in_corridor",
                "longest_off_run"):
        value = mean_of(rows, key)
        if value is not None:
            out[key] = value
    return out


def episode_containment(path):
    out = {}
    for row in read_csv(path):
        out.setdefault(row["algorithm"], []).append(row)
    result = {}
    for algorithm, rows in out.items():
        grass = [number(r["episode_grass"]) for r in rows]
        lat = [number(r["episode_lat"]) for r in rows]
        grass = [g for g in grass if g is not None]
        lat = [l for l in lat if l is not None]
        grass_sorted = sorted(grass)
        result[algorithm] = {
            "n": len(grass),
            "grass": stats.mean(grass) if grass else None,
            "grass_median": stats.median(grass) if grass else None,
            "grass_q1": grass_sorted[int(0.25 * (len(grass_sorted) - 1))] if grass else None,
            "grass_q3": grass_sorted[int(0.75 * (len(grass_sorted) - 1))] if grass else None,
            "lat": stats.mean(lat) if lat else None,
        }
    return result


def paired(rows, reference_rows, reference_algorithm, endpoint):
    key = lambda r: (r["experiment_id"], r["num_agents"], r["seed"])
    ref = {key(r): str(r.get(endpoint)) == "True"
           for r in reference_rows if r["algorithm"] == reference_algorithm}
    wins = losses = 0
    for row in rows:
        other = ref.get(key(row))
        if other is None:
            continue
        mine = str(row.get(endpoint)) == "True"
        if mine == other:
            continue
        if mine and not other:
            wins += 1
        else:
            losses += 1
    return {"win": wins, "lose": losses, "p": mcnemar_exact(wins, losses)}


def family(rows, reference_rows, reference_algorithm="rule_expert_gate"):
    draws = {}
    for algorithm in sorted({r["algorithm"] for r in rows}):
        subset = [r for r in rows if r["algorithm"] == algorithm]
        draws[algorithm] = counts(subset)
    if not draws:
        return {}
    block = {"draws": draws}
    for key in ENDPOINTS + ("rank_gain", "mean_speed", "time_to_pass_steps",
                            "mean_abs_lat", "in_corridor", "longest_off_run",
                            "latency_ms"):
        values = [d[key] for d in draws.values() if key in d]
        if not values:
            continue
        block[key + "_mean"] = stats.mean(values)
        block[key + "_range"] = [min(values), max(values)]
    block["paired_vs_rule"] = {}
    for endpoint in ("P", "E_pass", "E_valid", "E_full", "E_race"):
        pairs = [paired([r for r in rows if r["algorithm"] == a],
                        reference_rows, reference_algorithm, endpoint)
                 for a in draws]
        block["paired_vs_rule"][endpoint] = {
            "per_draw": pairs,
            "win_mean": stats.mean(p["win"] for p in pairs),
            "lose_mean": stats.mean(p["lose"] for p in pairs),
        }
    return block


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ours", required=True,
                        help="audit directory of the proposed controller (case_level.csv)")
    parser.add_argument("--ours-containment", required=True)
    parser.add_argument("--dlc-root", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--reference-containment", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    ours_rows = read_csv(os.path.join(args.ours, "case_level.csv"))
    reference_rows = read_csv(os.path.join(args.reference, "case_level.csv"))
    ours_grass = episode_containment(args.ours_containment)
    ref_grass = episode_containment(args.reference_containment)

    report = {"families": {}, "containment": {}, "reference": {}}
    report["families"]["proposed"] = family(ours_rows, reference_rows)
    for algorithm, block in ours_grass.items():
        report["containment"][algorithm] = block

    for draw_dir in sorted(os.listdir(args.dlc_root)):
        path = os.path.join(args.dlc_root, draw_dir)
        if not os.path.isdir(path) or not draw_dir.startswith("draw_"):
            continue
        rows = read_csv(os.path.join(path, "case_level.csv"))
        for algorithm in sorted({r["algorithm"] for r in rows}):
            block = report["families"].setdefault(algorithm, {})
            block.setdefault("per_draw", {})[draw_dir] = counts(
                [r for r in rows if r["algorithm"] == algorithm])
        for algorithm, block in episode_containment(
                os.path.join(path, "containment_episode_level.csv")).items():
            report["containment"].setdefault(algorithm, {}).setdefault(
                "per_draw", {})[draw_dir] = block
    for algorithm, block in report["families"].items():
        if algorithm == "proposed" or "per_draw" not in block:
            continue
        draws = block["per_draw"]
        block["draws"] = draws
        for key in ENDPOINTS + ("rank_gain", "mean_speed", "time_to_pass_steps",
                               "mean_abs_lat", "in_corridor", "longest_off_run",
                               "latency_ms"):
            values = [d[key] for d in draws.values() if key in d]
            if not values:
                continue
            block[key + "_mean"] = stats.mean(values)
            block[key + "_range"] = [min(values), max(values)]

    single = {}
    for algorithm in sorted({r["algorithm"] for r in reference_rows}):
        subset = [r for r in reference_rows if r["algorithm"] == algorithm]
        block = counts(subset)
        for endpoint in ("P", "E_pass", "E_valid", "E_full", "E_race"):
            block[endpoint + "_wilson"] = wilson(block[endpoint], block["n"])
        block["containment"] = ref_grass.get(algorithm)
        single[algorithm] = block
    report["reference"] = single

    report["proposed_single_map"] = {}
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, default=str)
    print(json.dumps(report, indent=2, default=str)[:400])


if __name__ == "__main__":
    main()
