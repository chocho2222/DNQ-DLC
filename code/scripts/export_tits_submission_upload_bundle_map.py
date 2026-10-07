#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
PUBLIC_RELEASE = "outputs/tits_dynamic_graph/public_release_plan/public_release_plan_manifest.json"
FAIR_ARCHIVE = "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tits_fair_archive_metadata_pack_manifest.json"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def count_csv_rows(path):
    path = Path(path)
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


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


def slot(slot_id, destination, required, local_files, author_action, boundary, evidence_note):
    return {
        "slot_id": slot_id,
        "destination": destination,
        "required_for_submission": required,
        "local_files": local_files,
        "author_action": author_action,
        "boundary": boundary,
        "evidence_note": evidence_note,
    }


def slot_rows():
    return [
        slot(
            "S01_main_text_drafts",
            "IEEE T-ITS manuscript text",
            "yes_author_formatting_required",
            "outputs/tits_dynamic_graph/tits_manuscript_package/materials/ABSTRACT_HIGHLIGHTS_DRAFT.md; outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/TITLE_ABSTRACT_KEYWORDS_DRAFT.md; outputs/tits_dynamic_graph/tits_manuscript_package/materials/METHODS_DRAFT.md; outputs/tits_dynamic_graph/tits_manuscript_package/materials/RESULTS_DRAFT.md; outputs/tits_dynamic_graph/tits_manuscript_package/materials/LIMITATIONS_DRAFT.md",
            "Convert the evidence-generated drafts into the final IEEE T-ITS template and manually polish narrative flow.",
            "Draft files are not a compiled IEEE manuscript and do not replace author-side formatting.",
            "Main text claims are linked to numeric trace and claim-boundary audits.",
        ),
        slot(
            "S02_main_figures",
            "Main manuscript figure uploads",
            "yes_author_selection_required",
            "outputs/tits_dynamic_graph/manuscript_english_figures/figures/figure_dynamic_dlc_overtaking_english.pdf; outputs/tits_dynamic_graph/manuscript_english_figures/figures/figure_dynamic_dlc_overtaking_english.svg; outputs/tits_dynamic_graph/manuscript_english_figures/figures/figure_dynamic_dlc_overtaking_english.tiff; outputs/tits_dynamic_graph/tits_figure_source_data_audit/materials/FIGURE_SOURCE_DATA_AUDIT.md; outputs/tits_dynamic_graph/tits_numbering_consistency_audit/materials/NUMBERING_CONSISTENCY_AUDIT.md; outputs/tits_dynamic_graph/tits_media_upload_quality_audit/materials/MEDIA_UPLOAD_QUALITY_AUDIT.md",
            "Select journal-preferred figure formats and verify final figure numbering against the manuscript.",
            "Figure exports are production candidates; final journal layout and resolution checks remain author-side.",
            "Figure source data and export QA are available.",
        ),
        slot(
            "S03_source_data",
            "Source data upload or data archive",
            "yes",
            "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv; outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/tables/source_data_crosswalk.csv; outputs/tits_dynamic_graph/tits_source_data_integrity_audit/materials/SOURCE_DATA_INTEGRITY_AUDIT.md; outputs/tits_dynamic_graph/tits_figure_source_data_audit/tables/figure_source_table_checks.csv",
            "Upload source CSVs to the selected data repository or journal source-data slot.",
            "Source data are simulation benchmark data only; they do not certify real-road behavior.",
            "The formal source table has 240 rows and links back to summary JSON paths.",
        ),
        slot(
            "S04_supplementary_information",
            "Supplementary information",
            "yes_author_selection_required",
            "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/SUPPLEMENTARY_MATERIALS_INDEX.md; outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/STATISTICAL_ANALYSIS_PLAN.md; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md; outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md; outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/materials/CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md; outputs/tits_dynamic_graph/tits_threats_validity_pack/materials/THREATS_TO_VALIDITY_DOSSIER.md",
            "Decide which supplementary reports are uploaded as SI versus kept in the data archive.",
            "Supplementary reports are evidence navigation and robustness material; they are not new experiments unless explicitly stated.",
            "The navigator maps supplement entries to claims, source data and reviewer use.",
        ),
        slot(
            "S05_reproducibility_packet",
            "Reviewer support / data archive reproducibility folder",
            "yes",
            "outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md; outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/THIRD_PARTY_REPRODUCTION_PACK.md; outputs/tits_dynamic_graph/tits_container_build_preflight/materials/CONTAINER_BUILD_PREFLIGHT.md",
            "Include as reviewer-facing reproduction guidance or archive documentation.",
            "Smoke tests, GIFs and container drafts are not formal statistical evidence; no container image has been built.",
            "Reproduction tiers separate smoke, reporting rebuild, full matrix rerun and visual evidence rebuild.",
        ),
        slot(
            "S06_data_archive",
            "Zenodo/OSF/Figshare/institutional data archive",
            "yes_author_deposition_required",
            "outputs/tits_dynamic_graph/public_release_plan/PUBLIC_RELEASE_PLAN.md; outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/materials/FAIR_ARCHIVE_METADATA_PACK.md; outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.md; outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv",
            "Create a real external archive, obtain DOI/accession and replace placeholders in final manuscript text.",
            "Local FAIR metadata and release plan are drafts; they are not an external DOI or archive receipt.",
            "Archive manifest provides SHA256 checksums and public-release routing.",
        ),
        slot(
            "S07_code_repository",
            "GitHub/GitLab code repository",
            "yes_author_repository_required",
            "README.md; LICENSE; environment.yml; Makefile; setup.py; configs/tits_dynamic_graph_experiments.json; dlc/graph_world_model.py; dlc/graph_policy.py; dlc/policies.py; gym_multi_car_racing/multi_car_racing.py; tracks/monza_scaled.npz; scripts/run_tits_full_pipeline.sh; outputs/tits_dynamic_graph/tits_dependency_license_audit/materials/DEPENDENCY_LICENSE_AUDIT.md",
            "Create a clean repository/release tag, confirm license/notices and decide which large artifacts stay in release assets or data archive.",
            "The local worktree is not itself a public release; author must choose license/repository URL/release tag.",
            "Public release plan separates code repository files from data-archive artifacts; dependency/license audit inventories third-party software notices.",
        ),
        slot(
            "S08_portal_metadata",
            "ScholarOne / IEEE submission portal fields",
            "yes_author_completion_required",
            "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/IEEE_TITS_SUBMISSION_METADATA_PACK.md; outputs/tits_dynamic_graph/tits_submission_metadata_pack/tables/submission_portal_checklist.csv; outputs/tits_dynamic_graph/tits_author_submission_closure_pack/materials/AUTHOR_SUBMISSION_CLOSURE_PACK.md; outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/materials/SUBMISSION_DRY_RUN_CHECKLIST.md",
            "Fill author names, ORCID, funding, conflict of interest, AI statement, DOI/URL and final cover letter fields.",
            "Local metadata drafts do not constitute a completed portal submission.",
            "Author-owned tasks are tracked separately from local evidence readiness.",
        ),
        slot(
            "S09_visual_supplement",
            "Supplementary video / visual evidence",
            "optional_author_selection_required",
            "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.md; outputs/tits_dynamic_graph/publication_gifs; outputs/tits_dynamic_graph/tits_media_upload_quality_audit/materials/MEDIA_UPLOAD_QUALITY_AUDIT.md",
            "Choose representative top-down and first-person GIFs/videos subject to journal file-size limits.",
            "GIFs are qualitative examples only; aggregate metrics come from the 240-run source data.",
            "Publication GIF manifest separates visual evidence from formal statistics.",
        ),
        slot(
            "S10_internal_only_excluded",
            "Do not upload as formal evidence",
            "no",
            "outputs/tits_dynamic_graph/smoke; outputs/tits_dynamic_graph/optimization_checks; outputs/tits_dynamic_graph/online_evaluation_matrix; outputs/tits_dynamic_graph/v6_confirmatory_matrix_partial_summary; outputs/tits_dynamic_graph/quality_aux_dlc_v4_matrix",
            "Keep these outputs local unless explicitly archived as historical/provenance material with boundary labels.",
            "These are smoke, tuning, legacy, partial or exploratory outputs and must not be cited as formal results.",
            "Navigator and cross-reference audits mark risky/historical outputs as boundary-only references.",
        ),
    ]


def split_files(value):
    return [item.strip() for item in value.split(";") if item.strip()]


def enrich_slots(root, rows):
    out = []
    file_rows = []
    for row in rows:
        files = split_files(row["local_files"])
        existing = []
        missing = []
        for item in files:
            path = root / item
            exists = path.exists()
            if exists:
                existing.append(item)
            else:
                missing.append(item)
            file_rows.append(
                {
                    "slot_id": row["slot_id"],
                    "destination": row["destination"],
                    "path": item,
                    "exists": exists,
                    "required_for_submission": row["required_for_submission"],
                    "boundary": row["boundary"],
                }
            )
        required = row["required_for_submission"] != "no"
        status = "pass" if (not required or not missing) else "review_required"
        out.append(
            {
                **row,
                "file_count": len(files),
                "existing_file_count": len(existing),
                "missing_file_count": len(missing),
                "missing_files": "; ".join(missing),
                "status": status,
            }
        )
    return out, file_rows


def build_report(root):
    final = read_json(root / FINAL_READINESS)
    release = read_json(root / PUBLIC_RELEASE)
    fair = read_json(root / FAIR_ARCHIVE)
    slots, files = enrich_slots(root, slot_rows())
    required_missing = [row for row in slots if row["required_for_submission"] != "no" and row["missing_file_count"] > 0]
    author_required = [row for row in slots if "author" in row["required_for_submission"] or "author" in row["author_action"].lower()]
    summary = {
        "status": "pass" if not required_missing else "review_required",
        "slot_count": len(slots),
        "file_reference_count": len(files),
        "required_missing_slot_count": len(required_missing),
        "author_action_slot_count": len(author_required),
        "formal_source_rows": count_csv_rows(root / SOURCE_DATA),
        "final_readiness": f"{final.get('pass_count', 'NA')}/{final.get('gate_count', 'NA')}",
        "public_release_status": release.get("status"),
        "artifact_file_count": release.get("summary", {}).get("artifact_file_count"),
        "fair_archive_status": fair.get("status"),
        "fair_archive_files": fair.get("summary", {}).get("artifact_files"),
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "slots": slots,
        "file_rows": files,
        "boundary": [
            "This map is a local upload-planning aid, not evidence that a journal portal upload or data deposition has occurred.",
            "Author-owned items include DOI/accession, repository URL, license confirmation, author metadata, declarations and final IEEE template formatting.",
            "Formal performance claims should cite the frozen 240-row source data and confirmatory evidence pack, not smoke, GIF-only, tuning or partial outputs.",
        ],
    }


def build_markdown(report):
    lines = [
        "# T-ITS Submission Upload Bundle Map",
        "",
        "该表把当前 T-ITS 证据链按投稿上传槽位分流：主文、图件、source data、补充材料、复现包、数据仓库、代码仓库、门户元数据、视觉补充和 internal-only 边界。",
        "它用于减少投稿时文件错放、把 smoke/调参结果误当正式证据、或把本地草案误写成 DOI/正式容器的风险。",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Upload Slots", "", "| Slot | Destination | Required | Status | Files | Missing | Author action | Boundary |", "|---|---|---|---|---:|---:|---|---|"])
    for row in report["slots"]:
        lines.append(
            f"| {row['slot_id']} | {row['destination']} | {row['required_for_submission']} | {row['status']} | "
            f"{row['file_count']} | {row['missing_file_count']} | {row['author_action']} | {row['boundary']} |"
        )
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in report["boundary"])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export IEEE/T-ITS submission upload bundle map.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_submission_upload_bundle_map")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    report = build_report(root)
    slot_fields = [
        "slot_id",
        "destination",
        "required_for_submission",
        "local_files",
        "file_count",
        "existing_file_count",
        "missing_file_count",
        "missing_files",
        "status",
        "author_action",
        "boundary",
        "evidence_note",
    ]
    file_fields = ["slot_id", "destination", "path", "exists", "required_for_submission", "boundary"]
    paths = {
        "bundle_map_md": write_text(materials / "SUBMISSION_UPLOAD_BUNDLE_MAP.md", build_markdown(report)),
        "bundle_map_json": write_json(materials / "SUBMISSION_UPLOAD_BUNDLE_MAP.json", report),
        "upload_slots_csv": write_csv(tables / "submission_upload_slots.csv", report["slots"], slot_fields),
        "upload_file_manifest_csv": write_csv(tables / "submission_upload_file_manifest.csv", report["file_rows"], file_fields),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_submission_upload_bundle_map_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
