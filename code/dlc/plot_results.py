import argparse
import json
import re
from pathlib import Path


COLORS = {
    "individual_transition": "#777777",
    "joint_transition": "#1f77b4",
    "joint_transition_observer": "#d62728",
}


def numeric_stage_step(stage):
    match = re.match(r"step_(\d+)$", stage)
    if match:
        return int(match.group(1))
    return None


def stage_step(summary, stage):
    if stage == "final":
        train_steps = summary.get("train_steps")
        if train_steps is not None:
            return int(train_steps)
        numeric_steps = [
            step
            for name in summary["aggregate"]
            for step in [numeric_stage_step(name)]
            if step is not None
        ]
        return max(numeric_steps) if numeric_steps else 0
    step = numeric_stage_step(stage)
    if step is not None:
        return step
    return 0


def stage_sort_key(summary, stage):
    return stage_step(summary, stage), 1 if stage == "final" else 0


def split_pairing(pairing):
    left, right = pairing.split("_vs_")
    return left, right


def collect_series(summary, metric):
    stages = sorted(summary["aggregate"].keys(), key=lambda stage: stage_sort_key(summary, stage))
    values_by_method_stage = {}
    for stage in stages:
        for pairing, metrics in summary["aggregate"][stage].items():
            left, right = split_pairing(pairing)
            values = metrics[metric]
            values_by_method_stage.setdefault(left, {}).setdefault(stage, []).append(float(values[0]))
            values_by_method_stage.setdefault(right, {}).setdefault(stage, []).append(float(values[1]))

    series = {}
    for method, stage_values in values_by_method_stage.items():
        points = []
        for stage in stages:
            values = stage_values.get(stage)
            if not values:
                continue
            points.append((stage_step(summary, stage), stage, sum(values) / len(values)))
        series[method] = points
    return stages, series


def nice_bounds(values, default_max=1.0):
    if not values:
        return 0.0, default_max
    lo = min(values)
    hi = max(values)
    if lo == hi:
        pad = max(abs(hi) * 0.1, 1.0)
        return lo - pad, hi + pad
    pad = (hi - lo) * 0.1
    return lo - pad, hi + pad


def render_svg(title, stages, series, y_label, y_min=None, y_max=None):
    width, height = 920, 520
    left, right, top, bottom = 88, 32, 56, 82
    plot_w = width - left - right
    plot_h = height - top - bottom

    xs = sorted({point[0] for points in series.values() for point in points})
    ys = [point[2] for points in series.values() for point in points]
    if y_min is None or y_max is None:
        y_min, y_max = nice_bounds(ys)
    if y_max == y_min:
        y_max = y_min + 1.0
    x_min = min(xs) if xs else 0
    x_max = max(xs) if xs else 1
    if x_min == x_max:
        x_max = x_min + 1

    def sx(x):
        return left + (x - x_min) / (x_max - x_min) * plot_w

    def sy(y):
        return top + (y_max - y) / (y_max - y_min) * plot_h

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left}" y="32" font-family="Arial" font-size="22" font-weight="700">{title}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#222"/>',
        f'<text x="20" y="{top + plot_h / 2}" transform="rotate(-90 20 {top + plot_h / 2})" font-family="Arial" font-size="14">{y_label}</text>',
        f'<text x="{left + plot_w / 2 - 52}" y="{height - 24}" font-family="Arial" font-size="14">Training step</text>',
    ]

    for i in range(6):
        y = y_min + (y_max - y_min) * i / 5
        yy = sy(y)
        lines.append(f'<line x1="{left}" y1="{yy:.2f}" x2="{left + plot_w}" y2="{yy:.2f}" stroke="#e8e8e8"/>')
        lines.append(f'<text x="{left - 12}" y="{yy + 4:.2f}" text-anchor="end" font-family="Arial" font-size="12">{y:.3g}</text>')

    tick_labels = {}
    for x in sorted({point[0] for points in series.values() for point in points}):
        tick_labels[x] = str(x)
    for x, stage in sorted(
        {(point[0], point[1]) for points in series.values() for point in points}
    ):
        if stage == "final":
            tick_labels[x] = "final"

    for x, label in sorted(tick_labels.items()):
        xx = sx(x)
        lines.append(f'<text x="{xx:.2f}" y="{top + plot_h + 22}" text-anchor="middle" font-family="Arial" font-size="12">{label}</text>')

    legend_y = top + 6
    for idx, (name, points) in enumerate(sorted(series.items())):
        color = COLORS.get(name, "#333333")
        points = sorted(points)
        coords = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, _, y in points)
        if coords:
            lines.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for x, _, y in points:
            lines.append(f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="4" fill="{color}"/>')
        lx = left + plot_w - 250
        ly = legend_y + idx * 22
        lines.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 24}" y2="{ly}" stroke="{color}" stroke-width="3"/>')
        lines.append(f'<text x="{lx + 32}" y="{ly + 4}" font-family="Arial" font-size="13">{name}</text>')

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Plot DLC telemetry aggregate result curves as SVG files."
    )
    parser.add_argument("summary_json")
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    summary_path = Path(args.summary_json)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir) if args.out_dir else summary_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    stages, win_series = collect_series(summary, "win_ratio_mean")
    _, score_series = collect_series(summary, "mean_score_mean")
    (out_dir / "win_ratio.svg").write_text(
        render_svg("Round-robin Win Ratio", stages, win_series, "Win ratio", y_min=0.0, y_max=1.0),
        encoding="utf-8",
    )
    (out_dir / "mean_score.svg").write_text(
        render_svg("Round-robin Mean Score", stages, score_series, "Mean score"),
        encoding="utf-8",
    )
    print(json.dumps({
        "win_ratio_svg": str(out_dir / "win_ratio.svg"),
        "mean_score_svg": str(out_dir / "mean_score.svg"),
    }, indent=2))


if __name__ == "__main__":
    main()
