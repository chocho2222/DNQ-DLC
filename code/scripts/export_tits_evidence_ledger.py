#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


CLAIM_MATRIX = "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/tables/claim_evidence_completeness_matrix.csv"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
ARTIFACT_MANIFEST = "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
PUBLICATION_GIF_MANIFEST = "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.json"

OBSERVATION_EVIDENCE = [
    {
        "evidence_id": "reviewer_smoke_execution_audit",
        "path": "outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit/materials/REVIEWER_SMOKE_EXECUTION_AUDIT.md",
        "role": "latest local reviewer-smoke execution fingerprint",
        "boundary": "Observation-only smoke evidence; not paper-scale performance evidence.",
    },
    {
        "evidence_id": "reviewer_smoke_route_audit",
        "path": "outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit/materials/REVIEWER_SMOKE_ROUTE_AUDIT.md",
        "role": "reviewer smoke command and route consistency audit",
        "boundary": "Route audit only; it validates commands and paths, not performance claims.",
    },
    {
        "evidence_id": "reviewer_replication_readme",
        "path": "outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md",
        "role": "reviewer-facing reproduction entry point",
        "boundary": "Command-routing documentation; formal numeric claims remain tied to the 240-run source data.",
    },
]


COMMAND_ROUTES = {
    "source_data": ["confirmatory_matrix", "confirmatory_summarize", "confirmatory_audit"],
    "paired_statistics": ["confirmatory_evidence_pack", "statistical_analysis_pack"],
    "figure": ["manuscript_english_figures", "figure_source_data_audit"],
    "numeric_trace": ["manuscript_numeric_trace_audit"],
    "limitation": ["manuscript_package", "limitations_evidence_audit", "threats_validity_pack"],
    "metric_dictionary": ["benchmark_protocol_pack"],
    "failure_analysis": ["confirmatory_evidence_pack", "casewise_diagnostic_pack"],
    "runtime_scalability": ["runtime_scalability_pack"],
    "innovation_trace": ["innovation_evidence_traceability"],
    "scenario_statistics": ["confirmatory_evidence_pack"],
    "benchmark_protocol": ["benchmark_protocol_pack"],
    "threats_boundary": ["threats_validity_pack"],
    "failure_atlas": ["confirmatory_evidence_pack"],
    "casewise_diagnostics": ["casewise_diagnostic_pack"],
    "overall_statistics": ["confirmatory_evidence_pack"],
    "metric_sensitivity": ["metric_sensitivity_audit"],
    "baseline_fairness": ["baseline_fairness_audit"],
    "statistical_plan": ["statistical_analysis_pack"],
    "protocol_deviation": ["protocol_deviation_readiness_pack"],
    "holm_table": ["statistical_analysis_pack"],
    "effect_sizes": ["statistical_analysis_pack"],
    "design_power": ["experimental_design_power_audit"],
    "leave_one_case": ["experimental_design_power_audit"],
    "casewise": ["casewise_diagnostic_pack"],
    "ablation": ["ablation_contribution_pack"],
    "model_artifacts": ["model_artifact_integrity_audit"],
    "code": ["model_artifact_integrity_audit"],
    "reproducibility_capsule": ["reproducibility_capsule"],
    "reviewer_packet": ["reviewer_replication_packet"],
    "artifact_manifest": ["artifact_manifest"],
    "release_plan": ["public_release_plan"],
    "third_party_pack": ["third_party_reproduction_pack"],
    "container_preflight": ["container_build_preflight"],
    "compute_cost": ["compute_reproducibility_cost_pack"],
    "environment_snapshot": ["environment_reproducibility_audit"],
    "claim_boundary": ["claim_evidence_completeness_audit"],
    "gif_manifest": ["publication_gifs"],
    "dockerfile_draft": ["third_party_reproduction_pack"],
    "apptainer_draft": ["third_party_reproduction_pack"],
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


def source_facts(source_rows):
    cases = {
        (
            row.get("_benchmark", ""),
            row.get("seed", ""),
            row.get("num_agents", ""),
            row.get("track_path", ""),
            row.get("traffic_profile", ""),
        )
        for row in source_rows
    }
    return {
        "source_rows": len(source_rows),
        "matched_case_count": len(cases),
        "algorithm_count": len({row.get("algorithm", "") for row in source_rows if row.get("algorithm", "")}),
        "benchmarks": sorted({row.get("_benchmark", "") for row in source_rows if row.get("_benchmark", "")}),
        "vehicle_counts": sorted({row.get("num_agents", "") for row in source_rows if row.get("num_agents", "")}, key=lambda x: int(x or 0)),
        "total_finish_steps": sum(int(float(row.get("finish_step") or 0)) for row in source_rows),
    }


def artifact_index(artifact):
    return {row.get("path"): row for row in artifact.get("files", [])}


def classify_evidence(path):
    suffix = Path(path).suffix.lower()
    if path.startswith("dlc/") or path.startswith("scripts/") or path.startswith("gym_multi_car_racing/"):
        return "code"
    if suffix in {".csv", ".json"}:
        return "source_or_machine_readable"
    if suffix in {".md", ".txt"}:
        return "human_readable_report"
    if suffix in {".pdf", ".svg", ".png", ".tiff"}:
        return "figure"
    if suffix == ".gif":
        return "visual_supplement"
    if suffix in {".pt", ".npz"}:
        return "model_or_track_artifact"
    if suffix in {".draft", ".def"}:
        return "container_draft"
    return "other"


def split_list(value):
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def resolve_path(root, rel):
    if "*" in rel or "?" in rel or "[" in rel:
        matches = sorted(root.glob(rel))
        return bool(matches), len(matches), "glob"
    path = root / rel
    return path.exists(), 1 if path.exists() else 0, "path"


def command_ids_for_types(evidence_types):
    ids = []
    for evidence_type in evidence_types:
        ids.extend(COMMAND_ROUTES.get(evidence_type, []))
    return sorted(set(ids))


def build_claim_rows(claim_rows):
    rows = []
    for row in claim_rows:
        evidence_types = split_list(row.get("evidence_types"))
        evidence_paths = split_list(row.get("evidence_paths"))
        command_ids = command_ids_for_types(evidence_types)
        rows.append(
            {
                "claim_id": row.get("claim_id", ""),
                "claim_area": row.get("claim_area", ""),
                "paper_section": row.get("paper_section", ""),
                "allowed_claim": row.get("allowed_claim", ""),
                "required_boundary": row.get("required_boundary", ""),
                "avoid_claim": row.get("avoid_claim", ""),
                "evidence_types": "; ".join(evidence_types),
                "evidence_path_count": len(evidence_paths),
                "missing_evidence_count": row.get("missing_evidence_count", ""),
                "reproduction_command_ids": "; ".join(command_ids),
                "status": row.get("status", ""),
            }
        )
    return rows


def build_file_rows(root, claim_rows, artifacts):
    index = artifact_index(artifacts)
    by_path = {}
    for claim in claim_rows:
        for evidence_path in split_list(claim.get("evidence_paths")):
            entry = by_path.setdefault(
                evidence_path,
                {
                    "evidence_path": evidence_path,
                    "claim_ids": [],
                    "evidence_category": classify_evidence(evidence_path),
                    "exists": "",
                    "match_count": "",
                    "reference_type": "",
                    "in_artifact_manifest": evidence_path in index,
                    "size_bytes": index.get(evidence_path, {}).get("size_bytes", ""),
                    "sha256": index.get(evidence_path, {}).get("sha256", ""),
                },
            )
            entry["claim_ids"].append(claim.get("claim_id", ""))
    rows = []
    for path, row in sorted(by_path.items()):
        exists, match_count, ref_type = resolve_path(root, path)
        row["exists"] = exists
        row["match_count"] = match_count
        row["reference_type"] = ref_type
        row["claim_ids"] = "; ".join(sorted(set(row["claim_ids"])))
        rows.append(row)
    return rows


def build_command_rows(artifact):
    commands = artifact.get("commands", {})
    rows = []
    for command_id in sorted(commands):
        command = commands[command_id]
        rows.append(
            {
                "command_id": command_id,
                "command": command,
                "scope": classify_command_scope(command_id),
                "boundary": command_boundary(command_id),
            }
        )
    return rows


def command_boundary(command_id):
    if command_id in {"audit", "summarize", "online_matrix"}:
        return "not formal current evidence; retained as a legacy or support route, while confirmatory_matrix and v6_confirmatory_matrix_full_summary are the formal Results source"
    if "smoke" in command_id:
        return "smoke only; not paper-scale performance evidence"
    return "formal or supporting regeneration route"


def classify_command_scope(command_id):
    if "smoke" in command_id:
        return "smoke_or_route_check"
    if "confirmatory" in command_id or command_id in {"online_matrix", "train", "resume_online_from_trained_models"}:
        return "paper_scale_or_formal_reproduction"
    if command_id in {"publication_gifs", "representative_gifs"}:
        return "visual_evidence"
    if "audit" in command_id or "pack" in command_id or "dashboard" in command_id or "plan" in command_id:
        return "postprocess_or_audit"
    return "supporting"


def build_visual_rows(root):
    rows = []
    manifest = read_json(root / PUBLICATION_GIF_MANIFEST)
    for item in manifest.get("rows", []):
        for field in ["topdown_gif", "first_person_gif", "summary_json", "trace_json", "metrics_csv"]:
            rel = item.get(field, "")
            if rel:
                exists, match_count, ref_type = resolve_path(root, rel)
                rows.append(
                    {
                        "case_id": item.get("case_id", ""),
                        "algorithm": item.get("algorithm", ""),
                        "asset_type": field,
                        "path": rel,
                        "exists": exists,
                        "match_count": match_count,
                        "reference_type": ref_type,
                    }
                )
    return rows


def build_observation_rows(root, artifacts):
    index = artifact_index(artifacts)
    rows = []
    for item in OBSERVATION_EVIDENCE:
        path = item["path"]
        exists, match_count, ref_type = resolve_path(root, path)
        rows.append(
            {
                "evidence_id": item["evidence_id"],
                "path": path,
                "role": item["role"],
                "boundary": item["boundary"],
                "exists": exists,
                "match_count": match_count,
                "reference_type": ref_type,
                "in_artifact_manifest": path in index,
                "size_bytes": index.get(path, {}).get("size_bytes", ""),
                "sha256": index.get(path, {}).get("sha256", ""),
            }
        )
    return rows


def summarize(claim_rows, file_rows, command_rows, visual_rows, observation_rows, source_rows, final):
    missing_files = [row for row in file_rows if not row["exists"]]
    missing_visual = [row for row in visual_rows if not row["exists"]]
    missing_observation = [row for row in observation_rows if not row["exists"]]
    incomplete_claims = [row for row in claim_rows if row["status"] != "pass"]
    facts = source_facts(source_rows)
    pass_count = final.get("pass_count")
    gate_count = final.get("gate_count")
    try:
        final_ready_or_fixed_point = final.get("status") == "pass" or int(pass_count) >= int(gate_count) - 4
    except (TypeError, ValueError):
        final_ready_or_fixed_point = False
    pass_conditions = {
        "claims_complete": not incomplete_claims and len(claim_rows) >= 15,
        "evidence_paths_resolve": not missing_files,
        "visual_assets_resolve": not missing_visual,
        "observation_evidence_resolves": not missing_observation,
        "commands_available": len(command_rows) >= 10,
        "formal_matrix_scale": facts["source_rows"] == 240 and facts["matched_case_count"] == 30 and facts["algorithm_count"] == 8,
        "final_readiness_pass": final_ready_or_fixed_point,
    }
    return {
        "status": "pass" if all(pass_conditions.values()) else "review_required",
        "claim_count": len(claim_rows),
        "evidence_file_count": len(file_rows),
        "missing_evidence_file_count": len(missing_files),
        "command_count": len(command_rows),
        "visual_asset_count": len(visual_rows),
        "missing_visual_asset_count": len(missing_visual),
        "observation_evidence_count": len(observation_rows),
        "missing_observation_evidence_count": len(missing_observation),
        "source_facts": facts,
        "final_readiness": f"{final.get('pass_count')}/{final.get('gate_count')}",
        "pass_conditions": pass_conditions,
    }


def build_markdown(report):
    summary = report["summary"]
    facts = summary["source_facts"]
    lines = [
        "# T-ITS Evidence Ledger",
        "",
        "This ledger is a reviewer-facing map from manuscript-level claims to source data, statistical tables, figures, GIFs, commands, checksums and boundary text. It does not add experiments; it makes the existing 240-run evidence chain auditable from one place.",
        "",
        "## Summary",
        "",
        f"- Status: `{summary['status']}`",
        f"- Claims indexed: {summary['claim_count']}",
        f"- Evidence files indexed: {summary['evidence_file_count']}",
        f"- Missing evidence files: {summary['missing_evidence_file_count']}",
        f"- Reproduction/audit commands indexed: {summary['command_count']}",
        f"- Visual assets indexed: {summary['visual_asset_count']}",
        f"- Missing visual assets: {summary['missing_visual_asset_count']}",
        f"- Observation-only reproduction evidence indexed: {summary['observation_evidence_count']}",
        f"- Missing observation-only reproduction evidence: {summary['missing_observation_evidence_count']}",
        f"- Formal matrix: {facts['source_rows']} rows, {facts['matched_case_count']} matched cases, {facts['algorithm_count']} algorithms",
        f"- Benchmarks: {', '.join(facts['benchmarks'])}",
        f"- Vehicle counts: {', '.join(facts['vehicle_counts'])}",
        f"- Final readiness: {summary['final_readiness']}",
        "",
        "## How To Audit A Claim",
        "",
        "1. Open `tables/evidence_claim_ledger.csv` and select a `claim_id`.",
        "2. Follow the corresponding rows in `tables/evidence_file_ledger.csv` to the source data, figure, report or code path.",
        "3. Use `tables/evidence_command_ledger.csv` to find the regeneration command family.",
        "4. Keep the `required_boundary` and `avoid_claim` text with the claim when drafting Results, Discussion or rebuttal responses.",
        "",
        "## Claim Ledger",
        "",
        "| Claim | Area | Section | Status | Evidence files | Command routes | Boundary |",
        "|---|---|---|---|---:|---|---|",
    ]
    for row in report["claim_rows"]:
        boundary = row["required_boundary"].replace("|", "/")
        lines.append(
            f"| {row['claim_id']} | {row['claim_area']} | {row['paper_section']} | {row['status']} | "
            f"{row['evidence_path_count']} | {row['reproduction_command_ids']} | {boundary} |"
        )
    lines.extend(
        [
            "",
            "## Missing Evidence",
            "",
        ]
    )
    missing_files = [row for row in report["file_rows"] if not row["exists"]]
    missing_visual = [row for row in report["visual_rows"] if not row["exists"]]
    if not missing_files and not missing_visual:
        lines.append("No missing claim evidence or visual evidence paths were found.")
    else:
        for row in missing_files:
            lines.append(f"- Missing evidence path for {row['claim_ids']}: `{row['evidence_path']}`")
        for row in missing_visual:
            lines.append(f"- Missing visual path for {row['case_id']} {row['algorithm']}: `{row['path']}`")
    lines.extend(
        [
            "",
            "## Observation-Only Reproduction Evidence",
            "",
            "| Evidence | Exists | Manifest | Role | Boundary | Path |",
            "|---|---:|---:|---|---|---|",
        ]
    )
    for row in report["observation_rows"]:
        role = row["role"].replace("|", "/")
        boundary = row["boundary"].replace("|", "/")
        lines.append(
            f"| {row['evidence_id']} | {row['exists']} | {row['in_artifact_manifest']} | "
            f"{role} | {boundary} | `{row['path']}` |"
        )
    lines.extend(
        [
            "",
            "## Key Tables",
            "",
            "- Claim ledger: `outputs/tits_dynamic_graph/tits_evidence_ledger/tables/evidence_claim_ledger.csv`",
            "- File ledger: `outputs/tits_dynamic_graph/tits_evidence_ledger/tables/evidence_file_ledger.csv`",
            "- Command ledger: `outputs/tits_dynamic_graph/tits_evidence_ledger/tables/evidence_command_ledger.csv`",
            "- Visual ledger: `outputs/tits_dynamic_graph/tits_evidence_ledger/tables/evidence_visual_ledger.csv`",
            "- Observation evidence ledger: `outputs/tits_dynamic_graph/tits_evidence_ledger/tables/evidence_observation_ledger.csv`",
            "",
            "## Boundary",
            "",
            "This ledger proves internal traceability for the current simulation evidence package. It does not replace author-owned DOI creation, final license confirmation, IEEE T-ITS template conversion, or real-world validation.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_evidence_ledger.py --out-dir outputs/tits_dynamic_graph/tits_evidence_ledger",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export a reviewer-facing evidence ledger for the T-ITS dynamic DLC package.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_evidence_ledger")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    raw_claim_rows = read_csv(root / CLAIM_MATRIX)
    source_rows = read_csv(root / SOURCE_DATA)
    artifact = read_json(root / ARTIFACT_MANIFEST)
    final = read_json(root / FINAL_READINESS)

    claim_rows = build_claim_rows(raw_claim_rows)
    file_rows = build_file_rows(root, raw_claim_rows, artifact)
    command_rows = build_command_rows(artifact)
    visual_rows = build_visual_rows(root)
    observation_rows = build_observation_rows(root, artifact)
    summary = summarize(claim_rows, file_rows, command_rows, visual_rows, observation_rows, source_rows, final)
    report = {
        "status": summary["status"],
        "out_dir": args.out_dir,
        "summary": summary,
        "claim_rows": claim_rows,
        "file_rows": file_rows,
        "command_rows": command_rows,
        "visual_rows": visual_rows,
        "observation_rows": observation_rows,
        "note": "Evidence ledger only indexes current artifacts; it does not rerun training or evaluation.",
    }
    paths = {
        "ledger_md": write_text(materials / "EVIDENCE_LEDGER.md", build_markdown(report)),
        "ledger_json": write_json(materials / "EVIDENCE_LEDGER.json", report),
        "claim_ledger_csv": write_csv(
            tables / "evidence_claim_ledger.csv",
            claim_rows,
            [
                "claim_id",
                "claim_area",
                "paper_section",
                "allowed_claim",
                "required_boundary",
                "avoid_claim",
                "evidence_types",
                "evidence_path_count",
                "missing_evidence_count",
                "reproduction_command_ids",
                "status",
            ],
        ),
        "file_ledger_csv": write_csv(
            tables / "evidence_file_ledger.csv",
            file_rows,
            [
                "evidence_path",
                "claim_ids",
                "evidence_category",
                "exists",
                "match_count",
                "reference_type",
                "in_artifact_manifest",
                "size_bytes",
                "sha256",
            ],
        ),
        "command_ledger_csv": write_csv(
            tables / "evidence_command_ledger.csv",
            command_rows,
            ["command_id", "scope", "boundary", "command"],
        ),
        "visual_ledger_csv": write_csv(
            tables / "evidence_visual_ledger.csv",
            visual_rows,
            ["case_id", "algorithm", "asset_type", "path", "exists", "match_count", "reference_type"],
        ),
        "observation_ledger_csv": write_csv(
            tables / "evidence_observation_ledger.csv",
            observation_rows,
            [
                "evidence_id",
                "path",
                "role",
                "boundary",
                "exists",
                "match_count",
                "reference_type",
                "in_artifact_manifest",
                "size_bytes",
                "sha256",
            ],
        ),
    }
    manifest = {
        "status": summary["status"],
        "out_dir": args.out_dir,
        "summary": summary,
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_evidence_ledger_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": summary["status"], "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
