#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


PANEL_REVIEW_MATRIX = {
    "figure_1_multicar_overtake_results": {
        "a": {
            "conclusion": "Strict full-lap success remains seed-limited: the locked overtake baseline is strong, while the graph+shield variant does not yet improve aggregate pass rate.",
            "source_data_filter": "panel contains `a-c`; compare `method`, `family`, and `status` rows in `figure_1_source_data.csv`.",
            "statistical_support": "Wilson intervals and exact counts are reported from saved strict full-lap rollouts; no broad superiority claim is made from the current seed count.",
            "claim_boundary": "Use as a transparent baseline/innovation comparison, not as evidence that graph+shield is generally better than the locked baseline.",
            "reviewer_risk": "Small seed batches and heterogeneous rows can invite overinterpretation unless the locked-baseline strength is stated explicitly.",
            "production_note": "Keep confidence intervals visible and preserve baseline labels in any journal-specific resizing.",
        },
        "b": {
            "conclusion": "Graph+shield can complete a full lap in selected seeds but shows near-complete and off-track failures in harder seeds.",
            "source_data_filter": "panel contains `a-c`; filter `method == graph_soft_shield` and inspect `seed`, `target_progress`, `steps`, and `status`.",
            "statistical_support": "Per-seed saved rollout telemetry supports a descriptive seed-level panel rather than an inferential population estimate.",
            "claim_boundary": "Use for failure localization and reproducibility, not for claiming stable full-lap completion across tracks.",
            "reviewer_risk": "Near-1.0 progress failures can look successful unless strict status and step cap are shown.",
            "production_note": "Preserve seed labels and the strict PASS/FAIL distinction.",
        },
        "c": {
            "conclusion": "Grass exposure and final rank separate overtaking failures from completion failures and explain why nominal front-running is insufficient.",
            "source_data_filter": "panel contains `a-c`; use `target_grass_rate`, `max_grass_rate`, `rank`, and `status`.",
            "statistical_support": "Saved telemetry-derived rates provide diagnostic failure evidence; this panel is not a safety certification.",
            "claim_boundary": "Use as controlled-environment failure decomposition only.",
            "reviewer_risk": "Rank can be misread as success; strict pass status and grass-rate thresholds must remain visible.",
            "production_note": "Keep axis labels explicit about target-car grass rate and final rank.",
        },
        "d": {
            "conclusion": "Ablations show that fallback controllers and shields change behavior, but the hard-case composition limits causal strength.",
            "source_data_filter": "panel contains `d` or ablation rows in `figure_1_source_data.csv`; compare method families and status.",
            "statistical_support": "Ablation rows are saved-run comparisons; larger matched sweeps are required for confirmatory causal attribution.",
            "claim_boundary": "Report as ablation evidence for mechanism plausibility, not as definitive component attribution.",
            "reviewer_risk": "The seed-7 hard case can dominate interpretation if not flagged.",
            "production_note": "Do not hide negative or neutral ablation rows.",
        },
    },
    "figure_2_portfolio_selector_summary": {
        "a": {
            "conclusion": "Multiple controllers are complementary, and no single candidate solves all strict full-lap overtaking cases.",
            "source_data_filter": "panel == `a`; compare `kind == single_method`, `label`, `pass_count`, `n`, and Wilson intervals.",
            "statistical_support": "Exact pass counts with confidence intervals summarize saved strict evaluations.",
            "claim_boundary": "Use to motivate portfolio selection, not to claim a universally dominant candidate.",
            "reviewer_risk": "The strong overtake baseline must be treated as a real comparator, not a strawman.",
            "production_note": "Keep baseline and innovation families visually distinguishable.",
        },
        "b": {
            "conclusion": "Diagnostic oracle portfolios expose available candidate complementarity and an upper bound on what selection could achieve.",
            "source_data_filter": "panel == `b`; use `kind == oracle` rows and `pass_count`.",
            "statistical_support": "Oracle values are computed from saved candidate outcomes at the seed level.",
            "claim_boundary": "Oracle bars are diagnostic upper bounds and are not online selector outputs.",
            "reviewer_risk": "Readers may confuse oracle with online autonomy unless the diagnostic label remains prominent.",
            "production_note": "Keep `oracle` wording in panel labels and legend.",
        },
        "c": {
            "conclusion": "Online probing can match the first held-out batch but exposes a heldout2 generalization boundary and a selector-oracle gap.",
            "source_data_filter": "panel == `c`; compare selector and oracle rows for heldout1/heldout2.",
            "statistical_support": "Saved held-out counts quantify selector performance and oracle gaps; calibration controls remain included as negative evidence.",
            "claim_boundary": "Use as evidence of partial transfer and remaining selector limitations, not broad robustness.",
            "reviewer_risk": "Heldout1 success can obscure heldout2 failure unless both are shown together.",
            "production_note": "Retain heldout2 rows and negative-control labels.",
        },
        "d": {
            "conclusion": "Seed-level complementarity explains why a portfolio can outperform individual candidates while also revealing unsolved seeds.",
            "source_data_filter": "panel == `d`; inspect method-by-seed pass/fail rows in `figure_2_source_data.csv`.",
            "statistical_support": "Binary seed outcome matrix is descriptive source evidence for complementarity.",
            "claim_boundary": "Use for mechanism visualization, not for estimating prevalence beyond the sampled seeds.",
            "reviewer_risk": "Showing only key methods could be seen as cherry-picking unless the full ledger remains available.",
            "production_note": "Cross-reference `tables/seed_outcome_ledger.md` when using this panel in text.",
        },
    },
    "figure_3_cross_heldout_validation": {
        "a": {
            "conclusion": "Across held-out stages, selector gains are inconsistent and heldout4 shows only partial transfer after targeted repair.",
            "source_data_filter": "panel contains `a-b`; compare `heldout`, `stage`, `selector_pass_count`, `oracle_pass_count`, and rates.",
            "statistical_support": "Wilson intervals and exact selector-oracle gap tests are reported in the cross-heldout statistical supplement.",
            "claim_boundary": "Use as external-validation staging evidence, not broad robustness.",
            "reviewer_risk": "Heldout3 targeted repair must be separated from heldout3 external validation.",
            "production_note": "Keep stage names long enough to preserve external/targeted distinctions.",
        },
        "b": {
            "conclusion": "Failure decomposition distinguishes selector misses from candidate-policy gaps, guiding future algorithm work.",
            "source_data_filter": "panel contains `a-b`; use `selector_miss_count`, `candidate_gap_count`, and seed lists.",
            "statistical_support": "Seed-level pass/fail decomposition is exact for saved runs and descriptive by design.",
            "claim_boundary": "Use to prioritize repair directions, not to certify general failure rates.",
            "reviewer_risk": "Candidate gaps and selector misses should not be merged into a single vague failure category.",
            "production_note": "Keep seed lists available in source data and table supplements.",
        },
        "c": {
            "conclusion": "The cross-heldout aggregate summarizes saved expanded-or-later runs and preserves a sizable selector-oracle gap.",
            "source_data_filter": "panel == `c`; use aggregate rows in `figure_3_source_data.csv` and cross-heldout supplement.",
            "statistical_support": "Aggregate exact counts are descriptive synthesis across saved held-out stages.",
            "claim_boundary": "Do not use the aggregate to average away heldout3/heldout4 limitations.",
            "reviewer_risk": "A single aggregate bar can overstate robustness if stage-level failures are omitted.",
            "production_note": "Pair aggregate panel with panels a-b in all manuscript uses.",
        },
    },
}


def build_legends(root):
    manifests = [
        load_json(root / "figures" / "figure_manifest.json"),
        load_json(root / "figures" / "figure_2_manifest.json"),
        load_json(root / "figures" / "figure_3_manifest.json"),
    ]
    titles = {
        "figure_1_multicar_overtake_results": "Figure 1 | Strict full-lap evaluation exposes baseline strength and failure modes.",
        "figure_2_portfolio_selector_summary": "Figure 2 | Portfolio complementarity supports online probing but reveals heldout2 limits.",
        "figure_3_cross_heldout_validation": "Figure 3 | Cross-heldout synthesis shows partial transfer rather than robustness.",
    }
    legends = []
    for manifest in manifests:
        panels = " ".join(
            f"({panel}) {description}" for panel, description in manifest["panels"].items()
        )
        legends.append(
            {
                "figure": manifest["figure"],
                "title": titles[manifest["figure"]],
                "legend": (
                    f"{titles[manifest['figure']]} {manifest['claim']} {panels} "
                    f"Source data are provided in `{manifest['source_data']}`. "
                    "Oracle results, where shown, are diagnostic upper bounds and not online selector outputs."
                ),
                "source_data": manifest["source_data"],
                "exports": manifest["exports"],
                "review_risks": manifest.get("review_risks", []),
                "panel_review_matrix": PANEL_REVIEW_MATRIX.get(manifest["figure"], {}),
            }
        )
    for item in legends:
        if item["figure"] == "figure_3_cross_heldout_validation":
            item["legend"] += (
                " A source-data dictionary is provided in "
                "`outputs/paper_multicar_overtake_20260618/figures/figure_3_source_data_dictionary.csv`, "
                "and uncertainty intervals plus exact selector-oracle gap tests are reported in "
                "`outputs/paper_multicar_overtake_20260618/tables/cross_heldout_statistical_supplement.md`."
            )
    return {
        "root": str(root),
        "purpose": "Submission-facing figure legends with source-data and review-risk traceability.",
        "legends": legends,
        "reporting_boundary": (
            "Figure 3 must be interpreted as a cross-heldout synthesis with partial heldout4 transfer, "
            "not as evidence for a broad robustness claim."
        ),
        "summary": {
            "figure_count": len(legends),
            "panel_review_row_count": sum(len(item["panel_review_matrix"]) for item in legends),
            "panel_review_fields": [
                "conclusion",
                "source_data_filter",
                "statistical_support",
                "claim_boundary",
                "reviewer_risk",
                "production_note",
            ],
        },
    }


def write_markdown(report, path):
    lines = [
        "# Figure Legends",
        "",
        report["purpose"],
        "",
        "Reporting boundary:",
        "",
        report["reporting_boundary"],
        "",
    ]
    for item in report["legends"]:
        lines.extend(
            [
                f"## {item['title']}",
                "",
                item["legend"],
                "",
                f"- Source data: `{item['source_data']}`",
                "- Exports:",
            ]
        )
        lines.extend(f"  - `{export}`" for export in item["exports"])
        lines.extend(["- Review risks:"])
        lines.extend(f"  - {risk}" for risk in item["review_risks"])
        lines.extend(
            [
                "",
                "### Panel Review Matrix",
                "",
                "| panel | conclusion | source-data filter | statistical support | claim boundary | reviewer risk | production note |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for panel, row in item["panel_review_matrix"].items():
            lines.append(
                f"| {panel} | {row['conclusion']} | {row['source_data_filter']} | "
                f"{row['statistical_support']} | {row['claim_boundary']} | "
                f"{row['reviewer_risk']} | {row['production_note']} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export manuscript-facing figure legends.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_legends(root)
    out_json = root / "materials" / "FIGURE_LEGENDS.json"
    out_md = root / "materials" / "FIGURE_LEGENDS.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md)}, indent=2))


if __name__ == "__main__":
    main()
