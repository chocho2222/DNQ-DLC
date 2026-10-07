#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Export paper experiment tables.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    table = json.loads((root / "tables" / "main_results.json").read_text(encoding="utf-8"))
    rows = []
    for item in table["baseline_rows"]:
        rows.append(
            {
                "method": item["name"],
                "split": "baseline_seed3",
                "validation_status": item["validation_status"],
                "target_completed_lap": item["target_completed_lap"],
                "target_final_rank_by_tiles": item["target_final_rank_by_tiles"],
                "target_grass_rate": item["target_grass_rate"],
                "max_grass_rate": item["max_grass_rate"],
                "tile_visited_count": " ".join(str(x) for x in item["tile_visited_count"]),
                "steps_run": item["steps_run"],
                "gif": item["gif"],
            }
        )
    for item in table["graph_bc_rows"]:
        rows.append(
            {
                "method": "graph_bc_safety_shield",
                "split": f"eval_seed_{item['seed']}",
                "validation_status": item["validation_status"],
                "target_completed_lap": item["target_completed_lap"],
                "target_final_rank_by_tiles": item["target_final_rank_by_tiles"],
                "target_grass_rate": item["target_grass_rate"],
                "max_grass_rate": item["max_grass_rate"],
                "tile_visited_count": " ".join(str(x) for x in item["tile_visited_count"]),
                "steps_run": item["steps_run"],
                "gif": item["gif"],
            }
        )
    for item in table.get("dlc_rows", []):
        rows.append(
            {
                "method": item["method"].replace("dlc:", "dlc_"),
                "split": f"eval_seed_{item['seed']}",
                "validation_status": item["validation_status"],
                "target_completed_lap": item["target_completed_lap"],
                "target_final_rank_by_tiles": item["target_final_rank_by_tiles"],
                "target_grass_rate": item["target_grass_rate"],
                "max_grass_rate": item["max_grass_rate"],
                "tile_visited_count": " ".join(str(x) for x in item["tile_visited_count"]),
                "steps_run": item["steps_run"],
                "gif": item["gif"],
            }
        )
    csv_path = root / "tables" / "main_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    md_lines = [
        "| method | split | status | target lap | rank | target grass | max grass | tiles | steps |",
        "|---|---:|---|---:|---:|---:|---:|---|---:|",
    ]
    for row in rows:
        md_lines.append(
            "| {method} | {split} | {validation_status} | {target_completed_lap} | "
            "{target_final_rank_by_tiles} | {target_grass_rate:.3f} | {max_grass_rate:.3f} | "
            "{tile_visited_count} | {steps_run} |".format(
                **{
                    **row,
                    "target_grass_rate": float(row["target_grass_rate"]),
                    "max_grass_rate": float(row["max_grass_rate"]),
                }
            )
        )
    (root / "tables" / "main_results.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(json.dumps({"csv": str(csv_path), "markdown": str(root / "tables" / "main_results.md")}, indent=2))


if __name__ == "__main__":
    main()
