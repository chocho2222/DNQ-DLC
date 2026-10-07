#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def row(
    stage,
    role,
    selector_result,
    oracle_result,
    selector_miss_count,
    selector_miss_seeds,
    candidate_gap_count,
    candidate_gap_seeds,
    failure_signature,
    interpretation_boundary,
    recommended_next_step,
    primary_evidence,
    claim_status,
):
    return {
        "stage": stage,
        "role": role,
        "selector_result": selector_result,
        "oracle_result": oracle_result,
        "selector_miss_count": selector_miss_count,
        "selector_miss_seeds": selector_miss_seeds,
        "candidate_gap_count": candidate_gap_count,
        "candidate_gap_seeds": candidate_gap_seeds,
        "failure_signature": failure_signature,
        "interpretation_boundary": interpretation_boundary,
        "recommended_next_step": recommended_next_step,
        "primary_evidence": primary_evidence,
        "claim_status": claim_status,
    }


def join_seeds(seeds):
    return "; ".join(str(seed) for seed in seeds) if seeds else "none"


def build_report(root):
    heldout2 = load_json(root / "tables" / "heldout2_failure_atlas.json")
    heldout3 = load_json(root / "tables" / "heldout3_external_validation.json")
    heldout3_targeted = load_json(root / "tables" / "heldout3_targeted_selector_generalization.json")
    heldout3_meta = load_json(root / "tables" / "heldout3_targeted_meta_selector.json")
    heldout4 = load_json(root / "tables" / "heldout4_failure_atlas.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")
    claim_tree = load_json(root / "materials" / "CLAIM_DECISION_TREE.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")

    claim_map = {item["id"]: item for item in claim_tree["rows"]}
    heldout3_selector_miss_seeds = [
        item["seed"]
        for item in heldout3["rows"]
        if item["oracle_status"] == "PASS" and item["expanded_selector_status"] != "PASS"
    ]
    heldout3_candidate_gap_seeds = heldout3["oracle"]["candidate_gap_seeds"]
    heldout3_targeted_selector_miss_seeds = heldout3_targeted["selector_miss_seeds_after_targeted_candidate"]
    heldout3_targeted_candidate_gap_seeds = heldout3_meta["oracle"]["candidate_gap_seeds"]

    rows = [
        row(
            "heldout2_expanded",
            "expanded candidate set stress repeat",
            f"{heldout2['summary']['pass_count']}/{heldout2['summary']['n']}",
            f"{heldout2['summary']['heldout2_selector']['oracle_pass_count']}/{heldout2['summary']['n']}",
            heldout2["summary"]["selector_miss_count"],
            join_seeds(heldout2["summary"]["selector_miss_seeds"]),
            heldout2["summary"]["candidate_gap_count"],
            join_seeds(heldout2["summary"]["candidate_gap_seeds"]),
            "mixed selector-miss and candidate-gap regime after candidate expansion",
            claim_map["DT04"]["claim_boundary"],
            claim_map["DT04"]["next_validation"],
            "tables/heldout2_failure_atlas.md; tables/cross_heldout_validation_synthesis.md; materials/CLAIM_DECISION_TREE.md",
            "downgraded_selector_progress",
        ),
        row(
            "heldout3_external",
            "negative external validation before targeted repair",
            f"{heldout3['expanded_selector']['pass_count']}/{heldout3['expanded_selector']['n']}",
            f"{heldout3['oracle']['pass_count']}/{heldout3['oracle']['n']}",
            len(heldout3_selector_miss_seeds),
            join_seeds(heldout3_selector_miss_seeds),
            len(heldout3_candidate_gap_seeds),
            join_seeds(heldout3_candidate_gap_seeds),
            "adverse external-validation batch with both selector misses and unresolved candidate gaps",
            claim_map["DT05"]["claim_boundary"],
            claim_map["DT05"]["next_validation"],
            "tables/heldout3_external_validation.json; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; materials/CLAIM_DECISION_TREE.md",
            "negative_external_boundary",
        ),
        row(
            "heldout3_targeted_repair",
            "diagnostic reuse after targeted candidate addition",
            f"{heldout3_targeted['targeted_selector']['pass_count']}/{heldout3_targeted['targeted_selector']['n']}",
            f"{heldout3_targeted['targeted_selector']['oracle_pass_count']}/{heldout3_targeted['targeted_selector']['n']}",
            len(heldout3_targeted_selector_miss_seeds),
            join_seeds(heldout3_targeted_selector_miss_seeds),
            len(heldout3_targeted_candidate_gap_seeds),
            join_seeds(heldout3_targeted_candidate_gap_seeds),
            "candidate coverage improves diagnostically, but selector misses remain dominant after targeted repair",
            claim_map["DT06"]["claim_boundary"],
            claim_map["DT06"]["next_validation"],
            "tables/heldout3_targeted_selector_generalization.json; tables/heldout3_targeted_meta_selector.json; materials/CONFIRMATORY_ROADMAP.md",
            "diagnostic_reuse_only",
        ),
        row(
            "heldout4_post_repair_external",
            "post-repair external validation with partial transfer",
            f"{heldout4['summary']['selector_pass_count']}/{heldout4['summary']['n']}",
            f"{heldout4['summary']['oracle_pass_count']}/{heldout4['summary']['n']}",
            heldout4["summary"]["selector_miss_count"],
            join_seeds(heldout4["summary"]["selector_miss_seeds"]),
            heldout4["summary"]["candidate_gap_count"],
            join_seeds(heldout4["summary"]["candidate_gap_seeds"]),
            "partial transfer with residual selector misses and remaining candidate-policy gaps",
            claim_map["DT07"]["claim_boundary"],
            claim_map["DT07"]["next_validation"],
            "tables/heldout4_failure_atlas.md; tables/heldout4_external_validation.json; materials/CLAIM_DECISION_TREE.md",
            "partial_transfer_only",
        ),
    ]

    report = {
        "root": str(root),
        "title": "Failure-Mode Atlas Summary",
        "purpose": (
            "Summarize cross-heldout failures into reviewer-facing categories that separate selector misses, "
            "candidate-policy gaps, external-validation boundaries, and diagnostic reuse."
        ),
        "interpretation": (
            "This summary does not create new empirical evidence. It compresses existing heldout2, heldout3, "
            "heldout3-targeted, and heldout4 failures into a single audit sheet for limitations, discussion, "
            "and reviewer response preparation."
        ),
        "summary": {
            "status": "pass",
            "row_count": len(rows),
            "negative_register_item_count": negative["summary"]["item_count"],
            "total_selector_miss_count": sum(item["selector_miss_count"] for item in rows),
            "total_candidate_gap_count": sum(item["candidate_gap_count"] for item in rows),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "claim_decision_tree_status": claim_tree["summary"]["status"],
            "not_new_empirical_evidence": True,
        },
        "rows": rows,
        "global_boundary": {
            "selector_miss_means_passing_candidate_exists": True,
            "candidate_gap_means_current_pool_has_no_strict_pass": True,
            "heldout3_targeted_repair_is_not_external_validation": True,
            "heldout4_is_partial_transfer_not_broad_robustness": True,
            "failure_rows_must_remain_visible": True,
        },
    }
    return report


def write_csv(report, path):
    fields = [
        "stage",
        "role",
        "selector_result",
        "oracle_result",
        "selector_miss_count",
        "selector_miss_seeds",
        "candidate_gap_count",
        "candidate_gap_seeds",
        "failure_signature",
        "interpretation_boundary",
        "recommended_next_step",
        "primary_evidence",
        "claim_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Failure-Mode Atlas Summary",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Global Boundary", ""])
    for key, value in report["global_boundary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Cross-Heldout Rows",
            "",
            "| stage | role | selector | oracle | selector misses | candidate gaps | failure signature | claim boundary | next step | evidence | status |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['stage']} | {item['role']} | {item['selector_result']} | {item['oracle_result']} | "
            f"{item['selector_miss_count']} ({item['selector_miss_seeds']}) | "
            f"{item['candidate_gap_count']} ({item['candidate_gap_seeds']}) | {item['failure_signature']} | "
            f"{item['interpretation_boundary']} | {item['recommended_next_step']} | "
            f"`{item['primary_evidence']}` | {item['claim_status']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export reviewer-facing cross-heldout failure-mode atlas summary.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "FAILURE_MODE_ATLAS_SUMMARY.json"
    out_md = materials / "FAILURE_MODE_ATLAS_SUMMARY.md"
    out_csv = materials / "FAILURE_MODE_ATLAS_SUMMARY.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
