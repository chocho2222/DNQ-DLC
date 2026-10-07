#!/usr/bin/env python
import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ratio(count, n):
    return f"{count}/{n}"


def csv_join(values):
    if isinstance(values, list):
        return ";".join(str(v) for v in values)
    if isinstance(values, dict):
        return json.dumps(values, sort_keys=True)
    return "" if values is None else str(values)


def summarize_failure_flags(rows, key="failure_flags"):
    counts = Counter()
    for row in rows:
        flags = row.get(key) or row.get("failure_reasons") or ""
        if isinstance(flags, list):
            parts = flags
        else:
            parts = str(flags).replace("+", ";").split(";")
        for part in parts:
            part = part.strip()
            if part:
                counts[part] += 1
    return dict(sorted(counts.items()))


def build_register(root):
    heldout2 = load_json(root / "tables" / "heldout2_failure_atlas.json")
    heldout3 = load_json(root / "tables" / "heldout3_external_validation.json")
    heldout3_expansion = load_json(root / "tables" / "heldout3_candidate_expansion.json")
    heldout4 = load_json(root / "tables" / "heldout4_failure_atlas.json")
    fast = load_json(root / "tables" / "heldout_expert_fast_smoke_report.json")
    barrier = load_json(root / "tables" / "heldout_expert_barrier_smoke_report.json")
    recovery = load_json(root / "tables" / "heldout_expert_recovery_smoke_report.json")
    dagger = load_json(root / "tables" / "dagger_failure_diagnosis.json")
    dagger_v2 = load_json(root / "tables" / "dagger_v2_heldout_failure_diagnosis.json")
    boundary = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")

    items = [
        {
            "id": "N1_heldout2_original_candidate_gaps",
            "category": "candidate_policy_gap",
            "scope": "heldout2 original five-candidate selector",
            "result": f"{heldout2['summary']['candidate_gap_count']} candidate-gap seeds",
            "affected_seeds": heldout2["summary"]["candidate_gap_seeds"],
            "failure_signature": "No tested candidate passes the strict validator.",
            "evidence": "tables/heldout2_failure_atlas.md; tables/heldout2_failure_atlas_seed_rows.csv",
            "interpretation": "The original candidate pool is insufficient on these seeds.",
            "action": "Retain as historical failure evidence; use candidate expansion results to show targeted coverage progress.",
        },
        {
            "id": "N2_heldout2_expanded_selector_misses",
            "category": "selector_miss",
            "scope": "heldout2 expanded six-candidate selector",
            "result": "expanded selector 7/10 against 10/10 oracle",
            "affected_seeds": [103, 109, 113],
            "failure_signature": "A passing candidate exists, but the online probe selector chooses a failing policy.",
            "evidence": "tables/heldout2_candidate_expansion.md; tables/expanded_selector_generalization.md",
            "interpretation": "Candidate coverage improved, but selection is still not reliable.",
            "action": "Improve selector features or distillation while preserving heldout1 10/10.",
        },
        {
            "id": "N3_heldout3_external_drop",
            "category": "external_validation_failure",
            "scope": "heldout3 external validation",
            "result": (
                f"expanded selector {ratio(heldout3['expanded_selector']['pass_count'], heldout3['expanded_selector']['n'])}; "
                f"oracle {ratio(heldout3['oracle']['pass_count'], heldout3['oracle']['n'])}"
            ),
            "affected_seeds": heldout3["expanded_selector"]["failed_seeds"],
            "failure_signature": "Both hand-scored and learned selectors drop on an unused held-out batch.",
            "evidence": "tables/heldout3_external_validation.md; tables/learned_selector_report.md",
            "interpretation": "Heldout2 learned-selector gains do not establish external robustness.",
            "action": "Treat learned selector as diagnostic until it is frozen and validated on a fresh batch.",
        },
        {
            "id": "N4_heldout3_targeted_repair_boundary",
            "category": "targeted_repair_boundary",
            "scope": "heldout3 targeted candidate repair",
            "result": (
                f"targeted oracle {ratio(heldout3_expansion['expanded_oracle']['pass_count'], heldout3_expansion['expanded_oracle']['n'])}; "
                "selector remains 4/10 in the targeted selector stage"
            ),
            "affected_seeds": heldout3["expanded_selector"]["failed_seeds"],
            "failure_signature": "Candidate coverage can be repaired, but repair is informed by heldout3 failures.",
            "evidence": "tables/heldout3_candidate_expansion.md; tables/heldout3_targeted_selector_generalization.md",
            "interpretation": "This is useful repair evidence, not external validation.",
            "action": "Use heldout4 or heldout5-style batches for post-repair external validation.",
        },
        {
            "id": "N5_heldout4_partial_transfer",
            "category": "post_repair_external_boundary",
            "scope": "heldout4 after heldout3-targeted repair",
            "result": (
                f"selector {ratio(heldout4['summary']['selector_pass_count'], heldout4['summary']['n'])}; "
                f"oracle {ratio(heldout4['summary']['oracle_pass_count'], heldout4['summary']['n'])}"
            ),
            "affected_seeds": heldout4["summary"]["selector_miss_seeds"] + heldout4["summary"]["candidate_gap_seeds"],
            "failure_signature": "Remaining failures split into selector misses and candidate-policy gaps.",
            "evidence": "tables/heldout4_external_validation.md; tables/heldout4_failure_atlas.md",
            "interpretation": "Post-repair transfer is partial, so robustness remains unproven.",
            "action": "Prioritize heldout4 selector-miss seeds 197/211 and candidate-gap seeds 233/239 before larger-N claims.",
        },
        {
            "id": "N6_hand_tuned_expert_negative_controls",
            "category": "negative_control",
            "scope": "expert fast/barrier/recovery hard-seed smoke tests",
            "result": "three hand-tuned expert variants fail all four hard smoke seeds",
            "affected_seeds": sorted({row["seed"] for report in [fast, barrier, recovery] for row in report["failures"]}),
            "failure_signature": "Simple hand-tuned speed, barrier, or conservative recovery rules do not satisfy strict full-lap criteria.",
            "evidence": "tables/heldout_expert_fast_smoke_report.md; tables/heldout_expert_barrier_smoke_report.md; tables/heldout_expert_recovery_smoke_report.md",
            "interpretation": "The package retains negative controls rather than only reporting successful candidates.",
            "action": "Use these failures to justify data-aggregated or selector-based approaches.",
        },
        {
            "id": "N7_dagger_recovery_near_misses",
            "category": "near_miss_diagnostic",
            "scope": "DAgger recovery diagnostics",
            "result": f"first recovery near misses {dagger['near_miss_count']}; DAgger-v2 heldout near misses {dagger_v2['near_miss_count']}",
            "affected_seeds": sorted({row["seed"] for row in dagger["near_misses"] + dagger_v2["near_misses"]}),
            "failure_signature": "Near-complete or near-safe runs still fail at least one strict endpoint.",
            "evidence": "tables/dagger_failure_diagnosis.md; tables/dagger_v2_heldout_failure_diagnosis.md",
            "interpretation": "Near misses motivate recovery data aggregation but are not counted as successes.",
            "action": "Report strict PASS only; use near-miss rows to design recovery labels and traffic-grass controls.",
        },
    ]

    summary = {
        "item_count": len(items),
        "categories": dict(sorted(Counter(row["category"] for row in items).items())),
        "heldout2_candidate_gap_seeds": heldout2["summary"]["candidate_gap_seeds"],
        "heldout2_selector_miss_seeds_after_expansion": [103, 109, 113],
        "heldout3_failed_seeds": heldout3["expanded_selector"]["failed_seeds"],
        "heldout4_selector_miss_seeds": heldout4["summary"]["selector_miss_seeds"],
        "heldout4_candidate_gap_seeds": heldout4["summary"]["candidate_gap_seeds"],
        "heldout4_failure_flag_counts": heldout4["summary"]["failure_flag_counts"],
        "dagger_v2_heldout_failure_flag_counts": summarize_failure_flags(dagger_v2["rows"], key="failure_reasons"),
        "external_validity_boundary": boundary["summary"]["expanded_or_later_selector"],
        "publication_verification_status": verification["summary"]["status"],
        "artifact_provenance": verification["summary"]["artifact_provenance"],
    }

    return {
        "root": str(root),
        "title": "Negative results and failure-mode register",
        "purpose": (
            "Collect negative controls, external-validation failures, targeted-repair boundaries, selector misses, "
            "candidate-policy gaps, and near-miss diagnostics in one reviewer-facing register."
        ),
        "summary": summary,
        "items": items,
        "interpretation": (
            "This register is intended to reduce file-drawer bias and protect manuscript claims. Failed and partial "
            "results are retained as evidence for method boundaries and future experimental priorities."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "id",
            "category",
            "scope",
            "result",
            "affected_seeds",
            "failure_signature",
            "evidence",
            "interpretation",
            "action",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["items"]:
            writer.writerow({key: csv_join(row.get(key)) for key in fieldnames})


def write_markdown(report, path):
    lines = [
        "# Negative Results and Failure-mode Register",
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
    lines.extend(
        [
            "",
            "## Register",
            "",
            "| id | category | scope | result | affected seeds | failure signature | evidence | interpretation | action |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["items"]:
        lines.append(
            f"| {row['id']} | {row['category']} | {row['scope']} | {row['result']} | "
            f"{csv_join(row['affected_seeds'])} | {row['failure_signature']} | `{row['evidence']}` | "
            f"{row['interpretation']} | {row['action']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export negative results and failure-mode register.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_register(root)
    out_json = materials / "NEGATIVE_RESULTS_FAILURE_REGISTER.json"
    out_md = materials / "NEGATIVE_RESULTS_FAILURE_REGISTER.md"
    out_csv = materials / "NEGATIVE_RESULTS_FAILURE_REGISTER.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
