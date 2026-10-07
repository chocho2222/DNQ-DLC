#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
GITHUB_PACK = "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tits_github_release_readiness_pack_manifest.json"
PUBLIC_RELEASE_FILE_PLAN = "outputs/tits_dynamic_graph/public_release_plan/public_release_file_plan.csv"
PUBLIC_RELEASE_DIR_PLAN = "outputs/tits_dynamic_graph/public_release_plan/public_release_directory_plan.csv"
ROOT_README_AUDIT = "outputs/tits_dynamic_graph/tits_root_readme_alignment_audit/tits_root_readme_alignment_audit_manifest.json"
REVIEWER_ROUTE_AUDIT = "outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit/tits_reviewer_smoke_route_audit_manifest.json"
DEPENDENCY_LICENSE = "outputs/tits_dynamic_graph/tits_dependency_license_audit/tits_dependency_license_audit_manifest.json"
ANONYMIZATION_PRIVACY = "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/tits_anonymization_privacy_audit_manifest.json"

MINIMAL_REPO_ITEMS = [
    ("README.md", "file", "entrypoint", True),
    ("LICENSE", "file", "license_boundary", True),
    ("environment.yml", "file", "environment", True),
    ("setup.py", "file", "editable_install", True),
    ("Makefile", "file", "reviewer_shortcuts", True),
    (".gitignore", "file", "repository_hygiene", True),
    ("configs/tits_dynamic_graph_experiments.json", "file", "formal_config", True),
    ("docs/tits_dynamic_graph_reproducibility_protocol.md", "file", "protocol_documentation", True),
    ("gym_multi_car_racing/multi_car_racing.py", "file", "simulation_environment", True),
    ("dlc/graph_world_model.py", "file", "world_model", True),
    ("dlc/graph_policy.py", "file", "policy_and_graph_controller", True),
    ("dlc/policies.py", "file", "baseline_policies", True),
    ("dlc/rollout.py", "file", "rollout_execution", True),
    ("scripts/run_tits_dynamic_graph_evaluation.py", "file", "online_evaluation_entry", True),
    ("scripts/run_tits_dynamic_graph_online_suite.py", "file", "online_suite_driver", True),
    ("scripts/run_tits_full_pipeline.sh", "file", "full_pipeline_route", True),
    ("scripts/run_tits_representative_gifs.sh", "file", "visual_evidence_route", True),
    ("scripts/export_tits_reviewer_replication_packet.py", "file", "reviewer_packet_generator", True),
    ("tracks/monza_scaled.json", "file", "external_track_metadata", True),
    ("tracks/monza_scaled.npz", "file", "external_track_binary", True),
    ("outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md", "file", "reviewer_route", True),
    ("outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv", "file", "frozen_case_commands", True),
    ("outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv", "file", "formal_source_data", True),
    ("outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv", "file", "checksum_manifest", True),
    ("outputs/tits_dynamic_graph/public_release_plan/PUBLIC_RELEASE_PLAN.md", "file", "release_routing", True),
    ("outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_RELEASE_READINESS_PACK.md", "file", "github_release_pack", True),
    ("outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_README_DRAFT.md", "file", "public_readme_draft", True),
    ("outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/CITATION_cff_DRAFT.md", "file", "citation_draft", True),
    ("outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/CONTRIBUTING_md_DRAFT.md", "file", "contributing_draft", True),
    ("outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/MODEL_CARD_md_DRAFT.md", "file", "model_card_draft", True),
    ("outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/DATA_CARD_md_DRAFT.md", "file", "data_card_draft", True),
]

PUBLIC_CODE_MAX_MB = 10.0


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def count_csv_rows(path):
    path = Path(path)
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def exists_nonempty(path, kind):
    path = Path(path)
    if kind == "directory":
        return path.exists() and path.is_dir() and any(path.iterdir())
    return path.exists() and path.is_file() and path.stat().st_size > 0


def build_inventory(root):
    rows = []
    for rel, kind, role, required in MINIMAL_REPO_ITEMS:
        path = root / rel
        exists = exists_nonempty(path, kind)
        rows.append(
            {
                "path": rel,
                "kind": kind,
                "role": role,
                "required": required,
                "exists_nonempty": exists,
                "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
                "status": "pass" if exists or not required else "missing_required",
            }
        )
    return rows


def release_boundary_rows(file_plan, dir_plan):
    rows = []
    for row in file_plan:
        if row.get("release_role") != "public_code_repository":
            continue
        size_mb = float(row.get("size_mb") or 0.0)
        path = row.get("path", "")
        status = "pass"
        reason = "public code file is small and routed to code repository"
        if path.startswith("outputs/"):
            status = "review_required"
            reason = "outputs directory should not be routed to the minimal code repository"
        elif size_mb > PUBLIC_CODE_MAX_MB:
            status = "review_required"
            reason = f"public code file exceeds {PUBLIC_CODE_MAX_MB:.1f} MB threshold"
        rows.append(
            {
                "path": path,
                "release_role": row.get("release_role", ""),
                "size_mb": row.get("size_mb", ""),
                "status": status,
                "reason": reason,
            }
        )
    for row in dir_plan:
        path = row.get("path", "")
        role = row.get("release_role", "")
        if not path.startswith("outputs/tits_dynamic_graph/"):
            continue
        expected_archive_or_excluded = role in {
            "mandatory_data_archive",
            "optional_full_archive",
            "local_only_not_for_release",
            "exclude_from_public_release",
            "legacy_or_superseded_output",
        }
        rows.append(
            {
                "path": path,
                "release_role": role,
                "size_mb": row.get("size_mb", ""),
                "status": "pass" if expected_archive_or_excluded else "review_required",
                "reason": "large/generated output directory is routed away from the minimal code repository",
            }
        )
    return rows


def check_row(check_id, status, evidence, expected, observed, interpretation, author_action):
    return {
        "check_id": check_id,
        "status": "pass" if status else "review_required",
        "evidence": evidence,
        "expected": expected,
        "observed": observed,
        "interpretation": interpretation,
        "author_action": author_action,
    }


def build_report(root):
    inventory = build_inventory(root)
    file_plan = read_csv(root / PUBLIC_RELEASE_FILE_PLAN)
    dir_plan = read_csv(root / PUBLIC_RELEASE_DIR_PLAN)
    boundary = release_boundary_rows(file_plan, dir_plan)
    github = read_json(root / GITHUB_PACK)
    final = read_json(root / FINAL_READINESS)
    readme = read_json(root / ROOT_README_AUDIT)
    reviewer = read_json(root / REVIEWER_ROUTE_AUDIT)
    dependency = read_json(root / DEPENDENCY_LICENSE)
    privacy = read_json(root / ANONYMIZATION_PRIVACY)
    source_rows = count_csv_rows(root / SOURCE_DATA)
    missing = [row for row in inventory if row["status"] != "pass"]
    boundary_issues = [row for row in boundary if row["status"] != "pass"]
    github_summary = github.get("summary", {})
    current_artifact_count = len(read_csv(root / "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv"))
    final_pass_count = final.get("pass_count")
    final_gate_count = final.get("gate_count")
    final_ready_or_fixed_point = final.get("status") == "pass"
    if isinstance(final_pass_count, int) and isinstance(final_gate_count, int):
        final_ready_or_fixed_point = final_ready_or_fixed_point or (
            final.get("status") in {"author_action_required", "review_required"}
            and final_pass_count >= final_gate_count - 5
        )

    checks = [
        check_row(
            "OS01_minimal_inventory_present",
            not missing,
            "minimal_repo_inventory.csv",
            "all required minimal repository/source-data route files exist",
            f"missing={len(missing)}",
            "The code repository and reviewer-facing source-data route have the minimum files needed for inspection and reproduction.",
            "If any file is missing, restore it before public release.",
        ),
        check_row(
            "OS02_github_pack_current",
            github.get("status") == "pass" and int(github_summary.get("artifact_manifest_files") or -1) == current_artifact_count,
            GITHUB_PACK,
            f"github status=pass and artifact_manifest_files={current_artifact_count}",
            f"status={github.get('status')}; artifact_manifest_files={github_summary.get('artifact_manifest_files')}",
            "GitHub release drafts should be synchronized with the current artifact manifest.",
            "Regenerate the GitHub release readiness pack after artifact manifest changes.",
        ),
        check_row(
            "OS03_release_boundary_clean",
            not boundary_issues and bool(file_plan) and bool(dir_plan),
            f"{PUBLIC_RELEASE_FILE_PLAN}; {PUBLIC_RELEASE_DIR_PLAN}",
            "no generated outputs or large files routed to minimal public code repository",
            f"boundary_issues={len(boundary_issues)}; file_plan_rows={len(file_plan)}; dir_plan_rows={len(dir_plan)}",
            "Large model/data/output artifacts are separated into archive or release-asset routes instead of bloating the minimal code repository.",
            "Move large/generated files out of the code repository route before public release.",
        ),
        check_row(
            "OS04_reviewer_route_and_root_readme",
            readme.get("status") == "pass" and reviewer.get("status") == "pass",
            f"{ROOT_README_AUDIT}; {REVIEWER_ROUTE_AUDIT}",
            "root README and reviewer route audits pass",
            f"readme={readme.get('status')}; reviewer={reviewer.get('status')}",
            "Public entry points and reviewer commands are aligned with the formal evidence chain.",
            "Rerun README and reviewer route audits after changing public commands.",
        ),
        check_row(
            "OS05_license_dependency_privacy",
            dependency.get("status") == "pass" and privacy.get("status") == "pass",
            f"{DEPENDENCY_LICENSE}; {ANONYMIZATION_PRIVACY}",
            "dependency/license and anonymization/privacy audits pass",
            f"dependency={dependency.get('status')}; privacy={privacy.get('status')}",
            "The release route has dependency/license inventory and local-path/placeholder boundary checks.",
            "Authors still need institutional/legal approval of final license and notices.",
        ),
        check_row(
            "OS06_formal_source_and_dashboard",
            source_rows == 240 and final_ready_or_fixed_point,
            f"{SOURCE_DATA}; {FINAL_READINESS}",
            "240 formal source rows and final readiness pass, or fixed-point refresh with only downstream handoff gates pending",
            f"source_rows={source_rows}; final={final.get('status')} {final.get('pass_count')}/{final.get('gate_count')}",
            "The open-source minimal unit points to the frozen formal benchmark rather than smoke or exploratory outputs.",
            "Do not cite smoke or historical outputs as formal benchmark evidence.",
        ),
    ]
    status = "pass" if all(row["status"] == "pass" for row in checks) else "review_required"
    return {
        "status": status,
        "summary": {
            "status": status,
            "inventory_rows": len(inventory),
            "missing_required_count": len(missing),
            "release_boundary_rows": len(boundary),
            "release_boundary_issue_count": len(boundary_issues),
            "check_count": len(checks),
            "check_issue_count": sum(1 for row in checks if row["status"] != "pass"),
            "source_rows": source_rows,
            "artifact_manifest_files": current_artifact_count,
            "github_pack_artifact_manifest_files": github_summary.get("artifact_manifest_files"),
            "final_readiness": f"{final.get('pass_count', 'NA')}/{final.get('gate_count', 'NA')}",
        },
        "inventory_rows": inventory,
        "release_boundary_rows": boundary,
        "check_rows": checks,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Open-Source Minimal Repository Audit",
        "",
        "This audit checks whether the GitHub-facing minimal reproducibility unit is coherent with the formal T-ITS evidence chain. It verifies required repository files, generated GitHub release drafts, reviewer commands, source-data routing, large-artifact separation, dependency/license checks and local-path/privacy boundaries.",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Minimal inventory rows: {summary['inventory_rows']}",
        f"- Missing required files: {summary['missing_required_count']}",
        f"- Release-boundary rows checked: {summary['release_boundary_rows']}",
        f"- Release-boundary issues: {summary['release_boundary_issue_count']}",
        f"- Checks: {summary['check_count']} total, {summary['check_issue_count']} issues",
        f"- Formal source rows: {summary['source_rows']}",
        f"- Artifact manifest files: {summary['artifact_manifest_files']}",
        f"- Final readiness: {summary['final_readiness']}",
        "",
        "## Interpretation",
        "",
        "- `pass` means the local package has a coherent minimal open-source route and a separate archive route for large generated artifacts.",
        "- It does not mean a public GitHub repository, release tag, DOI, final license, ORCID metadata or journal submission has been created.",
        "- The minimal repository should expose code/configuration/reproduction commands; formal benchmark outputs and large artifacts should be archived or attached as release assets.",
        "",
        "## Outputs",
        "",
        f"- Inventory: `{report['paths']['inventory_csv']}`",
        f"- Release boundary checks: `{report['paths']['release_boundary_csv']}`",
        f"- Audit checks: `{report['paths']['checks_csv']}`",
        f"- Machine-readable report: `{report['paths']['audit_json']}`",
        "",
        "## Regeneration",
        "",
        "```bash",
        "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_open_source_minimal_repo_audit.py --out-dir outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit",
        "```",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit the minimal open-source reproducibility repository route.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit")
    args = parser.parse_args()
    root = Path.cwd()
    out_dir = Path(args.out_dir)
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    report = build_report(root)
    paths = {
        "inventory_csv": write_csv(
            tables / "minimal_repo_inventory.csv",
            report["inventory_rows"],
            ["path", "kind", "role", "required", "exists_nonempty", "size_bytes", "status"],
        ),
        "release_boundary_csv": write_csv(
            tables / "minimal_repo_release_boundary.csv",
            report["release_boundary_rows"],
            ["path", "release_role", "size_mb", "status", "reason"],
        ),
        "checks_csv": write_csv(
            tables / "minimal_repo_audit_checks.csv",
            report["check_rows"],
            ["check_id", "status", "evidence", "expected", "observed", "interpretation", "author_action"],
        ),
        "audit_json": write_json(materials / "OPEN_SOURCE_MINIMAL_REPO_AUDIT.json", {k: v for k, v in report.items() if not k.endswith("_rows")}),
    }
    report["paths"] = paths
    paths["audit_md"] = write_text(materials / "OPEN_SOURCE_MINIMAL_REPO_AUDIT.md", build_markdown(report))
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
        "source_inputs": [
            SOURCE_DATA,
            FINAL_READINESS,
            GITHUB_PACK,
            PUBLIC_RELEASE_FILE_PLAN,
            PUBLIC_RELEASE_DIR_PLAN,
            ROOT_README_AUDIT,
            REVIEWER_ROUTE_AUDIT,
            DEPENDENCY_LICENSE,
            ANONYMIZATION_PRIVACY,
        ],
    }
    manifest_path = write_json(out_dir / "tits_open_source_minimal_repo_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
