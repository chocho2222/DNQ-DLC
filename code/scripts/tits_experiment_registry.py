#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import json
from copy import deepcopy
from pathlib import Path


MAIN_METHOD = "v6_runtime_dynamic_neighborhood_safe"

PAPER_DLC_MODEL_PATHS = {
    "dlc_joint_transition_observer": "outputs/tits_dynamic_graph_expanded/paper_dlc_baselines/joint_transition_observer.pt",
    "dlc_joint_transition": "outputs/tits_dynamic_graph_expanded/paper_dlc_baselines/joint_transition.pt",
    "dlc_individual_transition": "outputs/tits_dynamic_graph_expanded/paper_dlc_baselines/individual_transition.pt",
}

RL_MODEL_PATHS = {
    "ppo_continuous": "outputs/tits_dynamic_graph_expanded/rl_baselines/ppo_continuous/ppo_continuous.sb3.zip",
    "sac_continuous": "outputs/tits_dynamic_graph_expanded/rl_baselines/sac_continuous/sac_continuous.sb3.zip",
    "td3_continuous": "outputs/tits_dynamic_graph_expanded/rl_baselines/td3_continuous/td3_continuous.sb3.zip",
}

RULE_ALIASES = {
    "rule_expert_gate": {
        "name": "rule_expert_gate",
        "label_cn": "Rule expert",
        "policy": "telemetry_expert_gate",
        "neighbor_mode": "fixed",
        "max_neighbors": None,
        "kind": "rule_baseline",
    },
    "rule_safety_gate": {
        "name": "rule_safety_gate",
        "label_cn": "Safety-gated rule",
        "policy": "telemetry_expert_barrier",
        "neighbor_mode": "fixed",
        "max_neighbors": None,
        "kind": "rule_baseline_safety_gate",
    },
}


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def split_csv_cell(value):
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def base_algorithm_records(config):
    records = {}
    dynamic_graph = config.get("dynamic_graph", {})
    # The learned checkpoint has a fixed relation-slot interface.  A null
    # protocol value means "use the checkpoint width", not an unbounded
    # decoder input; keeping this bounded prevents rollout slot-layout
    # mismatches when the scene contains more vehicles.
    default_max_neighbors = dynamic_graph.get("max_neighbors") or 3
    for item in config.get("algorithms", []):
        policy = item.get("policy") or item.get("model_path")
        if not policy:
            continue
        is_rule_policy = str(policy).startswith("telemetry_")
        record = deepcopy(item)
        record["policy"] = policy
        record.setdefault("label_cn", item.get("name", ""))
        record.setdefault("neighbor_mode", "fixed" if is_rule_policy else "dynamic")
        if is_rule_policy:
            record.setdefault("max_neighbors", None)
        elif record.get("max_neighbors") in (None, ""):
            record["max_neighbors"] = default_max_neighbors
        record.setdefault(
            "neighbor_selection_mode",
            dynamic_graph.get("neighbor_selection_mode", "legacy"),
        )
        records[record["name"]] = record
    return records


def paper_dlc_record(name):
    label = {
        "dlc_joint_transition_observer": "DLC-JTO",
        "dlc_joint_transition": "DLC-JT",
        "dlc_individual_transition": "DLC-IT",
    }[name]
    return {
        "name": name,
        "label_cn": label,
        "policy": PAPER_DLC_MODEL_PATHS[name],
        "neighbor_mode": "fixed",
        "max_neighbors": None,
        "kind": "paper_dlc_world_model_baseline",
        "paper_dlc_model_type": name.replace("dlc_", ""),
        "overtake_aware_planner": False,
    }


def rl_record(name):
    label = {
        "ppo_continuous": "PPO",
        "sac_continuous": "SAC",
        "td3_continuous": "TD3",
    }[name]
    return {
        "name": name,
        "label_cn": label,
        "policy": RL_MODEL_PATHS[name],
        "neighbor_mode": "fixed",
        "max_neighbors": None,
        "kind": "rl_baseline",
    }


def make_ablation_records(base_records):
    full = deepcopy(base_records[MAIN_METHOD])
    full["name"] = "ours_full_v6_safe"
    full["label_cn"] = "Full V6-safe"
    full["kind"] = "formal_ablation_full"

    fixed = deepcopy(full)
    fixed["name"] = "w_o_dynamic_neighborhood"
    fixed["label_cn"] = "w/o dynamic neighborhood"
    fixed["neighbor_mode"] = "fixed"
    fixed["neighbor_selection_mode"] = "legacy"
    fixed["kind"] = "ablation_without_dynamic_neighborhood"

    no_interaction = deepcopy(full)
    no_interaction["name"] = "w_o_interaction_neighbor_selection"
    no_interaction["label_cn"] = "w/o interaction selection"
    no_interaction["neighbor_selection_mode"] = "legacy"
    no_interaction["kind"] = "ablation_without_interaction_neighbor_selection"

    no_quality = deepcopy(full)
    no_quality["name"] = "w_o_quality_proposal"
    no_quality["label_cn"] = "w/o quality proposal"
    for key in [
        "quality_proposal_path",
        "quality_planner_mode",
        "quality_rollout_blend",
        "quality_overtake_weight",
        "quality_lane_weight",
        "quality_grass_weight",
        "quality_close_gap_weight",
    ]:
        no_quality.pop(key, None)
    no_quality["kind"] = "ablation_without_quality_proposal"

    no_risk = deepcopy(full)
    no_risk["name"] = "w_o_risk_penalty"
    no_risk["label_cn"] = "w/o risk penalty"
    no_risk["planner_risk_weight"] = 0.0
    no_risk["planner_uncertainty_weight"] = 0.0
    no_risk["kind"] = "ablation_without_risk_penalty"

    no_safety_quality = deepcopy(full)
    no_safety_quality["name"] = "w_o_safety_quality_terms"
    no_safety_quality["label_cn"] = "w/o safety quality terms"
    no_safety_quality["quality_lane_weight"] = 0.0
    no_safety_quality["quality_grass_weight"] = 0.0
    no_safety_quality["quality_close_gap_weight"] = 0.0
    no_safety_quality["kind"] = "ablation_without_safety_quality_terms"

    no_overtake = deepcopy(full)
    no_overtake["name"] = "w_o_overtake_aware_planner"
    no_overtake["label_cn"] = "w/o overtake-aware planner"
    no_overtake["overtake_aware_planner"] = False
    no_overtake["kind"] = "ablation_without_overtake_aware_planner"

    low_budget = deepcopy(full)
    low_budget["name"] = "low_budget_planner"
    low_budget["label_cn"] = "Low-budget planner"
    low_budget["planner_horizon"] = 2
    low_budget["planner_candidates"] = 6
    low_budget["kind"] = "ablation_low_budget_planner"

    return {
        item["name"]: item
        for item in [
            full,
            fixed,
            no_interaction,
            no_quality,
            no_risk,
            no_safety_quality,
            no_overtake,
            low_budget,
        ]
    }


def build_algorithm_registry(config):
    records = base_algorithm_records(config)
    for name in PAPER_DLC_MODEL_PATHS:
        records[name] = paper_dlc_record(name)
    for name in RL_MODEL_PATHS:
        records[name] = rl_record(name)
    records.update(RULE_ALIASES)
    if MAIN_METHOD in records:
        records.update(make_ablation_records(records))
    return records


def track_manifest_by_id(track_rows):
    return {row["track_id"]: row["track_path"] for row in track_rows if row.get("track_id")}


def model_missing(record):
    policy = str(record.get("policy", ""))
    if not policy or policy.startswith("telemetry_"):
        return False
    return not Path(policy).exists()


def make_config(base_config, algorithm_records, output_dir):
    config = deepcopy(base_config)
    config.setdefault("reporting", {})
    config["reporting"]["output_dir"] = str(output_dir)
    config["reporting"].setdefault("figures_dir", str(Path(output_dir) / "figures"))
    config["reporting"].setdefault("tables_dir", str(Path(output_dir) / "tables"))
    config["reporting"].setdefault("gifs_dir", str(Path(output_dir) / "gifs"))
    config["reporting"].setdefault("logs_dir", str(Path(output_dir) / "logs"))
    config["algorithms"] = list(algorithm_records)
    return config
