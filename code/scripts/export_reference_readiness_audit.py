#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


CITATION_PATTERN = re.compile(r"\[@([A-Za-z0-9:_-]+)\]")
BIB_ENTRY_PATTERN = re.compile(r"@\w+\s*\{\s*([^,\s]+)")
PLACEHOLDER_PATTERN = re.compile(r"placeholder bibliography|add literature references", re.IGNORECASE)

REQUIRED_TOPICS = [
    {
        "topic": "simulation_platform",
        "required_keys": ["brockman2016openai"],
        "status_if_present": "starter_complete",
        "note": "Gym-style simulator/interface citation is present.",
    },
    {
        "topic": "imitation_learning_or_dagger",
        "required_keys": ["ross2011reduction"],
        "status_if_present": "starter_complete",
        "note": "DAgger-style hard-state recovery citation is present.",
    },
    {
        "topic": "graph_or_relational_inductive_bias",
        "required_keys": ["battaglia2018relational"],
        "status_if_present": "starter_complete",
        "note": "Graph/relational inductive bias citation is present.",
    },
    {
        "topic": "binomial_interval_statistics",
        "required_keys": ["wilson1927probable"],
        "status_if_present": "starter_complete",
        "note": "Wilson interval citation is present.",
    },
    {
        "topic": "autonomous_overtaking_and_racing_related_work",
        "required_keys": [
            "betz2022survey",
            "okelly2020f1tenth",
            "liniger2015optimization",
            "song2021autonomous",
            "wurman2022outracing",
        ],
        "status_if_present": "starter_complete",
        "note": "Domain-specific autonomous-racing, overtaking, platform, optimization-control, and deep-RL references are present; authors should still adapt final coverage to the target journal.",
    },
]


def line_no(text, index):
    return text.count("\n", 0, index) + 1


def parse_citations(text):
    rows = []
    for match in CITATION_PATTERN.finditer(text):
        rows.append({"citation_key": match.group(1), "line": line_no(text, match.start())})
    return rows


def parse_bib_entries(text):
    return [match.group(1).strip() for match in BIB_ENTRY_PATTERN.finditer(text)]


def build_report(root):
    manuscript_path = root / "manuscript" / "main.md"
    bib_path = root / "manuscript" / "references.bib"
    manuscript_text = manuscript_path.read_text(encoding="utf-8") if manuscript_path.exists() else ""
    bib_text = bib_path.read_text(encoding="utf-8") if bib_path.exists() else ""
    citation_rows = parse_citations(manuscript_text)
    citation_keys = sorted({row["citation_key"] for row in citation_rows})
    bib_keys = sorted(set(parse_bib_entries(bib_text)))
    missing_bib_keys = sorted(set(citation_keys) - set(bib_keys))
    unused_bib_keys = sorted(set(bib_keys) - set(citation_keys))
    placeholder_hits = [
        {"line": line_no(bib_text, match.start()), "matched_text": match.group(0)}
        for match in PLACEHOLDER_PATTERN.finditer(bib_text)
    ]

    topic_rows = []
    for spec in REQUIRED_TOPICS:
        if spec["required_keys"]:
            present = all(key in bib_keys and key in citation_keys for key in spec["required_keys"])
            status = spec["status_if_present"] if present else "missing"
        else:
            present = False
            status = spec["status_if_present"]
        topic_rows.append(
            {
                "topic": spec["topic"],
                "required_keys": ";".join(spec["required_keys"]),
                "present": present,
                "status": status,
                "note": spec["note"],
            }
        )

    blocking_topic_failures = [row for row in topic_rows if row["status"] == "missing"]
    status = "pass" if bib_path.exists() and bib_keys and not missing_bib_keys and not placeholder_hits and not blocking_topic_failures else "fail"
    verification_path = root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8")) if verification_path.exists() else {"summary": {}}
    return {
        "root": str(root),
        "title": "Reference Readiness Audit",
        "purpose": (
            "Check that manuscript citation keys resolve to references.bib and that the bibliography is no longer a pure placeholder."
        ),
        "summary": {
            "status": status,
            "citation_key_count": len(citation_keys),
            "citation_occurrence_count": len(citation_rows),
            "bib_entry_count": len(bib_keys),
            "missing_bib_key_count": len(missing_bib_keys),
            "unused_bib_key_count": len(unused_bib_keys),
            "placeholder_hit_count": len(placeholder_hits),
            "topic_count": len(topic_rows),
            "topic_missing_count": len(blocking_topic_failures),
            "topic_needs_author_completion_count": sum(1 for row in topic_rows if row["status"] == "needs_author_completion"),
            "publication_verification_status": verification.get("summary", {}).get("status", "unknown"),
            "artifact_provenance": verification.get("summary", {}).get("artifact_provenance", "unknown"),
        },
        "citation_rows": citation_rows,
        "citation_keys": citation_keys,
        "bib_keys": bib_keys,
        "missing_bib_keys": missing_bib_keys,
        "unused_bib_keys": unused_bib_keys,
        "placeholder_hits": placeholder_hits,
        "topic_rows": topic_rows,
        "interpretation": (
            "This audit checks citation plumbing and starter-method references. It does not claim the related-work section is complete; "
            "domain-specific autonomous-driving, racing, and multi-agent-control references now have starter coverage, while final journal-specific citation breadth remains author-curated."
        ),
    }


def write_csv(report, materials):
    citation_csv = materials / "REFERENCE_READINESS_CITATIONS.csv"
    topic_csv = materials / "REFERENCE_READINESS_TOPICS.csv"
    with citation_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = ["citation_key", "line", "in_bibliography"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        bib_keys = set(report["bib_keys"])
        for row in report["citation_rows"]:
            writer.writerow({**row, "in_bibliography": row["citation_key"] in bib_keys})
    with topic_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = ["topic", "required_keys", "present", "status", "note"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["topic_rows"])
    return citation_csv, topic_csv


def write_markdown(report, path):
    lines = [
        "# Reference Readiness Audit",
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
    lines.extend(["", "## Citation Keys", ""])
    lines.append(", ".join(f"`{key}`" for key in report["citation_keys"]) or "None.")
    lines.extend(
        [
            "",
            "## Topic Coverage",
            "",
            "| topic | status | required keys | note |",
            "|---|---|---|---|",
        ]
    )
    for row in report["topic_rows"]:
        lines.append(f"| {row['topic']} | {row['status']} | `{row['required_keys']}` | {row['note']} |")
    if report["missing_bib_keys"]:
        lines.extend(["", "## Missing BibTeX Keys", ""])
        for key in report["missing_bib_keys"]:
            lines.append(f"- `{key}`")
    if report["unused_bib_keys"]:
        lines.extend(["", "## Unused BibTeX Keys", ""])
        for key in report["unused_bib_keys"]:
            lines.append(f"- `{key}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export manuscript reference readiness audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "REFERENCE_READINESS_AUDIT.json"
    out_md = materials / "REFERENCE_READINESS_AUDIT.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    citation_csv, topic_csv = write_csv(report, materials)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "citation_csv": str(citation_csv),
                "topic_csv": str(topic_csv),
                "status": report["summary"]["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
