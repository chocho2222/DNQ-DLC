"""Resolve repository and frozen-artifact paths in both supported layouts.

The unit tests run in two trees: the development tree, where the evaluation
roots sit under ``outputs/tits_dynamic_graph_expanded`` and the manuscript under
``paper_rewriting_output_tits_dynamic_graph_draft_20260625/tits_submission_final``,
and the release repository, where the same roots are copied under
``source_data`` and ``checkpoints`` and the manuscript under ``paper``. Both are
resolved here so that no test hard-codes one of them.
"""

from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        has_configs = (parent / "configs").is_dir()
        has_scripts = (parent / "scripts").is_dir() or (parent / "code" / "scripts").is_dir()
        if has_configs and has_scripts:
            return parent
    return Path(__file__).resolve().parents[1]


REPO = _repo_root()
IS_RELEASE = (REPO / "source_data").is_dir()
DATA = REPO / "source_data" if IS_RELEASE else REPO / "outputs" / "tits_dynamic_graph_expanded"
PAPER = (REPO / "paper" if IS_RELEASE else
         REPO / "paper_rewriting_output_tits_dynamic_graph_draft_20260625" / "tits_submission_final")
CONFIGS = REPO / "configs"
CHECKPOINTS = REPO / "checkpoints"


def artifact(name: str) -> Path:
    """Directory of a frozen run root, in either layout."""
    for candidate in (DATA / name, DATA / "corrected_v2_20260920" / name, CHECKPOINTS / name):
        if candidate.is_dir():
            return candidate
    return DATA / name
