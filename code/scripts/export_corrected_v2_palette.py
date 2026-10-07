#!/usr/bin/env python
"""Validate and export the fixed algorithm colour vocabulary.

Every algorithm owns exactly one colour across every figure, screenshot and
video frame of the submission. This script refuses to export a palette that
violates that contract: a malformed hex, a colour reused by two different
controllers, or a colour outside the mandated band.
"""
import colorsys
import json
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.tits_figure_style import (
    ABLATION_ORDER,
    ALGORITHM_COLORS,
    ALGORITHM_COLOR_ROOTS,
    ALGORITHM_GROUPS,
    ALGORITHM_LABELS,
    ALGORITHM_LINESTYLES,
    ALGORITHM_MARKERS,
    ALGORITHM_ORDER,
    PALETTE,
)

HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
MANDATED = ["teal_green", "grass_green", "indigo", "bean_red", "warm_yellow", "brown_taupe"]
SATURATION_BAND = (28.0, 58.0)
VALUE_BAND = (62.0, 88.0)
# Ablations keep the method's hue so a reader reads them as one family; they are
# separated by value and by dash pattern rather than by hue.
HUE_FAMILY_CENTER = 233.5
HUE_FAMILY_TOLERANCE = 20.0
ABLATION_REQUIRED_HUE_GAP = 6.0
ABLATION_REQUIRED_VALUE_GAP = 3.0
# The submitted method must be the most saturated mid-value indigo so it reads
# as the primary series in grayscale print as well as in colour.
DEFAULT_OUT = "materials/palette_corrected_v2.json"


def hex_to_hsv(hex_color):
    text = hex_color.lstrip("#")
    red, green, blue = (int(text[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    return round(hue * 360.0, 2), round(saturation * 100.0, 2), round(value * 100.0, 2)


def validate():
    failures = []
    for name, hex_color in PALETTE.items():
        if not HEX_PATTERN.match(hex_color):
            failures.append(f"palette entry {name} is not a #RRGGBB colour: {hex_color}")
    roots = {}
    for algorithm, hex_color in ALGORITHM_COLORS.items():
        if not HEX_PATTERN.match(hex_color):
            failures.append(f"algorithm {algorithm} has a malformed colour: {hex_color}")
        roots.setdefault(ALGORITHM_COLOR_ROOTS.get(algorithm, algorithm), (algorithm, hex_color))
    owners = {}
    for root, (example, hex_color) in roots.items():
        owners.setdefault(hex_color, []).append(root)
    for hex_color, names in owners.items():
        if len(names) > 1:
            failures.append(f"colour {hex_color} is shared by {sorted(names)}")
    for algorithm in ALGORITHM_ORDER + ABLATION_ORDER:
        if algorithm not in ALGORITHM_COLORS:
            failures.append(f"algorithm {algorithm} has no colour")
    for hue_name in MANDATED:
        if hue_name not in PALETTE:
            failures.append(f"mandated palette entry {hue_name} is missing")
    for name, hex_color in PALETTE.items():
        if name.startswith("neutral_") or name in MANDATED:
            continue
        hue, saturation, value = hex_to_hsv(hex_color)
        if name.startswith("ablation_"):
            if abs(hue - HUE_FAMILY_CENTER) > HUE_FAMILY_TOLERANCE:
                failures.append(f"{name} ({hex_color}) left the method hue family: {hue}")
            continue
        if not SATURATION_BAND[0] <= saturation <= SATURATION_BAND[1]:
            failures.append(f"{name} ({hex_color}) leaves the saturation band: {saturation}")
        if not VALUE_BAND[0] <= value <= VALUE_BAND[1]:
            failures.append(f"{name} ({hex_color}) leaves the value band: {value}")
    ablations = [(name, hex_to_hsv(value)) for name, value in PALETTE.items() if name.startswith("ablation_")]
    for index, (name, (hue, _, value)) in enumerate(ablations):
        for other, (other_hue, _, other_value) in ablations[index + 1:]:
            if abs(hue - other_hue) < ABLATION_REQUIRED_HUE_GAP and abs(value - other_value) < ABLATION_REQUIRED_VALUE_GAP:
                failures.append(f"ablations {name} and {other} are not separable")
    return failures


def build_document():
    algorithms = []
    for algorithm, hex_color in sorted(ALGORITHM_COLORS.items()):
        hue, saturation, value = hex_to_hsv(hex_color)
        algorithms.append(
            {
                "algorithm": algorithm,
                "color_root": ALGORITHM_COLOR_ROOTS.get(algorithm, algorithm),
                "hex": hex_color,
                "hue_deg": hue,
                "saturation_pct": saturation,
                "value_pct": value,
                "label": ALGORITHM_LABELS.get(algorithm, algorithm),
                "group": ALGORITHM_GROUPS.get(algorithm, "Other"),
                "linestyle": ALGORITHM_LINESTYLES.get(algorithm, "-"),
                "marker": ALGORITHM_MARKERS.get(algorithm),
            }
        )
    return {
        "study": "corrected_v2_20260920",
        "contract": "one algorithm, one fixed colour, in every figure and every rendered frame",
        "accessibility": "ablations share the method hue and are separated by value, dash pattern and marker",
        "source": "scripts/tits_figure_style.py",
        "palette": {name: {"hex": value, "hue_deg": hex_to_hsv(value)[0],
                           "saturation_pct": hex_to_hsv(value)[1],
                           "value_pct": hex_to_hsv(value)[2]} for name, value in PALETTE.items()},
        "algorithms": algorithms,
    }


def main():
    out_path = Path(DEFAULT_OUT)
    failures = validate()
    if failures:
        for item in failures:
            print(f"FAIL: {item}")
        raise SystemExit(1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(build_document(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"palette OK: {len(ALGORITHM_COLORS)} algorithm names, "
          f"{len(PALETTE)} palette entries -> {out_path}")


if __name__ == "__main__":
    main()
