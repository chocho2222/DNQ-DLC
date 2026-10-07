#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


CORE_REPO_FILES = [
    "README.md",
    "LICENSE",
    "environment.yml",
    "setup.py",
    "Makefile",
    ".gitignore",
]
CORE_REPO_DIRS = [
    "configs",
    "dlc",
    "docs",
    "gym_multi_car_racing",
    "scripts",
    "tracks",
]
RECOMMENDED_DRAFT_FILES = [
    "CITATION.cff",
    "CONTRIBUTING.md",
    "MODEL_CARD.md",
    "DATA_CARD.md",
]


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


def load_json(path):
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


def exists_nonempty(path):
    path = Path(path)
    return path.exists() and (path.is_dir() or path.stat().st_size > 0)


def build_repo_file_rows(root):
    rows = []
    for rel in CORE_REPO_FILES:
        path = root / rel
        rows.append(
            {
                "path": rel,
                "kind": "file",
                "recommended_role": "public_code_repository",
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
                "action": "keep" if path.exists() else "create_before_release",
            }
        )
    for rel in CORE_REPO_DIRS:
        path = root / rel
        rows.append(
            {
                "path": rel,
                "kind": "directory",
                "recommended_role": "public_code_repository",
                "exists": path.exists() and path.is_dir(),
                "size_bytes": sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) if path.exists() and path.is_dir() else 0,
                "action": "keep" if path.exists() and path.is_dir() else "create_or_restore_before_release",
            }
        )
    for rel in RECOMMENDED_DRAFT_FILES:
        path = root / rel
        rows.append(
            {
                "path": rel,
                "kind": "recommended_metadata_file",
                "recommended_role": "public_code_repository",
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
                "action": "optional_create_from_draft" if not path.exists() else "keep",
            }
        )
    return rows


def build_author_action_rows(repo_rows):
    rows = []
    for rel in ["CITATION.cff", "CONTRIBUTING.md", "MODEL_CARD.md", "DATA_CARD.md"]:
        existing = next((row for row in repo_rows if row["path"] == rel), None)
        rows.append(
            {
                "item": rel,
                "status": "exists" if existing and existing["exists"] else "draft_available",
                "evidence": f"outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/{rel.replace('.', '_')}_DRAFT.md",
                "author_action": "Copy/adapt draft into repository root before public release if desired.",
            }
        )
    rows.extend(
        [
            {
                "item": "README.md",
                "status": "replacement_draft_available",
                "evidence": "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_README_DRAFT.md",
                "author_action": "Replace or prepend the legacy README with the T-ITS method/reproduction-focused draft before GitHub release.",
            },
            {
                "item": "release tag",
                "status": "author_action_required",
                "evidence": "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv",
                "author_action": "Create a public release tag after DOI/data-archive deposition and rerun checksum manifest.",
            },
            {
                "item": "large artifacts",
                "status": "data_archive_required",
                "evidence": "outputs/tits_dynamic_graph/public_release_plan/PUBLIC_RELEASE_PLAN.md",
                "author_action": "Keep large model/output artifacts in data release assets or archive rather than bloating the code repository.",
            },
        ]
    )
    return rows


def build_readme_draft():
    return """# Dynamic-Neighborhood World Models for Online Multi-Car Overtaking

This repository contains the code, configuration files and reproducibility route for a T-ITS-oriented simulation study of online multi-car overtaking. The method extends a DLC-style world-model controller with runtime dynamic-neighborhood graph construction, overtake-aware candidate planning and safety-oriented scoring.

## What This Repository Reproduces

- Online multi-car overtaking with the ego vehicle starting from the last grid position.
- Dynamic-neighborhood graph construction with a fixed neighbor budget and runtime vehicle selection.
- Comparisons against original DLC world model variants and a rule-based expert.
- Confirmatory evaluation over 30 matched cases and 240 algorithm-runs.
- Procedural tracks, 8-vehicle extrapolation and a Monza CSV-derived external track.
- Source data, paired statistics, failure diagnostics, visual evidence and artifact checksums.

## Minimal Setup

```bash
conda env create -f environment.yml
conda run -n vlm_planner python -m pip install -e . --no-deps
```

The locally validated Python executable is:

```bash
/home/itrc/.conda/envs/vlm_planner/bin/python
```

## Reviewer Smoke Test

Use this only to verify imports and the evaluation path; it is not a paper-scale result.

```bash
bash outputs/tits_dynamic_graph/reviewer_replication_packet/run_reviewer_smoke.sh
```

## Reproduce the Confirmatory Evidence

The frozen per-case commands are stored in:

```text
outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv
```

The full benchmark source data are stored in:

```text
outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv
```

The main reviewer route is:

```text
outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md
```

## Important Boundaries

- Results are simulation-only and do not certify real-vehicle deployment safety.
- The current external-track evidence uses one Monza CSV-derived track.
- Vehicle-count extrapolation is evaluated up to 8 vehicles.
- GIFs are representative visual evidence, not replacements for the quantitative matrix.
- Smoke, optimization and historical sweep outputs should not be cited as formal results.

## Data and Artifact Release

Large outputs, model weights, publication GIFs and source-data tables should be released through a data archive or release assets. The current routing plan is:

```text
outputs/tits_dynamic_graph/public_release_plan/PUBLIC_RELEASE_PLAN.md
```

The checksum manifest is:

```text
outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv
```

## License and Citation

Confirm the final code/model/data license before public release. Use the generated citation draft in:

```text
outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/CITATION_cff_DRAFT.md
```
"""


def build_citation_draft():
    return """# CITATION.cff Draft

```yaml
cff-version: 1.2.0
title: Dynamic-Neighborhood World Models for Online Multi-Car Overtaking
message: If you use this code or data package, please cite the associated paper and archived release.
type: software
authors:
  - family-names: TODO
    given-names: TODO
repository-code: https://github.com/TODO/TODO
url: https://doi.org/TODO
date-released: 2026-XX-XX
version: v1.0.0
license: TODO
keywords:
  - autonomous driving
  - overtaking
  - world model
  - multi-agent systems
  - reproducible research
```

Author-side action: replace TODO fields after final repository URL, DOI/accession, license and author metadata are known.
"""


def build_contributing_draft():
    return """# CONTRIBUTING.md Draft

Thank you for your interest in contributing. This repository is prepared primarily as a reproducibility package for a simulation study.

## Scope

Contributions should preserve the frozen benchmark protocol unless they are explicitly marked as new experiments. Please do not mix smoke outputs, tuning sweeps or exploratory runs with the formal confirmatory matrix.

## Reproducibility Rules

- Record exact commands, seeds, device settings and output directories.
- Keep source data and figure scripts versioned or archived.
- Regenerate artifact manifests after modifying formal evidence.
- Do not overwrite baseline weights or source data without documenting provenance.

## Pull Request Checklist

- The changed code has a smoke test or a reason why one is not applicable.
- New figures include source data.
- New benchmark claims include matched-case source data.
- Documentation distinguishes formal results from exploratory outputs.
"""


def build_model_card_draft():
    return """# MODEL_CARD.md Draft

## Model Family

Dynamic-neighborhood DLC-style graph world model for online multi-car overtaking.

## Intended Use

Simulation-based evaluation of autonomous overtaking controllers under the provided benchmark protocol.

## Not Intended For

Real-vehicle deployment, certified collision avoidance, legal compliance decisions or arbitrary traffic-density claims.

## Inputs

Telemetry-derived ego and neighbor states, dynamically selected nearby vehicles, slot masks and candidate actions.

## Outputs

Short-horizon progress, risk and quality-related predictions used by an online planner.

## Training and Evaluation Evidence

See `outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/` and `outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/`.
"""


def build_data_card_draft():
    return """# DATA_CARD.md Draft

## Dataset

Frozen online benchmark source data for the dynamic-neighborhood DLC world-model overtaking study.

## Primary Source File

`outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv`

## Coverage

30 matched benchmark cases, 8 algorithms per case and 240 algorithm-runs across procedural tracks, an 8-vehicle extrapolation setting and a Monza CSV-derived external track.

## Limitations

Simulation-only evidence; no real-vehicle data; external-track evidence currently includes one Monza-derived track.

## Provenance

Use the frozen case commands, summary JSON files and SHA256 artifact manifest to trace every reported result.
"""


def build_pack_md(summary):
    lines = [
        "# GitHub Release Readiness Pack",
        "",
        "该包把当前 T-ITS 证据链转换为 GitHub 开源发布前的最小仓库清单、README 草稿、引用文件草稿和贡献说明草稿。它不移动或删除现有文件，也不替代最终 license、DOI、仓库 URL 和 release tag。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Recommended Author Actions",
            "",
            "1. 用 `GITHUB_README_DRAFT.md` 替换或前置当前 legacy README 的 T-ITS 方法说明。",
            "2. 根据 `CITATION_cff_DRAFT.md` 创建正式 `CITATION.cff`，填入 DOI、作者和 license。",
            "3. 根据 `CONTRIBUTING_md_DRAFT.md` 创建贡献指南，强调 formal matrix 与 smoke/tuning 产物边界。",
            "4. 将大体量模型、GIF、source data 和审计包放入数据仓库或 release assets，不要塞进轻量代码仓库。",
            "5. 公开 release tag 后重跑 artifact manifest、public release plan 和 cross-reference audit。",
            "",
            "## Draft Files",
            "",
            "- `outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_README_DRAFT.md`",
            "- `outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/CITATION_cff_DRAFT.md`",
            "- `outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/CONTRIBUTING_md_DRAFT.md`",
            "- `outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/MODEL_CARD_md_DRAFT.md`",
            "- `outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/DATA_CARD_md_DRAFT.md`",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_github_release_readiness_pack.py --out-dir outputs/tits_dynamic_graph/tits_github_release_readiness_pack",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export GitHub release readiness pack for the T-ITS dynamic graph repository.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_github_release_readiness_pack")
    parser.add_argument("--public-release-file-plan", default="outputs/tits_dynamic_graph/public_release_plan/public_release_file_plan.csv")
    parser.add_argument("--artifact", default="outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    repo_rows = build_repo_file_rows(root)
    action_rows = build_author_action_rows(repo_rows)
    release_rows = read_csv(root / args.public_release_file_plan)
    artifact = load_json(root / args.artifact)
    critical_missing = [
        row["path"]
        for row in repo_rows
        if row["path"] in {"README.md", "LICENSE", "environment.yml", "setup.py"} and not row["exists"]
    ]
    public_code_count = sum(1 for row in release_rows if row.get("release_role") == "public_code_repository")
    mandatory_archive_count = sum(1 for row in release_rows if row.get("release_role") == "mandatory_data_archive")
    summary = {
        "status": "pass" if not critical_missing else "review_required",
        "critical_missing_count": len(critical_missing),
        "critical_missing": critical_missing,
        "repo_inventory_rows": len(repo_rows),
        "author_action_rows": len(action_rows),
        "public_code_file_count_from_release_plan": public_code_count,
        "mandatory_archive_file_count_from_release_plan": mandatory_archive_count,
        "artifact_manifest_files": artifact.get("summary", {}).get("file_count"),
        "note": "Drafts are generated for GitHub release preparation; final DOI, URL, license and author metadata remain author-owned.",
    }
    paths = {
        "pack_md": "",
        "readme_draft": write_text(materials / "GITHUB_README_DRAFT.md", build_readme_draft()),
        "citation_draft": write_text(materials / "CITATION_cff_DRAFT.md", build_citation_draft()),
        "contributing_draft": write_text(materials / "CONTRIBUTING_md_DRAFT.md", build_contributing_draft()),
        "model_card_draft": write_text(materials / "MODEL_CARD_md_DRAFT.md", build_model_card_draft()),
        "data_card_draft": write_text(materials / "DATA_CARD_md_DRAFT.md", build_data_card_draft()),
        "repo_inventory_csv": write_csv(tables / "github_repository_inventory.csv", repo_rows, ["path", "kind", "recommended_role", "exists", "size_bytes", "action"]),
        "author_actions_csv": write_csv(tables / "github_release_author_actions.csv", action_rows, ["item", "status", "evidence", "author_action"]),
        "qa_json": "",
    }
    qa = {
        "status": summary["status"],
        "checks": {
            "critical_repo_files_present": len(critical_missing) == 0,
            "readme_draft_created": True,
            "citation_draft_created": True,
            "contributing_draft_created": True,
            "model_card_draft_created": True,
            "data_card_draft_created": True,
            "release_plan_available": bool(release_rows),
            "artifact_manifest_available": bool(artifact),
        },
    }
    paths["qa_json"] = write_json(materials / "GITHUB_RELEASE_READINESS_QA.json", qa)
    paths["pack_md"] = write_text(materials / "GITHUB_RELEASE_READINESS_PACK.md", build_pack_md(summary))
    manifest = {
        "status": summary["status"],
        "out_dir": args.out_dir,
        "summary": summary,
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_github_release_readiness_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": summary["status"], "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
