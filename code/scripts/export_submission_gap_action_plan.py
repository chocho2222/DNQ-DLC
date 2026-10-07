#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_plan(root):
    reporting = load_json(root / "materials" / "TRANSPARENT_REPORTING_CHECKLIST.json")
    reviewer = load_json(root / "materials" / "REVIEWER_RESPONSE_MAP.json")
    atlas = load_json(root / "tables" / "heldout2_failure_atlas.json")
    candidate_expansion = load_json(root / "tables" / "heldout2_candidate_expansion.json")
    expanded_selector = load_json(root / "tables" / "expanded_selector_generalization.json")
    expanded_distillation = load_json(root / "tables" / "expanded_selector_distillation_report.json")
    learned_selector = load_json(root / "tables" / "learned_selector_report.json")
    heldout3 = load_json(root / "tables" / "heldout3_external_validation.json")
    heldout3_expansion = load_json(root / "tables" / "heldout3_candidate_expansion.json")
    heldout4 = load_json(root / "tables" / "heldout4_external_validation.json")
    cross_heldout = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")
    manifest = load_json(root / "manifest.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    reproducibility = load_json(root / "tables" / "reproducibility_audit.json")

    actions = [
        {
            "id": "A1_heldout4_and_crossheldout_selector_boundary",
            "priority": "P0",
            "gap": "post-repair selector and candidate gaps",
            "problem": (
                f"Heldout4 shows partial transfer after targeted repair: selector "
                f"{heldout4['selector']['pass_count']}/{heldout4['selector']['n']} against oracle "
                f"{heldout4['oracle']['pass_count']}/{heldout4['oracle']['n']}. Selector misses remain on "
                f"{heldout4['selector']['selector_miss_seeds']}, candidate gaps remain on "
                f"{heldout4['oracle']['candidate_gap_seeds']}, and the expanded-or-later cross-heldout selector-oracle gap is "
                f"{cross_heldout['aggregate_expanded_or_later']['selector_oracle_gap']} seeds."
            ),
            "target_seeds": {
                "heldout4_selector_miss_seeds": heldout4["selector"]["selector_miss_seeds"],
                "heldout4_candidate_gap_seeds": heldout4["oracle"]["candidate_gap_seeds"],
            },
            "recommended_work": (
                "Design the next selector/candidate changes using heldout1-4 diagnostics, then reserve a fresh heldout5 batch for external validation."
            ),
            "acceptance_criteria": [
                "New selector/candidate design is frozen before heldout5 is evaluated.",
                "Heldout1 does not regress from 10/10 and heldout2 does not regress from 7/10 expanded-selector performance.",
                "Heldout3 and heldout4 selector misses are reduced in diagnostic reruns without using full-rollout oracle labels at decision time.",
                "Heldout5 is reported as the next external validation rather than retuning on heldout4.",
            ],
            "expected_artifacts": [
                "tables/heldout5_external_validation.md",
                "tables/heldout5_failure_atlas.md",
                "figures/figure_4_external_validation.*",
                "tables/cross_heldout_validation_synthesis.md",
            ],
            "evidence_now": [
                "tables/heldout4_external_validation.md",
                "tables/heldout4_failure_atlas.md",
                "tables/cross_heldout_validation_synthesis.md",
                "figures/figure_3_cross_heldout_validation.*",
            ],
        },
        {
            "id": "A2_heldout3_candidate_and_selector_boundary",
            "priority": "P0",
            "gap": "heldout3 external-validation failure",
            "problem": (
                f"Heldout3 exposes the strongest current boundary: the expanded oracle is "
                f"{heldout3['oracle']['pass_count']}/{heldout3['oracle']['n']}, but the expanded selector and "
                f"primary learned selector are both {heldout3['expanded_selector']['pass_count']}/10. "
                f"Targeted repair raises candidate coverage to {heldout3_expansion['expanded_oracle']['pass_count']}/10; selector misses remain on "
                f"{learned_selector['variants'][learned_selector['primary_variant']]['external_heldout3']['selector_miss_seeds']}."
            ),
            "target_seeds": {
                "candidate_gap_seeds": heldout3_expansion["expanded_oracle"]["remaining_candidate_gap_seeds"],
                "selector_miss_seeds": learned_selector["variants"][learned_selector["primary_variant"]]["external_heldout3"]["selector_miss_seeds"],
            },
            "recommended_work": (
                "Train a selector using expanded probe telemetry and the targeted heldout3 candidate pool that reduces heldout3 selector misses without reducing heldout1."
            ),
            "acceptance_criteria": [
                "Heldout3 selector pass count improves beyond 4/10 when the targeted candidate pool is available.",
                "Heldout1 expanded selector remains 10/10 and heldout2 does not regress from 7/10.",
                "No full-rollout oracle labels are used at selector decision time.",
            ],
            "expected_artifacts": [
                "evaluations/heldout3_candidate_expansion/",
                "tables/heldout3_candidate_expansion.md",
                "tables/heldout3_selector_generalization.md",
                "tables/heldout3_external_validation.md",
                "tables/heldout3_candidate_expansion.md",
            ],
            "evidence_now": [
                "tables/heldout3_external_validation.md",
                "tables/portfolio_probe_selector_1200_heldout3_expanded.md",
                "tables/learned_selector_report.md",
            ],
        },
        {
            "id": "A3_expanded_pool_selector",
            "priority": "P0",
            "gap": "expanded-pool selector misses",
            "problem": (
                "The expanded heldout2 candidate oracle is 10/10 and the online simulator-loop selector improves to 7/10, but seeds 103, 109, and 113 remain selector misses. A heldout1-only scalar/priority distillation over "
                f"{expanded_distillation['grid']['heldout1_perfect_configs']} train-perfect configurations still peaks at 7/10. An exploratory feature-only learned selector reaches "
                f"{learned_selector['variants'][learned_selector['primary_variant']]['test']['pass_count']}/10 on heldout2 but drops heldout1 to "
                f"{learned_selector['variants'][learned_selector['primary_variant']]['train']['pass_count']}/10."
            ),
            "target_seeds": expanded_selector["summaries"]["heldout2_expanded"]["selector_miss_seeds"],
            "recommended_work": (
                "Train or distill a richer selector from expanded probe telemetry and candidate identity features; evaluate without full-rollout oracle labels."
            ),
            "acceptance_criteria": [
                "Heldout1 performance is not reduced from the expanded selector's 10/10 result.",
                "Heldout2 selector misses on seeds 103, 109, and 113 are reduced.",
                "A fresh heldout5 batch is evaluated before promoting a learned selector as an accepted replacement.",
                "The selector is evaluated with locked candidate suites and no full-rollout oracle labels at decision time.",
            ],
            "expected_artifacts": [
                "evaluations/learned_selector_expanded/selector_summary.json",
                "tables/learned_selector_expanded.md",
                "tables/expanded_selector_generalization.md",
                "tables/heldout_generalization.md",
            ],
            "evidence_now": [
                "tables/heldout2_failure_atlas.md",
                "tables/heldout2_candidate_expansion.md",
                "tables/expanded_selector_generalization.md",
                "tables/expanded_selector_distillation_report.md",
                "tables/learned_selector_report.md",
                "tables/selector_calibration.md",
                "materials/TRANSPARENT_REPORTING_CHECKLIST.md",
            ],
        },
        {
            "id": "A4_selector_distillation",
            "priority": "P0",
            "gap": "selector misses and expensive five-probe selector",
            "problem": (
                "The current probe score selects failing methods on heldout2 and costs five 1200-step probes; the expanded candidate pool increases this pressure."
            ),
            "target_seeds": atlas["summary"]["selector_miss_seeds"],
            "recommended_work": (
                "Train or distill a selector using early telemetry, track geometry, and candidate probe features; benchmark against the current hand-scored probe."
            ),
            "acceptance_criteria": [
                "Selector misses on heldout2 are reduced without reducing heldout1 below its current result.",
                "The new selector is evaluated on locked, heldout1, and heldout2 using the same strict validator.",
                "Compute/probe cost is reported relative to the five-candidate 1200-step selector.",
            ],
            "expected_artifacts": [
                "tables/learned_selector_report.md",
                "tables/selector_calibration.md",
                "tables/heldout_generalization.md",
                "materials/REVIEWER_RESPONSE_MAP.md",
            ],
            "evidence_now": [
                "tables/heldout2_failure_atlas_seed_rows.csv",
                "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.md",
                "tables/selector_distillation_report.md",
                "materials/TOP_JOURNAL_READINESS_CHECKLIST.md",
            ],
        },
        {
            "id": "A5_larger_n_stress",
            "priority": "P1",
            "gap": "limited robustness evidence",
            "problem": (
                "The current evidence has four disjoint 10-seed held-out batches; heldout3 is negative external validation and heldout4 shows only partial transfer after repair."
            ),
            "target_seeds": "new larger held-out batches",
            "recommended_work": (
                "Run larger-N held-out seed sweeps and traffic-density/opponent-diversity ablations after candidate and selector improvements."
            ),
            "acceptance_criteria": [
                "Report pass rates with Wilson intervals across larger held-out batches.",
                "Report traffic-density and opponent-diversity effects separately from seed variation.",
                "Keep negative results and failure atlas updates in the package.",
            ],
            "expected_artifacts": [
                "tables/larger_n_generalization_report.md",
                "tables/traffic_density_ablation_report.md",
                "tables/opponent_diversity_ablation_report.md",
                "figures/figure_4_generalization_stress.*",
            ],
            "evidence_now": [
                "materials/STATISTICAL_ANALYSIS_PLAN.md",
                "materials/TRANSPARENT_REPORTING_CHECKLIST.md",
                "materials/MANUSCRIPT_OUTLINE.md",
            ],
        },
        {
            "id": "A6_compute_cost_table",
            "priority": "P2",
            "gap": "selector and rollout cost reporting",
            "problem": (
                "The package now summarizes simulated rollout steps, selector probe counts, and devices, but wall-clock time and utilization are not recorded."
            ),
            "target_seeds": "all reported suites",
            "recommended_work": (
                "Add timed reruns or log parsing with explicit timestamps if elapsed-time or utilization accounting is required."
            ),
            "acceptance_criteria": [
                "Current cost report includes device list, number of probes, steps per probe, and simulated rollout steps.",
                "Optional timed rerun adds elapsed wall-clock and utilization fields without changing accuracy claims.",
            ],
            "expected_artifacts": [
                "tables/compute_cost_report.md",
                "tables/compute_cost_suite_rows.csv",
                "tables/compute_cost_selector_rows.csv",
                "materials/DATA_CODE_AVAILABILITY.md",
            ],
            "evidence_now": [
                "manifest.json",
                "tables/compute_cost_report.md",
                "materials/TRANSPARENT_REPORTING_CHECKLIST.md",
            ],
        },
        {
            "id": "A7_external_archive",
            "priority": "P2",
            "gap": "external DOI or repository accession",
            "problem": "The local package is complete, but no public DOI or repository accession is included.",
            "target_seeds": "not applicable",
            "recommended_work": (
                "Create a release archive after final experiments, then update Data/Code Availability with DOI or repository URL."
            ),
            "acceptance_criteria": [
                "Public archive includes code, package outputs, environment file, and reproduction guide.",
                "Data/Code Availability points to the public archive and local package layout.",
            ],
            "expected_artifacts": [
                "materials/DATA_CODE_AVAILABILITY.md",
                "manifest.json",
                "release_archive_manifest.json",
            ],
            "evidence_now": [
                "materials/DATA_CODE_AVAILABILITY.md",
                "materials/TRANSPARENT_REPORTING_CHECKLIST.md",
            ],
        },
        {
            "id": "A8_final_manuscript_package",
            "priority": "P2",
            "gap": "final submission manuscript source/PDF",
            "problem": "The experiment package now contains a local evidence-linked manuscript draft, but not a final submission PDF/source package.",
            "target_seeds": "not applicable",
            "recommended_work": (
                "After final experiments, promote the local manuscript draft into journal-formatted source and PDF."
            ),
            "acceptance_criteria": [
                "Manuscript text uses only claims allowed by the claim evidence matrix.",
                "All figure/table callouts map to package artifacts.",
                "Reviewer response map is updated after final claims are frozen.",
            ],
            "expected_artifacts": [
                "manuscript/main.md",
                "manuscript/references.bib",
                "manuscript/figures/",
                "materials/CLAIM_EVIDENCE_MATRIX.md",
            ],
            "evidence_now": [
                "materials/MANUSCRIPT_OUTLINE.md",
                "materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md",
                "materials/CLAIM_EVIDENCE_MATRIX.md",
            ],
        },
    ]

    status_counts = reporting["summary"]["status_counts"]
    hard_numbers = dict(reviewer["summary"]["hard_numbers"])
    hard_numbers["artifact_provenance"] = f"{provenance['complete_count']}/{len(provenance['artifacts'])}"
    hard_numbers["audit_missing_or_weak"] = len(reproducibility["missing_or_weak_items"])
    return {
        "root": str(root),
        "title": "Submission Gap Action Plan",
        "current_status": {
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "reproducibility_missing_or_weak": len(reproducibility["missing_or_weak_items"]),
            "transparent_reporting_status_counts": status_counts,
            "hard_numbers": hard_numbers,
        },
        "actions": actions,
        "interpretation": (
            "The local evidence package is strong, but heldout3 and heldout4 prevent a robustness claim. A top-journal submission should prioritize "
            "fresh selector/candidate design, heldout5-style external validation, and larger-N stress tests before external archiving and final manuscript packaging."
        ),
    }


def write_markdown(report, path):
    lines = [
        "# Submission Gap Action Plan",
        "",
        "This plan converts the remaining top-journal limitations into prioritized actions with acceptance criteria and expected artifacts.",
        "",
        "## Current Status",
        "",
        f"- Artifact provenance: {report['current_status']['artifact_provenance']}",
        f"- Reproducibility missing/weak items: {report['current_status']['reproducibility_missing_or_weak']}",
        f"- Transparent reporting status counts: {report['current_status']['transparent_reporting_status_counts']}",
        "",
        "Hard numbers:",
        "",
    ]
    for key, value in report["current_status"]["hard_numbers"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Prioritized Actions", ""])
    for action in report["actions"]:
        lines.extend(
            [
                f"### {action['id']} ({action['priority']})",
                "",
                f"- Gap: {action['gap']}",
                f"- Problem: {action['problem']}",
                f"- Target seeds/scope: `{action['target_seeds']}`",
                f"- Recommended work: {action['recommended_work']}",
                "",
                "Acceptance criteria:",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in action["acceptance_criteria"])
        lines.extend(["", "Expected artifacts:", ""])
        lines.extend(f"- `{item}`" for item in action["expected_artifacts"])
        lines.extend(["", "Current evidence:", ""])
        lines.extend(f"- `{item}`" for item in action["evidence_now"])
        lines.append("")
    lines.extend(["## Interpretation", "", report["interpretation"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(report, root):
    path = root / "materials" / "SUBMISSION_GAP_ACTION_PLAN.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "priority",
                "gap",
                "problem",
                "target_seeds",
                "recommended_work",
                "acceptance_criteria",
                "expected_artifacts",
                "evidence_now",
            ],
        )
        writer.writeheader()
        for action in report["actions"]:
            writer.writerow(
                {
                    "id": action["id"],
                    "priority": action["priority"],
                    "gap": action["gap"],
                    "problem": action["problem"],
                    "target_seeds": action["target_seeds"],
                    "recommended_work": action["recommended_work"],
                    "acceptance_criteria": "; ".join(action["acceptance_criteria"]),
                    "expected_artifacts": "; ".join(action["expected_artifacts"]),
                    "evidence_now": "; ".join(action["evidence_now"]),
                }
            )
    return path


def main():
    parser = argparse.ArgumentParser(description="Export prioritized submission gap action plan.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_plan(root)
    out_json = root / "materials" / "SUBMISSION_GAP_ACTION_PLAN.json"
    out_md = root / "materials" / "SUBMISSION_GAP_ACTION_PLAN.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    out_csv = write_csv(report, root)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
