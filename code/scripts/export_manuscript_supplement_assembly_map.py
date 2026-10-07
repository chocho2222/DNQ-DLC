#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def row(section, manuscript_location, claim_or_content, primary_files, supplement_files, upload_destination, author_action, boundary, status):
    return {
        "section": section,
        "manuscript_location": manuscript_location,
        "claim_or_content": claim_or_content,
        "primary_files": primary_files,
        "supplement_files": supplement_files,
        "upload_destination": upload_destination,
        "author_action": author_action,
        "boundary": boundary,
        "status": status,
    }


def evidence_route(route_id, manuscript_anchor, claim_scope, primary_evidence, supplement_evidence, source_data, boundary, reviewer_use, status):
    return {
        "route_id": route_id,
        "manuscript_anchor": manuscript_anchor,
        "claim_scope": claim_scope,
        "primary_evidence": primary_evidence,
        "supplement_evidence": supplement_evidence,
        "source_data": source_data,
        "boundary": boundary,
        "reviewer_use": reviewer_use,
        "status": status,
    }


def build_report(root):
    manifest = load_json(root / "manuscript" / "manuscript_manifest.json")
    cross_ref = load_json(root / "materials" / "MANUSCRIPT_CROSS_REFERENCE_AUDIT.json")
    source_package = load_json(root / "materials" / "MANUSCRIPT_SOURCE_PACKAGE_AUDIT.json")
    supplement = load_json(root / "materials" / "SUPPLEMENTARY_MATERIALS_INDEX.json")
    supplement_decision = load_json(root / "materials" / "SUPPLEMENT_UPLOAD_DECISION_MATRIX.json")
    table_legends = load_json(root / "materials" / "SUPPLEMENTARY_TABLE_LEGENDS.json")
    bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    upload = load_json(root / "materials" / "SUBMISSION_UPLOAD_SELECTION_PLAN.json")
    navigator = load_json(root / "materials" / "REPORTING_SUPPLEMENT_NAVIGATOR.json")
    replication = load_json(root / "materials" / "REVIEWER_REPLICATION_ROUTE.json")
    methods = load_json(root / "materials" / "METHODS_REPRODUCIBILITY_CAPSULE.json")
    ethics = load_json(root / "materials" / "ETHICS_DISCLOSURE_READINESS_PACK.json")
    figure_qc = load_json(root / "materials" / "FIGURE_TECHNICAL_QC.json")
    figure_source = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    statistical_appendix = load_json(root / "materials" / "STATISTICAL_REPORTING_APPENDIX.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    claim_qa = load_json(root / "materials" / "MANUSCRIPT_CLAIM_QA.json")
    narrative = load_json(root / "materials" / "NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.json")
    validity = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")

    rows = [
        row(
            "front_matter",
            "title_abstract_highlights",
            "Use evidence-bound short-form title, abstract, highlights, plain-language summary, and keywords.",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            "main_manuscript_or_portal_text",
            "Adapt to target journal word limits and style without adding unsupported claims.",
            "Short-form copy must retain simulator-only, no-broad-robustness, and diagnostic-oracle boundaries.",
            "ready_with_author_adaptation",
        ),
        row(
            "main_text",
            "introduction_related_work",
            "Position contribution as strict simulator-only full-lap evaluation with preserved baselines and explicit generalization limits.",
            "manuscript/main.md; materials/RELATED_WORK_POSITIONING_MATRIX.md",
            "materials/NOVELTY_POSITIONING_MATRIX.md; materials/SIGNIFICANCE_BRIEFING.md",
            "main_manuscript",
            "Author should review literature breadth and target-journal citation style.",
            "Do not imply real-road transfer, VLM autonomy, or champion-level racing performance.",
            "ready_with_author_review",
        ),
        row(
            "main_text",
            "methods",
            "Describe task, strict endpoint, seed partitions, methods, selector, compute, and reproducibility setup.",
            "manuscript/main.md; materials/METHODS_REPRODUCIBILITY_CAPSULE.md",
            "materials/EXPERIMENT_REGISTRY.csv; materials/SEED_PARTITION_AUDIT.md; materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
            "main_manuscript_and_supplement",
            "Convert capsule wording into selected journal Methods/Reporting Summary fields.",
            "Methods capsule summarizes saved evidence and does not enlarge the empirical scope.",
            methods["summary"]["status"],
        ),
        row(
            "main_text",
            "primary_results",
            "Report locked baseline, graph-adaptive, heldout selector/oracle, candidate expansion, targeted repair, heldout4, and cross-heldout synthesis.",
            "manuscript/main.md; tables/full_statistical_report.md; tables/cross_heldout_validation_synthesis.md",
            "tables/seed_outcome_ledger.csv; materials/NEGATIVE_RESULTS_FAILURE_REGISTER.csv; materials/STATISTICAL_REPORTING_APPENDIX.md",
            "main_manuscript_and_supplement",
            "Keep negative heldout2/heldout3/heldout4 outcomes visible.",
            "Oracle rows are diagnostic upper bounds; cross-heldout aggregate is not broad robustness.",
            "pass"
            if stats["summary"]["failed_checks"] == 0 and statistical_appendix["summary"]["status"] == "pass"
            else "review_required",
        ),
        row(
            "main_text",
            "discussion_limitations",
            "Integrate threats to validity, endpoint sensitivity, selector-oracle gap, candidate gaps, and future validation plan.",
            "manuscript/main.md; materials/MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.md",
            "materials/THREATS_TO_VALIDITY_AUDIT.md; materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md; materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.md",
            "main_manuscript_and_supplement",
            "Preserve visible limitations when converting to a journal template.",
            "Limitations are a claim-control requirement, not optional background text.",
            "pass",
        ),
        row(
            "figures",
            "figure_1_main_results",
            "Main baseline and method comparison figure.",
            "figures/figure_1_multicar_overtake_results.pdf; figures/figure_1_multicar_overtake_results.tiff",
            "figures/figure_1_source_data.csv; materials/FIGURE_SOURCE_DATA_AUDIT.md",
            "main_figure_upload_and_source_data",
            "Use final journal-preferred figure format and upload source data if requested.",
            "Figure claims inherit strict simulator-only endpoint boundaries.",
            "pass" if figure_qc["summary"]["status"] == "pass" and figure_source["summary"]["incomplete_count"] == 0 else "review_required",
        ),
        row(
            "figures",
            "figure_2_selector_summary",
            "Portfolio selector and oracle comparison figure.",
            "figures/figure_2_portfolio_selector_summary.pdf; figures/figure_2_portfolio_selector_summary.tiff",
            "figures/figure_2_source_data.csv; materials/SELECTOR_DECISION_AUDIT.md",
            "main_figure_upload_and_source_data",
            "Keep online simulator-loop selector and diagnostic oracle visually separated.",
            "Do not present oracle as an online selector output.",
            "pass" if figure_qc["summary"]["status"] == "pass" and figure_source["summary"]["incomplete_count"] == 0 else "review_required",
        ),
        row(
            "figures",
            "figure_3_cross_heldout",
            "Cross-heldout validation and external-validity boundary figure.",
            "figures/figure_3_cross_heldout_validation.pdf; figures/figure_3_cross_heldout_validation.tiff",
            "figures/figure_3_source_data.csv; figures/figure_3_source_data_dictionary.csv; tables/cross_heldout_statistical_supplement.md",
            "main_figure_upload_and_source_data",
            "Report heldout3 targeted repair and heldout4 partial transfer with correct labels.",
            "Figure 3 does not support broad robustness or real-road claims.",
            "pass" if figure_qc["summary"]["status"] == "pass" and figure_source["summary"]["incomplete_count"] == 0 else "review_required",
        ),
        row(
            "supplement",
            "required_supplement_tables",
            "Package registered supplementary tables and source data.",
            "materials/SUPPLEMENTARY_MATERIALS_INDEX.md; materials/SUPPLEMENT_UPLOAD_DECISION_MATRIX.md",
            "materials/SUPPLEMENTARY_TABLE_LEGENDS.md; materials/EXPERIMENT_REGISTRY.csv; tables/seed_outcome_ledger.csv; tables/cross_heldout_validation_synthesis_rows.csv; materials/SELECTOR_DECISION_AUDIT_ROWS.csv",
            "supplementary_information",
            "Adapt table numbering/captions to target journal style and decide optional reviewer-support uploads.",
            "Supplement tables must preserve negative results and failure decomposition.",
            "pass"
            if supplement["summary"]["review_required_count"] == 0
            and supplement_decision["summary"]["required_missing_count"] == 0
            and table_legends["summary"]["status"] == "pass"
            else "review_required",
        ),
        row(
            "supplement",
            "reviewer_navigation",
            "Provide one-page navigator, reviewer trace, and tiered replication route.",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md; materials/REVIEWER_EVIDENCE_TRACE_PACK.md; materials/REVIEWER_REPLICATION_ROUTE.md",
            "materials/REPRODUCTION_GUIDE.md; tables/artifact_provenance.md",
            "supplement_or_internal_pre_submission",
            "Upload only if journal allows reviewer-navigation supplements; otherwise keep for reviewer response/archive.",
            "Navigation aids point to evidence and do not replace source data.",
            "pass"
            if navigator["summary"].get("core_dashboard_review_required") == 0
            and navigator["summary"].get("core_trace_review_required") == 0
            and replication["summary"].get("core_dashboard_review_required") == 0
            else "review_required",
        ),
        row(
            "declarations",
            "ethics_disclosure_availability",
            "Use ethics/disclosure readiness, data/code availability, license, and archive metadata drafts.",
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.md; materials/DATA_CODE_AVAILABILITY.md",
            "materials/FAIR_ARCHIVE_METADATA.md; materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md",
            "portal_fields_and_archive",
            "Authors must certify conflicts, funding, affiliations, ORCID, and public DOI/URL.",
            "Automation cannot complete author-owned declarations or public archive identifiers.",
            ethics["summary"]["status"],
        ),
        row(
            "quality_control",
            "manuscript_source_package",
            "Use generated Markdown/LaTeX manuscript source package and compile/cross-reference preflights.",
            "manuscript/main.md; manuscript/main.tex; manuscript/references.bib",
            "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.md; materials/MANUSCRIPT_COMPILE_PREFLIGHT.md; materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.md",
            "internal_pre_submission",
            "Convert into selected journal template and final PDF outside this local package.",
            "Current source is a journal-neutral scaffold, not final submission source.",
            "pass" if source_package["summary"]["review_required_count"] == 0 and cross_ref["summary"]["status"] == "pass" else "review_required",
        ),
        row(
            "quality_control",
            "final_upload_bundle",
            "Use final bundle and upload selection plan to separate manuscript, figures, source data, supplement, archive, and internal QC.",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.md; materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md; materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            "journal_upload_planning",
            "Select final upload subset after target-journal choice.",
            "Bundle map is not a final journal receipt.",
            "pass" if bundle["summary"]["missing_required_count"] == 0 and upload["summary"]["status"] == "ready_with_author_selection" else "review_required",
        ),
        row(
            "quality_control",
            "package_gates",
            "Retain verification, smoke test, provenance, and data dictionary gates.",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md; materials/PUBLICATION_SMOKE_TEST.md",
            "tables/artifact_provenance.md; materials/DATA_DICTIONARY.md",
            "internal_pre_submission_and_archive",
            "Rerun after any content, figure, table, or script edit.",
            "Local gates support package integrity but do not imply journal acceptance.",
            "pass" if verification["summary"]["status"] == "pass" and smoke["summary"]["status"] == "pass" and dictionary["summary"]["complete"] else "review_required",
        ),
    ]

    review_required = [item for item in rows if item["status"] == "review_required"]
    journal_upload = [item for item in rows if "upload" in item["upload_destination"] or "portal" in item["upload_destination"]]
    internal_qc = [item for item in rows if "internal" in item["upload_destination"]]
    evidence_routes = [
        evidence_route(
            "MR1_abstract_results_numbers",
            "Abstract / Results",
            "Locked baseline, graph-adaptive, heldout selector/oracle, targeted repair, heldout4, and cross-heldout headline numbers.",
            "manuscript/main.md; tables/seed_outcome_ledger.md; tables/cross_heldout_validation_synthesis.md",
            "materials/CLAIM_EVIDENCE_MATRIX.md; materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.md; materials/STATISTICAL_CONSISTENCY_AUDIT.md",
            "figures/figure_1_source_data.csv; figures/figure_2_source_data.csv; figures/figure_3_source_data.csv",
            "Report descriptive seed-set evidence only; do not average away heldout3/heldout4 failures or claim broad robustness.",
            "Lets reviewers trace each headline number from prose to tables and figure source data.",
            "pass" if claim_qa["summary"]["status"] == "pass" and narrative["summary"]["status"] == "pass" else "review_required",
        ),
        evidence_route(
            "MR2_methods_protocol",
            "Methods / Environment And Task / Statistical Analysis",
            "Strict endpoint, seed partitions, simulator-only scope, selector protocol, and descriptive statistics.",
            "manuscript/main.md; materials/METHODS_REPRODUCIBILITY_CAPSULE.md; materials/STATISTICAL_ANALYSIS_PLAN.md",
            "materials/EXPERIMENT_REGISTRY.csv; materials/SEED_PARTITION_AUDIT.md; materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
            "tables/seed_outcome_ledger.csv; materials/EXPERIMENT_REGISTRY.csv",
            "Methods describe saved simulator evidence and do not imply real-road or perception-stack validation.",
            "Gives methods reviewers the seed/protocol/statistics trail without relying on narrative alone.",
            "pass" if methods["summary"]["status"] == "pass" and stats["summary"]["status"] == "pass" else "review_required",
        ),
        evidence_route(
            "MR3_baseline_and_selector_results",
            "Results / Strict Evaluation / Online Portfolio Probing",
            "Preserved strong baseline, graph-adaptive comparison, selector result, oracle upper bound, and selector decision transparency.",
            "tables/full_statistical_report.md; tables/portfolio_probe_selector_1200_heldout_dagger_v2.md; tables/expanded_selector_generalization.md",
            "materials/BASELINE_FAIRNESS_AUDIT.md; materials/SELECTOR_DECISION_AUDIT.md; materials/STATISTICAL_REPORTING_APPENDIX.md",
            "figures/figure_1_source_data.csv; figures/figure_2_source_data.csv; materials/SELECTOR_DECISION_AUDIT_ROWS.csv",
            "Oracle rows are diagnostic upper bounds; the selector is a simulator online-probe policy, not a zero-cost single controller.",
            "Separates online simulator-loop selector evidence from diagnostic oracle evidence.",
            "pass" if statistical_appendix["summary"]["status"] == "pass" else "review_required",
        ),
        evidence_route(
            "MR4_failure_decomposition",
            "Results / Failure Decomposition",
            "Heldout2 candidate gaps and selector misses, heldout3 external-validation drop, targeted repair diagnostic reuse, heldout4 partial transfer.",
            "tables/heldout2_failure_atlas.md; tables/heldout3_external_validation.md; tables/heldout4_external_validation.md; tables/heldout4_failure_atlas.md",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md; materials/THREATS_TO_VALIDITY_AUDIT.md",
            "tables/seed_outcome_ledger.csv; tables/cross_heldout_validation_synthesis_rows.csv",
            "Heldout3 targeted repair is diagnostic reuse; heldout4 is post-repair external validation with partial transfer, not broad robustness.",
            "Makes negative results auditable instead of leaving them embedded only in prose.",
            "pass" if negative["summary"]["item_count"] > 0 and validity["summary"]["expanded_or_later_selector"] == "31/50" else "review_required",
        ),
        evidence_route(
            "MR5_figures_and_source_data",
            "Figure And Table Callouts",
            "Main figures, legends, technical QC, source-data files, and source-data dictionaries.",
            "figures/figure_1_multicar_overtake_results.pdf; figures/figure_2_portfolio_selector_summary.pdf; figures/figure_3_cross_heldout_validation.pdf",
            "materials/FIGURE_LEGENDS.md; materials/FIGURE_SOURCE_DATA_AUDIT.md; materials/FIGURE_TECHNICAL_QC.md",
            "figures/figure_1_source_data.csv; figures/figure_2_source_data.csv; figures/figure_3_source_data.csv; figures/figure_3_source_data_dictionary.csv",
            "Figures summarize saved simulator evidence; GIFs and visuals are qualitative orientation only.",
            "Lets production/editorial checks confirm every figure has source data and boundary wording.",
            "pass" if figure_source["summary"]["incomplete_count"] == 0 and figure_qc["summary"]["status"] == "pass" else "review_required",
        ),
        evidence_route(
            "MR6_availability_and_archive",
            "Data And Code Availability / Compute Reporting",
            "Local package availability, release manifest, checksums, compute rows, and author-owned archive DOI/accession status.",
            "materials/DATA_CODE_AVAILABILITY.md; materials/RELEASE_ARCHIVE_MANIFEST.md; tables/compute_cost_report.md",
            "materials/FAIR_ARCHIVE_METADATA.md; materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/FINAL_CHECKSUM_FREEZE_RECORD.md",
            "materials/RELEASE_ARCHIVE_MANIFEST.csv; tables/artifact_provenance.csv",
            "Local readiness is not a public archive DOI, journal receipt, author-certified disclosure, or final accepted record.",
            "Separates locally verifiable reproducibility from author-owned archive and portal completion.",
            "pass" if verification["summary"]["status"] == "pass" and smoke["summary"]["status"] == "pass" else "review_required",
        ),
    ]
    route_review_required = [item for item in evidence_routes if item["status"] == "review_required"]
    return {
        "root": str(root),
        "title": "Manuscript-to-Supplement Assembly Map",
        "purpose": (
            "Map manuscript sections, figures, supplementary materials, source data, declarations, archive files, "
            "and internal QC files into a target-journal assembly plan."
        ),
        "rows": rows,
        "evidence_routes": evidence_routes,
        "summary": {
            "status": "pass" if not review_required else "review_required",
            "row_count": len(rows),
            "review_required_count": len(review_required),
            "evidence_route_count": len(evidence_routes),
            "evidence_route_review_required_count": len(route_review_required),
            "journal_upload_related_count": len(journal_upload),
            "internal_qc_count": len(internal_qc),
            "manuscript_status": manifest["status"],
            "manuscript_cross_reference_status": cross_ref["summary"]["status"],
            "supplement_review_required": supplement["summary"]["review_required_count"],
            "supplement_author_selection_required": supplement_decision["summary"]["author_selection_required_count"],
            "supplement_upload_decision_status": supplement_decision["summary"]["status"],
            "supplementary_table_legends_status": table_legends["summary"]["status"],
            "supplementary_table_legend_count": table_legends["summary"]["legend_count"],
            "final_bundle_missing_required": bundle["summary"]["missing_required_count"],
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "data_dictionary_complete": dictionary["summary"]["complete"],
            "claim_qa_status": claim_qa["summary"]["status"],
            "narrative_numeric_consistency_status": narrative["summary"]["status"],
            "statistical_reporting_appendix_status": statistical_appendix["summary"]["status"],
            "statistical_reporting_appendix_rows": statistical_appendix["summary"]["row_count"],
        },
        "interpretation": (
            "This assembly map is a pre-submission planning artifact. It does not create final journal-formatted source "
            "or author-certified declarations; it prevents evidence, supplement, source-data, and internal-QC materials from being misplaced."
        ),
    }


def write_csv(report, path):
    fields = [
        "kind",
        "route_id",
        "section",
        "manuscript_location",
        "claim_or_content",
        "primary_files",
        "supplement_files",
        "upload_destination",
        "author_action",
        "boundary",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow({"kind": "assembly_row", "route_id": "", **item})
        for item in report["evidence_routes"]:
            writer.writerow(
                {
                    "kind": "evidence_route",
                    "route_id": item["route_id"],
                    "section": "manuscript_evidence_route",
                    "manuscript_location": item["manuscript_anchor"],
                    "claim_or_content": item["claim_scope"],
                    "primary_files": item["primary_evidence"],
                    "supplement_files": item["supplement_evidence"],
                    "upload_destination": "main_manuscript_supplement_source_data",
                    "author_action": item["reviewer_use"],
                    "boundary": item["boundary"],
                    "status": item["status"],
                }
            )


def write_markdown(report, path):
    lines = [
        "# Manuscript-to-Supplement Assembly Map",
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
            "## Assembly Rows",
            "",
            "| section | manuscript location | status | content | primary files | supplement files | destination | author action | boundary |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['section']} | {item['manuscript_location']} | {item['status']} | {item['claim_or_content']} | "
            f"`{item['primary_files']}` | `{item['supplement_files']}` | {item['upload_destination']} | "
            f"{item['author_action']} | {item['boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Manuscript Evidence Routes",
            "",
            "| route | manuscript anchor | status | claim scope | primary evidence | supplement evidence | source data | boundary | reviewer use |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["evidence_routes"]:
        lines.append(
            f"| {item['route_id']} | {item['manuscript_anchor']} | {item['status']} | {item['claim_scope']} | "
            f"`{item['primary_evidence']}` | `{item['supplement_evidence']}` | `{item['source_data']}` | "
            f"{item['boundary']} | {item['reviewer_use']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export manuscript-to-supplement assembly map.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.json"
    out_md = materials / "MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md"
    out_csv = materials / "MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
