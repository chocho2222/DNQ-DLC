#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_plan(root):
    manifest = load_json(root / "manifest.json")
    heldout = load_json(root / "tables" / "heldout_generalization.json")
    full = load_json(root / "tables" / "full_statistical_report.json")
    calibration = load_json(root / "tables" / "selector_calibration.json")
    cross_stats_path = root / "tables" / "cross_heldout_statistical_supplement.json"
    cross_stats = load_json(cross_stats_path) if cross_stats_path.exists() else None

    return {
        "root": str(root),
        "title": "Statistical Analysis Plan",
        "scope": manifest["scope"],
        "seed_sets": manifest["seed_sets"],
        "primary_endpoint": {
            "name": "strict_full_lap_pass",
            "definition": (
                "A run passes only if the target completes a full lap, finishes rank 1 by tile progress, "
                "has a valid first-ahead event, remains below the target grass threshold, and the traffic "
                "quality constraint is satisfied."
            ),
        },
        "secondary_endpoints": [
            "target grass rate",
            "mean tile progress",
            "target final rank by visited tiles",
            "first-ahead step",
            "failure type composition",
            "seed-level method complementarity",
        ],
        "main_comparisons": [
            {
                "comparison": "locked single-method comparison",
                "methods": [
                    "main:overtake_base_only",
                    "adaptive:graph_adaptive_shield",
                    "main:graph_soft_shield",
                ],
                "interpretation_boundary": (
                    "The locked rule baseline is the primary hard baseline. Innovation methods should be "
                    "reported as narrowing or failing to narrow the gap unless they exceed it under paired "
                    "seed analysis."
                ),
            },
            {
                "comparison": "held-out online selector generalization",
                "methods": ["five-candidate 1200-step online probe selector"],
                "interpretation_boundary": (
                    "Heldout1 and heldout2 must be reported together. Heldout1 is a positive result; "
                    "heldout2 is a stress repeat that limits broad robustness claims."
                ),
            },
            {
                "comparison": "oracle portfolio upper bound",
                "methods": ["best candidate chosen after full rollout outcome"],
                "interpretation_boundary": "Oracle portfolios are diagnostic upper bounds and not online selector outputs.",
            },
            {
                "comparison": "selector calibration diagnosis",
                "methods": ["heldout1-calibrated linear probe score tested on heldout2"],
                "interpretation_boundary": (
                    "Calibration is considered insufficient if heldout2 remains below oracle or if candidate "
                    "gaps remain."
                ),
            },
            {
                "comparison": "cross-heldout selector-oracle synthesis",
                "methods": ["expanded-or-later online selector", "diagnostic candidate oracle"],
                "interpretation_boundary": (
                    "Cross-heldout statistics are descriptive because they combine development stages and external "
                    "validation stages. They quantify uncertainty and selector-oracle gap size but do not establish a broad robustness claim."
                ),
            },
        ],
        "intervals_and_tests": [
            "Wilson 95% confidence intervals for pass-rate estimates.",
            "Paired bootstrap 95% confidence intervals for paired pass-rate differences.",
            "McNemar tests for paired binary pass/fail comparisons on the same seeds.",
            "Explicit failure-type counts for qualitative failure-mode diagnosis.",
            "Exact McNemar tests for selector-vs-oracle discordance in cross-heldout synthesis.",
        ],
        "multiplicity_policy": (
            "The package treats statistical tests as descriptive because seed counts are small and the work is "
            "method-development oriented. Claims rely on effect direction, confidence intervals, held-out repeats, "
            "and conserved negative results rather than isolated p-values."
        ),
        "minimum_reporting_set": [
            "locked baseline result",
            "best innovation single-method result",
            "heldout1 selector and oracle",
            "heldout2 selector and oracle",
            "selector calibration and failure decomposition",
            "cross-heldout Figure 3 source data and statistical supplement",
            "artifact provenance and reproducibility audit status",
        ],
        "current_key_results": {
            "locked_interpretation": full["interpretation"],
            "heldout_interpretation": heldout["overall_interpretation"],
            "calibration_interpretation": calibration["interpretation"],
            "cross_heldout_statistical_supplement": (
                cross_stats["interpretation"] if cross_stats else "Not yet generated."
            ),
        },
        "prohibited_claims": [
            "Do not claim broad robustness evidence.",
            "Do not report heldout1 10/10 without heldout2 5/10.",
            "Do not present oracle portfolio results as online selector performance.",
            "Do not claim DAgger-v2 is a standalone robust controller.",
            "Do not claim score-only calibration solves selector generalization.",
            "Do not use the cross-heldout aggregate as confirmatory evidence for a broad robustness claim.",
        ],
    }


def write_markdown(report, path):
    lines = [
        "# Statistical Analysis Plan",
        "",
        "This document records the analysis rules used to interpret the saved non-VLM multi-car overtaking package.",
        "",
        "## Scope",
        "",
        f"- Task: {report['scope']['task']}",
        f"- Excluded: {report['scope']['excluded']}",
        f"- Validator: {report['scope']['validator']}",
        "",
        "## Seed Sets",
        "",
    ]
    for name, seeds in report["seed_sets"].items():
        lines.append(f"- `{name}`: {', '.join(str(seed) for seed in seeds)}")
    lines.extend(
        [
            "",
            "## Primary Endpoint",
            "",
            f"- `{report['primary_endpoint']['name']}`: {report['primary_endpoint']['definition']}",
            "",
            "## Secondary Endpoints",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["secondary_endpoints"])
    lines.extend(["", "## Main Comparisons", ""])
    for item in report["main_comparisons"]:
        lines.extend(
            [
                f"### {item['comparison']}",
                "",
                "Methods:",
                "",
            ]
        )
        lines.extend(f"- `{method}`" for method in item["methods"])
        lines.extend(["", "Interpretation boundary:", "", item["interpretation_boundary"], ""])
    lines.extend(["## Intervals And Tests", ""])
    lines.extend(f"- {item}" for item in report["intervals_and_tests"])
    lines.extend(
        [
            "",
            "## Multiplicity Policy",
            "",
            report["multiplicity_policy"],
            "",
            "## Minimum Reporting Set",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["minimum_reporting_set"])
    lines.extend(["", "## Current Key Interpretations", ""])
    for key, value in report["current_key_results"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Prohibited Claims", ""])
    lines.extend(f"- {item}" for item in report["prohibited_claims"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export a publication-facing statistical analysis plan.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_plan(root)
    out_json = root / "materials" / "STATISTICAL_ANALYSIS_PLAN.json"
    out_md = root / "materials" / "STATISTICAL_ANALYSIS_PLAN.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md)}, indent=2))


if __name__ == "__main__":
    main()
