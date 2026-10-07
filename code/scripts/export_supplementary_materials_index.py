#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def exists_size(root, rel_path):
    path = root / rel_path
    return path.exists(), path.stat().st_size if path.exists() and path.is_file() else None


def row(item_id, upload_group, display_label, file_type, rel_path, source, role, claim_boundary, priority):
    return {
        "id": item_id,
        "upload_group": upload_group,
        "display_label": display_label,
        "file_type": file_type,
        "path": rel_path,
        "source": source,
        "role": role,
        "claim_boundary": claim_boundary,
        "priority": priority,
    }


def reviewer_use_for(item):
    group = item["upload_group"]
    if group == "supplementary_table":
        return "Use to verify seed-level evidence, statistical summaries, audit rows, or reporting controls behind manuscript claims."
    if group == "source_data":
        return "Use as machine-readable source data for reproducing or checking figure panels and plotted values."
    if group == "supplementary_analysis":
        return "Use to navigate claim boundaries, reviewer risks, author actions, and pre-submission audit evidence."
    if group == "archive":
        return "Use for public deposition, checksum review, FAIR metadata, and data/code availability verification."
    return "Use as supporting material only after checking the claim boundary."


def upload_condition_for(item):
    priority = item["priority"]
    group = item["upload_group"]
    if priority == "required_supplement":
        return "Include in the core supplementary information or an equivalent consolidated supplement unless the target journal requires a different format."
    if priority == "required_source_data":
        return "Upload through the journal source-data channel when available, or include in the public archive with explicit figure linkage."
    if priority == "required_archive":
        return "Include in the public archive/deposition package and update DOI/URL/accession after external deposition."
    if priority == "recommended_supplement":
        return "Upload as reviewer support when size, anonymity, and journal-supplement limits allow; otherwise retain in the archive and cite from the navigator."
    if group == "supplementary_analysis":
        return "Treat as optional reviewer-support material unless requested by the journal or needed for response preparation."
    return "Decide after target-journal supplement and upload rules are fixed."


def build_index(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    data_dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    figure_audit = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    final_bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")

    rows = [
        row(
            "ST1",
            "supplementary_table",
            "Supplementary Table 1. Experiment registry and seed-set roles",
            "csv",
            "materials/EXPERIMENT_REGISTRY.csv",
            "materials/EXPERIMENT_REGISTRY.json",
            "Defines study stages, endpoints, seed partitions, evidence files, and allowed interpretations.",
            "Seed sets support simulator-only method evaluation; heldout3 targeted repair is diagnostic, not external validation.",
            "required_supplement",
        ),
        row(
            "ST2",
            "supplementary_table",
            "Supplementary Table 2. Seed-level selector outcome ledger",
            "csv",
            "tables/seed_outcome_ledger.csv",
            "tables/seed_outcome_ledger.json",
            "Per-seed selector/oracle outcomes, failures, candidate gaps, and selector misses.",
            "Oracle rows are diagnostic upper bounds, not online selector outputs.",
            "required_supplement",
        ),
        row(
            "ST3",
            "supplementary_table",
            "Supplementary Table 3. Cross-heldout validation synthesis",
            "csv",
            "tables/cross_heldout_validation_synthesis_rows.csv",
            "tables/cross_heldout_validation_synthesis.json",
            "Cross-heldout summary used for the main generalization figure and boundary claims.",
            "Supports partial simulator transfer only; does not support broad robustness or real-road claims.",
            "required_supplement",
        ),
        row(
            "ST4",
            "supplementary_table",
            "Supplementary Table 4. Cross-heldout statistical supplement",
            "csv",
            "tables/cross_heldout_statistical_supplement_rows.csv",
            "tables/cross_heldout_statistical_supplement.json",
            "Wilson intervals and paired selector-oracle tests for heldout stages.",
            "Small seed batches are descriptive and should not be framed as population-level proof.",
            "required_supplement",
        ),
        row(
            "ST5",
            "supplementary_table",
            "Supplementary Table 5. Endpoint sensitivity rows",
            "csv",
            "materials/ENDPOINT_SENSITIVITY_SCENARIO_ROWS.csv",
            "materials/ENDPOINT_SENSITIVITY_AUDIT.json",
            "Nearby endpoint-threshold grid computed from saved rollout summaries.",
            "Sensitivity is local to predefined thresholds and does not replace new validation rollouts.",
            "required_supplement",
        ),
        row(
            "ST6",
            "supplementary_table",
            "Supplementary Table 6. Selector decision audit",
            "csv",
            "materials/SELECTOR_DECISION_AUDIT_ROWS.csv",
            "materials/SELECTOR_DECISION_AUDIT.json",
            "Per-seed replay of online selector decisions from probe-only fields.",
            "Audits saved selector transparency, not optimality or out-of-distribution safety.",
            "required_supplement",
        ),
        row(
            "ST7",
            "supplementary_table",
            "Supplementary Table 7. Negative results and failure register",
            "csv",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.csv",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "Negative controls, selector misses, candidate gaps, and failure-mode boundaries retained for reviewers.",
            "Failure rows must remain visible and cannot be omitted to strengthen headline claims.",
            "required_supplement",
        ),
        row(
            "ST8",
            "supplementary_table",
            "Supplementary Table 8. Baseline fairness audit",
            "csv",
            "materials/BASELINE_FAIRNESS_AUDIT.csv",
            "materials/BASELINE_FAIRNESS_AUDIT.json",
            "Baseline preservation, common validator, common seeds, and fairness controls.",
            "Does not imply the proposed method uniformly dominates all baselines.",
            "required_supplement",
        ),
        row(
            "ST9",
            "supplementary_table",
            "Supplementary Table 9. Sample-size sensitivity and planning",
            "csv",
            "materials/SAMPLE_SIZE_SENSITIVITY_PLANNING_GRID.csv",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "Planning grid for larger confirmatory seed batches and Wilson-interval precision.",
            "Planning material only; future heldout5/larger-N results are not implied by current evidence.",
            "recommended_supplement",
        ),
        row(
            "ST10",
            "supplementary_table",
            "Supplementary Table 10. Compute-cost selector and rollout accounting",
            "csv",
            "tables/compute_cost_selector_rows.csv",
            "tables/compute_cost_report.json",
            "Selector probe counts, committed decisions, and simulated probe-step costs.",
            "Wall-clock/utilization are not complete for historical runs unless explicitly logged.",
            "recommended_supplement",
        ),
        row(
            "SD1",
            "source_data",
            "Source Data Fig. 1. Main method and baseline results",
            "csv",
            "figures/figure_1_source_data.csv",
            "figures/figure_manifest.json",
            "Machine-readable source data for Figure 1.",
            "Figure source data inherit the strict simulator-only endpoint boundary.",
            "required_source_data",
        ),
        row(
            "SD2",
            "source_data",
            "Source Data Fig. 2. Portfolio selector summary",
            "csv",
            "figures/figure_2_source_data.csv",
            "figures/figure_2_manifest.json",
            "Machine-readable source data for Figure 2.",
            "Selector comparisons separate online simulator-loop selector rows from diagnostic oracle rows.",
            "required_source_data",
        ),
        row(
            "SD3",
            "source_data",
            "Source Data Fig. 3. Cross-heldout validation",
            "csv",
            "figures/figure_3_source_data.csv",
            "figures/figure_3_manifest.json",
            "Machine-readable source data for Figure 3.",
            "Cross-heldout aggregate is simulator validation evidence, not real-world robustness.",
            "required_source_data",
        ),
        row(
            "SD4",
            "source_data",
            "Source Data dictionary for Figure 3",
            "csv",
            "figures/figure_3_source_data_dictionary.csv",
            "figures/figure_3_manifest.json",
            "Field definitions for Figure 3 source data.",
            "Complements the package-wide data dictionary.",
            "required_source_data",
        ),
        row(
            "SA1",
            "supplementary_analysis",
            "Supplementary analysis. Claim evidence matrix",
            "markdown",
            "materials/CLAIM_EVIDENCE_MATRIX.md",
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "Allowed/prohibited claims mapped to evidence and limitations.",
            "Final manuscript and cover-letter language must remain inside these boundaries.",
            "required_supplement",
        ),
        row(
            "SA1b",
            "supplementary_analysis",
            "Supplementary analysis. Claim downgrade and do-not-claim guardrails",
            "markdown",
            "materials/CLAIM_DOWNGRADE_MAP.md",
            "materials/CLAIM_BOUNDARY_COMMUNICATION_PACK.json",
            "Maps risky overclaims to evidence-bounded replacement wording and links to the one-page do-not-claim guardrail.",
            "Communication guardrails add no new empirical evidence and must be rerun after text edits.",
            "required_supplement",
        ),
        row(
            "SA2",
            "supplementary_analysis",
            "Supplementary analysis. Reviewer risk-response dossier",
            "markdown",
            "materials/REVIEWER_RISK_RESPONSE_DOSSIER.md",
            "materials/REVIEWER_RISK_RESPONSE_DOSSIER.json",
            "Likely reviewer questions mapped to evidence, response wording, and boundaries.",
            "Response wording is author-adapted support, not a substitute for final peer-review responses.",
            "recommended_supplement",
        ),
        row(
            "SA2b",
            "supplementary_analysis",
            "Supplementary analysis. Reviewer response seed pack",
            "markdown",
            "materials/REVIEWER_RESPONSE_SEED_PACK.md",
            "materials/REVIEWER_RESPONSE_SEED_PACK.json",
            "Journal-neutral response seeds for likely editor/reviewer critiques with evidence routes and claim boundaries.",
            "Response seeds are preparation aids, not author-certified rebuttal text or new empirical evidence.",
            "recommended_supplement",
        ),
        row(
            "SA2c",
            "supplementary_analysis",
            "Supplementary analysis. Revision response execution checklist",
            "markdown",
            "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.md",
            "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.json",
            "Revision actions, manuscript line placeholders, evidence routes, and claim-boundary locks for likely reviewer critiques.",
            "Checklist is not final rebuttal text; authors must add line references after revision.",
            "recommended_supplement",
        ),
        row(
            "SA2d",
            "supplementary_analysis",
            "Supplementary analysis. Portal copyedit lock audit",
            "markdown",
            "materials/PORTAL_COPYEDIT_LOCK_AUDIT.md",
            "materials/PORTAL_COPYEDIT_LOCK_AUDIT.json",
            "Conservative overclaim scan for title, abstract, highlights, cover-letter, narrative, and portal-field draft text.",
            "Audit pass applies only to saved drafts and does not certify final author-edited portal text.",
            "recommended_supplement",
        ),
        row(
            "SA2e",
            "supplementary_analysis",
            "Supplementary analysis. Blinded review and anonymization audit",
            "markdown",
            "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.md",
            "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.json",
            "Double-blind/single-blind readiness decisions for reviewer-facing materials, editor-only files, metadata, archive identifiers, and local paths.",
            "Audit does not anonymize files automatically and does not certify a target journal's policy.",
            "recommended_supplement",
        ),
        row(
            "SA2f",
            "supplementary_analysis",
            "Supplementary analysis. AI and tool-use disclosure audit",
            "markdown",
            "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.md",
            "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.json",
            "Journal-neutral audit separating package-supported automation facts from author-certified AI/tool-use declarations.",
            "Audit does not certify private author AI/tool use or replace target-journal disclosure forms.",
            "recommended_supplement",
        ),
        row(
            "SA2g",
            "supplementary_analysis",
            "Supplementary analysis. Final author handoff checklist",
            "markdown",
            "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.md",
            "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.json",
            "Author-facing upload sequence linking remaining author actions, acceptance criteria, evidence files, and rerun commands.",
            "Checklist indicates local handoff readiness only; authors must still certify metadata, disclosures, journal-specific formatting, and external identifiers.",
            "recommended_supplement",
        ),
        row(
            "SA2h",
            "supplementary_analysis",
            "Supplementary analysis. Confirmatory freeze audit",
            "markdown",
            "materials/CONFIRMATORY_FREEZE_AUDIT.md",
            "materials/CONFIRMATORY_FREEZE_AUDIT.json",
            "Frozen heldout5/larger-N selector template audit covering seed disjointness, candidate models, prohibited oracle fields, GPU policy, and not-executed boundaries.",
            "This is a future-run lock and audit, not evidence that heldout5, larger-N, traffic-density, or opponent-diversity results already exist.",
            "recommended_supplement",
        ),
        row(
            "SA2i",
            "supplementary_analysis",
            "Supplementary analysis. Confirmatory roadmap and claim-upgrade gates",
            "markdown",
            "materials/CONFIRMATORY_ROADMAP.md",
            "materials/CONFIRMATORY_ROADMAP.json",
            "Maps unresolved top-journal readiness gaps to frozen controls, required future evidence, decision gates, failure reporting, GPU execution, and conservative claim-upgrade boundaries.",
            "This is a future-experiment roadmap and not evidence that heldout5, larger-N, traffic-density, opponent-diversity, or cheaper-selector results already exist.",
            "recommended_supplement",
        ),
        row(
            "SA2j",
            "supplementary_analysis",
            "Supplementary analysis. Claim decision tree and upgrade/downgrade gates",
            "markdown",
            "materials/CLAIM_DECISION_TREE.md",
            "materials/CLAIM_DECISION_TREE.json",
            "Maps saved evidence and future-experiment gates to allowed, downgraded, diagnostic-only, or prohibited manuscript claims.",
            "This is a claim-control and reviewer-navigation artifact; it adds no new empirical evidence and cannot upgrade claims without fresh validation.",
            "recommended_supplement",
        ),
        row(
            "SA2k",
            "supplementary_analysis",
            "Supplementary analysis. Failure-mode atlas summary",
            "markdown",
            "materials/FAILURE_MODE_ATLAS_SUMMARY.md",
            "materials/FAILURE_MODE_ATLAS_SUMMARY.json",
            "Compresses heldout2, heldout3, heldout3-targeted, and heldout4 failures into reviewer-facing selector-miss, candidate-gap, diagnostic-reuse, and partial-transfer rows.",
            "This summary adds no new empirical evidence; it is a cross-heldout interpretation aid that must remain aligned with the saved failure atlases and claim boundaries.",
            "recommended_supplement",
        ),
        row(
            "SA3",
            "supplementary_analysis",
            "Supplementary analysis. Related-work positioning matrix",
            "markdown",
            "materials/RELATED_WORK_POSITIONING_MATRIX.md",
            "materials/RELATED_WORK_POSITIONING_MATRIX.json",
            "Citation areas, local evidence, positioning, and novelty boundaries.",
            "Final citation style and breadth remain author-reviewed.",
            "recommended_supplement",
        ),
        row(
            "ARCH1",
            "archive",
            "Archive manifest with checksums and file categories",
            "markdown",
            "materials/RELEASE_ARCHIVE_MANIFEST.md",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "File-count, size, and archive-layout manifest for public deposition.",
            "Local archive is prepared; public DOI/accession remains author-owned until deposition.",
            "required_archive",
        ),
        row(
            "ARCH2",
            "archive",
            "FAIR archive metadata draft",
            "markdown",
            "materials/FAIR_ARCHIVE_METADATA.md",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "DataCite/Zenodo-style metadata draft for public repository upload.",
            "Repository DOI/URL/accession must be inserted after external deposition.",
            "required_archive",
        ),
        row(
            "ARCH3",
            "archive",
            "Data and code availability rows",
            "csv",
            "materials/DATA_CODE_AVAILABILITY.csv",
            "materials/DATA_CODE_AVAILABILITY.json",
            "Machine-readable data/code availability statements, package locations, reproduction entry points, and archive boundaries.",
            "Local availability rows require public DOI/URL/accession insertion after deposition.",
            "required_archive",
        ),
    ]

    release_paths = {item["path"] for item in release["files"]}
    enriched = []
    for item in rows:
        exists, size = exists_size(root, item["path"])
        source_exists, _ = exists_size(root, item["source"])
        release_required = item["upload_group"] != "archive"
        release_ready = item["path"] in release_paths if release_required else True
        author_selection_ready = (
            item["upload_group"] == "supplementary_analysis"
            and item["priority"] == "recommended_supplement"
            and exists
            and source_exists
        )
        status = (
            "ready"
            if exists and source_exists and release_ready
            else "ready_with_author_selection"
            if author_selection_ready
            else "review_required"
        )
        enriched.append(
            {
                **item,
                "reviewer_use": reviewer_use_for(item),
                "upload_condition": upload_condition_for(item),
                "exists": exists,
                "source_exists": source_exists,
                "in_release_manifest": item["path"] in release_paths,
                "size_bytes": size,
                "status": status,
            }
        )

    missing_required = [
        item for item in enriched if item["priority"].startswith("required") and item["status"] == "review_required"
    ]
    review_required = [item for item in enriched if item["status"] == "review_required"]
    author_selection = [item for item in enriched if item["status"] == "ready_with_author_selection"]
    return {
        "root": str(root),
        "title": "Supplementary materials and source-data index",
        "purpose": (
            "Map reviewer-facing supplementary tables, analyses, source-data files, and archive files "
            "to authoritative local evidence and conservative claim boundaries."
        ),
        "scope": {
            "not_final_journal_numbering": True,
            "author_action_boundary": (
                "Journal-specific numbering, template conversion, and upload-slot selection remain author actions."
            ),
            "package_upload_boundary": final_bundle["scope"]["author_action_boundary"],
        },
        "items": enriched,
        "summary": {
            "item_count": len(enriched),
            "ready_count": sum(1 for item in enriched if item["status"] == "ready"),
            "review_required_count": len(review_required),
            "author_selection_required_count": len(author_selection),
            "required_review_required_count": len(missing_required),
            "source_data_item_count": sum(1 for item in enriched if item["upload_group"] == "source_data"),
            "supplementary_table_count": sum(1 for item in enriched if item["upload_group"] == "supplementary_table"),
            "figure_count": figure_audit["summary"]["figure_count"],
            "data_dictionary_complete": data_dictionary["summary"]["complete"],
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "submission_dashboard_review_required": dashboard["summary"]["review_required_row_count"],
        },
        "interpretation": (
            "This index is a pre-submission navigation and upload-planning artifact. It does not create new "
            "experimental claims and should be updated after target-journal formatting choices are made."
        ),
    }


def write_csv(report, path):
    fields = [
        "id",
        "upload_group",
        "display_label",
        "file_type",
        "path",
        "source",
        "role",
        "claim_boundary",
        "priority",
        "exists",
        "source_exists",
        "in_release_manifest",
        "size_bytes",
        "status",
        "reviewer_use",
        "upload_condition",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["items"]:
            writer.writerow({field: item[field] for field in fields})


def write_markdown(report, path):
    lines = [
        "# Supplementary Materials and Source-Data Index",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Items: {report['summary']['item_count']}",
        f"- Ready: {report['summary']['ready_count']}",
        f"- Review required: {report['summary']['review_required_count']}",
        f"- Author-selection required: {report['summary']['author_selection_required_count']}",
        f"- Required review required: {report['summary']['required_review_required_count']}",
        f"- Source-data items: {report['summary']['source_data_item_count']}",
        f"- Supplementary-table items: {report['summary']['supplementary_table_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- Data dictionary complete: {report['summary']['data_dictionary_complete']}",
        "",
        "## Items",
        "",
        "| id | group | label | status | priority | file | source | reviewer use | upload condition | role | boundary |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in report["items"]:
        lines.append(
            f"| {item['id']} | {item['upload_group']} | {item['display_label']} | {item['status']} | "
            f"{item['priority']} | `{item['path']}` | `{item['source']}` | {item['reviewer_use']} | "
            f"{item['upload_condition']} | {item['role']} | {item['claim_boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export supplementary materials and source-data index.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_index(root)
    out_json = materials / "SUPPLEMENTARY_MATERIALS_INDEX.json"
    out_md = materials / "SUPPLEMENTARY_MATERIALS_INDEX.md"
    out_csv = materials / "SUPPLEMENTARY_MATERIALS_INDEX.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
