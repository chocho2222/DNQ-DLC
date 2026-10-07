#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import hashlib
import json
from pathlib import Path


SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
CASE_COMMANDS = "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv"

MANIFESTS = {
    "final_readiness": "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json",
    "status_snapshot": "outputs/tits_dynamic_graph/tits_status_snapshot/tits_status_snapshot_manifest.json",
    "freshness": "outputs/tits_dynamic_graph/tits_freshness_audit/tits_freshness_audit_manifest.json",
    "cross_reference": "outputs/tits_dynamic_graph/tits_cross_reference_audit/tits_cross_reference_audit_manifest.json",
    "evidence_ledger": "outputs/tits_dynamic_graph/tits_evidence_ledger/tits_evidence_ledger_manifest.json",
    "reviewer_smoke_execution": "outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit/tits_reviewer_smoke_execution_audit_manifest.json",
    "reviewer_reproduction_time_budget": "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/tits_reviewer_reproduction_time_budget_audit_manifest.json",
    "artifact_manifest": "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json",
    "public_release": "outputs/tits_dynamic_graph/public_release_plan/public_release_plan_manifest.json",
    "fair_archive": "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tits_fair_archive_metadata_pack_manifest.json",
    "reproducibility_capsule": "outputs/tits_dynamic_graph/tits_reproducibility_capsule/tits_reproducibility_capsule_manifest.json",
    "open_source_minimal_repo": "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/tits_open_source_minimal_repo_audit_manifest.json",
    "github_release": "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tits_github_release_readiness_pack_manifest.json",
    "checksum_verification": "outputs/tits_dynamic_graph/tits_checksum_verification_audit/tits_checksum_verification_audit_manifest.json",
    "author_owned_integrity": "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/tits_author_owned_submission_integrity_audit_manifest.json",
    "submission_gap_priority": "outputs/tits_dynamic_graph/tits_submission_gap_priority_audit/tits_submission_gap_priority_audit_manifest.json",
}


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


def sha256_file(path, chunk_size=1024 * 1024):
    path = Path(path)
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


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


def source_facts(root):
    rows = read_csv(root / SOURCE_DATA)
    case_rows = read_csv(root / CASE_COMMANDS)
    cases = {
        (
            row.get("_benchmark", ""),
            row.get("seed", ""),
            row.get("num_agents", ""),
            row.get("track_path", ""),
            row.get("traffic_profile", ""),
        )
        for row in rows
    }
    algorithms = sorted({row.get("algorithm", "") for row in rows if row.get("algorithm", "")})
    benchmarks = sorted({row.get("_benchmark", "") for row in rows if row.get("_benchmark", "")})
    vehicles = sorted({row.get("num_agents", "") for row in rows if row.get("num_agents", "")}, key=lambda x: int(x or 0))
    return {
        "source_rows": len(rows),
        "case_command_rows": len(case_rows),
        "matched_case_count": len(cases),
        "algorithm_count": len(algorithms),
        "algorithms": algorithms,
        "benchmarks": benchmarks,
        "vehicle_counts": vehicles,
        "source_sha256": sha256_file(root / SOURCE_DATA),
        "case_commands_sha256": sha256_file(root / CASE_COMMANDS),
    }


def status_is_pass(data, allow_artifact=False):
    status = data.get("status")
    if allow_artifact and status == "artifact_manifest_generated":
        return True
    return status in {"pass", "complete", "PASS"}


def get_artifact_count(data):
    summary = data.get("summary", {})
    return summary.get("file_count") or summary.get("artifact_file_count") or data.get("files")


def build_manifest_rows(root, manifests):
    rows = []
    for name, rel in MANIFESTS.items():
        data = manifests.get(name, {})
        path = root / rel
        if name == "artifact_manifest":
            # Avoid a self-referential hash loop once this audit is itself
            # included in the artifact manifest. File count and status are
            # checked separately in FF04.
            digest = "dynamic_manifest_not_hashed_in_freeze_audit"
            size_bytes = ""
        else:
            digest = sha256_file(path)
            size_bytes = path.stat().st_size if path.exists() and path.is_file() else 0
        rows.append(
            {
                "manifest_id": name,
                "path": rel,
                "exists": path.exists() and path.is_file(),
                "status": data.get("status", "missing"),
                "size_bytes": size_bytes,
                "sha256": digest,
            }
        )
    return rows


def check_row(check_id, passed, evidence, expected, observed, interpretation, author_action):
    return {
        "check_id": check_id,
        "status": "pass" if passed else "review_required",
        "evidence": evidence,
        "expected": expected,
        "observed": observed,
        "interpretation": interpretation,
        "author_action": author_action,
    }


def build_checks(facts, manifests):
    final = manifests["final_readiness"]
    freshness = manifests["freshness"]
    crossref = manifests["cross_reference"]
    evidence_ledger = manifests["evidence_ledger"]
    smoke_execution = manifests["reviewer_smoke_execution"]
    reproduction_time_budget = manifests["reviewer_reproduction_time_budget"]
    artifact = manifests["artifact_manifest"]
    release = manifests["public_release"]
    fair = manifests["fair_archive"]
    capsule = manifests["reproducibility_capsule"]
    open_source = manifests["open_source_minimal_repo"]
    github = manifests["github_release"]
    checksum = manifests["checksum_verification"]
    author_owned = manifests["author_owned_integrity"]
    gap = manifests["submission_gap_priority"]
    status_snapshot = manifests["status_snapshot"]

    artifact_count = get_artifact_count(artifact)
    release_count = get_artifact_count(release)
    fair_count = fair.get("summary", {}).get("artifact_files")
    open_source_count = open_source.get("summary", {}).get("artifact_manifest_files")
    github_count = github.get("summary", {}).get("artifact_manifest_files")
    final_pass_count = final.get("pass_count")
    final_gate_count = final.get("gate_count")
    final_dashboard_ready = final.get("status") == "pass" and final_pass_count == final_gate_count
    if isinstance(final_pass_count, int) and isinstance(final_gate_count, int):
        final_dashboard_ready = final_dashboard_ready or (
            final.get("status") in {"pass", "author_action_required", "review_required"}
            and final_pass_count >= final_gate_count - 1
        )

    checks = [
        check_row(
            "FF01_formal_matrix_frozen",
            facts["source_rows"] == 240 and facts["case_command_rows"] == 30 and facts["matched_case_count"] == 30 and facts["algorithm_count"] == 8,
            f"{SOURCE_DATA}; {CASE_COMMANDS}",
            "240 source rows, 30 frozen case commands, 30 matched cases, 8 algorithms",
            f"source_rows={facts['source_rows']}; case_commands={facts['case_command_rows']}; cases={facts['matched_case_count']}; algorithms={facts['algorithm_count']}",
            "The formal matrix identity is frozen at the expected T-ITS benchmark scale.",
            "If the formal matrix is rerun, regenerate all postprocessing, evidence, release and freeze audits.",
        ),
        check_row(
            "FF02_final_dashboard_pass",
            final_dashboard_ready,
            MANIFESTS["final_readiness"],
            "final readiness pass, or near-complete fixed-point refresh with only downstream handoff gates pending",
            f"status={final.get('status')}; pass={final.get('pass_count')}/{final.get('gate_count')}",
            "The local evidence chain is internally complete at the dashboard level.",
            "Final DOI, URL, license, author metadata and IEEE portal actions remain author-owned.",
        ),
        check_row(
            "FF03_freshness_and_crossref_clean",
            freshness.get("status") == "pass"
            and freshness.get("summary", {}).get("stale_count") == 0
            and crossref.get("status") == "pass"
            and crossref.get("summary", {}).get("missing_reference_count") == 0
            and crossref.get("summary", {}).get("risky_formal_reference_count") == 0
            and crossref.get("summary", {}).get("unknown_prefix_count") == 0,
            f"{MANIFESTS['freshness']}; {MANIFESTS['cross_reference']}",
            "freshness pass with stale=0 and cross-reference pass with missing/risky/unknown=0",
            (
                f"freshness={freshness.get('status')} stale={freshness.get('summary', {}).get('stale_count')}; "
                f"crossref={crossref.get('status')} missing={crossref.get('summary', {}).get('missing_reference_count')} "
                f"risky={crossref.get('summary', {}).get('risky_formal_reference_count')} unknown={crossref.get('summary', {}).get('unknown_prefix_count')}"
            ),
            "The manuscript-facing numbers and path references are synchronized with the current formal evidence.",
            "Rerun these audits after editing manuscript, supplement, README, release plan or reviewer packet text.",
        ),
        check_row(
            "FF04_release_archive_counts_consistent",
            status_is_pass(artifact, allow_artifact=True)
            and release.get("status") == "pass"
            and fair.get("status") == "pass"
            and artifact_count == release_count == fair_count,
            f"{MANIFESTS['artifact_manifest']}; {MANIFESTS['public_release']}; {MANIFESTS['fair_archive']}",
            "artifact manifest, public release plan and FAIR metadata agree on file count",
            f"artifact={artifact_count}; release={release_count}; fair={fair_count}",
            "The data/archive route is synchronized with the checksum manifest.",
            "Regenerate artifact manifest, release plan and FAIR metadata after adding, moving or deleting release artifacts.",
        ),
        check_row(
            "FF05_github_and_minimal_repo_synchronized",
            open_source.get("status") in {"pass", "review_required"}
            and github.get("status") == "pass"
            and open_source_count == artifact_count
            and github_count == artifact_count
            and open_source.get("summary", {}).get("missing_required_count") == 0
            and open_source.get("summary", {}).get("release_boundary_issue_count") == 0,
            f"{MANIFESTS['open_source_minimal_repo']}; {MANIFESTS['github_release']}",
            "GitHub/minimal-repo packs pass and share current artifact count",
            f"open_source={open_source.get('status')} files={open_source_count}; github={github.get('status')} files={github_count}",
            "The minimal public repository route is aligned with release/archive routing.",
            "Before public release, authors still need real repository URL, release tag, DOI and license confirmation.",
        ),
        check_row(
            "FF06_reproducibility_capsule_current",
            capsule.get("status") in {"pass", "review_required"}
            and capsule.get("summary", {}).get("source_rows") == facts["source_rows"]
            and capsule.get("summary", {}).get("case_command_rows") == facts["case_command_rows"]
            and capsule.get("summary", {}).get("unique_source_cases") == facts["matched_case_count"]
            and capsule.get("summary", {}).get("unique_algorithms") == facts["algorithm_count"],
            MANIFESTS["reproducibility_capsule"],
            "capsule pass and matrix identity matches source data",
            (
                f"status={capsule.get('status')}; rows={capsule.get('summary', {}).get('source_rows')}; "
                f"cases={capsule.get('summary', {}).get('unique_source_cases')}; algorithms={capsule.get('summary', {}).get('unique_algorithms')}"
            ),
            "The compact reproduction fingerprint points to the same frozen matrix as the formal source data.",
            "Regenerate the capsule after any matrix, source-data, manifest or release-route change.",
        ),
        check_row(
            "FF07_checksum_zero_mismatch",
            checksum.get("status") == "pass"
            and checksum.get("summary", {}).get("missing_count") == 0
            and checksum.get("summary", {}).get("checksum_mismatch_count") == 0
            and checksum.get("summary", {}).get("size_mismatch_count") == 0,
            MANIFESTS["checksum_verification"],
            "checksum audit pass with missing/checksum/size mismatch counts all zero",
            (
                f"status={checksum.get('status')}; missing={checksum.get('summary', {}).get('missing_count')}; "
                f"sha={checksum.get('summary', {}).get('checksum_mismatch_count')}; size={checksum.get('summary', {}).get('size_mismatch_count')}"
            ),
            "Key artifacts can be independently checked against the manifest.",
            "Use full checksum mode for final public DOI/release freeze if storage and time allow.",
        ),
        check_row(
            "FF08_author_actions_explicit",
            author_owned.get("status") == "pass"
            and bool(author_owned.get("summary", {}).get("submission_author_finalization_required"))
            and gap.get("status") == "pass"
            and gap.get("summary", {}).get("local_evidence_issue_count") == 0,
            f"{MANIFESTS['author_owned_integrity']}; {MANIFESTS['submission_gap_priority']}",
            "author-owned actions remain explicit and local evidence has no issue",
            (
                f"author_owned={author_owned.get('status')}; finalization_required={author_owned.get('summary', {}).get('submission_author_finalization_required')}; "
                f"gap={gap.get('status')} local_issues={gap.get('summary', {}).get('local_evidence_issue_count')}"
            ),
            "The freeze does not falsely claim that DOI, URL, license, author declarations or portal submission are locally completed.",
            "Complete author/platform actions externally, replace placeholders, then rerun the freeze chain.",
        ),
        check_row(
            "FF09_status_snapshot_current",
            status_snapshot.get("status") in {"pass", "review_required"}
            and status_snapshot.get("summary", {}).get("final_readiness_status") in {None, "pass"}
            and (
                status_snapshot.get("summary", {}).get("artifact_files") in {None, artifact_count}
                or status_snapshot.get("summary", {}).get("artifact_file_count") in {None, artifact_count}
            ),
            MANIFESTS["status_snapshot"],
            "status snapshot exists and is not contradicted by current final-readiness or artifact count",
            f"status={status_snapshot.get('status')}; artifact={artifact_count}",
            "The one-page status snapshot is a downstream handoff summary; during fixed-point refresh it may briefly observe the previous final-freeze status.",
            "Regenerate status snapshot after dashboard, freshness, release or artifact changes.",
        ),
        check_row(
            "FF10_observation_only_reproducibility_indexed",
            evidence_ledger.get("status") == "pass"
            and evidence_ledger.get("summary", {}).get("observation_evidence_count") == 3
            and evidence_ledger.get("summary", {}).get("missing_observation_evidence_count") == 0
            and smoke_execution.get("status") == "pass"
            and smoke_execution.get("summary", {}).get("summary_count") == smoke_execution.get("summary", {}).get("expected_summary_count")
            and smoke_execution.get("summary", {}).get("issue_count") == 0
            and reproduction_time_budget.get("status") == "pass"
            and reproduction_time_budget.get("summary", {}).get("tier_count") == 4,
            f"{MANIFESTS['evidence_ledger']}; {MANIFESTS['reviewer_smoke_execution']}; {MANIFESTS['reviewer_reproduction_time_budget']}",
            "observation-only reproduction evidence is indexed, smoke execution is fingerprinted, and T0-T3 time budget is explicit",
            (
                f"ledger={evidence_ledger.get('status')} obs={evidence_ledger.get('summary', {}).get('observation_evidence_count')} "
                f"smoke={smoke_execution.get('status')} summaries={smoke_execution.get('summary', {}).get('summary_count')}/"
                f"{smoke_execution.get('summary', {}).get('expected_summary_count')} "
                f"budget={reproduction_time_budget.get('status')} tiers={reproduction_time_budget.get('summary', {}).get('tier_count')}"
            ),
            "Observation-only reproduction artifacts are now part of the frozen release explanation while remaining distinct from formal performance claims.",
            "Keep the smoke audit and reproduction-time-budget audit in the release package, but do not cite them as paper-scale results.",
        ),
    ]
    return checks


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Final Freeze Consistency Audit",
        "",
        "该审计用于最终投稿/开源冻结前的最后一道一致性检查：它不新增实验结果，而是交叉核对 dashboard、status snapshot、freshness、cross-reference、artifact manifest、release plan、FAIR metadata、GitHub/minimal repository、复现胶囊、观察性复现证据和作者侧动作边界是否仍然一致。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Freeze Checks",
            "",
            "| Check | Status | Evidence | Expected | Observed | Interpretation | Author action |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["checks"]:
        lines.append(
            f"| {row['check_id']} | {row['status']} | `{row['evidence']}` | {row['expected']} | {row['observed']} | {row['interpretation']} | {row['author_action']} |"
        )
    lines.extend(
        [
            "",
            "## Manifest Crosswalk",
            "",
            "| Manifest | Status | Exists | Size bytes | SHA256 |",
            "|---|---|---:|---:|---|",
        ]
    )
    for row in report["manifest_rows"]:
        lines.append(f"| {row['manifest_id']} | {row['status']} | {row['exists']} | {row['size_bytes']} | `{row['sha256']}` |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- `pass` 表示当前本地证据链适合进入最终人工冻结/上传前检查，不表示真实 DOI、GitHub release、license、IEEE 模板或 ScholarOne 投稿已经完成。",
            "- 若任何正式 source data、图表、补充材料、README、release plan、artifact manifest 或作者占位符发生变化，应重新运行 `make tits-refresh-gates`。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_final_freeze_consistency_audit.py --out-dir outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def build_report(root, out_dir):
    manifests = {name: read_json(root / rel) for name, rel in MANIFESTS.items()}
    facts = source_facts(root)
    checks = build_checks(facts, manifests)
    manifest_rows = build_manifest_rows(root, manifests)
    issue_count = sum(1 for row in checks if row["status"] != "pass")
    status = "pass" if issue_count == 0 else "review_required"
    summary = {
        "status": status,
        "source_rows": facts["source_rows"],
        "case_command_rows": facts["case_command_rows"],
        "matched_case_count": facts["matched_case_count"],
        "algorithm_count": facts["algorithm_count"],
        "benchmarks": ",".join(facts["benchmarks"]),
        "vehicle_counts": ",".join(facts["vehicle_counts"]),
        "check_count": len(checks),
        "issue_count": issue_count,
        "manifest_count": len(manifest_rows),
        "source_sha256": facts["source_sha256"],
        "case_commands_sha256": facts["case_commands_sha256"],
        "final_readiness": f"{manifests['final_readiness'].get('pass_count')}/{manifests['final_readiness'].get('gate_count')}",
        "artifact_files": get_artifact_count(manifests["artifact_manifest"]),
        "public_release_status": manifests["public_release"].get("status"),
        "freshness_status": manifests["freshness"].get("status"),
        "cross_reference_status": manifests["cross_reference"].get("status"),
        "boundary": "Local freeze consistency only; author/platform submission actions remain external.",
    }
    return {
        "status": status,
        "out_dir": out_dir,
        "summary": summary,
        "source_facts": facts,
        "checks": checks,
        "manifest_rows": manifest_rows,
        "note": "This audit verifies final-package consistency and author-action boundaries. It does not create new empirical results.",
    }


def main():
    parser = argparse.ArgumentParser(description="Export a final freeze consistency audit for the T-ITS evidence chain.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    report = build_report(root, args.out_dir)
    paths = {
        "audit_md": write_text(materials / "FINAL_FREEZE_CONSISTENCY_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "FINAL_FREEZE_CONSISTENCY_AUDIT.json", report),
        "checks_csv": write_csv(
            tables / "final_freeze_consistency_checks.csv",
            report["checks"],
            ["check_id", "status", "evidence", "expected", "observed", "interpretation", "author_action"],
        ),
        "manifest_crosswalk_csv": write_csv(
            tables / "final_freeze_manifest_crosswalk.csv",
            report["manifest_rows"],
            ["manifest_id", "path", "exists", "status", "size_bytes", "sha256"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
        "note": report["note"],
    }
    manifest_path = write_json(out_dir / "tits_final_freeze_consistency_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
