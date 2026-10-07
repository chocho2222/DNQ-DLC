#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def row(section, row_id, text, evidence, boundary, status="ready", note=""):
    return {
        "section": section,
        "id": row_id,
        "text": text,
        "evidence": evidence,
        "boundary": boundary,
        "status": status,
        "note": note,
    }


def word_count(text):
    return len(text.replace("/", " ").replace("-", " ").split())


def build_package(root):
    outline = load_json(root / "materials" / "MANUSCRIPT_OUTLINE.json")
    summary = load_json(root / "materials" / "PUBLICATION_PACKAGE_SUMMARY.json")
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    triage = load_json(root / "materials" / "EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.json")
    replication = load_json(root / "materials" / "REVIEWER_REPLICATION_ROUTE.json")
    assembly = load_json(root / "materials" / "MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.json")
    reference = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_PACKAGE_MAP.json")
    provenance_label = f"{provenance['complete_count']}/{len(provenance['artifacts'])}"

    main = summary["main_results"]
    abstract = outline["abstract"]

    title_rows = [
        row(
            "title",
            "T1_recommended",
            "Strict Simulator Full-lap Evaluation Reveals Complementarity and Generalization Limits in Multi-car Overtaking",
            "materials/MANUSCRIPT_OUTLINE.md; materials/EDITORIAL_NARRATIVE_PACKAGE.md",
            "Emphasizes evaluation, complementarity, and limits rather than broad robustness.",
        ),
        row(
            "title",
            "T2_method_focused",
            "Online Portfolio Probing for Simulator Multi-car Overtaking Under Held-out Track Variation",
            "tables/heldout_generalization.md; tables/cross_heldout_validation_synthesis.md",
            "Use only if the journal prefers a method-forward title; still report held-out limits in the abstract.",
        ),
        row(
            "title",
            "T3_reproducibility_focused",
            "A Reproducible Strict Simulator Benchmark for Multi-car Overtaking with Online Controller Selection",
            "materials/REPRODUCTION_GUIDE.md; tables/artifact_provenance.md",
            "Use only if the manuscript is positioned as benchmark/evidence infrastructure.",
        ),
    ]

    structured_abstract = [
        row(
            "abstract",
            "A1_background",
            abstract["background"],
            "materials/METHODS.md; materials/EDITORIAL_NARRATIVE_PACKAGE.md",
            "Do not imply real-road or perception-stack evidence.",
        ),
        row(
            "abstract",
            "A2_methods",
            abstract["methods"],
            "materials/METHODS.md; materials/STUDY_PROTOCOL_AND_DEVIATIONS.md",
            "Keep non-VLM and simulator-state scope explicit.",
        ),
        row(
            "abstract",
            "A3_results",
            abstract["results"],
            "tables/full_statistical_report.md; tables/heldout_generalization.md; tables/heldout3_external_validation.md; tables/heldout4_external_validation.md",
            "Report locked, heldout1, heldout2, heldout3, and heldout4 together.",
        ),
        row(
            "abstract",
            "A4_conclusion",
            abstract["conclusion"],
            "tables/cross_heldout_validation_synthesis.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "Frame online portfolio probing as promising but not broadly robust.",
        ),
    ]

    highlights = [
        row(
            "highlight",
            "H1_strict_endpoint",
            "Strict simulator full-lap validation exposes completion, rank, off-track, and traffic-quality failures hidden by short rollouts.",
            "materials/METHODS.md; materials/STATISTICAL_ANALYSIS_PLAN.md",
            "Simulation-only evidence.",
        ),
        row(
            "highlight",
            "H2_strong_baseline",
            f"In the simulator benchmark, the preserved rule overtake baseline reaches {main['locked_rule_overtake']}, while graph-adaptive shielding reaches {main['locked_graph_adaptive']}.",
            "tables/full_statistical_report.md; materials/BASELINE_FAIRNESS_AUDIT.md",
            "Do not claim the learned/shielded method surpasses the strongest locked baseline.",
        ),
        row(
            "highlight",
            "H3_selector",
            f"Online portfolio probing reaches {main['heldout1_expanded_selector']} on heldout1 and {main['heldout2_expanded_selector']} on heldout2 after candidate expansion.",
            "tables/expanded_selector_generalization.md; tables/heldout_generalization.md",
            "Selector performance is not a zero-cost single-controller result.",
        ),
        row(
            "highlight",
            "H4_external_limits",
            f"Generalization remains limited: heldout3 diagnostic stress performance is {main['heldout3_expanded_selector']} and heldout4 post-repair transfer is {main['heldout4_selector']}.",
            "tables/heldout3_external_validation.md; tables/heldout4_external_validation.md",
            "Heldout3 is a diagnostic stress boundary; heldout4 is partial post-repair transfer.",
        ),
        row(
            "highlight",
            "H5_reproducibility",
            (
                f"The local simulator-evidence package passes publication preflight with artifact provenance {provenance_label}, "
                f"{replication['summary']['quickstart_count']} reviewer quickstart checks, and "
                f"{assembly['summary']['evidence_route_count']} manuscript evidence routes."
            ),
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md; materials/REVIEWER_REPLICATION_ROUTE.md; materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md",
            "Local package readiness and reviewer quickstarts are not an external archive DOI or journal submission receipt.",
        ),
    ]

    plain_language = [
        row(
            "plain_language_summary",
            "PL1",
            (
                "Short racing demonstrations can look successful even when a car fails to finish a lap, leaves the track, "
                "or does not truly overtake traffic. This package tests multi-car overtaking over full laps with strict "
                "success rules and compares hand-designed baselines, learned graph policies, safety shields, and an online "
                "selector that probes several candidate controllers before committing."
            ),
            "materials/METHODS.md; figures/figure_1_multicar_overtake_results.*",
            "For general readers; still simulator-only.",
        ),
        row(
            "plain_language_summary",
            "PL2",
            (
                "The online selector is promising because different controllers solve different seeds, but the results also "
                "show clear limits. Some held-out tracks and traffic settings still fail, and diagnostic oracle portfolios "
                "are not online selector outputs. The main contribution is therefore a transparent simulator benchmark and "
                "evidence package, not a claim of solved or road-ready overtaking."
            ),
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md; materials/CLAIM_EVIDENCE_MATRIX.md",
            "Do not convert this into a deployment-readiness statement.",
        ),
    ]

    keywords = [
        row("keyword", "K1", "multi-car overtaking", "materials/METHODS.md", "Simulator task scope."),
        row("keyword", "K2", "online portfolio selection", "tables/expanded_selector_generalization.md", "Selector is probe-based and simulator-bound."),
        row("keyword", "K3", "full-lap validation", "materials/STATISTICAL_ANALYSIS_PLAN.md", "Strict endpoint, not visual-only evidence."),
        row("keyword", "K4", "graph policy", "materials/POLICY_MODEL_CARD.md", "Telemetry/state graph actor, not VLM perception."),
        row("keyword", "K5", "simulator reproducibility", "tables/artifact_provenance.md", "Local package readiness with archive DOI pending."),
    ]

    prohibited = [
        row("prohibited_wording", "P1", "Robust autonomous overtaking is solved.", "materials/CLAIM_EVIDENCE_MATRIX.md", "Unsupported by heldout3/heldout4 and sample size."),
        row("prohibited_wording", "P2", "The oracle portfolio is an online selector output.", "tables/portfolio_oracle.md", "Oracle is a diagnostic upper bound only."),
        row("prohibited_wording", "P3", "The package demonstrates real-road or perception-stack readiness.", "materials/SIMULATION_TO_REAL_APPLICABILITY.md", "No real-road, sensor, VLM, or safety-certification evidence."),
        row("prohibited_wording", "P4", "Heldout3-targeted repair is external validation.", "tables/heldout3_candidate_expansion.md", "Targeted repair is diagnostic."),
        row("prohibited_wording", "P5", "Heldout4 partial transfer proves broad generalization.", "tables/heldout4_external_validation.md", "Heldout4 still has selector misses and candidate gaps."),
    ]

    rows = title_rows + structured_abstract + highlights + plain_language + keywords + prohibited
    return {
        "root": str(root),
        "title": "Title, abstract, highlights, and plain-language package",
        "purpose": "Provide submission-ready short-form manuscript text constrained by saved evidence and claim guardrails.",
        "title_options": title_rows,
        "structured_abstract": structured_abstract,
        "highlights": highlights,
        "plain_language_summary": plain_language,
        "keywords": keywords,
        "prohibited_wording": prohibited,
        "summary": {
            "row_count": len(rows),
            "title_count": len(title_rows),
            "abstract_section_count": len(structured_abstract),
            "highlight_count": len(highlights),
            "plain_language_paragraph_count": len(plain_language),
            "keyword_count": len(keywords),
            "prohibited_wording_count": len(prohibited),
            "abstract_word_count": sum(word_count(item["text"]) for item in structured_abstract),
            "plain_language_word_count": sum(word_count(item["text"]) for item in plain_language),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": provenance_label,
            "statistical_consistency_status": stats["summary"]["status"],
            "claim_qa_status": load_json(root / "materials" / "MANUSCRIPT_CLAIM_QA.json")["summary"]["status"],
            "triage_checklist_count": triage["summary"]["checklist_count"],
            "reviewer_quickstart_count": replication["summary"]["quickstart_count"],
            "manuscript_evidence_route_count": assembly["summary"]["evidence_route_count"],
            "reference_status": reference["summary"]["status"],
            "portal_author_action_count": portal["summary"]["author_action_count"],
        },
        "rows": rows,
        "interpretation": (
            "These short-form texts are ready as evidence-bound drafts. Authors still need to adapt them to the selected "
            "journal's word limits and complete archive DOI, author metadata, disclosures, and related-work expansion."
        ),
    }


def write_csv(report, path):
    fields = ["section", "id", "text", "evidence", "boundary", "status", "note"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow(item)


def write_markdown(report, path):
    lines = [
        "# Title, Abstract, Highlights, and Plain-language Package",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Recommended Title",
        "",
        report["title_options"][0]["text"],
        "",
        "## Structured Abstract",
        "",
    ]
    for item in report["structured_abstract"]:
        label = item["id"].split("_", 1)[1].title()
        lines.append(f"**{label}:** {item['text']}")
        lines.append("")
    lines.extend(["## Highlights", ""])
    lines.extend(f"- {item['text']}" for item in report["highlights"])
    lines.extend(["", "## Plain-language Summary", ""])
    lines.extend(item["text"] + "\n" for item in report["plain_language_summary"])
    lines.extend(["## Keywords", ""])
    lines.append("; ".join(item["text"] for item in report["keywords"]))
    lines.extend(
        [
            "",
            "## Prohibited Wording",
            "",
        ]
    )
    lines.extend(f"- {item['text']} Boundary: {item['boundary']}" for item in report["prohibited_wording"])
    lines.extend(
        [
            "",
            "## Evidence Map",
            "",
            "| section | id | evidence | boundary |",
            "|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(f"| {item['section']} | {item['id']} | `{item['evidence']}` | {item['boundary']} |")
    lines.extend(
        [
            "",
            "## Snapshot",
            "",
            f"- Publication verification: `{report['summary']['publication_verification_status']}`",
            f"- Artifact provenance: {report['summary']['artifact_provenance']}",
            f"- Statistical consistency: `{report['summary']['statistical_consistency_status']}`",
            f"- Claim QA: `{report['summary']['claim_qa_status']}`",
            f"- Reviewer quickstart checks: {report['summary']['reviewer_quickstart_count']}",
            f"- Manuscript evidence routes: {report['summary']['manuscript_evidence_route_count']}",
            f"- Abstract word count: {report['summary']['abstract_word_count']}",
            f"- Plain-language word count: {report['summary']['plain_language_word_count']}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export title, abstract, highlights, and plain-language package.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_package(root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    out_json = materials / "TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json"
    out_md = materials / "TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md"
    out_csv = materials / "TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
