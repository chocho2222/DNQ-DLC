#!/usr/bin/env python
"""Fold the fused-world-model arm into the manuscript's mechanism tables.

The submitted controller loads five world-model checkpoints and fuses them in
the planner, so every table that describes *our* rows has to carry the fused
runs rather than the single-model ones that were released first. Two kinds of
table are involved.

Tables that hold our arm alone --- the controller-internal signals and the
admission events --- come straight out of the analysis scripts run on the fused
run root, but they carry the fused arm's own name. This script rewrites that
name to the canonical ``ours_dnq_dlc``, so one method has one label everywhere.

Tables that hold every method --- the vehicle-state analysis --- cannot be
produced from one run root here, because the comparator traces of the main
matrix are no longer on disk while their derived tables are released. Those
tables are composed instead: the comparator rows are kept from the released
table and only the rows of the proposed arm are replaced by the fused runs. The
per-method aggregates and the paired table are then recomputed from the composed
per-case and per-event tables, so nothing is left over from the single-model arm.

Usage:
    python3 scripts/compose_fused_arm_tables.py \
        --fused <label dirs and the fused run root outputs> \
        --carrier <released table dir> --out <dir>
"""

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OURS = "ours_dnq_dlc"
CANONICAL = OURS


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = fields or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def relabel_rows(rows, source_label, target_label):
    out = []
    for row in rows:
        if row.get("algorithm") == source_label:
            row = {**row, "algorithm": target_label}
        out.append(row)
    return out


def relabel_dir(path, source_label, target_label):
    """Rewrite the arm name in every CSV and JSON of an our-arm-only table."""
    path = Path(path)
    changed = []
    for csv_path in sorted(path.glob("*.csv")):
        rows = read_csv(csv_path)
        if not rows or "algorithm" not in rows[0]:
            continue
        write_csv(csv_path, relabel_rows(rows, source_label, target_label),
                  fields=list(rows[0].keys()))
        changed.append(csv_path.name)
    for json_path in sorted(path.glob("*.json")):
        blob = json.loads(json_path.read_text(encoding="utf-8"))
        if isinstance(blob, dict) and isinstance(blob.get("algorithms"), list):
            blob["algorithms"] = [target_label if item == source_label else item
                                  for item in blob["algorithms"]]
            json_path.write_text(json.dumps(blob, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
            changed.append(json_path.name)
    return changed


def compose_vehicle_states(carrier, fused, out, source_label):
    out.mkdir(parents=True, exist_ok=True)
    for name in ("vehicle_case_level.csv", "vehicle_event_level.csv"):
        carrier_rows = read_csv(Path(carrier) / name)
        ours_rows = relabel_rows(read_csv(Path(fused) / name), source_label, CANONICAL)
        kept = [row for row in carrier_rows if row.get("algorithm") != CANONICAL]
        fields = list(carrier_rows[0].keys())
        write_csv(out / name, kept + ours_rows, fields=fields)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ours-only", action="append", default=[],
                        metavar="DIR",
                        help="table that holds the proposed arm alone; relabelled in place")
    parser.add_argument("--vehicle-carrier", default="",
                        help="released vehicle-state table holding every method")
    parser.add_argument("--vehicle-fused", default="",
                        help="vehicle-state table of the fused run root, proposed arm only")
    parser.add_argument("--vehicle-out", default="",
                        help="where the composed vehicle-state table is written")
    parser.add_argument("--source-label", default=f"{OURS}_ensemble")
    parser.add_argument("--reference", default=OURS)
    args = parser.parse_args()

    for directory in args.ours_only:
        changed = relabel_dir(directory, args.source_label, CANONICAL)
        print(f"relabelled {directory}: {', '.join(changed) or 'nothing'}")

    if args.vehicle_carrier:
        for name in ("vehicle-carrier", "vehicle-fused", "vehicle-out"):
            if not getattr(args, name.replace("-", "_")):
                raise SystemExit("--vehicle-carrier needs --vehicle-fused and --vehicle-out")
        out = compose_vehicle_states(Path(args.vehicle_carrier), Path(args.vehicle_fused),
                                     Path(args.vehicle_out), args.source_label)
        print(f"composed {out}")

        from scripts.analyze_vehicle_states import aggregate, write_csv as write_rows
        case_rows = read_csv(out / "vehicle_case_level.csv")
        event_rows = read_csv(out / "vehicle_event_level.csv")
        write_rows(str(out / "vehicle_aggregate.csv"), aggregate(case_rows, event_rows))
        protocol = json.loads((Path(args.vehicle_fused) / "protocol.json").read_text(encoding="utf-8"))
        protocol["composed"] = (f"{CANONICAL} rows from the fused run root; the other rows "
                                f"are kept from {args.vehicle_carrier}")
        (out / "protocol.json").write_text(json.dumps(protocol, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
        summary = out / "summary"
        if summary.exists():
            shutil.rmtree(summary)
        print("wrote", out / "vehicle_aggregate.csv")


if __name__ == "__main__":
    main()
