#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the v2 top-journal evidence pack, audit tables and static website."""

import csv
import html
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageSequence


ROOT = Path("outputs/tits_dynamic_graph_expanded")
OUT = ROOT / "topjournal_evidence_pack_v2"
ASSETS = OUT / "assets"
FIGS = ASSETS / "figures"
MEDIA = ASSETS / "media"
TABLES = OUT / "tables"


AUDIT_FIELDS = [
    "experiment",
    "asset_type",
    "status",
    "placement",
    "claim",
    "source_data",
    "path",
    "rejection_reason",
    "note",
]


def ensure_dirs():
    for path in [OUT, ASSETS, FIGS, MEDIA, TABLES]:
        path.mkdir(parents=True, exist_ok=True)


def copy_file(src, dst_dir, label=None):
    src = Path(src)
    if not src.exists():
        return ""
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / (label or src.name)
    shutil.copy2(src, dst)
    return dst.relative_to(OUT).as_posix()


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path.relative_to(OUT).as_posix()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_frames(path):
    with Image.open(path) as image:
        return [frame.convert("RGB") for frame in ImageSequence.Iterator(image)]


def get_font(size=22, bold=False):
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def label_corner(image, title, subtitle):
    image = image.copy()
    draw = ImageDraw.Draw(image)
    f1 = get_font(24, bold=True)
    f2 = get_font(17)
    w = max(draw.textbbox((0, 0), title, font=f1)[2], draw.textbbox((0, 0), subtitle, font=f2)[2]) + 28
    h = 62
    draw.rounded_rectangle((14, 14, 14 + w, 14 + h), radius=8, fill=(8, 20, 36), outline=(255, 255, 255), width=1)
    draw.text((28, 21), title, fill=(255, 255, 255), font=f1)
    draw.text((28, 49), subtitle, fill=(208, 222, 238), font=f2)
    return image


def contact_sheet_from_gif(gif_path, out_path):
    gif_path = Path(gif_path)
    if not gif_path.exists():
        return ""
    frames = load_frames(gif_path)
    if not frames:
        return ""
    total = len(frames)
    labels = [("Start", "first frame"), ("Interaction", "mid rollout"), ("Pass", "late rollout"), ("End", "final frame")]
    indices = [0, int(total * 0.33), int(total * 0.66), total - 1]
    thumbs = []
    for idx, (title, subtitle) in zip(indices, labels):
        im = frames[min(max(idx, 0), total - 1)]
        scale = 620 / im.width
        im = im.resize((620, int(im.height * scale)), Image.Resampling.LANCZOS)
        thumbs.append(label_corner(im, title, subtitle))
    cell_h = max(t.height for t in thumbs)
    canvas = Image.new("RGB", (1240, cell_h * 2), (245, 247, 250))
    for i, im in enumerate(thumbs):
        canvas.paste(im, ((i % 2) * 620, (i // 2) * cell_h))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, quality=95)
    return out_path.relative_to(OUT).as_posix()


def visual_metrics(case_dir):
    rows = []
    for path in sorted((Path(case_dir) / "summaries").glob("*.summary.json")):
        data = read_json(path)
        rows.append(
            {
                "algorithm": data.get("algorithm", ""),
                "success": data.get("overtake_success_rate", ""),
                "off_track": data.get("target_grass_rate", ""),
                "elegant_count": data.get("elegant_overtake_count", ""),
                "progress": data.get("target_progress", ""),
                "p95_latency_ms": data.get("compute_latency_p95_ms", ""),
                "summary": path.as_posix(),
            }
        )
    return rows


def audit_row(experiment, asset_type, status, placement, claim, source_data, path, note, rejection_reason=""):
    return {
        "experiment": experiment,
        "asset_type": asset_type,
        "status": status,
        "placement": placement,
        "claim": claim,
        "source_data": source_data,
        "path": path,
        "rejection_reason": rejection_reason,
        "note": note,
    }


def build_cards_and_audit():
    cards = []
    audit = []

    figure_specs = [
        ("E1", "Main 200-episode benchmark", ROOT / "e1_200_summary/figures/figure_e1_nature_direct_benchmark.png", ROOT / "e1_200_summary/tables/online_benchmark_nature_direct_source_data.csv", "Main text Fig. 1", "DNQ-DLC improves success and completion time against the strongest rule/RL/DLC baselines.", "Use as the quantitative anchor."),
        ("E2", "Environmental generalization", ROOT / "geometry_generalization_six_experiments/six_experiment_paper_results/figures/figure_e2_environment_generalization.png", ROOT / "geometry_generalization_six_experiments/six_experiment_paper_results/tables/six_experiment_metric_summary.csv", "Main text Fig. 2 / Table 1", "DNQ-DLC remains effective across Oval, S-Curve, Hairpin and Monza-like topologies.", "Use with Monza visual case; Hairpin visuals remain supplementary because the rule expert is cleaner in screened cases."),
        ("E3", "Zero-shot scale extrapolation", ROOT / "geometry_generalization_six_experiments/six_experiment_paper_results/figures/figure_e3_scale_extension.png", ROOT / "geometry_generalization_six_experiments/six_experiment_paper_results/tables/six_experiment_metric_summary.csv", "Main text Fig. 3 / Table 2", "Dynamic-neighborhood repacking keeps runtime scaling stable from 4 to 12 vehicles.", "Use for scale/latency evidence."),
        ("E4", "Four-controller same-track race", ROOT / "e4_four_controller_race_no_background/data_analysis_figure/figures/figure_e4_four_controller_same_track_race_analysis.png", ROOT / "e4_four_controller_race_no_background/data_analysis_figure/tables/e4_four_controller_agent_metrics.csv", "Main text Fig. 4", "DNQ-DLC gains rank in a pure four-controller same-track race without background traffic.", "Use as direct same-race evidence."),
        ("E6", "High-pressure ablation", ROOT / "geometry_generalization_six_experiments/six_experiment_paper_results/figures/figure_e6_ablation.png", ROOT / "geometry_generalization_six_experiments/six_experiment_paper_results/tables/six_experiment_metric_summary.csv", "Main text Fig. 6", "Multi-seed aggregate ablation shows high-pressure module effects.", "Use aggregate figure only; unstable E6 visual cases are supplementary."),
    ]
    for exp, title, fig, source, placement, claim, note in figure_specs:
        fig_rel = copy_file(fig, FIGS / exp, fig.name)
        source_rel = copy_file(source, TABLES, source.name)
        cards.append({"id": exp, "title": title, "status": "main", "placement": placement, "claim": claim, "note": note, "figure": fig_rel, "links": [source_rel]})
        audit.append(audit_row(exp, "figure", "main" if fig_rel else "missing", placement, claim, source.as_posix(), fig.as_posix(), note))

    visual_specs = [
        ("E2-Monza", "E2 Monza visual", ROOT / "publication_visual_asset_pack_raw/E2_monza_n6_seed12006", "v6_runtime_dynamic_neighborhood_safe_n6_seed12006.first_person.gif", "main", "Main text visual / supplementary video", "Track-topology generalization on external Monza-like geometry.", "DNQ-DLC succeeds with low off-track exposure while DLC-JTO fails.", ""),
        ("E3-N10", "E3 ten-vehicle visual", ROOT / "publication_visual_asset_pack_raw/E3_scale_N10_seed20000", "v6_runtime_dynamic_neighborhood_safe_n10_seed20000.first_person.gif", "main", "Main text visual / supplementary video", "Dense 10-car zero-shot operation with stable track adherence.", "DNQ-DLC succeeds with zero off-track exposure in dense 10-car traffic.", ""),
        ("E6-Hairpin", "E6 ablation visual", ROOT / "publication_visual_asset_pack_raw/E6_hairpin_n8_seed30018", "ours_full_v6_safe_n8_seed30018.first_person.gif", "supplementary", "Supplementary visual only", "Stress-case illustration, not main evidence.", "Useful for showing ablation pressure.", "Full-model off-track exposure is non-trivial; use aggregate data, not this visual, for the main E6 claim."),
    ]
    for exp, title, case_dir, gif_name, status, placement, claim, note, rejection in visual_specs:
        media_dir = MEDIA / exp
        gif_rel = copy_file(case_dir / "gifs" / gif_name, media_dir, gif_name)
        sheet_rel = contact_sheet_from_gif(case_dir / "gifs" / gif_name, media_dir / f"{exp}_keyframes.png")
        metrics = visual_metrics(case_dir)
        metrics_rel = write_csv(TABLES / f"{exp}_metrics.csv", metrics, ["algorithm", "success", "off_track", "elegant_count", "progress", "p95_latency_ms", "summary"]) if metrics else ""
        cards.append({"id": exp, "title": title, "status": status, "placement": placement, "claim": claim, "note": note, "figure": sheet_rel, "gif": gif_rel, "links": [metrics_rel]})
        audit.append(audit_row(exp, "visual", status, placement, claim, metrics_rel, case_dir.as_posix(), note, rejection))

    e4_index = ROOT / "e4_four_controller_race_no_background/visual_pack_no_background_four_algorithms/tables/e4_four_controller_race_no_background_asset_index.csv"
    e4_sheet = ROOT / "e4_four_controller_race_no_background/visual_pack_no_background_four_algorithms/contact_sheets_clean/case02_nominal_s5_topdown_keyframes_clean.png"
    e4_sheet_rel = copy_file(e4_sheet, MEDIA / "E4", e4_sheet.name)
    e4_index_rel = copy_file(e4_index, TABLES, e4_index.name)
    cards.append({"id": "E4-visual", "title": "E4 four-controller same-track visual", "status": "main", "placement": "Main text visual / supplementary video", "claim": "Direct no-background same-track competition against Rule Expert, TD3 and DLC-JTO.", "note": "Nominal case: DNQ-DLC moves from fourth to first with two on-track/elegant overtakes.", "figure": e4_sheet_rel, "links": [e4_index_rel]})
    audit.append(audit_row("E4-visual", "visual", "main", "Main text visual / supplementary video", "Direct no-background four-controller competition.", e4_index.as_posix(), e4_sheet.as_posix(), "Use nominal same-track case."))

    e5_root = ROOT / "geometry_generalization_six_experiments"
    e5_dir = e5_root / "e5_keyframes/contact_sheets"
    e5_verified = copy_file(
        e5_root / "e5_keyframes/e5_mechanism_case_selection_verified.csv",
        TABLES,
        "e5_mechanism_case_selection_verified.csv",
    )
    e5_keyframe_index = copy_file(
        e5_root / "e5_keyframes/e5_visual_keyframe_index.csv",
        TABLES,
        "e5_visual_keyframe_index.csv",
    )
    for sheet in sorted(e5_dir.glob("*_first_person_sheet.png")):
        case_name = sheet.stem.replace("_first_person_sheet", "")
        case_dir = e5_root / "e5_visual_cases" / case_name
        case_metrics = next((case_dir / "tables").glob("*.csv"), None) if (case_dir / "tables").exists() else None
        case_summary = next((case_dir / "summaries").glob("*.summary.json"), None) if (case_dir / "summaries").exists() else None
        case_metrics_rel = copy_file(case_metrics, TABLES / "E5", f"{case_name}_{case_metrics.name}") if case_metrics else ""
        case_summary_rel = copy_file(case_summary, TABLES / "E5", f"{case_name}_{case_summary.name}") if case_summary else ""
        source_links = [link for link in [e5_verified, e5_keyframe_index, case_metrics_rel, case_summary_rel] if link]
        status = "main" if "dynamic_neighborhood" in sheet.name or "safety_intervention" in sheet.name else "supplementary"
        placement = "Main text mechanism visual" if status == "main" else "Supplementary mechanism visual"
        claim = "Dynamic-neighborhood switching or safety intervention is visible in first-person evidence." if status == "main" else "Additional qualitative mechanism or failure-boundary example."
        rel = copy_file(sheet, MEDIA / "E5", sheet.name)
        cards.append({"id": "E5", "title": f"E5 mechanism: {sheet.stem}", "status": status, "placement": placement, "claim": claim, "note": "Mechanism-level first-person evidence.", "figure": rel, "links": source_links})
        rejection = "" if status == "main" else "Supplementary qualitative example, not needed for the main mechanism claim."
        audit.append(audit_row("E5", "visual", status, placement, claim, ";".join(source_links), sheet.as_posix(), sheet.stem, rejection))

    rescue_rows = []
    for case_dir in sorted((ROOT / "topjournal_rescue_screening").glob("*")):
        if not (case_dir / "summaries").exists():
            continue
        for row in visual_metrics(case_dir):
            row["case"] = case_dir.name
            rescue_rows.append(row)
    if rescue_rows:
        rescue_rel = write_csv(TABLES / "rescue_screening_metrics.csv", rescue_rows, ["case", "algorithm", "success", "off_track", "elegant_count", "progress", "p95_latency_ms", "summary"])
        audit.append(audit_row("rescue-screening", "audit", "rejected-screening", "Supplementary audit only", "Documents rerun attempts and why some cases were not selected for main figures.", rescue_rel, rescue_rel, "Rejected screening cases retained for auditability.", "Screened E2 Hairpin/E6 cases do not improve the main evidence chain under the predefined criteria."))

    return cards, audit


def write_html(cards, audit_rel):
    def card_html(card):
        media = ""
        if card.get("figure"):
            media += f'<a href="{html.escape(card["figure"])}"><img src="{html.escape(card["figure"])}" alt="{html.escape(card["title"])}"></a>'
        if card.get("gif"):
            media += f'<p><a class="button" href="{html.escape(card["gif"])}">Open GIF</a></p>'
        links = "".join(f'<a class="link" href="{html.escape(link)}">{html.escape(Path(link).name)}</a>' for link in card.get("links", []) if link)
        return f"""
        <article class="card {html.escape(card.get('status', ''))}">
          <div class="tag">{html.escape(card["id"])} · {html.escape(card.get("status", ""))}</div>
          <h3>{html.escape(card["title"])}</h3>
          <p class="meta"><b>Placement:</b> {html.escape(card.get("placement", ""))}</p>
          <p class="meta"><b>Claim:</b> {html.escape(card.get("claim", ""))}</p>
          <p>{html.escape(card.get("note", ""))}</p>
          {media}
          <div class="links">{links}</div>
        </article>
        """

    sections = [
        ("Main-paper recommended", [c for c in cards if c.get("status") == "main"]),
        ("Supplementary only", [c for c in cards if c.get("status") == "supplementary"]),
        ("Rejected screening / audit trail", [c for c in cards if c.get("status") not in {"main", "supplementary"}]),
    ]
    body = "\n".join(
        f'<section class="band evidence-section" data-section="{html.escape(title)}"><h2>{html.escape(title)}</h2>' + "\n".join(card_html(c) for c in subset) + "</section>"
        for title, subset in sections
        if subset
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DNQ-DLC Top-Journal Evidence Pack v2</title>
  <style>
    body {{ margin:0; font-family: Arial, Helvetica, sans-serif; color:#172033; background:#f4f7fb; }}
    header {{ padding:34px 46px 24px; background:#10233f; color:white; }}
    header h1 {{ margin:0 0 8px; font-size:30px; letter-spacing:0; }}
    header p {{ max-width:1080px; line-height:1.55; color:#d7e3f2; }}
    main {{ padding:26px 34px 48px; }}
    .filters {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:18px; }}
    .filter {{ border:1px solid rgba(255,255,255,.35); background:rgba(255,255,255,.10); color:white; border-radius:6px; padding:7px 11px; cursor:pointer; font-weight:700; }}
    .filter.active {{ background:white; color:#10233f; }}
    .band {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap:22px; margin-bottom:36px; }}
    .band > h2 {{ grid-column:1/-1; font-size:23px; margin:4px 0 -4px; }}
    .card {{ background:white; border:1px solid #dbe3ee; border-radius:8px; padding:18px; box-shadow:0 8px 24px rgba(16,35,63,.08); }}
    .card.supplementary {{ border-color:#ead6a7; }}
    .card.rejected-screening {{ border-color:#e8b4b4; }}
    .tag {{ display:inline-block; padding:4px 9px; border-radius:999px; background:#e7eef8; color:#235a9f; font-weight:700; font-size:12px; }}
    h3 {{ font-size:19px; margin:12px 0 8px; }}
    p {{ line-height:1.52; }}
    .meta {{ color:#46566f; font-size:13px; margin:5px 0; }}
    img {{ display:block; width:100%; max-height:540px; object-fit:contain; background:#f8fafc; border:1px solid #e6edf5; border-radius:6px; }}
    .button, .link {{ display:inline-block; margin:8px 8px 0 0; padding:7px 10px; text-decoration:none; border-radius:6px; background:#235a9f; color:white; font-weight:700; font-size:13px; }}
    .link {{ background:#eef3fa; color:#17365f; }}
    footer {{ padding:0 46px 36px; color:#526070; }}
  </style>
</head>
<body>
  <header>
    <h1>DNQ-DLC Top-Journal Evidence Pack v2</h1>
    <p>This website freezes the manuscript evidence chain: main-paper figures, recommended visual evidence, supplementary-only cases, and rejected screening attempts. The rejected cases are intentionally retained so the visual selection remains auditable rather than cherry-picked.</p>
    <p><a class="button" href="{html.escape(audit_rel)}">Open evidence audit CSV</a></p>
    <div class="filters" aria-label="Evidence filters">
      <button class="filter active" data-filter="all">All evidence</button>
      <button class="filter" data-filter="Main-paper recommended">Main-paper recommended</button>
      <button class="filter" data-filter="Supplementary only">Supplementary only</button>
      <button class="filter" data-filter="Rejected screening / audit trail">Rejected screening</button>
    </div>
  </header>
  <main>{body}</main>
  <footer>Generated from local experiment artifacts. Use the CSV audit to trace every visual or figure back to source data and summary files.</footer>
  <script>
    const buttons = document.querySelectorAll('.filter');
    const sections = document.querySelectorAll('.evidence-section');
    buttons.forEach(button => {{
      button.addEventListener('click', () => {{
        buttons.forEach(b => b.classList.remove('active'));
        button.classList.add('active');
        const target = button.dataset.filter;
        sections.forEach(section => {{
          section.style.display = target === 'all' || section.dataset.section === target ? 'grid' : 'none';
        }});
      }});
    }});
  </script>
</body>
</html>
"""
    (OUT / "index.html").write_text(page, encoding="utf-8")


def build():
    ensure_dirs()
    cards, audit = build_cards_and_audit()
    audit_rel = write_csv(TABLES / "evidence_audit.csv", audit, AUDIT_FIELDS)
    write_html(cards, audit_rel)
    return {"out_dir": OUT.as_posix(), "index": (OUT / "index.html").as_posix(), "audit": (OUT / audit_rel).as_posix(), "card_count": len(cards)}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
