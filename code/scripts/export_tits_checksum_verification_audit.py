#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import hashlib
import json
from pathlib import Path


DEFAULT_MANIFEST = "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json"

KEY_EXACT_PATHS = {
    "configs/tits_dynamic_graph_experiments.json",
    "scripts/export_tits_checksum_verification_audit.py",
    "dlc/graph_world_model.py",
    "dlc/graph_policy.py",
    "gym_multi_car_racing/multi_car_racing.py",
    "README.md",
    "environment.yml",
    "Makefile",
}

KEY_PATH_SUBSTRINGS = [
    "v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv",
    "v6_confirmatory_matrix_full_summary/tables/online_benchmark_main_results.md",
    "v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv",
    "tits_confirmatory_evidence_pack/",
    "publication_gifs/publication_gif_manifest",
    "tits_model_artifact_integrity_audit/",
    "tracks/monza_scaled",
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


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def is_key_file(rel_path):
    return rel_path in KEY_EXACT_PATHS or any(token in rel_path for token in KEY_PATH_SUBSTRINGS)


def select_manifest_rows(manifest, full=False):
    files = manifest.get("files", [])
    if full:
        return files
    selected = [row for row in files if is_key_file(row.get("path", ""))]
    # Keep a small deterministic sample from large formal output categories so
    # the default audit stays quick while still checking manifest diversity.
    seen = {row.get("path") for row in selected}
    for prefix in [
        "outputs/tits_dynamic_graph/v6_confirmatory_matrix/",
        "outputs/tits_dynamic_graph/models/",
        "outputs/tits_dynamic_graph/publication_gifs/",
        "outputs/paper_multicar_overtake_20260618/models/",
    ]:
        picked = 0
        for row in files:
            rel = row.get("path", "")
            if rel in seen or not rel.startswith(prefix):
                continue
            selected.append(row)
            seen.add(rel)
            picked += 1
            if picked >= 3:
                break
    return selected


def verify_rows(root, manifest_rows):
    rows = []
    for item in sorted(manifest_rows, key=lambda row: row.get("path", "")):
        rel = item.get("path", "")
        expected = item.get("sha256", "")
        path = root / rel
        exists = path.exists() and path.is_file()
        actual = sha256_file(path) if exists else ""
        size_bytes = path.stat().st_size if exists else 0
        expected_size = int(item.get("size_bytes", 0) or 0)
        if not exists:
            status = "missing"
        elif actual != expected:
            status = "checksum_mismatch"
        elif size_bytes != expected_size:
            status = "size_mismatch"
        else:
            status = "pass"
        rows.append(
            {
                "path": rel,
                "category": item.get("category", ""),
                "expected_size_bytes": expected_size,
                "observed_size_bytes": size_bytes,
                "expected_sha256": expected,
                "observed_sha256": actual,
                "status": status,
            }
        )
    return rows


def summarize(rows, manifest, mode):
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    blocking = [row for row in rows if row["status"] != "pass"]
    return {
        "status": "pass" if not blocking and rows else "review_required",
        "mode": mode,
        "manifest_file_count": manifest.get("summary", {}).get("file_count"),
        "verified_file_count": len(rows),
        "pass_count": counts.get("pass", 0),
        "missing_count": counts.get("missing", 0),
        "checksum_mismatch_count": counts.get("checksum_mismatch", 0),
        "size_mismatch_count": counts.get("size_mismatch", 0),
        "status_counts": dict(sorted(counts.items())),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Checksum Verification Audit",
        "",
        "该审计从 artifact manifest 读取 SHA256 与文件大小记录，然后在当前工作区独立重算关键 artifact 的 SHA256，用于证明 manifest 不是孤立清单，而是可以被第三方重新校验的完整性证据。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Verification Scope",
            "",
            "- 默认模式覆盖 source data、case commands、主结果表、确认性证据包、publication GIF manifest、模型完整性审计、模型/轨道/核心代码样本和关键配置。",
            "- 默认模式刻意排除 final dashboard、status snapshot、evidence ledger、claim numeric audit、reproducibility capsule、release plan 和 artifact manifest 自身，因为这些文件会在 gate refresh 的固定点过程中继续更新；最终 DOI/release freeze 后可用 `--full` 做全量归档校验。",
            "",
            "## Blocking Rows",
            "",
        ]
    )
    blocking = [row for row in report["rows"] if row["status"] != "pass"]
    if not blocking:
        lines.append("No missing files, size mismatches, or SHA256 mismatches were found in the verified scope.")
    else:
        lines.extend(["| status | path | expected sha256 | observed sha256 |", "|---|---|---|---|"])
        for row in blocking:
            lines.append(
                f"| {row['status']} | `{row['path']}` | `{row['expected_sha256']}` | `{row['observed_sha256']}` |"
            )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- PASS 表示本地当前文件内容与当前 artifact manifest 在校验范围内一致。",
            "- 默认模式不是全量归档校验；最终上传或 DOI freeze 前建议运行 `--full` 并保存输出。",
            "- `--full` 应在所有 dashboard、release plan、status snapshot 和 manifest 都冻结后运行，否则自引用/固定点产物会产生预期内的 checksum 漂移。",
            "",
            "## Regeneration Commands",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_checksum_verification_audit.py --out-dir outputs/tits_dynamic_graph/tits_checksum_verification_audit",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_checksum_verification_audit.py --full --out-dir outputs/tits_dynamic_graph/tits_checksum_verification_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Verify selected or full SHA256 entries from the T-ITS artifact manifest.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--artifact-manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_checksum_verification_audit")
    parser.add_argument("--full", action="store_true", help="Verify every file in the artifact manifest instead of the key-file scope.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest = read_json(root / args.artifact_manifest)
    selected = select_manifest_rows(manifest, full=args.full)
    rows = verify_rows(root, selected)
    mode = "full" if args.full else "key_scope"
    summary = summarize(rows, manifest, mode)
    report = {
        "status": summary["status"],
        "root": str(root),
        "artifact_manifest": args.artifact_manifest,
        "summary": summary,
        "rows": rows,
        "note": "This audit independently recomputes local SHA256 values from the manifest scope; it does not upload, archive, or certify external DOI content.",
    }
    out_dir = root / args.out_dir
    paths = {
        "audit_md": write_text(out_dir / "materials" / "CHECKSUM_VERIFICATION_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(out_dir / "materials" / "CHECKSUM_VERIFICATION_AUDIT.json", report),
        "rows_csv": write_csv(
            out_dir / "tables" / "checksum_verification_rows.csv",
            rows,
            [
                "path",
                "category",
                "expected_size_bytes",
                "observed_size_bytes",
                "expected_sha256",
                "observed_sha256",
                "status",
            ],
        ),
    }
    manifest_out = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "artifact_manifest": args.artifact_manifest,
        "summary": summary,
        "paths": paths,
        "boundary": report["note"],
    }
    manifest_path = write_json(out_dir / "tits_checksum_verification_audit_manifest.json", manifest_out)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
