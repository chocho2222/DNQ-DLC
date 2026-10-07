#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


OURS_SAFE = "v6_runtime_dynamic_neighborhood_safe"
OURS_FULL = "v6_runtime_dynamic_neighborhood"
QUALITY = "quality_proposal_dlc_world_v1"
DLC = "dlc_world_original"
RULE = "rule_expert_gate"


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fmt(value, digits=3):
    value = as_float(value) if isinstance(value, str) else value
    if value is None:
        return "NA"
    return f"{value:.{digits}f}"


def find_overall(rows, algorithm):
    for row in rows:
        if row["algorithm"] == algorithm:
            return row
    raise KeyError(algorithm)


def find_scenario(rows, benchmark, num_agents, algorithm):
    for row in rows:
        if row["benchmark"] == benchmark and int(row["num_agents"]) == int(num_agents) and row["algorithm"] == algorithm:
            return row
    raise KeyError((benchmark, num_agents, algorithm))


def paired_lookup(rows, algorithm, metric):
    for row in rows:
        if row["algorithm"] == algorithm and row["metric"] == metric:
            return row
    raise KeyError((algorithm, metric))


def metric(row, name):
    return as_float(row.get(f"{name}_mean"))


def ci(row, name):
    return as_float(row.get(f"{name}_ci95_low")), as_float(row.get(f"{name}_ci95_high"))


def mean_ci(row, name, digits=3):
    mean = metric(row, name)
    lo, hi = ci(row, name)
    if mean is None:
        return "NA"
    if lo is None or hi is None:
        return fmt(mean, digits)
    return f"{fmt(mean, digits)} [{fmt(lo, digits)}, {fmt(hi, digits)}]"


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def build_numeric_index(overall, scenario, paired):
    safe = find_overall(overall, OURS_SAFE)
    full = find_overall(overall, OURS_FULL)
    quality = find_overall(overall, QUALITY)
    dlc = find_overall(overall, DLC)
    rule = find_overall(overall, RULE)
    n8_safe = find_scenario(scenario, "vehicle_count_extrapolation", 8, OURS_SAFE)
    n8_dlc = find_scenario(scenario, "vehicle_count_extrapolation", 8, DLC)
    monza6_safe = find_scenario(scenario, "monza_external_track", 6, OURS_SAFE)
    monza6_dlc = find_scenario(scenario, "monza_external_track", 6, DLC)
    monza4_quality = find_scenario(scenario, "monza_external_track", 4, QUALITY)
    monza4_dlc = find_scenario(scenario, "monza_external_track", 4, DLC)
    rows = [
        {"claim_key": "overall_safe_success", "value": mean_ci(safe, "overtake_success_rate"), "source": "confirmatory_overall_statistics.csv"},
        {"claim_key": "overall_dlc_success", "value": mean_ci(dlc, "overtake_success_rate"), "source": "confirmatory_overall_statistics.csv"},
        {"claim_key": "overall_safe_elegant", "value": mean_ci(safe, "elegant_overtake_rate"), "source": "confirmatory_overall_statistics.csv"},
        {"claim_key": "overall_dlc_elegant", "value": mean_ci(dlc, "elegant_overtake_rate"), "source": "confirmatory_overall_statistics.csv"},
        {"claim_key": "overall_safe_overtake_time", "value": mean_ci(safe, "overtake_start_to_complete_time", 1), "source": "confirmatory_overall_statistics.csv"},
        {"claim_key": "overall_dlc_overtake_time", "value": mean_ci(dlc, "overtake_start_to_complete_time", 1), "source": "confirmatory_overall_statistics.csv"},
        {"claim_key": "overall_quality_success", "value": mean_ci(quality, "overtake_success_rate"), "source": "confirmatory_overall_statistics.csv"},
        {"claim_key": "overall_rule_elegant", "value": mean_ci(rule, "elegant_overtake_rate"), "source": "confirmatory_overall_statistics.csv"},
        {"claim_key": "n8_safe_elegant", "value": mean_ci(n8_safe, "elegant_overtake_rate"), "source": "confirmatory_scenario_statistics.csv"},
        {"claim_key": "n8_dlc_elegant", "value": mean_ci(n8_dlc, "elegant_overtake_rate"), "source": "confirmatory_scenario_statistics.csv"},
        {"claim_key": "n8_safe_overtake_time", "value": mean_ci(n8_safe, "overtake_start_to_complete_time", 1), "source": "confirmatory_scenario_statistics.csv"},
        {"claim_key": "n8_dlc_overtake_time", "value": mean_ci(n8_dlc, "overtake_start_to_complete_time", 1), "source": "confirmatory_scenario_statistics.csv"},
        {"claim_key": "monza6_safe_success", "value": mean_ci(monza6_safe, "overtake_success_rate"), "source": "confirmatory_scenario_statistics.csv"},
        {"claim_key": "monza6_dlc_success", "value": mean_ci(monza6_dlc, "overtake_success_rate"), "source": "confirmatory_scenario_statistics.csv"},
        {"claim_key": "monza6_safe_elegant", "value": mean_ci(monza6_safe, "elegant_overtake_rate"), "source": "confirmatory_scenario_statistics.csv"},
        {"claim_key": "monza6_dlc_elegant", "value": mean_ci(monza6_dlc, "elegant_overtake_rate"), "source": "confirmatory_scenario_statistics.csv"},
        {"claim_key": "monza4_quality_elegant", "value": mean_ci(monza4_quality, "elegant_overtake_rate"), "source": "confirmatory_scenario_statistics.csv"},
        {"claim_key": "monza4_dlc_elegant", "value": mean_ci(monza4_dlc, "elegant_overtake_rate"), "source": "confirmatory_scenario_statistics.csv"},
        {"claim_key": "paired_safe_success_improvement", "value": fmt(paired_lookup(paired, OURS_SAFE, "overtake_success_rate")["improvement_vs_dlc_mean"]), "source": "confirmatory_paired_tests_vs_dlc.csv"},
        {"claim_key": "paired_safe_elegant_improvement", "value": fmt(paired_lookup(paired, OURS_SAFE, "elegant_overtake_rate")["improvement_vs_dlc_mean"]), "source": "confirmatory_paired_tests_vs_dlc.csv"},
        {"claim_key": "paired_safe_time_improvement_steps", "value": fmt(paired_lookup(paired, OURS_SAFE, "overtake_start_to_complete_time")["improvement_vs_dlc_mean"], 1), "source": "confirmatory_paired_tests_vs_dlc.csv"},
    ]
    return rows


def write_csv(path, rows):
    fields = ["claim_key", "value", "source"]
    path = Path(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def numeric(rows, key):
    for row in rows:
        if row["claim_key"] == key:
            return row["value"]
    return "NA"


def build_contributions():
    return """# Contributions Draft

This paper makes four contributions.

1. We reformulate DLC-style latent/world-model overtaking as a runtime dynamic-neighborhood graph planning problem, allowing the ego vehicle to rebuild its local interaction graph from nearby vehicles at each decision step instead of fixing the graph to a training-time vehicle count.

2. We introduce an overtake-aware online planning layer on top of the DLC world model, combining interaction-priority neighbor selection, risk-aware candidate evaluation, uncertainty penalties, lane/grass quality terms, and quality-guided proposal actions.

3. We define a multi-car online overtaking benchmark with last-place ego starts, procedural tracks, an 8-car vehicle-count extrapolation setting, and a Monza external CSV track converted into the simulation map format.

4. We provide a reproducibility package containing frozen case commands, source data, bootstrap confidence intervals, paired statistical tests, failure-mode diagnostics, top-down and first-person GIFs, and SHA256 artifact manifests.
"""


def build_methods():
    return """# Methods Draft

## Problem Formulation

We study online multi-car overtaking in a continuous-control racing simulator. Each episode contains one target vehicle controlled by the evaluated algorithm and multiple background vehicles controlled by fixed traffic policies. The target vehicle always starts from the last grid position, so performance reflects overtaking behavior rather than an initial launch advantage. At each decision step, the policy observes telemetry states, constructs a local traffic representation, selects a continuous steering/throttle/brake action, and receives the next simulator state.

## Optimized DLC World Model with Runtime Dynamic Neighborhoods

The proposed method builds on a DLC-style world-model controller. Instead of using a fixed-size interaction representation tied to a specific number of vehicles, the controller constructs a local graph at runtime. The ego node represents the target vehicle; neighboring nodes are selected from surrounding traffic using interaction priority, including relative progress, distance, lateral offset, and closing behavior. A slot mask distinguishes valid neighbors from padded slots, so the same trained model can be evaluated under different vehicle counts.

The graph world model predicts short-horizon progress, risk, and quality-relevant outcomes for candidate actions. The online planner evaluates candidate action sequences under the learned model and scores them using progress reward, collision/risk penalties, uncertainty penalties, lane quality, grass/off-track penalties, and overtaking-specific terms. The safety-oriented v6-safe variant increases risk and grass penalties while keeping a moderate candidate budget, making it the primary method used for the confirmatory evidence.

## Baselines and Ablations

The main baseline is the original DLC world-model controller. Three DLC variants are included: a balanced variant, a safety-weighted variant, and a progress-prioritized fast variant. A quality-proposal DLC branch adds a learned proposal actor trained from higher-quality overtaking and recovery windows. A rule expert is included as a strong hand-engineered baseline to test whether simple traffic rules can match the learned world-model controller.

## Benchmark Protocol

The confirmatory online matrix contains 30 benchmark cases and 240 algorithm-runs. The benchmark covers procedural tracks with 4, 5, and 6 vehicles, an 8-vehicle extrapolation setting, and a Monza external track converted from CSV and evaluated with 4 and 6 vehicles. Each case is evaluated with the same seed, vehicle count, track, background traffic profile, and target start order across algorithms.

## Metrics

The primary metrics are overtake success rate, on-track overtake rate, desirable overtaking behavior rate, rank gain, first overtake time, and time from overtake start to completion. Safety and quality are measured with target grass rate, grass recovery time, lateral deviation, heading error, and a close-contact proxy. Runtime efficiency is measured by mean and 95th-percentile online decision latency.

## Statistical Analysis

All aggregate results are computed from the frozen source CSV. Confidence intervals are estimated by bootstrap resampling over online runs. Comparisons against the original DLC world model use paired case-level differences under matched benchmark, vehicle count, and seed. Binary/rate outcomes are additionally summarized with exact sign tests and McNemar-style presence tests where applicable. A separate statistical analysis pack defines the primary v6-safe comparison family, applies Holm-Bonferroni correction across the five primary metrics, and reports exploratory adjusted p values as supporting rather than standalone confirmatory evidence.
"""


def build_results(index):
    return f"""# Results Draft

## Overall Online Overtaking Performance

Across the 240-run confirmatory matrix, the v6-safe dynamic-neighborhood DLC world model achieved an overtake success rate of {numeric(index, 'overall_safe_success')}, compared with {numeric(index, 'overall_dlc_success')} for the original DLC world model. The quality gap was larger when considering desirable overtaking behavior: v6-safe reached {numeric(index, 'overall_safe_elegant')}, whereas the original DLC world model reached {numeric(index, 'overall_dlc_elegant')}. The mean time from overtake start to completion was {numeric(index, 'overall_safe_overtake_time')} steps for v6-safe and {numeric(index, 'overall_dlc_overtake_time')} steps for the original DLC world model.

Paired case-level tests showed that v6-safe improved overtake success by {numeric(index, 'paired_safe_success_improvement')}, desirable overtaking behavior by {numeric(index, 'paired_safe_elegant_improvement')}, and reduced the start-to-completion overtaking time by {numeric(index, 'paired_safe_time_improvement_steps')} steps relative to the original DLC world model.

## Vehicle-Count Extrapolation

In the 8-vehicle extrapolation benchmark, v6-safe maintained a desirable overtaking behavior rate of {numeric(index, 'n8_safe_elegant')}, while the original DLC world model achieved {numeric(index, 'n8_dlc_elegant')}. The corresponding start-to-completion overtaking time was {numeric(index, 'n8_safe_overtake_time')} steps for v6-safe and {numeric(index, 'n8_dlc_overtake_time')} steps for the original DLC world model. These results support the role of runtime dynamic-neighborhood construction in evaluating vehicle counts beyond the primary 4/5/6-car settings.

## External Monza Track

On the Monza external track with six vehicles, v6-safe achieved an overtake success rate of {numeric(index, 'monza6_safe_success')} and a desirable overtaking behavior rate of {numeric(index, 'monza6_safe_elegant')}. The original DLC world model achieved {numeric(index, 'monza6_dlc_success')} success and {numeric(index, 'monza6_dlc_elegant')} desirable overtaking behavior in the same setting. On Monza with four vehicles, the quality-proposal branch achieved a desirable overtaking behavior rate of {numeric(index, 'monza4_quality_elegant')}, compared with {numeric(index, 'monza4_dlc_elegant')} for the original DLC model.

## Baseline Interpretation

The quality-proposal DLC branch achieved {numeric(index, 'overall_quality_success')} overtake success overall, making it a useful quality-oriented ablation. However, its desirable overtaking behavior rate was lower than v6-safe in the full matrix, so it is best interpreted as a complementary proposal mechanism rather than the primary method. The rule expert achieved {numeric(index, 'overall_rule_elegant')} desirable overtaking behavior overall and very low latency, but failure analysis shows high grass-rate cases, especially on more challenging external-track settings. This supports retaining it as a strong hand-engineered baseline rather than treating it as a replacement for learned world-model planning.
"""


def build_limitations():
    return """# Limitations Draft

The current evidence is limited to simulation. Although the benchmark includes a procedural track family, an 8-vehicle extrapolation setting, and a Monza external CSV-derived track, it does not establish real-vehicle safety or transfer to arbitrary road geometries.

The dynamic-neighborhood controller improves over the original DLC world-model baseline, but it does not eliminate all quality failures. In particular, v6-safe still exhibits high grass-rate cases and some successful but overtakes that do not satisfy desirable overtaking behavior criteria in the procedural four-vehicle setting. These cases should be reported as boundary conditions rather than hidden behind aggregate success rates.

The casewise diagnostic pack identifies worst-case cards for the primary v6-safe controller, including successful but low-quality overtakes with off-track/labels that do not satisfy desirable overtaking behavior criteria, high grass exposure, and long overtake windows. These cards should be used as transparent tail-case evidence in Discussion and reviewer responses, not as replacements for the 240-run aggregate statistics.

The rule expert remains a strong baseline in selected settings because hand-coded traffic rules can be fast and sometimes produce passes that satisfy desirable overtaking behavior criteria. However, its high grass-rate failure modes and lack of learned world-model adaptation limit its role as a general solution.

Metric sensitivity should be treated as an explicit post-hoc analysis boundary. The definitions of on-track and desirable overtaking behavior depend on threshold choices for grass exposure, lateral deviation, and overtake-window quality; therefore, threshold-based conclusions should be reported together with the protocol card and sensitivity evidence rather than as universal driving-quality guarantees.

The quality-proposal branch is a useful proposal mechanism within the DLC-style world-model family, not an independently optimal controller. Its role is to provide additional candidate actions and quality-biased comparisons; the confirmatory results show that it can improve completion behavior, but it should not be described as replacing risk-aware world-model planning.

The compute ledger is not a complete historical wall-clock trace for all cases because part of the matrix was completed through repair runs. The complete experimental scale is therefore best reported as 240 algorithm-runs and 528000 simulated finish steps, with wall-clock timing described as partially recorded.

The threats-to-validity dossier and claim guardrails should be used when preparing the final Discussion and reviewer response. They separate bounded simulator claims from prohibited statements about real-vehicle safety, arbitrary road geometry, unlimited traffic density, or certified collision-free behavior.

Future work should add more external tracks, higher-density traffic, more diverse background drivers, explicit contact/collision modeling, real-time deployment profiling, and sim-to-real validation in a higher-fidelity autonomous driving simulator.
"""


def build_abstract():
    return """# Abstract and Highlight Draft

## Abstract Draft

Learning-based autonomous overtaking remains difficult because the number and spatial arrangement of nearby vehicles change at runtime, while many world-model controllers assume a fixed interaction structure. We propose an optimized DLC-style world model with runtime dynamic-neighborhood graph construction for multi-car overtaking. The controller selects interaction-relevant neighbors online, evaluates overtake-aware action candidates with learned progress/risk/quality predictions, and supports evaluation under different vehicle counts without retraining the graph model for each traffic size. We evaluate the method in a 240-run online confirmatory matrix covering procedural tracks, an 8-vehicle extrapolation setting, and a Monza external CSV-derived track. Compared with the original DLC world-model baseline, the safety-oriented dynamic-neighborhood variant improves overtake success, desirable overtaking behavior, on-track overtaking, and overtake completion time. We further provide paired statistical tests, failure-mode analysis, top-down and first-person visual evidence, and a reproducibility package with source data and artifact checksums.

## Highlights

- Runtime dynamic-neighborhood graph construction enables online multi-car overtaking without fixing the graph to a single vehicle count.
- An overtake-aware DLC world-model planner improves success, on-track/desirable overtaking, and overtake completion time over the original DLC world model.
- Confirmatory evaluation covers 240 online runs across procedural, 8-car extrapolation, and Monza external-track benchmarks.
- The release includes source data, paired tests, failure atlas, GIF evidence, frozen commands, and SHA256 artifact manifests.
"""


def build_audit(paths, index):
    required = list(paths.values())
    missing = [path for path in required if not Path(path).exists() or Path(path).stat().st_size == 0]
    required_keys = [
        "overall_safe_success",
        "overall_dlc_success",
        "overall_safe_elegant",
        "overall_dlc_elegant",
        "n8_safe_elegant",
        "monza6_safe_success",
        "paired_safe_elegant_improvement",
    ]
    index_keys = {row["claim_key"] for row in index}
    missing_keys = [key for key in required_keys if key not in index_keys]
    return {
        "status": "pass" if not missing and not missing_keys else "fail",
        "missing_or_empty_files": missing,
        "missing_numeric_keys": missing_keys,
        "numeric_key_count": len(index),
        "note": "The manuscript package is generated from confirmatory evidence tables and should be treated as manuscript-ready draft material, not as a new empirical run.",
    }


def main():
    parser = argparse.ArgumentParser(description="Export T-ITS manuscript-ready draft package.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_manuscript_package")
    parser.add_argument("--overall", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv")
    parser.add_argument("--scenario", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_scenario_statistics.csv")
    parser.add_argument("--paired", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv")
    args = parser.parse_args()

    overall = read_csv(args.overall)
    scenario = read_csv(args.scenario)
    paired = read_csv(args.paired)
    out_dir = Path(args.out_dir)
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    index = build_numeric_index(overall, scenario, paired)
    paths = {
        "numeric_index_csv": write_csv(tables / "manuscript_numeric_index.csv", index),
        "contributions": write(materials / "CONTRIBUTIONS_DRAFT.md", build_contributions()),
        "methods": write(materials / "METHODS_DRAFT.md", build_methods()),
        "results": write(materials / "RESULTS_DRAFT.md", build_results(index)),
        "limitations": write(materials / "LIMITATIONS_DRAFT.md", build_limitations()),
        "abstract_highlights": write(materials / "ABSTRACT_HIGHLIGHTS_DRAFT.md", build_abstract()),
    }
    audit = build_audit(paths, index)
    paths["numeric_consistency_audit"] = write(out_dir / "manuscript_numeric_consistency_audit.json", json.dumps(audit, ensure_ascii=False, indent=2))
    manifest = {
        "status": "complete" if audit["status"] == "pass" else "needs_attention",
        "out_dir": str(out_dir),
        "inputs": {
            "overall": args.overall,
            "scenario": args.scenario,
            "paired": args.paired,
        },
        "paths": paths,
        "audit": audit,
    }
    manifest_path = write(out_dir / "tits_manuscript_package_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "numeric_keys": len(index)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
