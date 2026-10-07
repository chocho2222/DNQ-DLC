#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
    }
)


PALETTE = {
    "selector": "#3B7EA1",
    "oracle": "#D99A44",
    "selector_miss": "#C96F5A",
    "candidate_gap": "#7A869A",
    "pass": "#4C9F70",
    "grid": "#D8DEE6",
    "text": "#1F2933",
}


STAGE_LABELS = {
    "five_candidate_original": "5-cand.\noriginal",
    "six_candidate_expanded": "6-cand.\nexpanded",
    "six_candidate_external": "6-cand.\nexternal",
    "seven_candidate_targeted": "7-cand.\ntargeted",
    "seven_candidate_external_after_targeted_repair": "7-cand.\npost-repair\nexternal",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_pub(fig, out_stem):
    fig.savefig(f"{out_stem}.svg", bbox_inches="tight")
    fig.savefig(f"{out_stem}.pdf", bbox_inches="tight")
    fig.savefig(f"{out_stem}.tiff", dpi=600, bbox_inches="tight")
    fig.savefig(f"{out_stem}.png", dpi=300, bbox_inches="tight")


def write_source_data(report, out_csv):
    fields = [
        "panel",
        "heldout",
        "stage",
        "status",
        "n",
        "selector_pass_count",
        "oracle_pass_count",
        "selector_pass_rate",
        "oracle_pass_rate",
        "selector_miss_count",
        "candidate_gap_count",
        "failed_count",
        "selector_miss_seeds",
        "candidate_gap_seeds",
    ]
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["entries"]:
            writer.writerow(
                {
                    "panel": "a-b",
                    "heldout": row["heldout"],
                    "stage": row["stage"],
                    "status": row["status"],
                    "n": row["n"],
                    "selector_pass_count": row["selector_pass_count"],
                    "oracle_pass_count": row["oracle_pass_count"],
                    "selector_pass_rate": row["selector_pass_rate"],
                    "oracle_pass_rate": row["oracle_pass_rate"],
                    "selector_miss_count": len(row["selector_miss_seeds"]),
                    "candidate_gap_count": len(row["candidate_gap_seeds"]),
                    "failed_count": len(row["failed_seeds"]),
                    "selector_miss_seeds": ";".join(map(str, row["selector_miss_seeds"])),
                    "candidate_gap_seeds": ";".join(map(str, row["candidate_gap_seeds"])),
                }
            )


def draw(report, out_dir):
    entries = report["entries"]
    labels = [f"{row['heldout']}\n{STAGE_LABELS.get(row['stage'], row['stage'])}" for row in entries]
    x = np.arange(len(entries))
    width = 0.34

    fig = plt.figure(figsize=(8.2, 4.8), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.95], width_ratios=[1.25, 0.85])
    ax_a = fig.add_subplot(gs[0, :])
    ax_b = fig.add_subplot(gs[1, 0])
    ax_c = fig.add_subplot(gs[1, 1])

    selector_rates = [row["selector_pass_rate"] for row in entries]
    oracle_rates = [row["oracle_pass_rate"] for row in entries]
    ax_a.bar(x - width / 2, selector_rates, width=width, color=PALETTE["selector"], label="online selector")
    ax_a.bar(x + width / 2, oracle_rates, width=width, color=PALETTE["oracle"], label="diagnostic oracle")
    for i, row in enumerate(entries):
        ax_a.text(
            i - width / 2,
            min(selector_rates[i] + 0.04, 1.03),
            f"{row['selector_pass_count']}/{row['n']}",
            ha="center",
            va="bottom",
        )
        ax_a.text(
            i + width / 2,
            min(oracle_rates[i] + 0.04, 1.03),
            f"{row['oracle_pass_count']}/{row['n']}",
            ha="center",
            va="bottom",
        )
    ax_a.set_xticks(x, labels)
    ax_a.set_ylim(0, 1.08)
    ax_a.set_ylabel("strict pass rate")
    ax_a.set_title("a  Cross-heldout selector versus oracle")
    ax_a.legend(loc="upper right", ncol=2)
    ax_a.axhline(1.0, color=PALETTE["grid"], lw=0.8, zorder=0)

    selector_miss = np.asarray([len(row["selector_miss_seeds"]) for row in entries])
    candidate_gap = np.asarray([len(row["candidate_gap_seeds"]) for row in entries])
    ax_b.bar(x, selector_miss, color=PALETTE["selector_miss"], label="selector miss")
    ax_b.bar(x, candidate_gap, bottom=selector_miss, color=PALETTE["candidate_gap"], label="candidate gap")
    for i, row in enumerate(entries):
        total = selector_miss[i] + candidate_gap[i]
        if total:
            ax_b.text(i, total + 0.12, str(int(total)), ha="center", va="bottom")
    ax_b.set_xticks(x, [row["heldout"] for row in entries], rotation=25, ha="right")
    ax_b.set_ylabel("failed seeds")
    ax_b.set_title("b  Failure decomposition")
    ax_b.legend(loc="upper left")

    agg = report["aggregate_expanded_or_later"]
    values = [agg["selector_pass_count"], agg["oracle_pass_count"], agg["selector_oracle_gap"]]
    totals = [agg["n"], agg["n"], agg["n"]]
    colors = [PALETTE["selector"], PALETTE["oracle"], PALETTE["selector_miss"]]
    ax_c.bar(["selector\nPASS", "oracle\nPASS", "selector-\noracle gap"], values, color=colors, width=0.62)
    for i, value in enumerate(values):
        ax_c.text(i, value + 0.8, f"{value}/{totals[i]}", ha="center", va="bottom")
    ax_c.set_ylim(0, max(totals) + 3)
    ax_c.set_ylabel("seed count")
    ax_c.set_title("c  Expanded-or-later aggregate")
    ax_c.text(
        0.0,
        -0.28,
        "Aggregate is descriptive; it does not imply a broad robustness claim.",
        transform=ax_c.transAxes,
        ha="left",
        va="top",
        fontsize=6.5,
        color=PALETTE["text"],
    )

    for ax in [ax_a, ax_b, ax_c]:
        ax.tick_params(length=3, width=0.7)

    out_stem = out_dir / "figure_3_cross_heldout_validation"
    save_pub(fig, out_stem)
    plt.close(fig)
    return out_stem


def main():
    parser = argparse.ArgumentParser(description="Export publication figure for cross-heldout validation synthesis.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    out_dir = root / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")
    source_csv = out_dir / "figure_3_source_data.csv"
    write_source_data(report, source_csv)
    out_stem = draw(report, out_dir)
    manifest = {
        "figure": "figure_3_cross_heldout_validation",
        "claim": (
            "Across held-out validation, the online portfolio selector is useful but not robust: "
            "heldout4 shows partial post-repair transfer, while the remaining selector-oracle gap separates "
            "selector misses from candidate-policy gaps."
        ),
        "panels": {
            "a": "Selector and diagnostic oracle strict pass rates across held-out stages.",
            "b": "Seed-level failure decomposition into selector misses and candidate-policy gaps.",
            "c": "Descriptive expanded-or-later aggregate, reported only as a synthesis of saved runs.",
        },
        "source_data": str(source_csv),
        "exports": [str(out_stem) + ext for ext in [".svg", ".pdf", ".tiff", ".png"]],
        "review_risks": [
            "Oracle bars are diagnostic upper bounds and are not online selector outputs.",
            "Heldout3 targeted repair is separated from heldout3 external validation.",
            "Heldout4 is reported as partial transfer after targeted repair, not as a broad robustness claim.",
            "The aggregate panel is descriptive and should not be used to average away heldout3/heldout4 failures.",
        ],
    }
    (out_dir / "figure_3_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "manifest": manifest}, indent=2))


if __name__ == "__main__":
    main()
