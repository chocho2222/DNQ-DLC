#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dlc.graph_policy import GraphActorBundle  # noqa: E402
from dlc.graph_world_model import GraphWorldModelBundle  # noqa: E402


ALGORITHM_CARDS = "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv"
CONFIG_PATH = "configs/tits_dynamic_graph_experiments.json"
EXPECTED_ACTION_DIM = 3
HISTORICAL_BASELINE_PREFIX = "outputs/paper_multicar_overtake_20260618/models/"


def read_csv(path):
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def clean_value(value):
    if value is None:
        return ""
    value = str(value).strip()
    if value.lower() in {"", "nan", "none", "null"}:
        return ""
    return value


def artifact_type(path):
    path = str(path)
    if path.endswith(".graphworld.pt"):
        return "graph_world_model"
    if path.endswith(".graph.pt"):
        return "graph_actor"
    return "unknown"


def flatten_meta(meta):
    keys = [
        "obs_dim",
        "action_dim",
        "num_agents",
        "hidden_dim",
        "proposal_hidden_dim",
        "ego_dim",
        "opponent_dim",
        "pooling_mode",
        "use_slot_mask",
        "slot_feature_dim",
        "quality_dim",
        "max_agents_train",
        "max_neighbors",
        "neighbor_mode",
        "neighbor_selection_mode",
    ]
    out = {}
    for key in keys:
        value = meta.get(key, "")
        if isinstance(value, (list, tuple, dict)):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        out[key] = value
    return out


def load_artifact(path):
    kind = artifact_type(path)
    if kind == "graph_world_model":
        bundle = GraphWorldModelBundle.load(path, map_location="cpu")
        return kind, bundle.meta
    if kind == "graph_actor":
        bundle = GraphActorBundle.load(path, map_location="cpu")
        return kind, bundle.meta
    raise ValueError(f"unsupported model artifact extension: {path}")


def load_config_algorithms(path):
    config = read_json(path)
    return {item.get("name"): item for item in config.get("algorithms", []) if item.get("name")}


def collect_artifact_refs(cards):
    refs = {}
    crosswalk = []
    for card in cards:
        algorithm = card["algorithm"]
        kind = card.get("kind", "")
        is_rule = "rule" in kind
        for field_name in ["model_path", "quality_proposal_path"]:
            path = clean_value(card.get(field_name, ""))
            if not path:
                status = "not_applicable" if (is_rule or field_name == "quality_proposal_path") else "missing_required_model_path"
                crosswalk.append(
                    {
                        "algorithm": algorithm,
                        "label_cn": card.get("label_cn", ""),
                        "kind": kind,
                        "field_name": field_name,
                        "path": "",
                        "artifact_type": "",
                        "algorithm_card_status": status,
                        "config_algorithm_found": "",
                        "config_path_match": "",
                        "note": "规则基线不需要权重。" if is_rule else "该字段对该算法不是必需项。",
                    }
                )
                continue
            item = refs.setdefault(
                path,
                {
                    "path": path,
                    "fields": set(),
                    "algorithms": set(),
                    "labels": set(),
                    "kinds": set(),
                },
            )
            item["fields"].add(field_name)
            item["algorithms"].add(algorithm)
            item["labels"].add(card.get("label_cn", ""))
            item["kinds"].add(kind)
            crosswalk.append(
                {
                    "algorithm": algorithm,
                    "label_cn": card.get("label_cn", ""),
                    "kind": kind,
                    "field_name": field_name,
                    "path": path,
                    "artifact_type": artifact_type(path),
                    "algorithm_card_status": "path_declared",
                    "config_algorithm_found": "",
                    "config_path_match": "",
                    "note": "",
                }
            )
    return refs, crosswalk


def enrich_crosswalk_with_config(crosswalk, config_algorithms):
    for row in crosswalk:
        algorithm = row["algorithm"]
        field_name = row["field_name"]
        card_path = clean_value(row["path"])
        config_item = config_algorithms.get(algorithm)
        row["config_algorithm_found"] = bool(config_item)
        if not card_path:
            row["config_path_match"] = "not_applicable"
            continue
        config_path = clean_value(config_item.get(field_name, "")) if config_item else ""
        if not config_item:
            row["config_path_match"] = "warning_config_algorithm_missing"
            row["note"] = "正式算法卡中的算法未在 config algorithms 中找到。"
        elif config_path == card_path:
            row["config_path_match"] = "pass"
        else:
            row["config_path_match"] = "warning_path_differs"
            row["note"] = f"config 中 {field_name}={config_path or '<empty>'}"
    return crosswalk


def build_inventory(root, refs):
    rows = []
    for path, ref in sorted(refs.items()):
        full = root / path
        row = {
            "path": path,
            "artifact_type": artifact_type(path),
            "declared_fields": ";".join(sorted(ref["fields"])),
            "algorithms": ";".join(sorted(ref["algorithms"])),
            "label_cn": ";".join(sorted(label for label in ref["labels"] if label)),
            "kinds": ";".join(sorted(kind for kind in ref["kinds"] if kind)),
            "exists": full.exists(),
            "size_bytes": full.stat().st_size if full.exists() else 0,
            "sha256": sha256_file(full) if full.exists() and full.is_file() else "",
            "load_status": "",
            "load_error": "",
            "archive_note": "historical_dlc_baseline_weight" if path.startswith(HISTORICAL_BASELINE_PREFIX) else "current_tits_model_weight",
            "expected_difference_note": "",
            "blocking_error": "",
            "warning": "",
        }
        row.update(flatten_meta({}))
        if not full.exists():
            row["load_status"] = "missing"
            row["blocking_error"] = "model_path_does_not_exist"
            rows.append(row)
            continue
        if row["size_bytes"] <= 0:
            row["blocking_error"] = "empty_model_file"
        try:
            _, meta = load_artifact(full)
            row.update(flatten_meta(meta))
            row["load_status"] = "pass"
            if int(meta.get("action_dim", -1)) != EXPECTED_ACTION_DIM:
                row["blocking_error"] = f"unexpected_action_dim_{meta.get('action_dim')}"
            if path.startswith(HISTORICAL_BASELINE_PREFIX):
                row["warning"] = "baseline weight is stored in the original DLC reproduction directory; archive it with the release package."
            if meta.get("obs_dim") in {38, "38"}:
                row["expected_difference_note"] = "original DLC-style telemetry schema (obs_dim=38)"
            elif meta.get("obs_dim") in {41, "41"}:
                row["expected_difference_note"] = "dynamic-neighborhood schema with slot mask/features (obs_dim=41)"
        except Exception as exc:
            row["load_status"] = "load_failed"
            row["load_error"] = repr(exc)
            row["blocking_error"] = "model_load_failed"
        rows.append(row)
    return rows


def summarize(inventory, crosswalk):
    errors = [row for row in inventory if row.get("blocking_error")]
    warnings = [row for row in inventory if row.get("warning")]
    crosswalk_warnings = [
        row
        for row in crosswalk
        if str(row.get("config_path_match", "")).startswith("warning")
        or row.get("algorithm_card_status") == "missing_required_model_path"
    ]
    status = "pass" if not errors and not any(row.get("algorithm_card_status") == "missing_required_model_path" for row in crosswalk) else "review_required"
    return {
        "status": status,
        "artifact_count": len(inventory),
        "load_pass_count": sum(1 for row in inventory if row.get("load_status") == "pass"),
        "blocking_error_count": len(errors),
        "warning_count": len(warnings) + len(crosswalk_warnings),
        "historical_baseline_weight_count": sum(1 for row in inventory if row["archive_note"] == "historical_dlc_baseline_weight"),
        "current_tits_model_weight_count": sum(1 for row in inventory if row["archive_note"] == "current_tits_model_weight"),
        "algorithm_card_rows": len(crosswalk),
        "algorithm_card_declared_paths": sum(1 for row in crosswalk if row.get("path")),
        "algorithm_card_not_applicable_fields": sum(1 for row in crosswalk if row.get("algorithm_card_status") == "not_applicable"),
        "blocking_paths": [row["path"] for row in errors],
        "configuration_warnings": [row for row in crosswalk_warnings],
    }


def build_markdown(report):
    summary = report["summary"]
    inventory = report["inventory"]
    crosswalk = report["crosswalk"]
    lines = [
        "# T-ITS Model Artifact Integrity Audit",
        "",
        "该审计面向投稿复现：检查正式 algorithm card 中声明的模型权重是否存在、非空、可在 CPU 上加载，并记录模型 schema、checksum 与算法配置的对应关系。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        if key == "configuration_warnings":
            lines.append(f"- {key}: {len(value)}")
        else:
            lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `graph_world_model` 对应 DLC world-model bundle；`graph_actor` 对应 quality/BC proposal actor。",
            "- 当前动态邻域方法的正式权重位于 `outputs/tits_dynamic_graph/models/`。",
            "- 原始 DLC 及三个 DLC 变种权重仍位于 `outputs/paper_multicar_overtake_20260618/models/`；这些是正式 baseline 权重，已纳入本审计和发布归档路由。",
            "- `obs_dim=41` 与 `obs_dim=38` 是预期的架构差异：前者包含动态邻域 slot mask/features，后者对应早期 DLC-style telemetry schema；这不是错误。",
            "- 规则专家 baseline 无模型权重，algorithm card 中空路径记为 `not_applicable`。",
            "",
            "## Model Inventory",
            "",
            "| Type | Path | Algorithms | Load | obs_dim | action_dim | Archive note |",
            "|---|---|---|---|---:|---:|---|",
        ]
    )
    for row in inventory:
        lines.append(
            f"| {row['artifact_type']} | `{row['path']}` | {row['algorithms']} | {row['load_status']} | {row.get('obs_dim', '')} | {row.get('action_dim', '')} | {row['archive_note']} |"
        )
    blocking = [row for row in inventory if row.get("blocking_error")]
    lines.extend(["", "## Blocking Errors", ""])
    if not blocking:
        lines.append("No blocking model artifact errors were found.")
    else:
        lines.extend(["| Path | Error | Load error |", "|---|---|---|"])
        for row in blocking:
            lines.append(f"| `{row['path']}` | {row['blocking_error']} | {row['load_error']} |")
    warnings = [row for row in inventory if row.get("warning")]
    config_warnings = summary.get("configuration_warnings", [])
    lines.extend(["", "## Warnings and Release Notes", ""])
    if not warnings and not config_warnings:
        lines.append("No non-blocking warnings were found.")
    else:
        for row in warnings:
            lines.append(f"- `{row['path']}`: {row['warning']}")
        for row in config_warnings:
            lines.append(
                f"- `{row['algorithm']}` `{row['field_name']}`: {row.get('config_path_match')} {row.get('note', '')}"
            )
    lines.extend(
        [
            "",
            "## Algorithm-to-Artifact Crosswalk",
            "",
            "| Algorithm | Field | Path | Config match | Status |",
            "|---|---|---|---|---|",
        ]
    )
    for row in crosswalk:
        path = f"`{row['path']}`" if row["path"] else ""
        lines.append(
            f"| {row['algorithm']} | {row['field_name']} | {path} | {row['config_path_match']} | {row['algorithm_card_status']} |"
        )
    lines.extend(
        [
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_model_artifact_integrity_audit.py --out-dir outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit model artifacts used by the formal T-ITS benchmark algorithms.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--algorithm-cards", default=ALGORITHM_CARDS)
    parser.add_argument("--config", default=CONFIG_PATH)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    cards = read_csv(root / args.algorithm_cards)
    config_algorithms = load_config_algorithms(root / args.config)
    refs, crosswalk = collect_artifact_refs(cards)
    crosswalk = enrich_crosswalk_with_config(crosswalk, config_algorithms)
    inventory = build_inventory(root, refs)
    report = {
        "status": "pending",
        "out_dir": args.out_dir,
        "algorithm_cards": args.algorithm_cards,
        "config": args.config,
        "inventory": inventory,
        "crosswalk": crosswalk,
        "note": "This audit verifies artifact presence, loadability, checksum provenance, and algorithm-card/config consistency. It does not evaluate driving performance.",
    }
    report["summary"] = summarize(inventory, crosswalk)
    report["status"] = report["summary"]["status"]

    inventory_fields = [
        "path",
        "artifact_type",
        "declared_fields",
        "algorithms",
        "label_cn",
        "kinds",
        "exists",
        "size_bytes",
        "sha256",
        "load_status",
        "load_error",
        "archive_note",
        "expected_difference_note",
        "obs_dim",
        "action_dim",
        "num_agents",
        "hidden_dim",
        "proposal_hidden_dim",
        "ego_dim",
        "opponent_dim",
        "pooling_mode",
        "use_slot_mask",
        "slot_feature_dim",
        "quality_dim",
        "max_agents_train",
        "max_neighbors",
        "neighbor_mode",
        "neighbor_selection_mode",
        "blocking_error",
        "warning",
    ]
    crosswalk_fields = [
        "algorithm",
        "label_cn",
        "kind",
        "field_name",
        "path",
        "artifact_type",
        "algorithm_card_status",
        "config_algorithm_found",
        "config_path_match",
        "note",
    ]
    paths = {
        "audit_md": write_text(materials / "MODEL_ARTIFACT_INTEGRITY_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "MODEL_ARTIFACT_INTEGRITY_AUDIT.json", report),
        "model_inventory_csv": write_csv(tables / "model_artifact_inventory.csv", inventory, inventory_fields),
        "algorithm_crosswalk_csv": write_csv(tables / "model_algorithm_path_crosswalk.csv", crosswalk, crosswalk_fields),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_model_artifact_integrity_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
