#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


ABSTRACT = "outputs/tits_dynamic_graph/tits_manuscript_package/materials/ABSTRACT_HIGHLIGHTS_DRAFT.md"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
SECTION_TRACE = "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/tits_manuscript_section_trace_audit_manifest.json"
CLAIM_LANGUAGE = "outputs/tits_dynamic_graph/tits_claim_language_audit/tits_claim_language_audit_manifest.json"
RESULTS_REPORTING = "outputs/tits_dynamic_graph/tits_results_reporting_checklist/tits_results_reporting_checklist_manifest.json"
RESULTS_NARRATIVE = "outputs/tits_dynamic_graph/tits_results_narrative_pack/tits_results_narrative_pack_manifest.json"
FIGURE_CAPTION = "outputs/tits_dynamic_graph/tits_figure_caption_claim_audit/tits_figure_caption_claim_audit_manifest.json"
GIF_PROVENANCE = "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/tits_publication_gif_provenance_audit_manifest.json"
REVIEWER_PACKET = "outputs/tits_dynamic_graph/reviewer_replication_packet/reviewer_replication_packet_manifest.json"
ARTIFACT = "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json"
REPRO_CAPSULE = "outputs/tits_dynamic_graph/tits_reproducibility_capsule/tits_reproducibility_capsule_manifest.json"
INNOVATION_TRACE = "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tits_innovation_evidence_traceability_manifest.json"

FORBIDDEN_PHRASES = [
    "real-world deployment",
    "certified safety",
    "guarantees",
    "solves autonomous overtaking",
    "arbitrary traffic",
    "unlimited traffic",
]


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path):
    path = Path(path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def source_facts(rows):
    cases = {
        (
            row.get("_benchmark"),
            row.get("seed"),
            row.get("num_agents"),
            row.get("track_path"),
            row.get("traffic_profile"),
        )
        for row in rows
    }
    return {
        "source_rows": len(rows),
        "matched_case_count": len(cases),
        "algorithm_count": len({row.get("algorithm") for row in rows if row.get("algorithm")}),
        "benchmarks": sorted({row.get("_benchmark", "") for row in rows if row.get("_benchmark")}),
        "vehicle_counts": sorted({row.get("num_agents", "") for row in rows if row.get("num_agents")}, key=lambda x: int(x or 0)),
    }


def has_all(text, phrases):
    lowered = text.lower()
    return all(phrase.lower() in lowered for phrase in phrases)


def build_claim_rows(root, text, facts):
    manifests = {
        "section_trace": read_json(root / SECTION_TRACE),
        "claim_language": read_json(root / CLAIM_LANGUAGE),
        "results_reporting": read_json(root / RESULTS_REPORTING),
        "results_narrative": read_json(root / RESULTS_NARRATIVE),
        "figure_caption": read_json(root / FIGURE_CAPTION),
        "gif_provenance": read_json(root / GIF_PROVENANCE),
        "reviewer_packet": read_json(root / REVIEWER_PACKET),
        "artifact": read_json(root / ARTIFACT),
        "repro_capsule": read_json(root / REPRO_CAPSULE),
        "innovation_trace": read_json(root / INNOVATION_TRACE),
    }
    claims = [
        {
            "claim_id": "AH01",
            "claim_area": "problem_and_method",
            "abstract_signal": "fixed interaction structure; runtime dynamic-neighborhood graph construction",
            "required_text": ["fixed interaction structure", "runtime dynamic-neighborhood graph construction"],
            "required_evidence": [INNOVATION_TRACE, SECTION_TRACE],
            "evidence_status": [manifests["innovation_trace"].get("status"), manifests["section_trace"].get("status")],
            "expected": "method motivation and dynamic-neighborhood contribution are present and traceable",
        },
        {
            "claim_id": "AH02",
            "claim_area": "benchmark_scope",
            "abstract_signal": "240-run online confirmatory matrix; procedural, 8-vehicle, Monza external track",
            "required_text": ["240-run", "procedural", "8-vehicle", "Monza"],
            "required_evidence": [SOURCE_DATA, REPRO_CAPSULE],
            "evidence_status": ["pass" if facts["source_rows"] == 240 and facts["matched_case_count"] == 30 and "8" in facts["vehicle_counts"] else "review_required", manifests["repro_capsule"].get("status")],
            "expected": "abstract benchmark scope matches formal source data",
        },
        {
            "claim_id": "AH03",
            "claim_area": "primary_results",
            "abstract_signal": "improves success, desirable/on-track overtaking, and completion time vs original DLC",
            "required_text": ["improves overtake success", "desirable overtaking behavior", "on-track overtaking", "overtake completion time"],
            "required_evidence": [RESULTS_REPORTING, RESULTS_NARRATIVE],
            "evidence_status": [manifests["results_reporting"].get("status"), manifests["results_narrative"].get("status")],
            "expected": "primary result language is backed by Results reporting and narrative packs",
        },
        {
            "claim_id": "AH04",
            "claim_area": "visual_and_reproducibility_evidence",
            "abstract_signal": "paired tests, failure analysis, visual evidence, source data and checksums",
            "required_text": ["paired statistical tests", "failure-mode analysis", "visual evidence", "source data", "artifact checksums"],
            "required_evidence": [FIGURE_CAPTION, GIF_PROVENANCE, REVIEWER_PACKET, ARTIFACT],
            "evidence_status": [manifests["figure_caption"].get("status"), manifests["gif_provenance"].get("status"), "pass" if manifests["reviewer_packet"] else "review_required", manifests["artifact"].get("status")],
            "expected": "abstract reproducibility and visual-evidence claims route to local evidence",
        },
        {
            "claim_id": "AH05",
            "claim_area": "claim_boundary",
            "abstract_signal": "no real-world or arbitrary-density overclaim in abstract/highlights",
            "required_text": [],
            "required_evidence": [CLAIM_LANGUAGE],
            "evidence_status": [manifests["claim_language"].get("status")],
            "expected": "claim-language audit passes and forbidden phrases are absent",
        },
    ]
    lowered = text.lower()
    rows = []
    for claim in claims:
        missing_text = [phrase for phrase in claim["required_text"] if phrase.lower() not in lowered]
        missing_evidence = [
            evidence
            for evidence, status in zip(claim["required_evidence"], claim["evidence_status"])
            if status not in {"pass", "complete", "artifact_manifest_generated"}
        ]
        forbidden_hits = []
        if claim["claim_id"] == "AH05":
            forbidden_hits = [phrase for phrase in FORBIDDEN_PHRASES if phrase in lowered]
        status = "pass" if not missing_text and not missing_evidence and not forbidden_hits else "review_required"
        rows.append(
            {
                "claim_id": claim["claim_id"],
                "claim_area": claim["claim_area"],
                "abstract_signal": claim["abstract_signal"],
                "status": status,
                "missing_text": ";".join(missing_text),
                "missing_evidence": ";".join(missing_evidence),
                "forbidden_hits": ";".join(forbidden_hits),
                "expected": claim["expected"],
                "evidence": ";".join(claim["required_evidence"]),
            }
        )
    return rows


def build_checks(root, text, facts):
    section_trace = read_json(root / SECTION_TRACE)
    claim_language = read_json(root / CLAIM_LANGUAGE)
    checks = [
        {
            "check_id": "AH_file_exists",
            "category": "input_presence",
            "status": "pass" if (root / ABSTRACT).exists() and text.strip() else "review_required",
            "observed": "present" if text.strip() else "missing",
            "expected": "abstract/highlights draft exists and is nonempty",
            "evidence": ABSTRACT,
        },
        {
            "check_id": "AH_sections_present",
            "category": "structure",
            "status": "pass" if "## Abstract Draft" in text and "## Highlights" in text else "review_required",
            "observed": f"abstract={'## Abstract Draft' in text}; highlights={'## Highlights' in text}",
            "expected": "Abstract Draft and Highlights sections are present",
            "evidence": ABSTRACT,
        },
        {
            "check_id": "AH_highlight_count",
            "category": "structure",
            "status": "pass" if sum(1 for line in text.splitlines() if line.startswith("- ")) == 4 else "review_required",
            "observed": sum(1 for line in text.splitlines() if line.startswith("- ")),
            "expected": 4,
            "evidence": ABSTRACT,
        },
        {
            "check_id": "AH_source_scale",
            "category": "source_data",
            "status": "pass" if facts["source_rows"] == 240 and facts["matched_case_count"] == 30 and facts["algorithm_count"] == 8 else "review_required",
            "observed": f"rows={facts['source_rows']}; cases={facts['matched_case_count']}; algorithms={facts['algorithm_count']}; vehicles={','.join(facts['vehicle_counts'])}",
            "expected": "240 rows; 30 matched cases; 8 algorithms; vehicles include 8",
            "evidence": SOURCE_DATA,
        },
        {
            "check_id": "AH_upstream_language_and_trace",
            "category": "upstream_audit",
            "status": "pass" if section_trace.get("status") == "pass" and claim_language.get("status") == "pass" else "review_required",
            "observed": f"section_trace={section_trace.get('status')}; claim_language={claim_language.get('status')}",
            "expected": "section trace and claim-language audits pass",
            "evidence": f"{SECTION_TRACE};{CLAIM_LANGUAGE}",
        },
    ]
    return checks


def build_report(root):
    text = read_text(root / ABSTRACT)
    source_rows = read_csv(root / SOURCE_DATA)
    facts = source_facts(source_rows)
    claim_rows = build_claim_rows(root, text, facts)
    check_rows = build_checks(root, text, facts)
    issue_count = sum(1 for row in claim_rows + check_rows if row["status"] != "pass")
    summary = {
        "status": "pass" if issue_count == 0 else "review_required",
        "claim_count": len(claim_rows),
        "claim_issue_count": sum(1 for row in claim_rows if row["status"] != "pass"),
        "check_count": len(check_rows),
        "check_issue_count": sum(1 for row in check_rows if row["status"] != "pass"),
        "source_rows": facts["source_rows"],
        "matched_case_count": facts["matched_case_count"],
        "algorithm_count": facts["algorithm_count"],
        "vehicle_counts": ",".join(facts["vehicle_counts"]),
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "claim_rows": claim_rows,
        "check_rows": check_rows,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Abstract and Highlights Evidence Audit",
        "",
        "该审计检查摘要和 Highlights 中的核心声明是否有正式证据支撑、是否符合仿真边界、是否与 Results/图件/复现材料一致。它不改写摘要，只给出投稿前的证据映射。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Abstract Claim Map",
            "",
            "| Claim | Area | Status | Missing text | Missing evidence | Forbidden hits | Evidence |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["claim_rows"]:
        lines.append(
            f"| {row['claim_id']} | {row['claim_area']} | {row['status']} | {row['missing_text']} | "
            f"{row['missing_evidence']} | {row['forbidden_hits']} | `{row['evidence']}` |"
        )
    lines.extend(
        [
            "",
            "## Checklist",
            "",
            "| Check | Category | Status | Observed | Expected | Evidence |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["check_rows"]:
        lines.append(
            f"| {row['check_id']} | {row['category']} | {row['status']} | {row['observed']} | {row['expected']} | `{row['evidence']}` |"
        )
    lines.extend(
        [
            "",
            "## Writing Boundary",
            "",
            "- Abstract wording should remain bounded to simulation, 240 runs, 30 matched cases, 8 algorithms and evaluated 4/5/6/8-vehicle settings.",
            "- Do not imply real-vehicle deployment safety, arbitrary road-geometry generalization or unlimited traffic-density support.",
            "- If abstract or highlights are rewritten, rerun this audit, claim-language audit and freshness audit.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_abstract_highlights_evidence_audit.py --out-dir outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit abstract/highlights claims against formal T-ITS evidence.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit")
    args = parser.parse_args()
    root = Path(".").resolve()
    report = build_report(root)
    out_dir = Path(args.out_dir)
    paths = {
        "report_md": write_text(out_dir / "materials" / "ABSTRACT_HIGHLIGHTS_EVIDENCE_AUDIT.md", build_markdown(report)),
        "claim_csv": write_csv(
            out_dir / "tables" / "abstract_highlights_claim_map.csv",
            report["claim_rows"],
            ["claim_id", "claim_area", "abstract_signal", "status", "missing_text", "missing_evidence", "forbidden_hits", "expected", "evidence"],
        ),
        "check_csv": write_csv(
            out_dir / "tables" / "abstract_highlights_evidence_checks.csv",
            report["check_rows"],
            ["check_id", "category", "status", "observed", "expected", "evidence"],
        ),
        "report_json": write_json(out_dir / "materials" / "ABSTRACT_HIGHLIGHTS_EVIDENCE_AUDIT.json", report),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
        "boundary": "Abstract/highlights evidence audit only; it checks manuscript claim support and does not rerun simulations.",
    }
    manifest_path = write_json(out_dir / "tits_abstract_highlights_evidence_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
