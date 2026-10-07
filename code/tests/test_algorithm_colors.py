import numpy as np
import pyglet
import unittest

pyglet.options['headless'] = True

from dlc.rollout import make_env
from scripts.tits_figure_style import (
    ABLATION_ORDER, ALGORITHM_COLORS, ALGORITHM_COLOR_ROOTS, ALGORITHM_ORDER, PALETTE,
    bind_algorithm_colors, canonical_algorithm, color_for_algorithm, hex_to_float_rgb,
    marker_for_algorithm,
)
from scripts.export_corrected_v2_palette import validate

MANDATED = {
    "teal_green": "#55A69A",     # 青绿
    "grass_green": "#8BA66B",    # 草绿
    "indigo": "#777E88",         # 靛蓝 (hex column of the supplied palette)
    "bean_red": "#C77F86",       # 豆沙
    "warm_yellow": "#D8BC62",    # 暖黄
    "brown_taupe": "#AD8B73",    # 棕褐
}


def test_method_aliases_and_unique_colors():
    assert color_for_algorithm('DNQ-DLC') == color_for_algorithm('dnq_dlc_full')
    assert color_for_algorithm('DLC-JTO') == color_for_algorithm('dlc_joint_transition_observer')
    # The three continuous-control agents are one regime and deliberately share
    # one colour; marker and line style separate them. Every other arm owns a
    # colour of its own.
    assert len({color_for_algorithm(a) for a in ('ppo_continuous', 'sac_continuous',
                                                'td3_continuous')}) == 1
    roots = {ALGORITHM_COLOR_ROOTS.get(canonical_algorithm(a), canonical_algorithm(a))
             for a in ALGORITHM_ORDER}
    assert len({color_for_algorithm(a) for a in ALGORITHM_ORDER}) == len(roots)


def test_mandated_palette_is_shipped_verbatim():
    for name, hex_color in MANDATED.items():
        assert PALETTE[name] == hex_color
    assert color_for_algorithm('DNQ-DLC') == MANDATED['teal_green']
    assert color_for_algorithm('ours_corrected_v2_sball') == MANDATED['teal_green']
    assert color_for_algorithm('rule_expert_gate') == MANDATED['grass_green']
    assert color_for_algorithm('dlc_individual_transition') == MANDATED['bean_red']
    assert color_for_algorithm('dlc_joint_transition') == MANDATED['warm_yellow']
    assert color_for_algorithm('dlc_joint_transition_observer') == MANDATED['indigo']
    assert color_for_algorithm('ppo_continuous') == MANDATED['brown_taupe']
    assert color_for_algorithm('sac_continuous') == MANDATED['brown_taupe']
    assert color_for_algorithm('td3_continuous') == MANDATED['brown_taupe']


def test_palette_contract_holds_for_every_shipped_algorithm():
    assert validate() == []
    roots = {}
    for algorithm, hex_color in ALGORITHM_COLORS.items():
        roots.setdefault(ALGORITHM_COLOR_ROOTS.get(algorithm, algorithm), hex_color)
    assert len(set(roots.values())) == len(roots)


def test_ablations_are_separated_without_relying_on_hue():
    for algorithm in ABLATION_ORDER:
        color = color_for_algorithm(algorithm)
        assert color.startswith('#') and len(color) == 7
        assert marker_for_algorithm(algorithm) is not None


class PaletteContractTests(unittest.TestCase):
    def test_mandated_palette_is_shipped_verbatim(self):
        test_mandated_palette_is_shipped_verbatim()

    def test_palette_contract_holds_for_every_shipped_algorithm(self):
        test_palette_contract_holds_for_every_shipped_algorithm()

    def test_ablations_are_separated_without_relying_on_hue(self):
        test_ablations_are_separated_without_relying_on_hue()

    def test_method_aliases_and_unique_colors(self):
        test_method_aliases_and_unique_colors()


def test_assignment_survives_reset_and_view_changes():
    env = make_env(num_agents=2, seed=3, observation_type='telemetry_dynamic')
    try:
        for assignment in [('DNQ-DLC', 'DLC-JTO'), ('DLC-JTO', 'DNQ-DLC')]:
            bind_algorithm_colors(env, assignment)
            env.reset()
            expected = [hex_to_float_rgb(color_for_algorithm(a)) for a in assignment]
            assert [car.hull.color for car in env.unwrapped.cars] == expected
            env.unwrapped.use_ego_color = True
            frames = env.render('rgb_array')
            assert len(frames) == 2
            assert all(np.asarray(frame).std() > 0 for frame in frames)
            assert [car.hull.color for car in env.unwrapped.cars] == expected
            assert [r['color'] for r in env.unwrapped.algorithm_color_assignment] == [
                color_for_algorithm(a) for a in assignment
            ]
        with unittest.TestCase().assertRaises(ValueError):
            env.unwrapped.set_vehicle_colors([(1, 0, 0)])
        with unittest.TestCase().assertRaises(ValueError):
            env.unwrapped.set_vehicle_colors([(2, 0, 0), (0, 0, 0)])
    finally:
        env.close()


if __name__ == '__main__':
    test_method_aliases_and_unique_colors()
    test_assignment_survives_reset_and_view_changes()
    print('Algorithm color tests passed (including both rendered viewpoints).')
