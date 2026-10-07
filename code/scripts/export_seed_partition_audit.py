#!/usr/bin/env python
import argparse
import csv
import json
from itertools import combinations
from pathlib import Path


PRIMARY_SEED_SETS = ["locked", "heldout1", "heldout2", "heldout3", "heldout4"]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def set_status(a, b, overlap):
    if not overlap:
        return "pass"
    if "hard_smoke" in (a, b):
        return "documented_diagnostic_overlap"
    return "review"


def make_seed_set_rows(seed_sets):
    rows = []
    for name, seeds in seed_sets.items():
        rows.append(
            {
                "seed_set": name,
                "seed_count": len(seeds),
                "seed_list": ",".join(str(seed) for seed in seeds),
                "role": (
                    "primary_partition"
                    if name in PRIMARY_SEED_SETS
                    else "diagnostic_subset"
                ),
                "interpretation": (
                    "Used for development/validation partition accounting."
                    if name in PRIMARY_SEED_SETS
                    else "Reuses hard held-out seeds for smoke diagnostics; not independent validation."
                ),
            }
        )
    return rows


def make_overlap_rows(seed_sets):
    rows = []
    for a, b in combinations(sorted(seed_sets), 2):
        overlap = sorted(set(seed_sets[a]) & set(seed_sets[b]))
        rows.append(
            {
                "seed_set_a": a,
                "seed_set_b": b,
                "overlap_count": len(overlap),
                "overlap_seeds": ",".join(str(seed) for seed in overlap),
                "status": set_status(a, b, overlap),
                "interpretation": (
                    "Primary partitions are disjoint."
                    if not overlap
                    else "Overlap is expected only for hard-smoke diagnostics and must not be used as independent validation."
                    if "hard_smoke" in (a, b)
                    else "Unexpected overlap requiring claim review."
                ),
            }
        )
    return rows


def classify_experiment(exp):
    status = exp.get("status", "").lower()
    role = exp.get("role", "").lower()
    stage = exp.get("stage", "").lower()
    boundary = exp.get("interpretation_boundary", "").lower()
    if "locked" in stage or "development" in role:
        return "development_benchmark"
    if "targeted" in status or "targeted" in role or "targeted" in stage or "targeted" in boundary:
        return "targeted_diagnostic"
    if "exploratory" in status or "exploratory" in role:
        return "exploratory_diagnostic"
    if "candidate" in role or "diagnostic" in role or "oracle" in exp.get("primary_endpoint", "").lower():
        return "diagnostic_followup"
    if "external" in role or "external" in status or "heldout3" == stage or "heldout4" == stage:
        return "external_validation_or_boundary"
    if "heldout" in stage:
        return "heldout_validation_or_stress"
    if "cross" in stage:
        return "descriptive_synthesis"
    return "review"


def allowed_claim_for_class(cls):
    return {
        "development_benchmark": "method comparison on locked seeds only",
        "heldout_validation_or_stress": "held-out result with later-stage caveats",
        "external_validation_or_boundary": "external validation or negative boundary, as stated",
        "targeted_diagnostic": "targeted repair or candidate-coverage diagnostic only",
        "diagnostic_followup": "diagnostic follow-up, not online selector performance unless explicitly stated",
        "exploratory_diagnostic": "exploratory diagnostic only",
        "descriptive_synthesis": "descriptive aggregate/failure accounting only",
        "review": "requires manual claim review",
    }[cls]


def make_experiment_rows(experiments, primary_seed_sets):
    rows = []
    for exp in experiments:
        cls = classify_experiment(exp)
        seeds = set(exp.get("seeds", []))
        seed_set = exp.get("seed_set", "")
        overlaps = {
            name: len(seeds & set(values))
            for name, values in primary_seed_sets.items()
            if seeds
        }
        external_ok = cls in {"external_validation_or_boundary", "heldout_validation_or_stress"} and len(
            [name for name, count in overlaps.items() if count]
        ) == 1
        rows.append(
            {
                "id": exp["id"],
                "stage": exp.get("stage", ""),
                "role": exp.get("role", ""),
                "seed_set": seed_set,
                "seed_count": exp.get("seed_count", len(seeds)),
                "partition_class": cls,
                "external_validation_eligible": external_ok,
                "allowed_claim": allowed_claim_for_class(cls),
                "overlap_with_primary_sets": ";".join(f"{name}:{count}" for name, count in overlaps.items() if count),
                "interpretation_boundary": exp.get("interpretation_boundary", ""),
                "status": "pass" if cls != "review" else "review",
            }
        )
    return rows


def make_protocol_rows(protocol_rows):
    rows = []
    for row in protocol_rows:
        prohibited = row.get("prohibited_interpretation", "").lower()
        allowed = row.get("allowed_interpretation", "").lower()
        has_boundary = bool(prohibited and allowed)
        rows.append(
            {
                "id": row["id"],
                "stage": row.get("stage", ""),
                "seed_set": row.get("seed_set", ""),
                "status": row.get("status", ""),
                "has_allowed_boundary": bool(allowed),
                "has_prohibited_boundary": bool(prohibited),
                "targeted_boundary_present": "targeted" not in row.get("stage", "").lower()
                or "not" in prohibited
                or "do not" in prohibited,
                "external_boundary_present": "external" not in row.get("status", "").lower()
                or "do not" in prohibited
                or "not" in prohibited,
                "audit_status": "pass" if has_boundary else "review",
            }
        )
    return rows


def write_csv(rows, path, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def build_report(root):
    manifest = load_json(root / "manifest.json")
    registry = load_json(root / "materials" / "EXPERIMENT_REGISTRY.json")
    protocol = load_json(root / "materials" / "STUDY_PROTOCOL_AND_DEVIATIONS.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")

    seed_sets = manifest["seed_sets"]
    primary_seed_sets = {name: seed_sets[name] for name in PRIMARY_SEED_SETS}
    seed_set_rows = make_seed_set_rows(seed_sets)
    overlap_rows = make_overlap_rows(seed_sets)
    experiment_rows = make_experiment_rows(registry["experiments"], primary_seed_sets)
    protocol_rows = make_protocol_rows(protocol["rows"])

    unexpected_overlaps = [
        row for row in overlap_rows if row["status"] == "review"
    ]
    experiment_reviews = [row for row in experiment_rows if row["status"] == "review"]
    protocol_reviews = [row for row in protocol_rows if row["audit_status"] == "review"]
    external_eligible = [row for row in experiment_rows if row["external_validation_eligible"]]

    return {
        "root": str(root),
        "title": "Seed Partition and Leakage Boundary Audit",
        "purpose": (
            "Check simulator seed-set disjointness, document diagnostic seed reuse, and classify experiments by "
            "development, held-out validation, targeted diagnostic repair, exploratory diagnostic, or descriptive synthesis role."
        ),
        "summary": {
            "seed_set_count": len(seed_set_rows),
            "primary_seed_set_count": len(PRIMARY_SEED_SETS),
            "unexpected_overlap_count": len(unexpected_overlaps),
            "documented_diagnostic_overlap_count": sum(
                row["status"] == "documented_diagnostic_overlap" for row in overlap_rows
            ),
            "experiment_count": len(experiment_rows),
            "external_validation_eligible_count": len(external_eligible),
            "experiment_review_count": len(experiment_reviews),
            "protocol_review_count": len(protocol_reviews),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
            "status": "pass" if not unexpected_overlaps and not experiment_reviews and not protocol_reviews else "review",
        },
        "seed_sets": seed_set_rows,
        "overlaps": overlap_rows,
        "experiments": experiment_rows,
        "protocol_boundaries": protocol_rows,
        "interpretation": (
            "This audit is a reporting-boundary control. It does not prove out-of-distribution robustness; it documents which "
            "seed partitions are disjoint and which analyses are targeted or diagnostic so that manuscript claims remain conservative."
        ),
    }


def write_markdown(report, path):
    lines = [
        "# Seed Partition and Leakage Boundary Audit",
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
            "## Seed-set Overlap",
            "",
            "| seed set A | seed set B | overlap | status | interpretation |",
            "|---|---|---:|---|---|",
        ]
    )
    for row in report["overlaps"]:
        if row["overlap_count"] or row["seed_set_a"] in PRIMARY_SEED_SETS and row["seed_set_b"] in PRIMARY_SEED_SETS:
            lines.append(
                f"| {row['seed_set_a']} | {row['seed_set_b']} | {row['overlap_count']} | "
                f"{row['status']} | {row['interpretation']} |"
            )
    lines.extend(
        [
            "",
            "## Experiment Classes",
            "",
            "| id | stage | partition class | external eligible | allowed claim |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["experiments"]:
        lines.append(
            f"| {row['id']} | {row['stage']} | {row['partition_class']} | "
            f"{row['external_validation_eligible']} | {row['allowed_claim']} |"
        )
    lines.extend(
        [
            "",
            "Machine-readable seed-set, overlap, experiment, and protocol-boundary rows are exported as CSV files.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export seed partition and leakage boundary audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "SEED_PARTITION_AUDIT.json"
    out_md = materials / "SEED_PARTITION_AUDIT.md"
    seed_csv = materials / "SEED_PARTITION_SEED_SETS.csv"
    overlap_csv = materials / "SEED_PARTITION_OVERLAPS.csv"
    experiment_csv = materials / "SEED_PARTITION_EXPERIMENT_ROWS.csv"
    protocol_csv = materials / "SEED_PARTITION_PROTOCOL_ROWS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report["seed_sets"], seed_csv, ["seed_set", "seed_count", "seed_list", "role", "interpretation"])
    write_csv(
        report["overlaps"],
        overlap_csv,
        ["seed_set_a", "seed_set_b", "overlap_count", "overlap_seeds", "status", "interpretation"],
    )
    write_csv(
        report["experiments"],
        experiment_csv,
        [
            "id",
            "stage",
            "role",
            "seed_set",
            "seed_count",
            "partition_class",
            "external_validation_eligible",
            "allowed_claim",
            "overlap_with_primary_sets",
            "interpretation_boundary",
            "status",
        ],
    )
    write_csv(
        report["protocol_boundaries"],
        protocol_csv,
        [
            "id",
            "stage",
            "seed_set",
            "status",
            "has_allowed_boundary",
            "has_prohibited_boundary",
            "targeted_boundary_present",
            "external_boundary_present",
            "audit_status",
        ],
    )
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "seed_csv": str(seed_csv),
                "overlap_csv": str(overlap_csv),
                "experiment_csv": str(experiment_csv),
                "protocol_csv": str(protocol_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
