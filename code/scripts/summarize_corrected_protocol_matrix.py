#!/usr/bin/env python
"""Aggregate a corrected-protocol run matrix into one table.

Reads every ``<tag>_n<N>_seed<S>`` case directory below ``--roots`` and joins

* the per-algorithm online metrics the runner already writes
  (``tables/online_metrics_*.csv``) with
* read-only trace statistics the summary does not carry: how often the ego left
  the road (|lateral| > 1 half-width), how often it was in a recorded contact,
  and how much of the run any contact involved it.

Columns are averaged over seeds per (experiment tag, algorithm), and every mean
is reported with its standard deviation and case count so that a lucky seed
cannot be read as an effect.

Usage:
    python3 scripts/summarize_corrected_protocol_matrix.py --roots <dir> [...] \
        --out-csv <path> --out-md <path>
"""
import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path

CASE_RE = re.compile(r"^(?P<experiment>.+)_n(?P<agents>\d+)_seed(?P<seed>\d+)$")
METRIC_COLUMNS = [
    ("overtake_count", "overtakes"),
    ("on_track_overtake_count", "overtakes_on_track"),
    ("elegant_overtake_count", "overtakes_elegant"),
    ("rank_gain", "rank_gain"),
    ("target_mean_speed", "mean_speed"),
    ("target_grass_rate", "grass_rate"),
    ("target_mean_abs_lateral", "mean_abs_lateral"),
    ("target_progress", "progress"),
    ("collision_or_contact_proxy", "contact_proxy"),
    ("min_pair_distance", "min_pair_distance"),
    ("compute_latency_ms", "latency_ms"),
]


def trace_statistics(path, ego):
    trace = json.load(open(path))
    steps = len(trace)
    off_road = ego_contact = any_contact = 0
    for row in trace:
        lateral = row.get("telemetry", {}).get("lateral_error") or []
        if len(lateral) > ego and abs(float(lateral[ego])) > 1.0:
            off_road += 1
        pairs = row.get("contacts") or []
        if pairs:
            any_contact += 1
            if any(ego in pair["agents"] for pair in pairs):
                ego_contact += 1
    if not steps:
        return {}
    return {
        "off_road_rate": off_road / steps,
        "ego_contact_rate": ego_contact / steps,
        "any_contact_rate": any_contact / steps,
        "steps": steps,
    }


def collect(root):
    rows = []
    for case_dir in sorted(Path(root).iterdir()):
        match = CASE_RE.match(case_dir.name)
        if not match or not case_dir.is_dir():
            continue
        table_dir = case_dir / "tables"
        if not table_dir.is_dir():
            continue
        trace_dir = case_dir / "traces"
        agents = int(match.group("agents"))
        ego = agents - 1
        traces = {p.name.split("_n")[0]: p for p in trace_dir.glob("*.trace.json")} if trace_dir.is_dir() else {}
        for table in sorted(table_dir.glob("online_metrics_*.csv")):
            for record in csv.DictReader(open(table)):
                item = {
                    "experiment": match.group("experiment"),
                    "agents": agents,
                    "seed": int(match.group("seed")),
                    "algorithm": record["algorithm"],
                }
                for source, target in METRIC_COLUMNS:
                    raw = record.get(source)
                    try:
                        item[target] = float(raw) if raw not in (None, "", "None") else float("nan")
                    except ValueError:
                        item[target] = float("nan")
                trace = traces.get(record["algorithm"])
                item.update(trace_statistics(trace, ego) if trace else {})
                rows.append(item)
    return rows


def aggregate(rows):
    buckets = defaultdict(list)
    for row in rows:
        buckets[(row["experiment"], row["algorithm"])].append(row)
    out = []
    keys = [target for _, target in METRIC_COLUMNS] + [
        "off_road_rate", "ego_contact_rate", "any_contact_rate"]
    for (experiment, algorithm), group in sorted(buckets.items()):
        summary = {"experiment": experiment, "algorithm": algorithm, "cases": len(group),
                   "agents": group[0]["agents"], "seeds": ",".join(str(g["seed"]) for g in group)}
        for key in keys:
            values = [g[key] for g in group if key in g and not math.isnan(g.get(key, float("nan")))]
            if not values:
                continue
            mean = sum(values) / len(values)
            var = sum((v - mean) ** 2 for v in values) / (len(values) - 1) if len(values) > 1 else 0.0
            summary[key] = mean
            summary[key + "_sd"] = math.sqrt(var)
        out.append(summary)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", nargs="+", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--filter", default="", help="only cases whose directory name contains this")
    args = parser.parse_args()

    rows = []
    for root in args.roots:
        rows.extend(collect(root))
    if args.filter:
        rows = [r for r in rows if args.filter in r.get("experiment", "")]
    summary = aggregate(rows)

    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_csv, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({k for row in summary for k in row}))
        writer.writeheader()
        writer.writerows(summary)

    columns = ["overtakes", "overtakes_on_track", "overtakes_elegant", "rank_gain",
               "mean_speed", "grass_rate", "off_road_rate", "ego_contact_rate", "progress"]
    lines = ["| experiment | algorithm | n | " + " | ".join(columns) + " |",
             "|---|---|---|" + "---|" * len(columns)]
    for row in summary:
        cells = []
        for column in columns:
            if column in row:
                cells.append(f"{row[column]:.2f}±{row.get(column + '_sd', 0.0):.2f}")
            else:
                cells.append("-")
        lines.append(f"| {row['experiment']} | {row['algorithm']} | {row['cases']} | " + " | ".join(cells) + " |")
    Path(args.out_md).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
