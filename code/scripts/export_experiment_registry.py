#!/usr/bin/env python
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ratio(count, n):
    return f"{count}/{n}"


def seed_text(seeds):
    return ",".join(str(seed) for seed in seeds)


def artifact_complete(provenance, name):
    for artifact in provenance["artifacts"]:
        if artifact["name"] == name:
            return bool(artifact["complete"])
    return False


def build_registry(root):
    manifest = load_json(root / "manifest.json")
    full = load_json(root / "tables" / "full_statistical_report.json")
    heldout = load_json(root / "tables" / "heldout_generalization.json")
    expanded = load_json(root / "tables" / "expanded_selector_generalization.json")
    learned = load_json(root / "tables" / "learned_selector_report.json")
    heldout3 = load_json(root / "tables" / "heldout3_external_validation.json")
    heldout3_expansion = load_json(root / "tables" / "heldout3_candidate_expansion.json")
    heldout4 = load_json(root / "tables" / "heldout4_external_validation.json")
    cross = load_json(root / "tables" / "cross_heldout_validation_synthesis.json")
    cross_stats = load_json(root / "tables" / "cross_heldout_statistical_supplement.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    audit = load_json(root / "tables" / "reproducibility_audit.json")

    method_summary = {item["method"]: item for item in full["method_summaries"]}
    h1 = heldout["sets"]["heldout1"]["selector"]
    h2 = heldout["sets"]["heldout2"]["selector"]
    expanded_h1 = expanded["summaries"]["heldout1_expanded"]
    expanded_h2 = expanded["summaries"]["heldout2_expanded"]
    learned_primary = learned["variants"][learned["primary_variant"]]
    cross_agg = cross["aggregate_expanded_or_later"]
    cross_stat = cross_stats["aggregate_expanded_or_later"]

    experiments = [
        {
            "id": "E01_locked_single_method_baselines",
            "role": "locked development benchmark",
            "stage": "locked",
            "seed_set": "locked",
            "seeds": manifest["seed_sets"]["locked"],
            "unit": "10 fixed simulator seeds",
            "primary_endpoint": "strict full-lap PASS",
            "selector_result": "NA",
            "oracle_result": "NA",
            "primary_result": (
                "overtake_base_only "
                f"{ratio(method_summary['main:overtake_base_only']['pass_count'], method_summary['main:overtake_base_only']['n'])}; "
                "graph_adaptive_shield "
                f"{ratio(method_summary['adaptive:graph_adaptive_shield']['pass_count'], method_summary['adaptive:graph_adaptive_shield']['n'])}; "
                "graph_soft_shield "
                f"{ratio(method_summary['main:graph_soft_shield']['pass_count'], method_summary['main:graph_soft_shield']['n'])}"
            ),
            "status": "baseline preserved",
            "interpretation_boundary": "Locked seeds preserve baseline and innovation comparisons; they are not external validation.",
            "primary_evidence": [
                "tables/full_statistical_report.md",
                "tables/main_results.csv",
                "figures/figure_1_multicar_overtake_results.*",
            ],
            "provenance_artifacts": ["full_statistical_report"],
        },
        {
            "id": "E02_heldout1_online_selector",
            "role": "first held-out selector validation",
            "stage": "heldout1",
            "seed_set": "heldout1",
            "seeds": manifest["seed_sets"]["heldout1"],
            "unit": "10 disjoint simulator seeds",
            "primary_endpoint": "strict full-lap PASS by 1200-step online simulator-loop probe selector",
            "selector_result": ratio(h1["pass_count"], h1["n"]),
            "oracle_result": ratio(h1["oracle_pass_count"], h1["n"]),
            "primary_result": f"selector {ratio(h1['pass_count'], h1['n'])}; diagnostic oracle {ratio(h1['oracle_pass_count'], h1['n'])}",
            "status": "positive held-out result",
            "interpretation_boundary": "Deployable in-simulator selector result on heldout1 only; must be paired with heldout2 and later held-out results.",
            "primary_evidence": [
                "tables/heldout_generalization.md",
                "tables/portfolio_probe_selector_1200_heldout_dagger_v2.md",
                "tables/seed_outcome_ledger.md",
                "figures/figure_2_portfolio_selector_summary.*",
            ],
            "provenance_artifacts": ["heldout_generalization", "online_probe_selector_1200_heldout_dagger_v2"],
        },
        {
            "id": "E03_heldout2_online_selector_stress_repeat",
            "role": "second held-out stress repeat",
            "stage": "heldout2",
            "seed_set": "heldout2",
            "seeds": manifest["seed_sets"]["heldout2"],
            "unit": "10 disjoint simulator seeds",
            "primary_endpoint": "strict full-lap PASS by same online simulator-loop selector family",
            "selector_result": ratio(h2["pass_count"], h2["n"]),
            "oracle_result": ratio(h2["oracle_pass_count"], h2["n"]),
            "primary_result": f"selector {ratio(h2['pass_count'], h2['n'])}; diagnostic oracle {ratio(h2['oracle_pass_count'], h2['n'])}",
            "status": "negative generalization boundary",
            "interpretation_boundary": "Stress repeat exposes both selector misses and candidate-policy gaps; no broad robustness claim follows.",
            "primary_evidence": [
                "tables/heldout_generalization.md",
                "tables/selector_calibration.md",
                "tables/heldout2_failure_atlas.md",
                "tables/seed_outcome_ledger.md",
            ],
            "provenance_artifacts": ["heldout_generalization", "selector_calibration", "heldout2_failure_atlas"],
        },
        {
            "id": "E04_heldout2_candidate_expansion",
            "role": "candidate-policy expansion diagnostic",
            "stage": "heldout2_expansion",
            "seed_set": "heldout2",
            "seeds": manifest["seed_sets"]["heldout2"],
            "unit": "10 disjoint simulator seeds",
            "primary_endpoint": "diagnostic candidate oracle after adding candidates",
            "selector_result": ratio(expanded_h2["pass_count"], expanded_h2["n"]),
            "oracle_result": ratio(expanded_h2["oracle_pass_count"], expanded_h2["n"]),
            "primary_result": (
                f"expanded selector {ratio(expanded_h2['pass_count'], expanded_h2['n'])}; "
                f"expanded oracle {ratio(expanded_h2['oracle_pass_count'], expanded_h2['n'])}; "
                f"newly covered seeds {expanded['candidate_expansion']['newly_covered_seeds']}"
            ),
            "status": "candidate coverage improved, selector gap remains",
            "interpretation_boundary": "Expanded oracle is a diagnostic upper bound, not online selector performance.",
            "primary_evidence": [
                "tables/heldout2_candidate_expansion.md",
                "tables/expanded_selector_generalization.md",
                "tables/portfolio_probe_selector_1200_heldout2_expanded.md",
                "tables/seed_outcome_ledger.md",
            ],
            "provenance_artifacts": ["heldout2_candidate_expansion", "expanded_selector_generalization"],
        },
        {
            "id": "E05_heldout1_expanded_selector_regression_check",
            "role": "regression check after candidate expansion",
            "stage": "heldout1_expanded",
            "seed_set": "heldout1",
            "seeds": manifest["seed_sets"]["heldout1"],
            "unit": "10 disjoint simulator seeds",
            "primary_endpoint": "strict full-lap PASS after adding a candidate",
            "selector_result": ratio(expanded_h1["pass_count"], expanded_h1["n"]),
            "oracle_result": ratio(expanded_h1["oracle_pass_count"], expanded_h1["n"]),
            "primary_result": f"expanded selector {ratio(expanded_h1['pass_count'], expanded_h1['n'])}; oracle {ratio(expanded_h1['oracle_pass_count'], expanded_h1['n'])}",
            "status": "no heldout1 regression",
            "interpretation_boundary": "Regression check only; heldout1 remains insufficient without heldout2-4.",
            "primary_evidence": [
                "tables/expanded_selector_generalization.md",
                "tables/portfolio_probe_selector_1200_heldout_expanded.md",
                "tables/seed_outcome_ledger.md",
            ],
            "provenance_artifacts": ["expanded_selector_generalization"],
        },
        {
            "id": "E06_learned_selector_diagnostic",
            "role": "exploratory learned selector diagnostic",
            "stage": "heldout1_train_heldout2_test_heldout3_external",
            "seed_set": "heldout1/heldout2/heldout3",
            "seeds": manifest["seed_sets"]["heldout1"] + manifest["seed_sets"]["heldout2"] + manifest["seed_sets"]["heldout3"],
            "unit": "30 simulator seeds across train/test/external partitions",
            "primary_endpoint": "strict full-lap PASS by feature-only learned selector",
            "selector_result": (
                "heldout1 "
                f"{ratio(learned_primary['train']['pass_count'], learned_primary['train']['n'])}; "
                "heldout2 "
                f"{ratio(learned_primary['test']['pass_count'], learned_primary['test']['n'])}; "
                "heldout3 "
                f"{ratio(learned_primary['external_heldout3']['pass_count'], learned_primary['external_heldout3']['n'])}"
            ),
            "oracle_result": (
                "heldout2 "
                f"{ratio(learned_primary['test']['oracle_pass_count'], learned_primary['test']['n'])}; "
                "heldout3 "
                f"{ratio(learned_primary['external_heldout3']['oracle_pass_count'], learned_primary['external_heldout3']['n'])}"
            ),
            "primary_result": "Improves heldout2 to 8/10 but reduces heldout1 to 9/10 and reaches 4/10 on heldout3.",
            "status": "exploratory, not accepted replacement",
            "interpretation_boundary": "Feature-only learned selector is diagnostic; it is not the accepted online selector.",
            "primary_evidence": [
                "tables/learned_selector_report.md",
                "tables/learned_selector_rows.csv",
            ],
            "provenance_artifacts": ["learned_selector_diagnostic"],
        },
        {
            "id": "E07_heldout3_external_validation",
            "role": "third disjoint external validation",
            "stage": "heldout3",
            "seed_set": "heldout3",
            "seeds": manifest["seed_sets"]["heldout3"],
            "unit": "10 unused simulator seeds",
            "primary_endpoint": "strict full-lap PASS by expanded selector and diagnostic oracle",
            "selector_result": ratio(heldout3["expanded_selector"]["pass_count"], heldout3["expanded_selector"]["n"]),
            "oracle_result": ratio(heldout3["oracle"]["pass_count"], heldout3["oracle"]["n"]),
            "primary_result": (
                f"expanded selector {ratio(heldout3['expanded_selector']['pass_count'], heldout3['expanded_selector']['n'])}; "
                f"learned selector {ratio(heldout3['learned_selector_primary']['pass_count'], heldout3['learned_selector_primary']['n'])}; "
                f"oracle {ratio(heldout3['oracle']['pass_count'], heldout3['oracle']['n'])}"
            ),
            "status": "negative external validation",
            "interpretation_boundary": "External validation shows heldout2 gains do not transfer cleanly.",
            "primary_evidence": [
                "tables/heldout3_external_validation.md",
                "tables/portfolio_probe_selector_1200_heldout3_expanded.md",
                "tables/seed_outcome_ledger.md",
            ],
            "provenance_artifacts": ["heldout3_external_validation"],
        },
        {
            "id": "E08_heldout3_targeted_candidate_repair",
            "role": "targeted diagnostic repair",
            "stage": "heldout3_targeted_repair",
            "seed_set": "heldout3",
            "seeds": manifest["seed_sets"]["heldout3"],
            "unit": "10 heldout3 seeds used for targeted repair diagnosis",
            "primary_endpoint": "diagnostic candidate oracle after targeted repair",
            "selector_result": "NA",
            "oracle_result": ratio(heldout3_expansion["expanded_oracle"]["pass_count"], heldout3_expansion["expanded_oracle"]["n"]),
            "primary_result": (
                f"targeted expanded oracle {ratio(heldout3_expansion['expanded_oracle']['pass_count'], heldout3_expansion['expanded_oracle']['n'])}; "
                f"newly covered seeds {heldout3_expansion['expanded_oracle']['newly_covered_seeds']}"
            ),
            "status": "targeted diagnostic only",
            "interpretation_boundary": "Because heldout3 guided the repair, this is not external validation and not online selector performance.",
            "primary_evidence": [
                "tables/heldout3_candidate_expansion.md",
                "tables/heldout3_targeted_recovery_suite_report.md",
                "tables/heldout3_traffic_adaptive_conservative_suite_report.md",
            ],
            "provenance_artifacts": ["heldout3_candidate_expansion"],
        },
        {
            "id": "E09_heldout4_post_repair_external_validation",
            "role": "post-repair external validation",
            "stage": "heldout4",
            "seed_set": "heldout4",
            "seeds": manifest["seed_sets"]["heldout4"],
            "unit": "10 unused simulator seeds after heldout3-targeted repair",
            "primary_endpoint": "strict full-lap PASS by targeted seven-candidate online selector",
            "selector_result": ratio(heldout4["selector"]["pass_count"], heldout4["selector"]["n"]),
            "oracle_result": ratio(heldout4["oracle"]["pass_count"], heldout4["oracle"]["n"]),
            "primary_result": (
                f"selector {ratio(heldout4['selector']['pass_count'], heldout4['selector']['n'])}; "
                f"oracle {ratio(heldout4['oracle']['pass_count'], heldout4['oracle']['n'])}; "
                f"selector misses {heldout4['selector']['selector_miss_seeds']}; "
                f"candidate gaps {heldout4['oracle']['candidate_gap_seeds']}"
            ),
            "status": "partial transfer with remaining gaps",
            "interpretation_boundary": "Heldout4 is external validation after targeted repair and supports only partial transfer.",
            "primary_evidence": [
                "tables/heldout4_external_validation.md",
                "tables/heldout4_failure_atlas.md",
                "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.md",
                "tables/seed_outcome_ledger.md",
                "figures/figure_3_cross_heldout_validation.*",
            ],
            "provenance_artifacts": ["heldout4_external_validation", "heldout4_failure_atlas"],
        },
        {
            "id": "E10_cross_heldout_synthesis",
            "role": "descriptive cross-heldout synthesis",
            "stage": "cross_heldout",
            "seed_set": "heldout1+heldout2+heldout3+heldout4 expanded-or-later entries",
            "seeds": [],
            "unit": f"{cross_agg['n']} selector/oracle paired seed outcomes",
            "primary_endpoint": "selector pass rate, oracle pass rate, and selector-oracle gap",
            "selector_result": ratio(cross_agg["selector_pass_count"], cross_agg["n"]),
            "oracle_result": ratio(cross_agg["oracle_pass_count"], cross_agg["n"]),
            "primary_result": (
                f"selector {ratio(cross_agg['selector_pass_count'], cross_agg['n'])}, "
                f"Wilson 95% CI [{cross_stat['selector_ci95_low']:.3f}, {cross_stat['selector_ci95_high']:.3f}]; "
                f"oracle {ratio(cross_agg['oracle_pass_count'], cross_agg['n'])}, "
                f"Wilson 95% CI [{cross_stat['oracle_ci95_low']:.3f}, {cross_stat['oracle_ci95_high']:.3f}]; "
                f"gap {cross_agg['selector_oracle_gap']}"
            ),
            "status": "descriptive synthesis",
            "interpretation_boundary": "Combines development and validation stages; useful for failure accounting but not confirmatory broad robustness evidence.",
            "primary_evidence": [
                "tables/cross_heldout_validation_synthesis.md",
                "tables/cross_heldout_statistical_supplement.md",
                "tables/seed_outcome_ledger.md",
                "figures/figure_3_cross_heldout_validation.*",
                "figures/figure_3_source_data.csv",
            ],
            "provenance_artifacts": ["cross_heldout_validation_synthesis", "cross_heldout_statistical_supplement", "cross_heldout_validation_figure"],
        },
    ]

    for experiment in experiments:
        experiment["seed_count"] = len(experiment["seeds"])
        experiment["seed_list"] = seed_text(experiment["seeds"])
        experiment["evidence_complete"] = all((root / path.replace(".*", ".png")).exists() if path.endswith(".*") else (root / path).exists() for path in experiment["primary_evidence"])
        experiment["provenance_complete"] = all(artifact_complete(provenance, name) for name in experiment["provenance_artifacts"])

    return {
        "root": str(root),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": (
            "Reviewer-facing registry of experiment roles, seed sets, endpoints, evidence files, and claim boundaries. "
            "It is designed to separate development, stress-repeat, external-validation, targeted-diagnostic, and synthesis stages."
        ),
        "seed_sets": manifest["seed_sets"],
        "global_endpoint": manifest["scope"]["validator"],
        "experiments": experiments,
        "summary": {
            "experiment_count": len(experiments),
            "all_primary_evidence_present": all(item["evidence_complete"] for item in experiments),
            "all_provenance_complete": all(item["provenance_complete"] for item in experiments),
            "artifact_provenance_complete": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "reproducibility_missing_or_weak": len(audit["missing_or_weak_items"]),
        },
        "interpretation": (
            "The registry supports a conservative manuscript framing: heldout1 is positive, heldout2/heldout3 expose "
            "generalization boundaries, heldout3 repair is targeted diagnostic work, heldout4 shows partial transfer, "
            "and the cross-heldout aggregate is descriptive failure accounting."
        ),
    }


def write_csv(report, path):
    fieldnames = [
        "id",
        "role",
        "stage",
        "seed_set",
        "seed_count",
        "seed_list",
        "primary_endpoint",
        "selector_result",
        "oracle_result",
        "primary_result",
        "status",
        "interpretation_boundary",
        "primary_evidence",
        "provenance_artifacts",
        "evidence_complete",
        "provenance_complete",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["experiments"]:
            writer.writerow(
                {
                    key: (
                        "; ".join(row[key])
                        if key in {"primary_evidence", "provenance_artifacts"}
                        else row.get(key)
                    )
                    for key in fieldnames
                }
            )


def write_markdown(report, path):
    lines = [
        "# Experiment Registry",
        "",
        report["purpose"],
        "",
        f"- Root: `{report['root']}`",
        f"- Timestamp (UTC): {report['timestamp_utc']}",
        f"- Global endpoint: {report['global_endpoint']}",
        f"- Experiments registered: {report['summary']['experiment_count']}",
        f"- All primary evidence present: {report['summary']['all_primary_evidence_present']}",
        f"- All provenance complete: {report['summary']['all_provenance_complete']}",
        f"- Artifact provenance: {report['summary']['artifact_provenance_complete']}",
        f"- Reproducibility missing/weak items: {report['summary']['reproducibility_missing_or_weak']}",
        "",
        "## Seed Sets",
        "",
    ]
    for name, seeds in report["seed_sets"].items():
        lines.append(f"- `{name}`: {seed_text(seeds)}")
    lines.extend(
        [
            "",
            "## Registered Experiments",
            "",
            "| id | role | seed set | selector | oracle | status | evidence | provenance |",
            "|---|---|---|---:|---:|---|---|---|",
        ]
    )
    for row in report["experiments"]:
        lines.append(
            f"| {row['id']} | {row['role']} | {row['seed_set']} | {row['selector_result']} | "
            f"{row['oracle_result']} | {row['status']} | {row['evidence_complete']} | {row['provenance_complete']} |"
        )
    lines.extend(["", "## Details", ""])
    for row in report["experiments"]:
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- Role: {row['role']}",
                f"- Stage: {row['stage']}",
                f"- Seed set: {row['seed_set']}",
                f"- Seeds: `{row['seed_list'] or 'see cross-heldout source data'}`",
                f"- Unit: {row['unit']}",
                f"- Primary endpoint: {row['primary_endpoint']}",
                f"- Primary result: {row['primary_result']}",
                f"- Interpretation boundary: {row['interpretation_boundary']}",
                f"- Evidence complete: {row['evidence_complete']}",
                f"- Provenance complete: {row['provenance_complete']}",
                "",
                "Primary evidence:",
                "",
            ]
        )
        lines.extend(f"- `{item}`" for item in row["primary_evidence"])
        lines.extend(["", "Provenance artifacts:", ""])
        lines.extend(f"- `{item}`" for item in row["provenance_artifacts"])
        lines.append("")
    lines.extend(["## Interpretation", "", report["interpretation"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export reviewer-facing experiment registry.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_registry(root)
    out_json = materials / "EXPERIMENT_REGISTRY.json"
    out_md = materials / "EXPERIMENT_REGISTRY.md"
    out_csv = materials / "EXPERIMENT_REGISTRY.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
