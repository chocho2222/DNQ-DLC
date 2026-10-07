"""The qualitative panel has to agree with the run it claims to show.

The snapshot figure is the only place in the manuscript where a reader sees the
cars rather than a table, so a drift between the picture and the recorded data
would be invisible. This test re-reads the plotted values, the plotted step and
the endpoint audit of the same episode, and checks all three against the trace
the figure was drawn from.

The two panels come from different runs on purpose: the proposed controller is
the released training draw replayed with the shipped planner, and the rule
expert is the recorded matrix run of the same episode. Both traces are archived
next to the audit they feed, which is what makes the comparison reproducible.
"""
import csv
import json
import re
import unittest
from pathlib import Path


from _repo_paths import PAPER, artifact

CASE = "M8_scale_n8_seed29"
NUM_AGENTS = 8
SEED = 29
TARGET = NUM_AGENTS - 1
SOURCE = PAPER / "figures" / "figure_snapshot_m8_seed29.csv"
PROPOSED_TRACE = "ours_dnq_dlc_seed13"
RULE_TRACE = "rule_expert_gate"
PROPOSED_AUDIT = artifact("validity_ours_corridor_return_fix_20260929") / "case_level.csv"
PROPOSED_AUDIT_ALGORITHM = "ours_dnq_dlc_seed13"
RULE_AUDIT = artifact("validity_final_all") / "case_level.csv"


def _trace_root(algorithm):
    """First frozen root that carries the trace of this episode."""
    name = f"{algorithm}_n{NUM_AGENTS}_seed{SEED}.trace.json"
    for candidate in (artifact("qualitative_snapshot_fix_20260929"),
                      artifact("main_final_20260922"),
                      artifact("validity_ours_corridor_return_fix_20260929")):
        if (candidate / CASE / "traces" / name).exists():
            return candidate
    return artifact("qualitative_snapshot_fix_20260929")


PROPOSED_ROOT = _trace_root(PROPOSED_TRACE)
RULE_ROOT = _trace_root(RULE_TRACE)


def _yes(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


@unittest.skipUnless(
    SOURCE.exists()
    and (PROPOSED_ROOT / CASE / "traces" / f"{PROPOSED_TRACE}_n{NUM_AGENTS}_seed{SEED}.trace.json").exists()
    and (RULE_ROOT / CASE / "traces" / f"{RULE_TRACE}_n{NUM_AGENTS}_seed{SEED}.trace.json").exists()
    and PROPOSED_AUDIT.exists() and RULE_AUDIT.exists(),
    "released evaluation artifacts unavailable")
class QualitativeSnapshotTests(unittest.TestCase):
    ROOTS = {PROPOSED_TRACE: PROPOSED_ROOT, RULE_TRACE: RULE_ROOT}
    AUDITS = {
        PROPOSED_TRACE: (PROPOSED_AUDIT, PROPOSED_AUDIT_ALGORITHM),
        RULE_TRACE: (RULE_AUDIT, RULE_TRACE),
    }

    def rows(self):
        with open(SOURCE) as handle:
            return list(csv.DictReader(handle))

    def trace(self, algorithm):
        path = (self.ROOTS[algorithm] / CASE / "traces"
                / f"{algorithm}_n{NUM_AGENTS}_seed{SEED}.trace.json")
        return json.loads(path.read_text())

    def audit(self, algorithm):
        path, name = self.AUDITS[algorithm]
        with open(path) as handle:
            for row in csv.DictReader(handle):
                if (row["experiment_id"] == "M8_scale" and row["algorithm"] == name
                        and int(row["seed"]) == SEED):
                    return row
        raise AssertionError(f"no audit row for {algorithm}")

    @staticmethod
    def nearest_rival(row, index=TARGET):
        positions = [item for item in row["positions"]]
        target = positions[index]
        gaps = [((x - target[0]) ** 2 + (y - target[1]) ** 2) ** 0.5
                for other, (x, y) in enumerate(positions) if other != index]
        return min(gaps)

    def test_plotted_step_is_the_closest_approach_of_the_evaluated_car(self):
        for row in self.rows():
            trace = self.trace(row["algorithm"])
            step = int(row["step"])
            gaps = [self.nearest_rival(item) for item in trace]
            self.assertEqual(step, gaps.index(min(gaps)) + 1)

    def test_plotted_values_match_the_trace(self):
        for row in self.rows():
            step = int(row["step"])
            record = self.trace(row["algorithm"])[step - 1]
            self.assertEqual(int(record["step"]), step)
            self.assertAlmostEqual(self.nearest_rival(record),
                                   float(row["min_pair_distance_m"]), places=3)
            self.assertAlmostEqual(float(record["speed"][TARGET]),
                                   float(row["target_speed_mps"]), places=3)
            self.assertAlmostEqual(float(record["speed"][int(row["rival_agent"])]),
                                   float(row["rival_speed_mps"]), places=3)

    def test_panels_carry_the_audited_outcome_of_the_same_episode(self):
        ours, rule = self.audit(PROPOSED_TRACE), self.audit(RULE_TRACE)
        # Both controllers complete the pass in this episode; they differ in
        # whether the manoeuvre stays inside the corridor, which is what the
        # panel is there to show.
        self.assertTrue(_yes(ours["E_full"]))
        self.assertTrue(_yes(rule["E_full"]))
        self.assertAlmostEqual(float(ours["in_corridor_man"]), 1.00, places=2)
        self.assertAlmostEqual(float(ours["grass_fraction"]), 0.000, places=3)
        self.assertAlmostEqual(float(rule["in_corridor_man"]), 0.71, places=2)
        self.assertAlmostEqual(float(rule["grass_fraction"]), 0.244, places=3)

    def test_caption_matches_the_figure_and_the_runs(self):
        caption = (PAPER / "main.tex").read_text(encoding="utf-8")
        panel = caption.split("{figures/figure_snapshot_m8_seed29.pdf}", 1)[1]
        panel = panel.split("\\label{fig:snapshot}", 1)[0]
        for step in ("946", "459"):
            self.assertIn(step, panel)
        self.assertIn("seed 29", panel)
        # The caption names the rivals the selector admitted at that step; the
        # panel itself carries no text beyond the car indices.
        self.assertIn("admits rivals 0, 1 and 6", panel)
        # A submitted caption describes the measurement; the path of the script
        # that drew it belongs to the data-availability statement.
        self.assertNotIn("scripts/", panel)
        self.assertNotIn(".py", panel)

    def test_figure_file_is_the_one_referenced(self):
        tex = (PAPER / "main.tex").read_text(encoding="utf-8")
        self.assertIn("figures/figure_snapshot_m8_seed29.pdf", tex)
        self.assertTrue((PAPER / "figures" / "figure_snapshot_m8_seed29.pdf").exists())
        self.assertTrue(re.search(r"figures/figure_snapshot_m8_seed29\.pdf", tex))


if __name__ == "__main__":
    unittest.main()
