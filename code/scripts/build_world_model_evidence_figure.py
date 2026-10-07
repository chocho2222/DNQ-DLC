#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Evidence figure for the action-conditioned world model.

Two panels, both produced by the audit scripts rather than by hand:

* (a) one-step fidelity per telemetry channel against a persistence baseline
  (`scripts/audit_world_model_fidelity.py`), which is the honest scale for "the
  model predicts the next state";
* (b) the counterfactual action response (`scripts/audit_world_model_action_response.py`):
  the same state is stepped through the model and through the simulator under a
  grid of throttle commands, so the sign of the response can be compared.

The colour of the learned model is the colour the method owns everywhere else.

Usage:
    python3 scripts/build_world_model_evidence_figure.py --diagnostics <dir> --out <path.png>
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.tits_figure_style import (  # noqa: E402
    PALETTE,
    configure_publication_matplotlib,
)

MODEL_COLOR = PALETTE["indigo"]
BASELINE_COLOR = PALETTE["neutral_mid"]
TRUTH_COLOR = PALETTE["neutral_dark"]

SHORT_NAMES = {
    "x/PLAYFIELD": "$x$", "y/PLAYFIELD": "$y$", "vx/50": "$v_x$", "vy/50": "$v_y$",
    "speed/50": "$|v|$", "sin h": "$\\sin\\psi$", "cos h": "$\\cos\\psi$",
    "omega/5": "$\\omega$", "track_index": "tile", "tile_progress": "progress",
    "dx/TW": "$\\Delta x_n$", "dy/TW": "$\\Delta y_n$", "lateral": "$\\ell$",
    "sin e_psi": "$\\sin e_\\psi$", "cos e_psi": "$\\cos e_\\psi$",
    "grass": "grass", "backward": "back",
}


def load(diagnostics):
    diagnostics = Path(diagnostics)
    fidelity = json.loads((diagnostics / "fidelity" / "fidelity.json").read_text())
    response = json.loads((diagnostics / "action_response" / "action_response.json").read_text())
    return fidelity, response


def build(diagnostics, out_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    configure_publication_matplotlib(font_size=9.0)
    fidelity, response = load(diagnostics)
    channels = fidelity["channels"]

    figure, (left, right) = plt.subplots(1, 2, figsize=(7.4, 3.4),
                                         gridspec_kw={"width_ratios": [1.45, 1.0]})

    usable = [row for row in channels if row["persistence_mae"] > 0 and row["model_mae"] > 0]
    usable.sort(key=lambda row: row["model_mae"] / row["persistence_mae"])
    labels = [SHORT_NAMES.get(row["feature"], row["feature"]) for row in usable]
    y = np.arange(len(usable))
    ratio = np.array([row["model_mae"] / row["persistence_mae"] for row in usable])
    left.barh(y, ratio, height=0.62, color=MODEL_COLOR)
    left.axvline(1.0, color=PALETTE["neutral_dark"], linewidth=1.1)
    left.set_xscale("log")
    left.set_yticks(y)
    left.set_yticklabels(labels, fontsize=8)
    left.set_xlabel("one-step error relative to persistence (log scale)")
    left.set_title("(a) next-state fidelity", fontsize=9.5)
    left.grid(axis="x", color="#E5E7EB", linewidth=0.6)
    for side in ("top", "right"):
        left.spines[side].set_visible(False)
    better = sum(1 for row in channels if row["skill"] > 0)
    left.text(0.03, 0.03,
              f"bar $=E_{{model}}/E_{{persistence}}$; left of the line = better than\n"
              f"doing nothing. better than persistence: {better}/{len(channels)} channels",
              transform=left.transAxes, ha="left", va="bottom", fontsize=7.2,
              color=PALETTE["neutral_dark"])
    left.set_xlim(min(ratio.min(), 0.5) * 0.5, ratio.max() * 3.0)

    rows = [row for row in response["rows"] if abs(row["steer"]) < 1e-9]
    rows.sort(key=lambda row: row["gas"])
    gas = np.array([row["gas"] for row in rows])
    true_speed = np.array([row["true_d_speed"] for row in rows])
    model_speed = np.array([row["model_d_speed"] for row in rows])
    right.axhline(0.0, color=PALETTE["neutral_light"], linewidth=0.8)
    right.plot(gas, true_speed, color=TRUTH_COLOR, marker="o", markersize=4,
               linewidth=1.4, label="simulator")
    right.plot(gas, model_speed, color=MODEL_COLOR, marker="s", markersize=4,
               linewidth=1.4, linestyle="--", label="world model")
    right.set_xlabel("commanded throttle")
    right.set_ylabel("$\\Delta|v|$ over one step")
    right.set_title("(b) counterfactual throttle response", fontsize=9.5)
    right.legend(fontsize=7.5, loc="best", frameon=False)
    right.grid(color="#E5E7EB", linewidth=0.6)
    for side in ("top", "right"):
        right.spines[side].set_visible(False)
    all_rows = response["rows"]
    sign_ok = int(np.sum([np.sign(row["true_d_speed"]) == np.sign(row["model_d_speed"])
                          for row in all_rows]))
    right.text(0.98, 0.02, f"sign agreement: {sign_ok}/{len(all_rows)}",
               transform=right.transAxes, ha="right", va="bottom", fontsize=7.5,
               color=PALETTE["neutral_dark"])

    figure.tight_layout()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, dpi=300)
    figure.savefig(str(out).replace(".png", ".pdf"))
    print(f"wrote {out}")
    print(f"position error {fidelity['position_error_m']:.2f} m vs persistence "
          f"{fidelity['position_persistence_m']:.2f} m")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnostics", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    build(args.diagnostics, args.out)


if __name__ == "__main__":
    main()
