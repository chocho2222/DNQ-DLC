#!/usr/bin/env python
"""Draw a deterministic vector architecture diagram for DNQ-DLC.

The figure is intentionally SVG-native so that all labels remain exact and
consistent with the manuscript methodology. It avoids raster generation because
the diagram contains many mathematical symbols and network-module names.
"""

from pathlib import Path
from xml.sax.saxutils import escape


W, H = 1800, 940


PALETTE = {
    "ink": "#1F2937",
    "muted": "#6B7280",
    "grid": "#E5E7EB",
    "blue": "#2F5F9F",
    "blue2": "#D9E8F7",
    "green": "#2F7A4F",
    "green2": "#DDEFE4",
    "orange": "#B85F18",
    "orange2": "#F6E4D2",
    "purple": "#6F5A9A",
    "purple2": "#E9E3F4",
    "red": "#B04A4A",
    "red2": "#F3DADA",
    "panel": "#F8FAFC",
    "white": "#FFFFFF",
}


def tspan_lines(text):
    return [line.strip() for line in text.split("\n")]


class SVG:
    def __init__(self):
        self.items = []

    def add(self, s):
        self.items.append(s)

    def line(self, x1, y1, x2, y2, stroke="#1F2937", width=2, dash=None, marker=True):
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        marker_attr = ' marker-end="url(#arrow)"' if marker else ""
        self.add(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{stroke}" stroke-width="{width}" fill="none"{dash_attr}{marker_attr}/>'
        )

    def path(self, d, stroke="#1F2937", width=2, fill="none", dash=None, marker=True):
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        marker_attr = ' marker-end="url(#arrow)"' if marker else ""
        self.add(
            f'<path d="{d}" stroke="{stroke}" stroke-width="{width}" fill="{fill}" '
            f'stroke-linecap="round" stroke-linejoin="round"{dash_attr}{marker_attr}/>'
        )

    def rect(self, x, y, w, h, fill="#FFFFFF", stroke="#CBD5E1", width=1.5, rx=12):
        self.add(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'
        )

    def text(self, x, y, text, size=24, fill="#1F2937", weight="400", anchor="middle", italic=False):
        style = "italic" if italic else "normal"
        lines = tspan_lines(text)
        if len(lines) == 1:
            self.add(
                f'<text x="{x}" y="{y}" font-family="Times New Roman, Times, serif" '
                f'font-size="{size}" font-weight="{weight}" font-style="{style}" '
                f'fill="{fill}" text-anchor="{anchor}">{escape(lines[0])}</text>'
            )
        else:
            self.add(
                f'<text x="{x}" y="{y}" font-family="Times New Roman, Times, serif" '
                f'font-size="{size}" font-weight="{weight}" font-style="{style}" '
                f'fill="{fill}" text-anchor="{anchor}">'
            )
            for i, line in enumerate(lines):
                dy = 0 if i == 0 else size * 1.18
                self.add(f'<tspan x="{x}" dy="{dy}">{escape(line)}</tspan>')
            self.add("</text>")

    def block(self, x, y, w, h, title, body, fill, stroke, title_color=None, title_size=22, body_size=18):
        self.rect(x, y, w, h, fill=fill, stroke=stroke, width=1.6, rx=14)
        self.text(x + w / 2, y + 30, title, size=title_size, fill=title_color or stroke, weight="700")
        if body:
            self.text(x + w / 2, y + 62, body, size=body_size, fill=PALETTE["ink"])

    def small_layer_stack(self, x, y, w=52, h=64, color="#2F5F9F"):
        for i in range(4):
            xx = x + i * 12
            self.rect(xx, y + i * 4, w, h - i * 8, fill="#FFFFFF", stroke=color, width=1.4, rx=5)

    def circle(self, cx, cy, r, fill="#FFFFFF", stroke="#1F2937", width=1.5, dash=None):
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{dash_attr}/>')

    def render(self):
        defs = f"""
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="{PALETTE['ink']}"/>
  </marker>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="0" dy="2" stdDeviation="2.5" flood-color="#94A3B8" flood-opacity="0.28"/>
  </filter>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#F7FAFC"/>
    <stop offset="50%" stop-color="#EEF6F4"/>
    <stop offset="100%" stop-color="#FFF8F0"/>
  </linearGradient>
</defs>
"""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
            + defs
            + "\n".join(self.items)
            + "\n</svg>\n"
        )


def draw_track_icon(svg, x, y):
    svg.path(f"M{x+10},{y+120} C{x+70},{y+40} {x+110},{y+40} {x+160},{y+120}", stroke="#94A3B8", width=7, marker=False)
    svg.path(f"M{x+40},{y+124} C{x+82},{y+70} {x+105},{y+72} {x+135},{y+124}", stroke="#CBD5E1", width=3, dash="8 7", marker=False)
    svg.rect(x + 72, y + 64, 34, 54, fill="#D9E8F7", stroke="#2F5F9F", width=2, rx=7)
    svg.rect(x + 84, y + 45, 26, 40, fill="#F3F4F6", stroke="#64748B", width=1.5, rx=6)
    svg.text(x + 143, y + 62, "local\nframe", size=17, fill=PALETTE["muted"])


def draw_graph_icon(svg, x, y):
    pts = [(x + 85, y + 80), (x + 42, y + 42), (x + 145, y + 48), (x + 47, y + 122), (x + 141, y + 126), (x + 190, y + 88)]
    edges = [(0, 1), (0, 2), (0, 3), (0, 4), (2, 5), (4, 5)]
    for a, b in edges:
        svg.line(pts[a][0], pts[a][1], pts[b][0], pts[b][1], stroke="#7BA4C8", width=2.2, marker=False)
    for i, (cx, cy) in enumerate(pts):
        svg.circle(cx, cy, 14 if i == 0 else 10, fill="#2F5F9F" if i == 0 else "#D9E8F7", stroke="#2F5F9F", width=2)
    svg.circle(x + 85, y + 80, 62, fill="none", stroke="#94A3B8", width=2, dash="6 6")


def draw_head_row(svg, x, y):
    labels = [("next μ", "#D9E8F7"), ("log σ²", "#E9E3F4"), ("reward", "#DDEFE4"), ("risk", "#F3DADA"), ("quality q̂", "#F6E4D2")]
    for i, (lab, fill) in enumerate(labels):
        svg.rect(x + i * 95, y, 78, 44, fill=fill, stroke="#CBD5E1", width=1.3, rx=8)
        svg.text(x + i * 95 + 39, y + 28, lab, size=17, fill=PALETTE["ink"])


def main():
    svg = SVG()
    svg.rect(0, 0, W, H, fill="url(#bg)", stroke="none", width=0, rx=0)
    svg.text(W / 2, 42, "DNQ-DLC: Dynamic-Neighborhood Quality-Guided DLC World Model", size=34, weight="700", fill="#17324D")
    svg.text(W / 2, 72, "Network modules, variable generation, and online overtaking decision flow", size=20, fill=PALETTE["muted"])

    # Stage panels.
    panels = [
        (36, 100, 548, 720, "Stage I  Map-relative dynamic-neighborhood representation", PALETTE["blue"], PALETTE["blue2"]),
        (626, 100, 548, 720, "Stage II  Graph DLC world model", PALETTE["green"], PALETTE["green2"]),
        (1216, 100, 548, 720, "Stage III  Quality-guided finite-candidate decision", PALETTE["orange"], PALETTE["orange2"]),
    ]
    for x, y, w, h, title, color, fill in panels:
        svg.rect(x, y, w, h, fill="#FFFFFF", stroke=color, width=2, rx=18)
        svg.rect(x, y, w, 48, fill=fill, stroke=color, width=1.5, rx=18)
        svg.text(x + w / 2, y + 32, title, size=23, fill=color, weight="700")

    # Stage I details.
    svg.block(60, 172, 185, 140, "Telemetry", "xᵢₜ, aₜ₋₁\ntrack map M\nprogress ηₜ", "#F8FBFF", PALETTE["blue"], body_size=18)
    draw_track_icon(svg, 282, 166)
    svg.block(285, 172, 258, 140, "Map-relative variables", "Δf, Δl, ℓ, eψ, κ, o\ncenterline frame Fₜ", "#F8FBFF", PALETTE["blue"], body_size=18)
    svg.line(245, 242, 285, 242, stroke=PALETTE["blue"], width=2.3)

    svg.block(60, 350, 230, 150, "Risk relevance ρⱼ(t)", "front gap + closing speed\n− lateral gap − distance\nlocal radius Rloc", "#F8FBFF", PALETTE["blue"], body_size=18)
    svg.block(320, 350, 224, 150, "Dynamic graph Gₜ", "all locally relevant cars\nnot fixed top-k\nmask Mₜ pads tensors", "#F8FBFF", PALETTE["blue"], body_size=18)
    draw_graph_icon(svg, 185, 515)
    svg.text(310, 684, "Vₜ: ego + selected neighbors     Eₜ: risk-weighted relations     Mₜ: valid slots", size=18, fill=PALETTE["ink"])
    svg.line(405, 312, 405, 350, stroke=PALETTE["blue"], width=2.3)
    svg.line(290, 425, 320, 425, stroke=PALETTE["blue"], width=2.3)

    # Stage II graph encoder.
    svg.block(650, 168, 232, 152, "Ego encoder φe", "MLP: x⁰ₜ → e₀", "#FAFFFB", PALETTE["green"], body_size=20)
    svg.small_layer_stack(706, 238, color=PALETTE["green"])
    svg.block(916, 168, 232, 152, "Relation encoder φr", "MLP: r⁰ʲₜ → eⱼ", "#FAFFFB", PALETTE["green"], body_size=20)
    svg.small_layer_stack(974, 238, color=PALETTE["green"])
    svg.block(650, 358, 230, 142, "Masked aggregation", "mean / attention pooling\n{eⱼ, mⱼ} → ēᵣ", "#FAFFFB", PALETTE["green"], body_size=19)
    svg.block(916, 358, 232, 142, "Scene embedding φa", "[e₀, ēᵣ] → zₜ", "#FAFFFB", PALETTE["green"], body_size=20)
    svg.line(766, 320, 766, 358, stroke=PALETTE["green"], width=2.3)
    svg.line(1032, 320, 1032, 358, stroke=PALETTE["green"], width=2.3)
    svg.line(880, 429, 916, 429, stroke=PALETTE["green"], width=2.3)
    svg.line(1148, 429, 1198, 429, stroke=PALETTE["green"], width=2.3)

    # Stage II transition model.
    svg.block(650, 545, 176, 118, "Action encoder φu", "MLP: aₜ → eₐ", "#FAFFFB", PALETTE["green"], body_size=19)
    svg.block(856, 545, 210, 118, "Fusion MLP φf", "[node, relation,\naction, scene] → ζ", "#FAFFFB", PALETTE["green"], body_size=18)
    svg.block(650, 695, 498, 88, "Prediction heads", "next-state, uncertainty, reward, risk, quality", "#FAFFFB", PALETTE["green"], body_size=19)
    draw_head_row(svg, 672, 728)
    svg.line(826, 604, 856, 604, stroke=PALETTE["green"], width=2.3)
    svg.line(966, 663, 966, 695, stroke=PALETTE["green"], width=2.3)
    svg.path("M1032,500 C1040,522 992,527 966,545", stroke=PALETTE["green"], width=2.3)

    # Stage III.
    svg.block(1240, 168, 210, 142, "Base DLC actor πθ", "zₜ / ôₜ → aᵇᵃˢᵉ", "#FFFDF9", PALETTE["orange"], body_size=20)
    svg.block(1488, 168, 230, 142, "Quality actor πθq", "set actor:\nego MLP + relation MLP\n→ aᵠᵘᵃˡ", "#FFFDF9", PALETTE["orange"], body_size=18)
    svg.block(1240, 350, 230, 142, "Analytic proposals", "pass left / right\nrecover / brake / safe", "#FFFDF9", PALETTE["orange"], body_size=19)
    svg.block(1500, 350, 218, 142, "Candidate set", "Aᶜᵃⁿᵈₜ\nfinite action library", "#FFFDF9", PALETTE["orange"], body_size=20)
    svg.line(1350, 310, 1500, 382, stroke=PALETTE["orange"], width=2.3)
    svg.line(1603, 310, 1603, 350, stroke=PALETTE["orange"], width=2.3)
    svg.line(1470, 421, 1500, 421, stroke=PALETTE["orange"], width=2.3)

    svg.block(1240, 545, 230, 140, "H-step imagination", "DLC world model rollout\nôₜ₊ₖ₊₁ = μθ(ôₜ₊ₖ, âₜ₊ₖ)", "#FFFDF9", PALETTE["orange"], body_size=18)
    svg.block(1500, 545, 218, 140, "Multi-objective score", "J(A): progress + overtake\n− off-track − close gap\n− risk − uncertainty", "#FFFDF9", PALETTE["orange"], body_size=17)
    svg.block(1300, 720, 360, 64, "Select n* = arg max J(A⁽ⁿ⁾); execute first action a*ₜ", "", "#FFFDF9", PALETTE["orange"], title_size=22)
    svg.line(1609, 492, 1609, 545, stroke=PALETTE["orange"], width=2.3)
    svg.line(1500, 615, 1470, 615, stroke=PALETTE["orange"], width=2.3)
    svg.line(1609, 685, 1520, 720, stroke=PALETTE["orange"], width=2.3)
    svg.line(1355, 685, 1440, 720, stroke=PALETTE["orange"], width=2.3)

    # Inter-stage arrows.
    svg.line(544, 425, 650, 425, stroke=PALETTE["ink"], width=2.6)
    svg.text(596, 404, "normalized\nmasked obs ōₜ", size=17, fill=PALETTE["muted"])
    svg.line(1148, 429, 1240, 239, stroke=PALETTE["ink"], width=2.6)
    svg.line(1148, 740, 1240, 615, stroke=PALETTE["ink"], width=2.6)
    svg.text(1190, 590, "predicted\nheads", size=17, fill=PALETTE["muted"])

    # Feedback loop.
    svg.path("M1480,784 L1480,865 L105,865 L105,312", stroke="#17324D", width=3.0, marker=True)
    svg.rect(835, 842, 150, 44, fill="#EAF2FA", stroke="#2F5F9F", width=1.5, rx=10)
    svg.text(910, 870, "t ← t + 1", size=22, weight="700", fill="#17324D")
    svg.text(900, 912, "Receding-horizon loop: observe, rebuild graph, re-score candidates", size=21, fill=PALETTE["muted"])

    # Legend.
    svg.rect(42, 830, 410, 58, fill="#FFFFFF", stroke="#CBD5E1", width=1.2, rx=12)
    svg.circle(72, 859, 8, fill=PALETTE["green"], stroke=PALETTE["green"])
    svg.text(172, 866, "learned neural module", size=18, anchor="middle")
    svg.rect(276, 849, 18, 18, fill=PALETTE["orange2"], stroke=PALETTE["orange"], width=1.2, rx=3)
    svg.text(370, 866, "analytic decision logic", size=18, anchor="middle")

    out_dir = Path("multi_car_racing/paper_rewriting_output_tits_dynamic_graph_draft_20260625/tits_submission_final/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path = out_dir / "figure_method_dnq_dlc_architecture_network_v4.svg"
    svg_path.write_text(svg.render(), encoding="utf-8")

    mirror_dir = Path("multi_car_racing/outputs/tits_dynamic_graph_expanded/architecture/vector")
    mirror_dir.mkdir(parents=True, exist_ok=True)
    (mirror_dir / svg_path.name).write_text(svg_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(svg_path)


if __name__ == "__main__":
    main()
