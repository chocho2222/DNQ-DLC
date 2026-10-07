#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
UPLOAD_BUNDLE = "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/tits_submission_upload_bundle_map_manifest.json"
AUTHOR_CLOSURE = "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tits_author_submission_closure_pack_manifest.json"
NUMBERING = "outputs/tits_dynamic_graph/tits_numbering_consistency_audit/tits_numbering_consistency_audit_manifest.json"
FRESHNESS = "outputs/tits_dynamic_graph/tits_freshness_audit/tits_freshness_audit_manifest.json"
CROSSREF = "outputs/tits_dynamic_graph/tits_cross_reference_audit/tits_cross_reference_audit_manifest.json"
FAIR = "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tits_fair_archive_metadata_pack_manifest.json"
DEPENDENCY = "outputs/tits_dynamic_graph/tits_dependency_license_audit/tits_dependency_license_audit_manifest.json"
CONTAINER = "outputs/tits_dynamic_graph/tits_container_build_preflight/tits_container_build_preflight_manifest.json"

OFFICIAL_SOURCE_NOTES = [
    {
        "source_id": "TITS_AUTHOR_INFO",
        "url": "https://ieee-itss.org/pub/t-its/",
        "used_for": "T-ITS author-facing journal route, manuscript type, keywords and submission-route reminders.",
    },
    {
        "source_id": "IEEE_AUTHOR_CENTER",
        "url": "https://ieeeauthorcenter.ieee.org/",
        "used_for": "IEEE author workflow, manuscript preparation, graphical/source-data and publication process reminders.",
    },
    {
        "source_id": "IEEE_REPRODUCIBLE_RESEARCH",
        "url": "https://ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-the-text-of-your-article/reproducible-research/",
        "used_for": "Code/data availability, reproducibility material and source-data routing reminders.",
    },
    {
        "source_id": "IEEE_AI_DISCLOSURE",
        "url": "https://open.ieee.org/author-guidelines-for-artificial-intelligence-ai-generated-text/",
        "used_for": "AI-tool disclosure boundary and author-side declaration reminder.",
    },
]


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def split_refs(value):
    return [item.strip() for item in value.split(";") if item.strip()]


def exists_all(root, refs):
    missing = []
    for ref in refs:
        if not (root / ref).exists():
            missing.append(ref)
    return missing


def row(step_id, phase, item, local_evidence, author_action, portal_or_upload_target, blocking_if_missing, official_source_id, boundary):
    return {
        "step_id": step_id,
        "phase": phase,
        "item": item,
        "local_evidence": local_evidence,
        "author_action": author_action,
        "portal_or_upload_target": portal_or_upload_target,
        "blocking_if_missing": blocking_if_missing,
        "official_source_id": official_source_id,
        "boundary": boundary,
    }


def checklist_rows():
    return [
        row(
            "D01",
            "scope_and_article_type",
            "Confirm that the manuscript is framed as a T-ITS regular simulation/reproducibility paper, not a deployment-safety claim.",
            "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/TITLE_ABSTRACT_KEYWORDS_DRAFT.md; outputs/tits_dynamic_graph/tits_threats_validity_pack/materials/THREATS_TO_VALIDITY_DOSSIER.md",
            "Authors must confirm final article type, scope fit and any page/format constraints in the live portal.",
            "ScholarOne manuscript type / cover letter",
            "yes",
            "TITS_AUTHOR_INFO",
            "Local scope fit is a draft assessment; only the journal/editorial office determines final fit.",
        ),
        row(
            "D02",
            "main_text",
            "Convert Methods, Results, Limitations and Abstract drafts into the final IEEE template.",
            "outputs/tits_dynamic_graph/tits_manuscript_package/materials/METHODS_DRAFT.md; outputs/tits_dynamic_graph/tits_manuscript_package/materials/RESULTS_DRAFT.md; outputs/tits_dynamic_graph/tits_manuscript_package/materials/LIMITATIONS_DRAFT.md; outputs/tits_dynamic_graph/tits_manuscript_package/materials/ABSTRACT_HIGHLIGHTS_DRAFT.md",
            "Authors must polish the narrative, compile the final PDF/Word/LaTeX and verify page, caption and reference formatting.",
            "Main manuscript upload",
            "yes",
            "IEEE_AUTHOR_CENTER",
            "Draft markdown files are not a compiled submission manuscript.",
        ),
        row(
            "D03",
            "title_abstract_keywords",
            "Use the evidence-grounded title, one-paragraph abstract and keyword plan.",
            "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/TITLE_ABSTRACT_KEYWORDS_DRAFT.md; outputs/tits_dynamic_graph/tits_submission_metadata_pack/tables/keyword_plan.csv",
            "Authors must paste final title/abstract/keywords into the portal and verify current word/keyword constraints.",
            "Portal title, abstract and keywords",
            "yes",
            "TITS_AUTHOR_INFO",
            "Local keyword mapping is a draft; portal fields are authoritative at submission time.",
        ),
        row(
            "D04",
            "figures",
            "Upload main figures with source data, multi-format exports and numbering consistency checks.",
            "outputs/tits_dynamic_graph/manuscript_english_figures/figures/figure_dynamic_dlc_overtaking_english.pdf; outputs/tits_dynamic_graph/manuscript_english_figures/figures/figure_dynamic_dlc_overtaking_english.tiff; outputs/tits_dynamic_graph/tits_figure_source_data_audit/materials/FIGURE_SOURCE_DATA_AUDIT.md; outputs/tits_dynamic_graph/tits_numbering_consistency_audit/materials/NUMBERING_CONSISTENCY_AUDIT.md",
            "Authors must select journal-preferred formats and ensure final in-manuscript figure numbers match captions.",
            "Figure upload / manuscript embedded figures",
            "yes",
            "IEEE_AUTHOR_CENTER",
            "Local figure QA does not replace final production checks by IEEE.",
        ),
        row(
            "D05",
            "source_data",
            "Attach or archive the frozen 240-run source data and figure source tables.",
            "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv; outputs/tits_dynamic_graph/tits_source_data_integrity_audit/materials/SOURCE_DATA_INTEGRITY_AUDIT.md; outputs/tits_dynamic_graph/tits_figure_source_data_audit/tables/figure_source_table_checks.csv",
            "Authors must decide whether source data are uploaded directly, deposited in an archive, or both.",
            "Source data upload / data archive",
            "yes",
            "IEEE_REPRODUCIBLE_RESEARCH",
            "Simulation source data do not certify real-road behavior.",
        ),
        row(
            "D06",
            "supplementary_information",
            "Choose final supplementary notes, statistical tables, robustness analyses and failure diagnostics.",
            "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/SUPPLEMENTARY_MATERIALS_INDEX.md; outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/STATISTICAL_ANALYSIS_PLAN.md; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md; outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md",
            "Authors must decide what goes into SI versus the data archive, then update final manuscript cross-references.",
            "Supplementary information upload",
            "yes",
            "IEEE_AUTHOR_CENTER",
            "Supplementary reports are evidence navigation and robustness material unless explicitly identified as results.",
        ),
        row(
            "D07",
            "visual_supplement",
            "Select top-down and first-person GIFs/videos as qualitative evidence.",
            "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.md; outputs/tits_dynamic_graph/publication_gifs",
            "Authors must check journal file-size/format limits and decide whether GIFs are SI or data-archive items.",
            "Supplementary video / data archive visual folder",
            "optional",
            "IEEE_AUTHOR_CENTER",
            "GIFs are representative visualizations; statistics come from source data.",
        ),
        row(
            "D08",
            "reproducibility_packet",
            "Provide reviewer-facing smoke route, full matrix rerun route and result fingerprints.",
            "outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md; outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/THIRD_PARTY_REPRODUCTION_PACK.md",
            "Authors must decide where to host reviewer instructions and whether any private review link is needed.",
            "Reviewer support files / data archive",
            "yes",
            "IEEE_REPRODUCIBLE_RESEARCH",
            "Smoke tests are not formal performance evidence.",
        ),
        row(
            "D09",
            "code_repository",
            "Prepare public code repository contents, dependency notices and minimal reproduction route.",
            "README.md; LICENSE; environment.yml; configs/tits_dynamic_graph_experiments.json; scripts/run_tits_full_pipeline.sh; outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_RELEASE_READINESS_PACK.md; outputs/tits_dynamic_graph/tits_dependency_license_audit/materials/DEPENDENCY_LICENSE_AUDIT.md",
            "Authors must create the real repository/release tag, confirm license and replace placeholders with public URLs.",
            "Code availability statement / repository URL",
            "yes",
            "IEEE_REPRODUCIBLE_RESEARCH",
            "Local repository state is not a public release.",
        ),
        row(
            "D10",
            "data_archive",
            "Prepare FAIR archive metadata, public release routing and SHA256 manifest.",
            "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/materials/FAIR_ARCHIVE_METADATA_PACK.md; outputs/tits_dynamic_graph/public_release_plan/PUBLIC_RELEASE_PLAN.md; outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv",
            "Authors must deposit data, obtain DOI/accession and update manuscript/repository references.",
            "Data availability statement / archive DOI",
            "yes",
            "IEEE_REPRODUCIBLE_RESEARCH",
            "Local FAIR metadata do not create a DOI or external archive.",
        ),
        row(
            "D11",
            "author_declarations",
            "Finalize author metadata, ORCID, funding, conflicts, ethics/safety and AI-tool disclosure.",
            "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/AUTHOR_DECLARATIONS_AND_AI_DISCLOSURE_DRAFT.md; outputs/tits_dynamic_graph/tits_author_submission_closure_pack/materials/AUTHOR_SUBMISSION_CLOSURE_PACK.md",
            "Authors must fill actual names, affiliations, ORCID, grants, conflicts and exact AI-tool usage.",
            "Portal declarations / manuscript front matter",
            "yes",
            "IEEE_AI_DISCLOSURE",
            "Draft declaration text requires author verification and final portal wording.",
        ),
        row(
            "D12",
            "claim_boundary",
            "Check that Results/Abstract/Discussion claims remain within simulation evidence.",
            "outputs/tits_dynamic_graph/tits_claim_language_audit/materials/CLAIM_LANGUAGE_AUDIT.md; outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/materials/CLAIM_EVIDENCE_COMPLETENESS_AUDIT.md; outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/materials/REVIEWER_REBUTTAL_READINESS_PACK.md",
            "Authors must rerun claim audits after final manuscript edits.",
            "Final manuscript text / rebuttal preparation",
            "yes",
            "IEEE_AUTHOR_CENTER",
            "No local audit proves real-road safety or arbitrary traffic generalization.",
        ),
        row(
            "D13",
            "container_boundary",
            "Disclose that Docker/Apptainer files are drafts unless an image is actually built and tested.",
            "outputs/tits_dynamic_graph/tits_container_build_preflight/materials/CONTAINER_BUILD_PREFLIGHT.md; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/Dockerfile.draft; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/apptainer.def.draft",
            "If authors publish a container, they must build it, record digest and rerun environment/container audits.",
            "Reproducibility supplement / data archive",
            "yes",
            "IEEE_REPRODUCIBLE_RESEARCH",
            "Current evidence supports container draft readiness only, not a released image.",
        ),
        row(
            "D14",
            "final_freeze",
            "Rerun freshness, cross-reference, artifact manifest, release plan and final dashboard after author edits.",
            "outputs/tits_dynamic_graph/tits_freshness_audit/materials/FRESHNESS_AUDIT.md; outputs/tits_dynamic_graph/tits_cross_reference_audit/materials/FORMAL_CROSS_REFERENCE_AUDIT.md; outputs/tits_dynamic_graph/final_readiness_dashboard/FINAL_READINESS_DASHBOARD.md",
            "Authors must do this after replacing DOI/URL/license/author placeholders and after final figure numbering.",
            "Internal final submission freeze",
            "yes",
            "IEEE_AUTHOR_CENTER",
            "This is a local quality gate, not an IEEE submission receipt.",
        ),
    ]


def enrich_rows(root, rows):
    out = []
    evidence_rows = []
    for item in rows:
        refs = split_refs(item["local_evidence"])
        missing = exists_all(root, refs)
        for ref in refs:
            evidence_rows.append(
                {
                    "step_id": item["step_id"],
                    "evidence_path": ref,
                    "exists": (root / ref).exists(),
                }
            )
        local_status = "local_ready" if not missing else "missing_local_evidence"
        portal_status = "author_action_required" if item["blocking_if_missing"] in {"yes", "optional"} else "local_only"
        out.append(
            {
                **item,
                "evidence_count": len(refs),
                "missing_evidence_count": len(missing),
                "missing_evidence": "; ".join(missing),
                "local_status": local_status,
                "portal_status": portal_status,
                "dry_run_status": "pass" if not missing else "review_required",
            }
        )
    return out, evidence_rows


def build_report(root):
    rows, evidence = enrich_rows(root, checklist_rows())
    missing_rows = [row for row in rows if row["dry_run_status"] != "pass"]
    final = read_json(root / FINAL_READINESS)
    upload = read_json(root / UPLOAD_BUNDLE)
    author = read_json(root / AUTHOR_CLOSURE)
    numbering = read_json(root / NUMBERING)
    freshness = read_json(root / FRESHNESS)
    crossref = read_json(root / CROSSREF)
    fair = read_json(root / FAIR)
    dependency = read_json(root / DEPENDENCY)
    container = read_json(root / CONTAINER)
    summary = {
        "status": "pass" if not missing_rows else "review_required",
        "checklist_item_count": len(rows),
        "local_ready_count": sum(1 for row in rows if row["local_status"] == "local_ready"),
        "missing_local_evidence_count": len(missing_rows),
        "author_action_required_count": sum(1 for row in rows if row["portal_status"] == "author_action_required"),
        "official_source_count": len(OFFICIAL_SOURCE_NOTES),
        "final_readiness": f"{final.get('pass_count', 'NA')}/{final.get('gate_count', 'NA')}",
        "upload_bundle_status": upload.get("status", ""),
        "author_closure_status": author.get("status", ""),
        "numbering_status": numbering.get("status", ""),
        "freshness_status": freshness.get("status", ""),
        "freshness_stale_count": freshness.get("summary", {}).get("stale_count"),
        "crossref_missing_reference_count": crossref.get("summary", {}).get("missing_reference_count"),
        "fair_archive_status": fair.get("status", ""),
        "dependency_license_status": dependency.get("status", ""),
        "container_build_feasibility": container.get("summary", {}).get("build_feasibility"),
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "checklist_rows": rows,
        "evidence_rows": evidence,
        "official_sources": OFFICIAL_SOURCE_NOTES,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Submission Dry-Run Checklist",
        "",
        "该清单模拟作者打开 IEEE/T-ITS 投稿门户前的逐项检查：哪些文件已经本地准备好，哪些字段必须由作者在真实门户、代码仓库或数据仓库中完成。它不代表 ScholarOne/IEEE 已提交，也不代表 DOI、license 或容器镜像已经真实发布。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Dry-Run Items",
            "",
            "| Step | Phase | Item | Local status | Portal status | Evidence | Missing | Author action | Boundary |",
            "|---|---|---|---|---|---:|---:|---|---|",
        ]
    )
    for row in report["checklist_rows"]:
        lines.append(
            f"| {row['step_id']} | {row['phase']} | {row['item']} | {row['local_status']} | {row['portal_status']} | {row['evidence_count']} | {row['missing_evidence_count']} | {row['author_action']} | {row['boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Official Source Notes",
            "",
            "| Source | URL | Used for |",
            "|---|---|---|",
        ]
    )
    for row in report["official_sources"]:
        lines.append(f"| {row['source_id']} | {row['url']} | {row['used_for']} |")
    lines.extend(
        [
            "",
            "## Author-Owned Items That Remain Outside Local Automation",
            "",
            "- Final IEEE/T-ITS Word or LaTeX manuscript and portal upload receipt.",
            "- Author names, ORCID, affiliations, funding, conflict of interest and exact AI-tool disclosure.",
            "- Public code repository URL, release tag, license approval and data archive DOI/accession.",
            "- Final choice of supplementary files and visual evidence under journal file-size constraints.",
            "- Actual container image digest if authors decide to publish a built Docker/Apptainer image.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_submission_dry_run_checklist.py --out-dir outputs/tits_dynamic_graph/tits_submission_dry_run_checklist",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export a T-ITS/IEEE submission dry-run checklist.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_submission_dry_run_checklist")
    args = parser.parse_args()

    root = Path(".").resolve()
    out_dir = Path(args.out_dir)
    report = build_report(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "report_md": write_text(out_dir / "materials" / "SUBMISSION_DRY_RUN_CHECKLIST.md", build_markdown(report)),
        "checklist_csv": write_csv(
            out_dir / "tables" / "submission_dry_run_checklist.csv",
            report["checklist_rows"],
            [
                "step_id",
                "phase",
                "item",
                "local_evidence",
                "author_action",
                "portal_or_upload_target",
                "blocking_if_missing",
                "official_source_id",
                "boundary",
                "evidence_count",
                "missing_evidence_count",
                "missing_evidence",
                "local_status",
                "portal_status",
                "dry_run_status",
            ],
        ),
        "evidence_csv": write_csv(
            out_dir / "tables" / "submission_dry_run_evidence_checks.csv",
            report["evidence_rows"],
            ["step_id", "evidence_path", "exists"],
        ),
        "official_sources_json": write_json(out_dir / "materials" / "official_source_notes.json", report["official_sources"]),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
        "boundary": "Local dry-run only; not a journal submission receipt, DOI deposition receipt, legal license confirmation, or built container image.",
    }
    manifest_path = write_json(out_dir / "tits_submission_dry_run_checklist_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
