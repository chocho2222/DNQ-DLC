#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Shared visual style for the T-ITS multi-car overtaking experiments."""

from pathlib import Path


PROPOSED = "v6_runtime_dynamic_neighborhood_safe"
PROPOSED_E6 = "ours_full_v6_safe"

ALGORITHM_ORDER = [
    "rule_expert_gate",
    "rule_safety_gate",
    "ppo_continuous",
    "sac_continuous",
    "td3_continuous",
    "dlc_individual_transition",
    "dlc_joint_transition",
    "dlc_joint_transition_observer",
    PROPOSED,
]

ALGORITHM_LABELS = {
    "rule_expert_gate": "Rule expert",
    "rule_safety_gate": "Safety rule",
    "ppo_continuous": "PPO",
    "sac_continuous": "SAC",
    "td3_continuous": "TD3",
    "dlc_individual_transition": "DLC-IT",
    "dlc_joint_transition": "DLC-JT",
    "dlc_joint_transition_observer": "DLC-JTO",
    PROPOSED: "Proposed",
    "mixed_target_v6_runtime_dynamic_neighborhood_safe": "Proposed",
    PROPOSED_E6: "Proposed",
    "w_o_dynamic_neighborhood": "w/o dynamic graph",
    "w_o_interaction_neighbor_selection": "w/o interaction selection",
    "w_o_quality_proposal": "w/o quality proposal",
    "w_o_risk_penalty": "w/o risk penalty",
    "w_o_safety_quality_terms": "w/o safety-quality terms",
    "w_o_overtake_aware_planner": "w/o overtaking planner",
    "low_budget_planner": "Low-budget planner",
}

ALGORITHM_GROUPS = {
    "rule_expert_gate": "Rule-based",
    "rule_safety_gate": "Rule-based",
    "ppo_continuous": "RL",
    "sac_continuous": "RL",
    "td3_continuous": "RL",
    "dlc_individual_transition": "DLC variants",
    "dlc_joint_transition": "DLC variants",
    "dlc_joint_transition_observer": "DLC variants",
    PROPOSED: "Ours",
    "mixed_target_v6_runtime_dynamic_neighborhood_safe": "Ours",
    PROPOSED_E6: "Ours",
}

ALGORITHM_COLORS = {
    "rule_expert_gate": "#CF8A86",
    "rule_safety_gate": "#D7A574",
    "ppo_continuous": "#CDBB7A",
    "sac_continuous": "#8CBF9B",
    "td3_continuous": "#86B8BC",
    "dlc_individual_transition": "#9DB7D1",
    "dlc_joint_transition": "#AFA6CF",
    "dlc_joint_transition_observer": "#C2A2CE",
    PROPOSED: "#235A9F",
    "mixed_target_v6_runtime_dynamic_neighborhood_safe": "#235A9F",
    PROPOSED_E6: "#235A9F",
    "w_o_dynamic_neighborhood": "#8FA7C5",
    "w_o_interaction_neighbor_selection": "#A9A0C8",
    "w_o_quality_proposal": "#C1A1C5",
    "w_o_risk_penalty": "#D3A36F",
    "w_o_safety_quality_terms": "#C98F8B",
    "w_o_overtake_aware_planner": "#91B596",
    "low_budget_planner": "#7AA7A9",
}

ABLATION_ORDER = [
    "w_o_dynamic_neighborhood",
    "w_o_interaction_neighbor_selection",
    "w_o_quality_proposal",
    "w_o_risk_penalty",
    "w_o_safety_quality_terms",
    "w_o_overtake_aware_planner",
    "low_budget_planner",
    PROPOSED_E6,
]

VEHICLE_COLORS_HEX = [
    "#235A9F",
    "#CF8A86",
    "#D7A574",
    "#CDBB7A",
    "#8CBF9B",
    "#86B8BC",
    "#9DB7D1",
    "#AFA6CF",
    "#C2A2CE",
    "#6B7280",
    "#9CA3AF",
    "#4B5563",
]


def hex_to_rgb(hex_color):
    text = hex_color.strip().lstrip("#")
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_float_rgb(hex_color):
    return tuple(channel / 255.0 for channel in hex_to_rgb(hex_color))


VEHICLE_COLORS_RGB = [hex_to_rgb(item) for item in VEHICLE_COLORS_HEX]
VEHICLE_COLORS_FLOAT = [hex_to_float_rgb(item) for item in VEHICLE_COLORS_HEX]


def color_for_algorithm(algorithm):
    return ALGORITHM_COLORS.get(algorithm, "#9CA3AF")


def label_for_algorithm(algorithm):
    return ALGORITHM_LABELS.get(algorithm, algorithm)


def group_for_algorithm(algorithm):
    return ALGORITHM_GROUPS.get(algorithm, "Other")


def sorted_algorithms(algorithms):
    rank = {name: idx for idx, name in enumerate(ALGORITHM_ORDER)}
    rank.update({name: len(rank) + idx for idx, name in enumerate(ABLATION_ORDER)})
    return sorted(algorithms, key=lambda name: rank.get(name, 10_000))


def configure_publication_matplotlib(font_size=7.0):
    import matplotlib as mpl
    from matplotlib import font_manager

    for item in [
        "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/times.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ]:
        path = Path(item)
        if path.exists():
            font_manager.fontManager.addfont(str(path))
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif", "serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": font_size,
            "text.color": "black",
            "axes.labelcolor": "black",
            "axes.titlecolor": "black",
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.color": "black",
            "ytick.color": "black",
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.unicode_minus": False,
        }
    )
    return "Times New Roman"
