#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


TERM_RULES = {
    "TV1_external_generalization": ["heldout3", "heldout4", "broad robust", "generalization"],
    "TV2_seed_reuse_and_targeted_repair": ["targeted repair", "diagnostic", "heldout3"],
    "TV3_small_n_precision": ["n=10", "Wilson", "small", "descriptive"],
    "TV4_selector_decision_transparency": ["probe", "selector", "oracle"],
    "TV5_endpoint_definition_sensitivity": ["strict", "threshold", "endpoint"],
    "TV6_negative_result_visibility": ["negative", "failure", "selector miss", "candidate gap"],
    "TV7_visual_evidence_overread": ["GIF", "qualitative", "tables"],
    "TV8_simulation_to_real_scope": ["simulator-only", "non-VLM", "real-road", "perception"],
    "TV9_figure_and_source_data_integrity": ["source data", "Figure", "QC"],
    "TV10_archive_and_author_metadata": ["DOI", "author", "archive", "submission"],
}


SECTION_HEAD_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$", re.MULTILINE)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def line_no(text, index):
    return text.count("\n", 0, index) + 1


def section_at(text, index):
    current = "front_matter"
    for match in SECTION_HEAD_RE.finditer(text):
        if match.start() > index:
            break
        current = match.group(2).strip()
    return current


def find_terms(text, terms):
    matches = []
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        for match in pattern.finditer(text):
            matches.append(
                {
                    "term": term,
                    "line": line_no(text, match.start()),
                    "section": section_at(text, match.start()),
                }
            )
    return matches


def build_report(root):
    threats = load_json(root / "materials" / "THREATS_TO_VALIDITY_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    manuscript_path = root / "manuscript" / "main.md"
    manuscript_text = manuscript_path.read_text(encoding="utf-8")

    rows = []
    for threat in threats["threats"]:
        threat_id = threat["id"]
        required_terms = TERM_RULES.get(threat_id, [])
        matches = find_terms(manuscript_text, required_terms)
        matched_terms = sorted({item["term"] for item in matches})
        covered = len(matched_terms) >= min(2, len(required_terms)) if required_terms else False
        rows.append(
            {
                "threat_id": threat_id,
                "domain": threat["domain"],
                "severity": threat["severity"],
                "threat_status": threat["status"],
                "manuscript_covered": covered,
                "required_terms": "; ".join(required_terms),
                "matched_terms": "; ".join(matched_terms),
                "matched_locations": "; ".join(
                    f"{item['section']}:L{item['line']}:{item['term']}" for item in matches[:8]
                ),
                "residual_risk": threat["residual_risk"],
                "prohibited_claim": threat["prohibited_claim"],
                "recommended_manuscript_action": threat["recommended_action"],
                "evidence": threat["evidence"],
            }
        )

    uncovered = [row for row in rows if not row["manuscript_covered"]]
    high_uncovered = [row for row in uncovered if row["severity"] == "high"]
    return {
        "root": str(root),
        "title": "Manuscript Limitation Integration Audit",
        "purpose": (
            "Check whether the conservative manuscript draft visibly carries the threats-to-validity boundaries "
            "that are documented in the reviewer-facing audit."
        ),
        "scope": {
            "manuscript": "manuscript/main.md",
            "threat_source": "materials/THREATS_TO_VALIDITY_AUDIT.json",
            "not_semantic_proof": True,
        },
        "rows": rows,
        "summary": {
            "status": "pass" if not high_uncovered else "review_required",
            "threat_count": len(rows),
            "covered_count": sum(1 for row in rows if row["manuscript_covered"]),
            "uncovered_count": len(uncovered),
            "high_uncovered_count": len(high_uncovered),
            "publication_verification_status": verification["summary"]["status"],
        },
        "interpretation": (
            "This is a static text-integration audit. Passing rows mean the draft contains visible wording cues for "
            "the limitation; authors still need to preserve the same boundaries in the final journal template."
        ),
    }


def write_csv(report, path):
    fields = [
        "threat_id",
        "domain",
        "severity",
        "threat_status",
        "manuscript_covered",
        "required_terms",
        "matched_terms",
        "matched_locations",
        "residual_risk",
        "prohibited_claim",
        "recommended_manuscript_action",
        "evidence",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow(row)


def write_markdown(report, path):
    lines = [
        "# Manuscript Limitation Integration Audit",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Status: `{report['summary']['status']}`",
        f"- Threats checked: {report['summary']['threat_count']}",
        f"- Covered: {report['summary']['covered_count']}",
        f"- Uncovered: {report['summary']['uncovered_count']}",
        f"- High-severity uncovered: {report['summary']['high_uncovered_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        "",
        "## Rows",
        "",
        "| threat | severity | covered | matched terms | locations | manuscript action |",
        "|---|---|---:|---|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['threat_id']} | {row['severity']} | {row['manuscript_covered']} | "
            f"{row['matched_terms']} | {row['matched_locations']} | {row['recommended_manuscript_action']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export manuscript limitation integration audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.json"
    out_md = materials / "MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.md"
    out_csv = materials / "MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
