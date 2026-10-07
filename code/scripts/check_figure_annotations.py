#!/usr/bin/env python
"""Check that no legend or annotation sits on top of a plotted mark.

Every data figure of the manuscript is regenerated in memory, and for each panel
the display box of every legend and text object is tested against the display box
of every bar, marker, scatter point and error-bar whisker in the same panel. This
is the geometric counterpart of reading the PDF: it catches the overlaps that a
reader notices in print but that no test of the numbers would catch, such as a
legend drawn across an error bar or a count label printed on top of the bar it
counts.

The script prints one line per figure and exits non-zero if any overlap is found.
It reads the released tables of the final matrix, so it is run after those tables
change, not as part of the unit-test suite.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
from matplotlib.container import ErrorbarContainer  # noqa: E402
from matplotlib.transforms import Bbox  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.build_final_paper_figures as figures  # noqa: E402

DEFAULT_ROOT = (ROOT / "outputs" / "tits_dynamic_graph_expanded" / "corrected_v2_20260920")


def capture(fig, stem):
    """Replace the writer of the figure module, so figures are built, not saved."""
    CAPTURED.append((Path(stem).name, fig))
    return []


def mark_boxes(fig):
    boxes = []
    for axis in fig.axes:
        panel = getattr(axis, "_panel_letter", "")
        for patch in axis.patches:
            # a leader line drawn by ``annotate`` is meant to touch its own mark
            if patch.get_gid() == "leader-line":
                continue
            try:
                boxes.append((panel, "patch", patch.get_window_extent()))
            except Exception:
                pass
        for line in axis.lines:
            if line.get_marker() in (None, "None", ""):
                continue
            for x, y in zip(line.get_xdata(), line.get_ydata()):
                if np.isfinite(x) and np.isfinite(y):
                    px, py = axis.transData.transform((x, y))
                    boxes.append((panel, "marker", Bbox.from_bounds(px - 3, py - 3, 6, 6)))
        for collection in axis.collections:
            try:
                offsets = np.asarray(collection.get_offsets())
            except Exception:
                continue
            if offsets.ndim != 2:
                continue
            for x, y in offsets:
                if np.isfinite(x) and np.isfinite(y):
                    px, py = axis.transData.transform((x, y))
                    boxes.append((panel, "point", Bbox.from_bounds(px - 2, py - 2, 4, 4)))
        for container in axis.containers:
            if not isinstance(container, ErrorbarContainer):
                continue
            for artist in container[2]:
                for path in artist.get_paths():
                    points = axis.transData.transform(path.vertices)
                    if len(points):
                        boxes.append((panel, "error bar", Bbox.from_extents(
                            points[:, 0].min(), points[:, 1].min(),
                            points[:, 0].max(), points[:, 1].max())))
    return boxes


def text_boxes(fig):
    boxes = []
    for axis in fig.axes:
        panel = getattr(axis, "_panel_letter", "")
        legend = axis.get_legend()
        if legend is not None:
            boxes.append((panel, "legend", legend.get_window_extent()))
        for child in axis.texts:
            # a panel letter sits above the axes, where no mark is drawn
            if child.get_gid() == "panel-letter":
                continue
            boxes.append((panel, "text " + child.get_text()[:14],
                          child.get_window_extent()))
    return boxes


def check(fig):
    fig.canvas.draw()
    marks = mark_boxes(fig)
    labels = text_boxes(fig)
    problems = []
    for panel, kind, box in labels:
        for mark_panel, mark_kind, mark_box in marks:
            if panel == mark_panel and box.overlaps(mark_box):
                problems.append(f"{kind} overlaps {mark_kind}")
    # Two labels on the same panel must not touch either: a crowded two-label
    # near-miss in the main table's right-hand panel is the reason this is
    # checked here and not only by eye.
    for index, (panel, kind, box) in enumerate(labels):
        for other_panel, other_kind, other_box in labels[index + 1:]:
            if panel == other_panel and box.overlaps(other_box):
                problems.append(f"{kind} overlaps {other_kind}")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=str(DEFAULT_ROOT),
                        help="root holding validity_final_all, controller_signals_* and "
                             "the other tables of the final matrix")
    parser.add_argument("--ours-validity", default="",
                        help="audit of the proposed controller; the fused table is the default")
    parser.add_argument("--ours-containment", default="",
                        help="containment of the proposed controller; the fused table is the default")
    parser.add_argument("--ours-tables", choices=("fused", "seedspread"), default="fused",
                        help="which proposed-controller table the manuscript figures are built "
                             "from; 'seedspread' checks the five single-model arms of the "
                             "seed-spread study, 'fused' the submitted five-model policy")
    parser.add_argument("--signals", default="",
                        help="directory of controller_signals_by_scale.csv and "
                             "controller_admitted_size_hist.csv; default is the "
                             "proposed-controller mechanism table of the printed figure")
    parser.add_argument("--events", default="",
                        help="directory of vehicle_event_level.csv behind the manoeuvre figure")
    parser.add_argument("--admission", default="",
                        help="directory of neighborhood_event_level.csv behind the scale figure")
    args = parser.parse_args()
    root = Path(args.data_root)
    expanded = Path(__file__).resolve().parents[1] / "outputs" / "tits_dynamic_graph_expanded"
    suffix = "_fused_20260928" if args.ours_tables == "fused" else ""
    if not args.ours_validity:
        name = ("validity_ours_ensemble_20260928" if args.ours_tables == "fused"
                else "validity_ours_seedspread_20260928")
        args.ours_validity = str(expanded / name / "case_level.csv")
    if not args.ours_containment:
        name = ("containment_ours_ensemble_20260928" if args.ours_tables == "fused"
                else "containment_ours_seedspread_20260928")
        args.ours_containment = str(expanded / name / "episode_level.csv")
    # Defaults follow the recipe that reproduces the shipped figures byte for
    # byte: the mechanism table, the event table and the neighbourhood table of
    # the 2026-09-29 correction wave.
    fix_root = expanded / "validity_ours_corridor_return_fix_20260929"
    signals_dir = Path(args.signals) if args.signals else fix_root / "mechanism"
    events_dir = Path(args.events) if args.events else expanded / "manoeuvre_events_20260929"
    windows_dir = Path(args.admission) if args.admission else fix_root / "neighborhood_events"

    figures._save = capture
    figures.configure_publication_matplotlib()
    figures.load_episode_containment(root / "containment_all_20260923" / "episode_level.csv")
    cases = [r for r in figures.read_csv(root / "validity_final_all" / "case_level.csv")
             if r["status"] == "ok"]
    signals = figures.read_csv(signals_dir / "controller_signals_by_scale.csv")
    histogram = figures.read_csv(signals_dir / "controller_admitted_size_hist.csv")
    events = figures.read_csv(events_dir / "vehicle_event_level.csv")
    windows = figures.read_csv(windows_dir / "neighborhood_event_level.csv")

    # Mirror what the manuscript figure does: the three continuous-control
    # families are pooled over five training seeds and replace the single-seed
    # rows of the main matrix. Checking the figure without them would test a
    # panel that is not the one printed.
    figures.load_rl_strict(figures.ROOT / "outputs" / "tits_dynamic_graph_expanded"
                           / "validity_rl_strict_20260927" / "case_level.csv")
    figures.load_rl_containment(figures.ROOT / "outputs" / "tits_dynamic_graph_expanded"
                                / "validity_rl_strict_20260927" / "episode_level.csv")
    if Path(args.ours_validity).exists():
        figures.load_ours_seedspread(args.ours_validity)
    if Path(args.ours_containment).exists():
        figures.load_ours_containment(args.ours_containment)
    figures.RESAMPLED_ROWS[:] = list(figures.OURS_ROWS) + list(figures.RL_ROWS)
    pooled = set(figures.RL_FAMILY.values()) | (
        {figures.OURS} if figures.OURS_ROWS else set())
    cases = [r for r in cases if r["algorithm"] not in pooled] + figures.RESAMPLED_ROWS

    scratch = Path("/tmp")
    figures.figure_endpoints(cases, scratch)
    figures.figure_scale_membership(cases, windows, scratch)
    figures.figure_manoeuvre(events, scratch)
    figures.figure_mechanism(signals, histogram, scratch)

    failures = 0
    for name, fig in CAPTURED:
        problems = check(fig)
        failures += len(problems)
        print(f"{name:34s} {'OK' if not problems else 'OVERLAP: ' + ', '.join(sorted(set(problems)))}")
    return 1 if failures else 0


CAPTURED = []

if __name__ == "__main__":
    raise SystemExit(main())
