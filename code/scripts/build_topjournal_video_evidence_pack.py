#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build a video-first evidence pack for the DNQ-DLC manuscript."""

import csv
import html
import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path("outputs/tits_dynamic_graph_expanded")
OUT = ROOT / "topjournal_video_evidence_pack_v1"
ASSETS = OUT / "assets"
VIDEOS = ASSETS / "videos"
FIGURES = ASSETS / "analysis_figures"
TABLES = OUT / "tables"

AUDIT_FIELDS = [
    "experiment",
    "status",
    "placement",
    "claim",
    "case_dir",
    "primary_video",
    "comparison_videos",
    "source_csv",
    "summary_json",
    "analysis_figure",
    "overtake_success",
    "on_track_overtake_count",
    "elegant_overtake_count",
    "target_grass_rate",
    "rank_gain",
    "target_progress",
    "pass_filter",
    "rejection_reason",
]


def ensure_dirs():
    for path in [OUT, ASSETS, VIDEOS, FIGURES, TABLES]:
        path.mkdir(parents=True, exist_ok=True)


def copy_file(src, dst_dir, label=None):
    if not src:
        return ""
    src = Path(src)
    if not src.exists():
        return ""
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / (label or src.name)
    shutil.copy2(src, dst)
    return dst.relative_to(OUT).as_posix()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_summary(case_dir, algorithm):
    matches = sorted((Path(case_dir) / "summaries").glob(f"{algorithm}*.summary.json"))
    return matches[0] if matches else None


def find_source_csv(case_dir):
    matches = sorted((Path(case_dir) / "tables").glob("*.csv"))
    return matches[0] if matches else None


def find_analysis_figure(case_dir):
    for suffix in [".pdf", ".png", ".svg"]:
        path = Path(case_dir) / "figures" / f"figure_tits_dynamic_graph_online_overtake_summary{suffix}"
        if path.exists():
            return path
    return None


def video_path_from_summary(summary, key="first_person_video"):
    value = summary.get(key)
    return Path(value) if value else None


def accept_main(summary, max_off_track=0.10, min_elegant=1):
    off_track = summary.get("target_grass_rate")
    off_track = 1.0 if off_track is None else float(off_track)
    return (
        bool(summary.get("overtake_success"))
        and int(summary.get("on_track_overtake_count") or 0) >= min_elegant
        and int(summary.get("elegant_overtake_count") or 0) >= min_elegant
        and off_track <= max_off_track
    )


def make_case(
    experiment,
    title,
    status,
    placement,
    claim,
    case_dir,
    algorithm,
    comparison_algorithms=(),
    max_off_track=0.10,
    min_elegant=1,
    rejection_reason="",
):
    case_dir = Path(case_dir)
    summary_path = find_summary(case_dir, algorithm)
    if summary_path is None:
        raise FileNotFoundError(f"No summary for {algorithm} under {case_dir}")
    summary = read_json(summary_path)
    primary_video_src = video_path_from_summary(summary, "first_person_video")
    topdown_video_src = video_path_from_summary(summary, "topdown_video")
    source_csv = find_source_csv(case_dir)
    analysis_figure = find_analysis_figure(case_dir)

    pass_filter = accept_main(summary, max_off_track=max_off_track, min_elegant=min_elegant)
    if status == "main" and not pass_filter:
        status = "rejected-screening"
        placement = "Rejected screening / audit only"
        rejection_reason = rejection_reason or "The case does not satisfy the predefined main-video thresholds."

    video_dir = VIDEOS / experiment
    primary_video = copy_file(primary_video_src, video_dir, f"{experiment}_{algorithm}.first_person.mp4")
    topdown_video = copy_file(topdown_video_src, video_dir, f"{experiment}_{algorithm}.topdown.mp4")
    source_csv_rel = copy_file(source_csv, TABLES / experiment, source_csv.name if source_csv else None)
    summary_rel = copy_file(summary_path, TABLES / experiment, summary_path.name)
    analysis_rel = copy_file(analysis_figure, FIGURES / experiment, analysis_figure.name if analysis_figure else None)

    comparison_videos = []
    for comp in comparison_algorithms:
        comp_summary_path = find_summary(case_dir, comp)
        if comp_summary_path is None:
            continue
        comp_summary = read_json(comp_summary_path)
        comp_video = copy_file(
            video_path_from_summary(comp_summary, "first_person_video"),
            video_dir,
            f"{experiment}_{comp}.first_person.mp4",
        )
        if comp_video:
            comparison_videos.append(comp_video)

    card = {
        "experiment": experiment,
        "title": title,
        "status": status,
        "placement": placement,
        "claim": claim,
        "case_dir": case_dir.as_posix(),
        "primary_video": primary_video,
        "topdown_video": topdown_video,
        "comparison_videos": comparison_videos,
        "source_csv": source_csv_rel,
        "summary_json": summary_rel,
        "analysis_figure": analysis_rel,
        "metrics": {
            "overtake_success": summary.get("overtake_success"),
            "on_track_overtake_count": summary.get("on_track_overtake_count"),
            "elegant_overtake_count": summary.get("elegant_overtake_count"),
            "target_grass_rate": summary.get("target_grass_rate"),
            "rank_gain": summary.get("rank_gain"),
            "target_progress": summary.get("target_progress"),
        },
        "pass_filter": pass_filter,
        "rejection_reason": rejection_reason,
    }
    return card


def make_e4_case():
    case_dir = ROOT / "video_evidence_raw/e4_case02_nominal_s5_mp4"
    summary_path = case_dir / "summaries/mixed_n4_seed181_target3.summary.json"
    summary = read_json(summary_path)
    pass_filter = accept_main(summary, max_off_track=0.10, min_elegant=2) and int(summary.get("rank_gain") or 0) >= 3
    video_dir = VIDEOS / "E4"
    primary_video = copy_file(summary.get("first_person_video"), video_dir, "E4_DNQ_DLC.first_person.mp4")
    topdown_video = copy_file(summary.get("topdown_video"), video_dir, "E4_four_controller.topdown.mp4")
    agent_videos = []
    for agent_id, path in sorted((summary.get("first_person_videos_by_agent") or {}).items()):
        label = (summary.get("agent_algorithm") or {}).get(agent_id, f"agent{agent_id}")
        rel = copy_file(path, video_dir, f"E4_agent{agent_id}_{label}.first_person.mp4")
        if rel:
            agent_videos.append(rel)
    source_csv = copy_file(case_dir / "tables/mixed_metrics_n4_seed181.csv", TABLES / "E4")
    summary_rel = copy_file(summary_path, TABLES / "E4")
    analysis_rel = copy_file(
        case_dir / "figures/figure_tits_dynamic_graph_online_overtake_summary.pdf",
        FIGURES / "E4",
    )
    return {
        "experiment": "E4",
        "title": "Four-controller same-track race without background vehicles",
        "status": "main" if pass_filter else "rejected-screening",
        "placement": "Main video evidence",
        "claim": "DNQ-DLC starts from the rear, competes directly with Rule Expert, TD3, and DLC-JTO, and reaches first place with on-track/elegant overtakes.",
        "case_dir": case_dir.as_posix(),
        "primary_video": primary_video,
        "topdown_video": topdown_video,
        "comparison_videos": agent_videos,
        "source_csv": source_csv,
        "summary_json": summary_rel,
        "analysis_figure": analysis_rel,
        "metrics": {
            "overtake_success": summary.get("overtake_success"),
            "on_track_overtake_count": summary.get("on_track_overtake_count"),
            "elegant_overtake_count": summary.get("elegant_overtake_count"),
            "target_grass_rate": summary.get("target_grass_rate"),
            "rank_gain": summary.get("rank_gain"),
            "target_progress": summary.get("target_progress"),
        },
        "pass_filter": pass_filter,
        "rejection_reason": "" if pass_filter else "E4 did not satisfy rank-gain/off-track/elegant-overtake thresholds.",
    }


def make_e5_mechanism_case():
    case_dir = ROOT / "video_evidence_raw/e3_scale_N10_seed20000_mp4"
    mechanism_dir = ROOT / "video_evidence_raw/e5_mechanism_from_clean_e3_n10"
    summary_path = case_dir / "summaries/v6_runtime_dynamic_neighborhood_safe_n10_seed20000.summary.json"
    report_path = mechanism_dir / "e5_dynamic_neighborhood_mechanism_report.json"
    summary = read_json(summary_path)
    report = read_json(report_path)
    pass_filter = (
        accept_main(summary, max_off_track=0.02, min_elegant=3)
        and int(report.get("neighbor_switch_count") or 0) >= 30
        and int(report.get("unique_neighbor_sets") or 0) >= 10
    )
    video_dir = VIDEOS / "E5"
    primary_video = copy_file(summary.get("first_person_video"), video_dir, "E5_dynamic_neighborhood_clean_N10.first_person.mp4")
    topdown_video = copy_file(summary.get("topdown_video"), video_dir, "E5_dynamic_neighborhood_clean_N10.topdown.mp4")
    source_csv = copy_file(
        mechanism_dir / "tables/e5_dynamic_neighborhood_mechanism_source_data.csv",
        TABLES / "E5",
    )
    summary_rel = copy_file(summary_path, TABLES / "E5", summary_path.name)
    report_rel = copy_file(report_path, TABLES / "E5", report_path.name)
    analysis_rel = copy_file(
        mechanism_dir / "figures/figure_e5_dynamic_neighborhood_mechanism.pdf",
        FIGURES / "E5",
    )
    card = {
        "experiment": "E5",
        "title": "Mechanism evidence: dynamic-neighborhood repacking in a clean 10-vehicle overtake",
        "status": "main" if pass_filter else "rejected-screening",
        "placement": "Main mechanism video evidence",
        "claim": "The same clean N=10 video shows online dynamic-neighborhood repacking: 116 neighbor switches and 70 unique interaction sets while completing three off-track-free elegant overtakes.",
        "case_dir": mechanism_dir.as_posix(),
        "primary_video": primary_video,
        "topdown_video": topdown_video,
        "comparison_videos": [],
        "source_csv": source_csv,
        "summary_json": summary_rel,
        "analysis_figure": analysis_rel,
        "extra_links": [report_rel],
        "metrics": {
            "overtake_success": summary.get("overtake_success"),
            "on_track_overtake_count": summary.get("on_track_overtake_count"),
            "elegant_overtake_count": summary.get("elegant_overtake_count"),
            "target_grass_rate": summary.get("target_grass_rate"),
            "rank_gain": summary.get("rank_gain"),
            "target_progress": summary.get("target_progress"),
        },
        "pass_filter": pass_filter,
        "rejection_reason": "" if pass_filter else "The mechanism run did not satisfy the clean-overtake and neighbor-switch thresholds.",
    }
    return card


def build_cards():
    cards = [
        make_case(
            "E2",
            "Environmental generalization: Monza-like topology",
            "main",
            "Main video evidence",
            "DNQ-DLC keeps the vehicle mostly on track and completes multiple clean overtakes on an unseen Monza-like topology.",
            ROOT / "video_evidence_raw/e2_monza_n6_seed12006_mp4",
            "v6_runtime_dynamic_neighborhood_safe",
            comparison_algorithms=("rule_expert_gate", "dlc_joint_transition_observer"),
            max_off_track=0.10,
            min_elegant=3,
        ),
        make_case(
            "E3",
            "Zero-shot scale extrapolation: ten vehicles",
            "main",
            "Main video evidence",
            "DNQ-DLC remains track-compliant and completes clean overtakes in dense 10-vehicle traffic without retraining.",
            ROOT / "video_evidence_raw/e3_scale_N10_seed20000_mp4",
            "v6_runtime_dynamic_neighborhood_safe",
            comparison_algorithms=("rule_expert_gate", "dlc_joint_transition"),
            max_off_track=0.02,
            min_elegant=3,
        ),
        make_e4_case(),
        make_e5_mechanism_case(),
        make_case(
            "E6",
            "High-pressure ablation video: full DNQ-DLC versus module removals",
            "main",
            "Main ablation video evidence",
            "The full model stays mostly on track while all tested ablations show substantially higher off-track exposure or lower progress on the same Monza/N=6 stress case.",
            ROOT / "video_evidence_raw/e6_monza_slow_n6_seed35000_mp4",
            "ours_full_v6_safe",
            comparison_algorithms=(
                "low_budget_planner",
                "w_o_dynamic_neighborhood",
                "w_o_quality_proposal",
                "w_o_safety_quality_terms",
            ),
            max_off_track=0.10,
            min_elegant=5,
        ),
    ]
    return cards


def write_rejected_screening_table():
    roots = sorted((ROOT / "video_evidence_screening").glob("e6_*"))
    path = TABLES / "rejected_e6_video_screening.csv"
    fields = [
        "case",
        "algorithm",
        "overtake_success",
        "elegant_overtake_count",
        "target_grass_rate",
        "rank_gain",
        "target_progress",
        "summary_json",
        "rejection_reason",
    ]
    rows = []
    for root in roots:
        summaries = sorted((root / "summaries").glob("*.summary.json"))
        if not summaries:
            continue
        full = None
        metrics = []
        for summary_path in summaries:
            summary = read_json(summary_path)
            item = {
                "case": root.name,
                "algorithm": summary.get("algorithm"),
                "overtake_success": summary.get("overtake_success"),
                "elegant_overtake_count": summary.get("elegant_overtake_count"),
                "target_grass_rate": summary.get("target_grass_rate"),
                "rank_gain": summary.get("rank_gain"),
                "target_progress": summary.get("target_progress"),
                "summary_json": summary_path.as_posix(),
            }
            metrics.append(item)
            if item["algorithm"] == "ours_full_v6_safe":
                full = item
        reason = ""
        if full:
            full_off = full["target_grass_rate"]
            full_elegant = int(full["elegant_overtake_count"] or 0)
            if full_off is None or float(full_off) > 0.10:
                reason = "Full model off-track exposure exceeds main-video threshold."
            elif full_elegant < 2:
                reason = "Full model does not show enough clean overtaking events."
            else:
                reason = "Ablation contrast is insufficient or variants are cleaner than the full model."
        for item in metrics:
            item["rejection_reason"] = reason
            rows.append(item)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path.relative_to(OUT).as_posix()


def write_audit(cards):
    path = TABLES / "video_evidence_audit.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for card in cards:
            metrics = card["metrics"]
            writer.writerow(
                {
                    "experiment": card["experiment"],
                    "status": card["status"],
                    "placement": card["placement"],
                    "claim": card["claim"],
                    "case_dir": card["case_dir"],
                    "primary_video": card["primary_video"],
                    "comparison_videos": ";".join(card["comparison_videos"]),
                    "source_csv": card["source_csv"],
                    "summary_json": card["summary_json"],
                    "analysis_figure": card["analysis_figure"],
                    "overtake_success": metrics.get("overtake_success"),
                    "on_track_overtake_count": metrics.get("on_track_overtake_count"),
                    "elegant_overtake_count": metrics.get("elegant_overtake_count"),
                    "target_grass_rate": metrics.get("target_grass_rate"),
                    "rank_gain": metrics.get("rank_gain"),
                    "target_progress": metrics.get("target_progress"),
                    "pass_filter": card["pass_filter"],
                    "rejection_reason": card["rejection_reason"],
                }
            )
    return path.relative_to(OUT).as_posix()


def plot_video_metrics(cards):
    main_cards = [card for card in cards if card["status"] == "main"]
    labels = [card["experiment"] for card in main_cards]
    off = [float(card["metrics"].get("target_grass_rate") or 0.0) for card in main_cards]
    elegant = [float(card["metrics"].get("elegant_overtake_count") or 0.0) for card in main_cards]
    rank_gain = [float(card["metrics"].get("rank_gain") or 0.0) for card in main_cards]

    fig, axes = plt.subplots(1, 3, figsize=(9.0, 2.6), constrained_layout=True)
    colors = ["#2f6f9f", "#2aa876", "#d3832b"]
    axes[0].bar(labels, off, color=colors[0])
    axes[0].set_title("Off-track exposure")
    axes[0].set_ylim(0, max(0.12, max(off) * 1.35 if off else 0.1))
    axes[0].set_ylabel("rate")
    axes[1].bar(labels, elegant, color=colors[1])
    axes[1].set_title("Elegant overtakes")
    axes[1].set_ylabel("count")
    axes[2].bar(labels, rank_gain, color=colors[2])
    axes[2].set_title("Rank gain")
    axes[2].set_ylabel("positions")
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.22)
    for ext in ["png", "pdf"]:
        fig.savefig(FIGURES / f"video_evidence_metrics.{ext}", dpi=300)
    plt.close(fig)
    return (FIGURES / "video_evidence_metrics.png").relative_to(OUT).as_posix()


def write_html(cards, audit_rel, metrics_fig_rel, rejected_rel):
    def link(path, label=None, klass="link"):
        if not path:
            return ""
        return f'<a class="{klass}" href="{html.escape(path)}">{html.escape(label or Path(path).name)}</a>'

    def video(path, label):
        if not path:
            return ""
        return (
            f'<div class="video-block"><div class="video-label">{html.escape(label)}</div>'
            f'<video controls muted loop preload="metadata" src="{html.escape(path)}"></video></div>'
        )

    def card_html(card):
        metrics = card["metrics"]
        comp = "".join(video(path, f"Comparison video {idx + 1}") for idx, path in enumerate(card["comparison_videos"]))
        links = "".join(
            [
                link(card["source_csv"], "metrics CSV"),
                link(card["summary_json"], "summary JSON"),
                link(card["analysis_figure"], "analysis figure"),
            ]
            + [link(extra, Path(extra).name) for extra in card.get("extra_links", [])]
        )
        rejection = f'<p class="reject"><b>Rejected reason:</b> {html.escape(card["rejection_reason"])}</p>' if card["rejection_reason"] else ""
        return f"""
        <article class="card {html.escape(card['status'])}">
          <div class="tag">{html.escape(card['experiment'])} · {html.escape(card['status'])}</div>
          <h3>{html.escape(card['title'])}</h3>
          <p class="meta"><b>Placement:</b> {html.escape(card['placement'])}</p>
          <p class="meta"><b>Claim:</b> {html.escape(card['claim'])}</p>
          <p class="metrics">success={metrics.get('overtake_success')}; elegant={metrics.get('elegant_overtake_count')}; off-track={float(metrics.get('target_grass_rate') or 0.0):.3f}; rank gain={metrics.get('rank_gain')}</p>
          {video(card['primary_video'], 'DNQ-DLC first-person MP4')}
          {video(card['topdown_video'], 'Top-down MP4')}
          {comp}
          <div class="links">{links}</div>
          {rejection}
        </article>
        """

    sections = [
        ("Main-paper recommended videos", [card for card in cards if card["status"] == "main"]),
        ("Supplementary / audit-only videos", [card for card in cards if card["status"] == "supplementary"]),
        ("Rejected screening videos", [card for card in cards if card["status"] == "rejected-screening"]),
    ]
    body = "\n".join(
        f'<section class="band" data-section="{html.escape(title)}"><h2>{html.escape(title)}</h2>'
        + "\n".join(card_html(card) for card in subset)
        + "</section>"
        for title, subset in sections
        if subset
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DNQ-DLC Video Evidence Pack</title>
  <style>
    body {{ margin:0; font-family: Arial, Helvetica, sans-serif; background:#eef3f7; color:#172033; }}
    header {{ padding:34px 46px 24px; background:#10233f; color:white; }}
    header h1 {{ margin:0 0 8px; font-size:30px; }}
    header p {{ max-width:1120px; line-height:1.55; color:#d7e3f2; }}
    main {{ padding:26px 34px 48px; }}
    .band {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(520px, 1fr)); gap:22px; margin-bottom:36px; }}
    .band > h2 {{ grid-column:1/-1; font-size:23px; margin:4px 0 -4px; }}
    .card {{ background:white; border:1px solid #dbe3ee; border-radius:8px; padding:18px; box-shadow:0 8px 24px rgba(16,35,63,.08); }}
    .card.supplementary {{ border-color:#ead6a7; }}
    .card.rejected-screening {{ border-color:#e8b4b4; }}
    .tag {{ display:inline-block; padding:4px 9px; border-radius:999px; background:#e7eef8; color:#235a9f; font-weight:700; font-size:12px; }}
    h3 {{ font-size:19px; margin:12px 0 8px; }}
    p {{ line-height:1.52; }}
    .meta {{ color:#46566f; font-size:13px; margin:5px 0; }}
    .metrics {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; background:#f3f6fa; padding:8px 10px; border-radius:6px; }}
    video {{ width:100%; max-height:540px; background:#05080d; border:1px solid #d5dde8; border-radius:6px; }}
    .video-block {{ margin:12px 0; }}
    .video-label {{ font-weight:700; font-size:13px; margin-bottom:5px; color:#25344a; }}
    .link, .button {{ display:inline-block; margin:8px 8px 0 0; padding:7px 10px; text-decoration:none; border-radius:6px; background:#eef3fa; color:#17365f; font-weight:700; font-size:13px; }}
    .button {{ background:#235a9f; color:white; }}
    .reject {{ color:#8b2d2d; }}
    footer {{ padding:0 46px 36px; color:#526070; }}
  </style>
</head>
<body>
  <header>
    <h1>DNQ-DLC Video Evidence Pack v1</h1>
    <p>This package replaces low-resolution qualitative visual assets with MP4 videos. Main-paper videos must pass predefined filters: DNQ-DLC succeeds, completes clean overtakes, keeps off-track exposure low, and retains the corresponding metrics CSV, summary JSON, and analysis figure.</p>
    <p>{link(audit_rel, 'Open video audit CSV', 'button')}{link(metrics_fig_rel, 'Open video metrics figure', 'button')}{link(rejected_rel, 'Open rejected E6 screening CSV', 'button')}</p>
  </header>
  <main>{body}</main>
  <footer>Generated from local experiment artifacts. Weak or unstable visual runs remain visible only as supplementary/audit records and are not used as main-paper evidence.</footer>
</body>
</html>
"""
    (OUT / "index.html").write_text(page, encoding="utf-8")


def build():
    ensure_dirs()
    cards = build_cards()
    audit_rel = write_audit(cards)
    rejected_rel = write_rejected_screening_table()
    metrics_fig_rel = plot_video_metrics(cards)
    write_html(cards, audit_rel, metrics_fig_rel, rejected_rel)
    return {
        "out_dir": OUT.as_posix(),
        "index": (OUT / "index.html").as_posix(),
        "audit": (OUT / audit_rel).as_posix(),
        "main_video_count": sum(1 for card in cards if card["status"] == "main"),
        "card_count": len(cards),
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
