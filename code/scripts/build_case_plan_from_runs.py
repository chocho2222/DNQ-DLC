#!/usr/bin/env python
"""Build a validity-endpoint case plan from a directory of finished runs.

The audit (``scripts/audit_validity_endpoint_v3.py``) consumes a case plan with
one row per run: experiment tag, agent count, seed, algorithms and the output
directory relative to the archive root. This script derives that table by
scanning the run directories the evaluation runner produced, so a newly
finished matrix can be audited without hand-written bookkeeping.

Usage:
    python3 scripts/build_case_plan_from_runs.py --root <archive> [--root <..>] \
        --out <case_plan.csv>
"""
import argparse
import csv
import re
from pathlib import Path

SUMMARY_SUFFIX_RE = re.compile(r"_n\d+_seed\d+$")

CASE_RE = re.compile(r"^(?P<experiment>.+)_n(?P<agents>\d+)_seed(?P<seed>\d+)$")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", nargs="+", required=True,
                        help="directories that contain <tag>_n<N>_seed<S> case folders")
    parser.add_argument("--out", required=True)
    parser.add_argument("--archive-root", default="",
                        help="root the out_dir column is relative to; defaults to the common parent")
    parser.add_argument("--require-summary", action="store_true", default=True)
    args = parser.parse_args()

    rows = []
    index = 0
    for root in args.root:
        root_path = Path(root).resolve()
        archive = Path(args.archive_root).resolve() if args.archive_root else root_path
        for case in sorted(root_path.iterdir()):
            match = CASE_RE.match(case.name)
            if not match or not case.is_dir():
                continue
            summaries = sorted((case / "summaries").glob("*.summary.json")) if (case / "summaries").is_dir() else []
            # The variant name may itself contain "_n" (nearest, dynamic, ...),
            # so the trailing case suffix has to be removed by pattern and not
            # by the first occurrence of the separator.
            algorithms = [SUMMARY_SUFFIX_RE.sub("", p.name.rsplit(".summary.json", 1)[0])
                          for p in summaries]
            if not algorithms:
                continue
            index += 1
            rows.append({
                "case_index": index,
                "experiment_id": match.group("experiment"),
                "track_id": "procedural",
                "track_path": "",
                "num_agents": match.group("agents"),
                "seed": match.group("seed"),
                "algorithms": ",".join(algorithms),
                "device": "cuda",
                "out_dir": str(case.relative_to(archive)),
                "command": "",
            })
    with open(args.out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [
            "case_index", "experiment_id", "track_id", "track_path", "num_agents",
            "seed", "algorithms", "device", "out_dir", "command"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} cases -> {args.out}")


if __name__ == "__main__":
    main()
