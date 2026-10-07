#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Shared visual style for the T-ITS multi-car overtaking experiments."""

import re
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
    "ours_dnq_dlc",
]

ALGORITHM_LABELS = {
    'joint_clearance_pilot': 'Joint-clearance pilot (development)',
    'graph_actor_pilot': 'Graph proposal pilot (development)',
    'graph_dlc_pilot': 'Graph-DLC pilot (development)',
    'graph_physical_rules_pilot': 'Physical rules + legacy score (pilot)',
    'graph_physical_quality_pilot': 'Physical rules + geometric score (pilot)',
    "rule_expert_gate": "Rule expert",
    "rule_safety_gate": "Safety rule",
    "ppo_continuous": "PPO",
    "sac_continuous": "SAC",
    "td3_continuous": "TD3",
    "dlc_individual_transition": "DLC-IT",
    "dlc_joint_transition": "DLC-JT",
    "dlc_joint_transition_observer": "DLC-JTO",
    PROPOSED: "DNQ-DLC",
    "ours_dnq_dlc": "DNQ-DLC (ours)",
    "mixed_target_v6_runtime_dynamic_neighborhood_safe": "DNQ-DLC",
    PROPOSED_E6: "DNQ-DLC",
    "w_o_dynamic_neighborhood": "w/o dynamic graph",
    "w_o_interaction_neighbor_selection": "w/o interaction selection",
    "w_o_quality_proposal": "w/o quality proposal",
    "w_o_risk_penalty": "w/o risk penalty",
    "w_o_safety_quality_terms": "w/o safety-quality terms",
    "w_o_overtake_aware_planner": "w/o overtaking planner",
    "low_budget_planner": "Low-budget planner",
    # corrected-protocol run identifiers
    "dnq_dlc_final": "DNQ-DLC (ours)",
    "ours_corrected_v2": "DNQ-DLC",
    "ours_corrected_v2_best": "DNQ-DLC (ours)",
    "ours_corrected_v2_sball": "DNQ-DLC (speed-balanced)",
    "ours_corrected_v2_guard_filter": "DNQ-DLC (guard filter)",
    "ours_corrected_v2_guard_free": "DNQ-DLC w/o safety shield",
    "ours_corrected_v2_best_no_liveness": "DNQ-DLC w/o liveness",
    "ours_corrected_v2_best_hold1": "DNQ-DLC (hold = 1)",
    "ours_corrected_v2_clearance": "DNQ-DLC + clearance feasibility",
    "ours_corrected_v2_live17w15": "DNQ-DLC (speed reference 17, w=1.5)",
    "ours_corrected_v2_clearpen": "DNQ-DLC (penalty + clearance)",
    "ours_corrected_v2_clr17w15": "DNQ-DLC (clearance + speed reference 17)",
    "ours_corrected_v2_clr17w25": "DNQ-DLC (clearance + speed reference 17, w=2.5)",
    "ours_corrected_v2_live17w30": "DNQ-DLC (speed reference 17, w=3.0)",
    # E6 ablation identifiers (same ablations as w_o_*, run under a shorter tag)
    "no_dynamic_graph": "w/o dynamic graph",
    "no_world_model": "w/o world model",
    "no_quality_proposal": "w/o quality proposal",
    "no_risk_head": "w/o risk penalty",
    "no_safety_shield": "w/o safety shield",
    "no_liveness": "w/o liveness constraint",
    "no_overtake_candidates": "w/o overtaking candidates",
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
    "dnq_dlc_final": "Ours",
    "mixed_target_v6_runtime_dynamic_neighborhood_safe": "Ours",
    PROPOSED_E6: "Ours",
    "no_dynamic_graph": "Ablations",
    "no_world_model": "Ablations",
    "no_quality_proposal": "Ablations",
    "no_risk_head": "Ablations",
    "no_safety_shield": "Ablations",
    "no_liveness": "Ablations",
    "no_overtake_candidates": "Ablations",
}

# Fixed colour vocabulary. One algorithm owns exactly one colour across every
# figure, screenshot and video frame of the submission; the mapping never
# depends on which algorithms happen to appear in a plot.
#
# The first six entries are the mandated palette (青绿, 草绿, 靛蓝, 豆沙, 暖黄,
# 棕褐), taken verbatim from the supplied hex column. Note that the supplied
# H/S/V row for 靛蓝 (233.54°, 35.33 %, 72.16 %) resolves to #777EB8 rather than
# to the adjacent hex #777E88, which is a desaturated slate (240°, 12.5 %,
# 53.3 %). The hex column was treated as authoritative; switching to the H/S/V
# row would mean re-colouring every 靛蓝 series. The remaining entries extend the
# palette inside the same saturation (30-55 %) and value (64-85 %) band.
#
# The six mandated colours are assigned to the six objects the comparison
# figures actually distinguish: the proposed controller (青绿), the rule expert
# (草绿), the three DLC variants (豆沙, 暖黄, 靛蓝) and the continuous-control
# group (棕褐). The three reinforcement-learning agents share 棕褐 because the
# paper treats them as one regime and never compares them as three separate
# contributions; they stay distinguishable by marker (^, v, D) and by line
# style, never by hue alone.
PALETTE = {
    "teal_green": "#55A69A",     # 青绿
    "grass_green": "#8BA66B",    # 草绿
    "indigo": "#777E88",         # 靛蓝
    "bean_red": "#C77F86",       # 豆沙
    "warm_yellow": "#D8BC62",    # 暖黄
    "brown_taupe": "#AD8B73",    # 棕褐
    "moss_green": "#6FB291",
    "haze_blue": "#769AB8",
    "cyan_blue": "#6DA9B5",
    "lilac_grey": "#A284BD",
    "lotus_pink": "#C280A6",
    "citron": "#B0B86A",
    "sand_taupe": "#BDA884",
    "olive": "#88B279",
    "ablation_1": "#8C96DB",
    "ablation_2": "#8A83CC",
    "ablation_3": "#839BCC",
    "ablation_4": "#5F67A3",
    "ablation_5": "#726AB8",
    "ablation_6": "#6A84B8",
    "ablation_7": "#8D94C9",
    "ablation_8": "#7772A3",
    "ablation_9": "#7D74AE",
    "ablation_10": "#9489D4",
    "ablation_11": "#8E85C0",
    "ablation_12": "#7F9BC4",
    "ablation_13": "#8FA3D6",
    "ablation_14": "#6E7FB0",
    "ablation_15": "#5A6BA8",
    "ablation_16": "#A9B5E3",
    "neutral_dark": "#6B7280",
    "neutral_mid": "#9CA3AF",
    "neutral_light": "#D1D5DB",
}

ALGORITHM_COLORS = {
    # rule-based baselines
    "rule_expert_gate": PALETTE["grass_green"],
    "rule_safety_gate": PALETTE["neutral_mid"],
    # reinforcement-learning baselines: one regime, one colour
    "ppo_continuous": PALETTE["brown_taupe"],
    "sac_continuous": PALETTE["brown_taupe"],
    "td3_continuous": PALETTE["brown_taupe"],
    # DLC family
    "dlc_individual_transition": PALETTE["bean_red"],
    "dlc_joint_transition": PALETTE["warm_yellow"],
    "dlc_joint_transition_observer": PALETTE["indigo"],
    "ours_dnq_dlc": PALETTE["teal_green"],
    # the submitted method, its aliases and its recorded variants
    PROPOSED: PALETTE["teal_green"],
    "mixed_target_v6_runtime_dynamic_neighborhood_safe": PALETTE["teal_green"],
    PROPOSED_E6: PALETTE["teal_green"],
    "dnq_dlc_full": PALETTE["teal_green"],
    "dnq_dlc_final": PALETTE["teal_green"],
    "ours_corrected_v2": PALETTE["teal_green"],
    "ours_corrected_v2_sball": PALETTE["teal_green"],
    "ours_corrected_v2_guard_filter": PALETTE["teal_green"],
    "ours_corrected_v2_best": PALETTE["teal_green"],
    "ours_corrected_v2_clearance": PALETTE["teal_green"],
    "ours_corrected_v2_live17w15": PALETTE["ablation_12"],
    "ours_corrected_v2_clearpen": PALETTE["ablation_14"],
    "ours_corrected_v2_clr17w15": PALETTE["ablation_15"],
    "ours_corrected_v2_clr17w25": PALETTE["ablation_16"],
    "ours_corrected_v2_live17w30": PALETTE["ablation_13"],
    # ablations: same hue family, separated by value, line style and marker
    "ours_corrected_v2_guard_free": PALETTE["ablation_3"],
    "ours_corrected_v2_best_no_liveness": PALETTE["ablation_9"],
    "ours_corrected_v2_best_hold1": PALETTE["ablation_10"],
    "w_o_dynamic_neighborhood": PALETTE["ablation_1"],
    "w_o_interaction_neighbor_selection": PALETTE["ablation_2"],
    "w_o_quality_proposal": PALETTE["ablation_6"],
    "w_o_risk_penalty": PALETTE["ablation_4"],
    "w_o_safety_quality_terms": PALETTE["ablation_5"],
    "w_o_overtake_aware_planner": PALETTE["ablation_7"],
    "low_budget_planner": PALETTE["ablation_8"],
    # E6 ablation identifiers keep the colour of the ablation they denote, so a
    # component owns one colour regardless of which tag the run used.
    "no_dynamic_graph": PALETTE["ablation_1"],
    "no_world_model": PALETTE["ablation_11"],
    "no_quality_proposal": PALETTE["ablation_6"],
    "no_risk_head": PALETTE["ablation_4"],
    "no_safety_shield": PALETTE["ablation_5"],
    "no_liveness": PALETTE["ablation_9"],
    "no_overtake_candidates": PALETTE["ablation_7"],
    # development pilots, kept out of the final figures
    "joint_clearance_pilot": PALETTE["moss_green"],
    "graph_actor_pilot": PALETTE["lotus_pink"],
    "graph_dlc_pilot": PALETTE["citron"],
    "graph_physical_rules_pilot": PALETTE["sand_taupe"],
    "graph_physical_quality_pilot": PALETTE["olive"],
}

# Names that denote the same controller. The palette validator collapses these
# before checking that no two distinct algorithms share a colour.
ALGORITHM_COLOR_ROOTS = {
    # The three continuous-control agents form one regime and share one colour;
    # they are separated by marker and line style.
    "ppo_continuous": "rl_group",
    "sac_continuous": "rl_group",
    "td3_continuous": "rl_group",
    "mixed_target_v6_runtime_dynamic_neighborhood_safe": PROPOSED,
    PROPOSED_E6: PROPOSED,
    # `ours_dnq_dlc` is the identifier the released matrix and the submitted
    # figures use for the proposed method; it is the same arm as PROPOSED.
    "ours_dnq_dlc": PROPOSED,
    "dnq_dlc_full": PROPOSED,
    "dnq_dlc_final": PROPOSED,
    "ours_corrected_v2": PROPOSED,
    "ours_corrected_v2_best": PROPOSED,
    "ours_corrected_v2_sball": PROPOSED,
    "ours_corrected_v2_guard_filter": PROPOSED,
    "ours_corrected_v2_clearance": PROPOSED,
    # E6 identifiers denote the same ablations as their w_o_* / best_no_* roots.
    "no_dynamic_graph": "w_o_dynamic_neighborhood",
    "no_world_model": "w_o_world_model",
    "no_quality_proposal": "w_o_quality_proposal",
    "no_risk_head": "w_o_risk_penalty",
    "no_safety_shield": "w_o_safety_quality_terms",
    "no_liveness": "ours_corrected_v2_best_no_liveness",
    "no_overtake_candidates": "w_o_overtake_aware_planner",
}

# Ablations share the method hue, so identity is also carried by dash pattern
# and marker; no figure may rely on hue alone.
ALGORITHM_LINESTYLES = {
    "sac_continuous": "--",
    "td3_continuous": "-.",
    "w_o_dynamic_neighborhood": "--",
    "w_o_interaction_neighbor_selection": "-.",
    "w_o_quality_proposal": ":",
    "w_o_risk_penalty": (0, (3, 1, 1, 1)),
    "w_o_safety_quality_terms": (0, (5, 1)),
    "w_o_overtake_aware_planner": (0, (1, 1)),
    "low_budget_planner": (0, (4, 2, 1, 2)),
    "ours_corrected_v2_guard_free": "--",
    "ours_corrected_v2_best_no_liveness": "-.",
    "ours_corrected_v2_best_hold1": (0, (3, 1, 1, 1)),
    "no_dynamic_graph": "--",
    "no_world_model": "-.",
    "no_quality_proposal": ":",
    "no_risk_head": (0, (3, 1, 1, 1)),
    "no_safety_shield": (0, (5, 1)),
    "no_liveness": (0, (3, 1, 1, 1)),
    "no_overtake_candidates": (0, (1, 1)),
}

ALGORITHM_MARKERS = {
    "rule_expert_gate": "o",
    "rule_safety_gate": "s",
    "ppo_continuous": "^",
    "sac_continuous": "v",
    "td3_continuous": "D",
    "dlc_individual_transition": "<",
    "dlc_joint_transition": ">",
    "dlc_joint_transition_observer": "P",
    PROPOSED: "*",
    "ours_dnq_dlc": "*",
    "dnq_dlc_final": "*",
    "ours_corrected_v2_guard_free": "X",
    "ours_corrected_v2_best_no_liveness": "2",
    "ours_corrected_v2_best_hold1": "3",
    "w_o_dynamic_neighborhood": "1",
    "w_o_interaction_neighbor_selection": "2",
    "w_o_quality_proposal": "3",
    "w_o_risk_penalty": "4",
    "w_o_safety_quality_terms": "1",
    "w_o_overtake_aware_planner": "2",
    "low_budget_planner": "3",
    PROPOSED_E6: "*",
    "no_dynamic_graph": "1",
    "no_world_model": "2",
    "no_quality_proposal": "3",
    "no_risk_head": "4",
    "no_safety_shield": "s",
    "no_liveness": "2",
    "no_overtake_candidates": "2",
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
    "no_dynamic_graph",
    "no_world_model",
    "no_quality_proposal",
    "no_risk_head",
    "no_safety_shield",
    "no_liveness",
    "no_overtake_candidates",
]

VEHICLE_COLORS_HEX = [
    PALETTE["indigo"],
    PALETTE["bean_red"],
    PALETTE["brown_taupe"],
    PALETTE["teal_green"],
    PALETTE["grass_green"],
    PALETTE["warm_yellow"],
    PALETTE["cyan_blue"],
    PALETTE["haze_blue"],
    PALETTE["lilac_grey"],
    PALETTE["neutral_dark"],
    PALETTE["neutral_mid"],
    PALETTE["neutral_light"],
]


def hex_to_rgb(hex_color):
    text = hex_color.strip().lstrip("#")
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_float_rgb(hex_color):
    return tuple(channel / 255.0 for channel in hex_to_rgb(hex_color))


VEHICLE_COLORS_RGB = [hex_to_rgb(item) for item in VEHICLE_COLORS_HEX]
VEHICLE_COLORS_FLOAT = [hex_to_float_rgb(item) for item in VEHICLE_COLORS_HEX]


_SEED_SUFFIX_RE = re.compile(r"_seed\d+$")


def color_for_algorithm(algorithm):
    return ALGORITHM_COLORS.get(canonical_algorithm(algorithm), "#9CA3AF")


def label_for_algorithm(algorithm):
    name = canonical_algorithm(algorithm)
    return ALGORITHM_LABELS.get(name, algorithm)


def canonical_algorithm(algorithm):
    # A trained draw is referenced as ``<algorithm>_seed<k>`` by the seed-spread
    # runs; the draw is a training seed, not a different controller, so the
    # suffix is dropped before the colour and label tables are consulted.
    algorithm = _SEED_SUFFIX_RE.sub("", algorithm)
    aliases = {
        "DNQ-DLC": PROPOSED, "dnq_dlc_full": PROPOSED,
        "ours_dnq_dlc": PROPOSED,
        "DNQ-DLC (corrected)": PROPOSED,
        "ours": PROPOSED, "Ours": PROPOSED,
        "Rule Expert": "rule_expert_gate", "Rule expert": "rule_expert_gate",
        "Safety Rule": "rule_safety_gate", "Safety rule": "rule_safety_gate",
        "DLC-IT": "dlc_individual_transition",
        "DLC-JT": "dlc_joint_transition",
        "DLC-JTO": "dlc_joint_transition_observer",
        "PPO": "ppo_continuous", "SAC": "sac_continuous", "TD3": "td3_continuous",
    }
    return aliases.get(algorithm, algorithm)


def linestyle_for_algorithm(algorithm):
    return ALGORITHM_LINESTYLES.get(canonical_algorithm(algorithm), "-")


def marker_for_algorithm(algorithm):
    return ALGORITHM_MARKERS.get(canonical_algorithm(algorithm))


def bind_algorithm_colors(env, assignment):
    """Bind hull and trajectory colors to controllers, never camera or grid slot."""
    base = env.unwrapped
    colors = [hex_to_float_rgb(color_for_algorithm(name)) for name in assignment]
    base.set_vehicle_colors(colors)
    base.algorithm_color_assignment = [
        {"agent_id": i, "algorithm": name, "label": label_for_algorithm(name),
         "color": color_for_algorithm(name)}
        for i, name in enumerate(assignment)
    ]
    return [hex_to_rgb(color_for_algorithm(name)) for name in assignment]


def group_for_algorithm(algorithm):
    return ALGORITHM_GROUPS.get(algorithm, "Other")


def sorted_algorithms(algorithms):
    rank = {name: idx for idx, name in enumerate(ALGORITHM_ORDER)}
    rank.update({name: len(rank) + idx for idx, name in enumerate(ABLATION_ORDER)})
    return sorted(algorithms, key=lambda name: rank.get(name, 10_000))


def configure_publication_matplotlib(font_size=10.5):
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
            "font.weight": "normal",
            "axes.titleweight": "normal",
            "figure.titleweight": "normal",
            "text.color": "black",
            "axes.labelcolor": "black",
            "axes.titlecolor": "black",
            "axes.spines.right": False,
            "axes.spines.top": False,
            # The figures are drawn at the size they print at, so a 2 pt rule
            # would print as a 2 pt rule and read as a heavy box around the
            # data. Journal axes sit near 1 pt.
            "axes.linewidth":  1.1,
            "xtick.major.width":  1.1,
            "ytick.major.width":  1.1,
            "xtick.color": "black",
            "ytick.color": "black",
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.unicode_minus": False,
        }
    )
    return "Times New Roman"
