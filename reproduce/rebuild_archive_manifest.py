#!/usr/bin/env python
"""Rebuild the local integrity record for the release package.

The manifest covers every release file except Git metadata, caches and the three
self-referential manifest files. Run it from anywhere; paths resolve against the
repository root.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "materials"
SELF = {
    "materials/RELEASE_ARCHIVE_MANIFEST.md",
    "materials/RELEASE_ARCHIVE_MANIFEST.json",
    "materials/RELEASE_ARCHIVE_MANIFEST.csv",
}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "dnq_dlc.egg-info"}


def category(rel: str) -> str:
    top = rel.split("/")[0]
    if top in {"code", "reproduce"}:
        return "code"
    if top in {"checkpoints", "configs", "docs", "source_data", "paper"}:
        return top
    return "governance"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        parts = path.relative_to(ROOT).parts
        rel = path.relative_to(ROOT).as_posix()
        if rel in SELF or any(part in SKIP_DIRS for part in parts):
            continue
        files.append({
            "path": rel,
            "category": category(rel),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })

    by_category: dict[str, dict[str, int]] = {}
    for entry in files:
        bucket = by_category.setdefault(entry["category"], {"file_count": 0, "size_bytes": 0})
        bucket["file_count"] += 1
        bucket["size_bytes"] += entry["size_bytes"]

    summary = {
        "file_count": len(files),
        "size_bytes": sum(entry["size_bytes"] for entry in files),
        "by_category": dict(sorted(by_category.items())),
    }
    manifest = {
        "root": ".",
        "release_status": "private_github_release_candidate",
        "external_archive": {
            "doi": None,
            "url": None,
            "note": "No external DOI or repository accession has been assigned yet.",
        },
        "summary": summary,
        "files": files,
    }
    MATERIALS.mkdir(parents=True, exist_ok=True)
    (MATERIALS / "RELEASE_ARCHIVE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    with (MATERIALS / "RELEASE_ARCHIVE_MANIFEST.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "category", "size_bytes", "sha256"])
        for entry in files:
            writer.writerow([entry["path"], entry["category"], entry["size_bytes"], entry["sha256"]])

    lines = [
        "# Release Archive Manifest",
        "",
        "Local integrity record for the DNQ-DLC GitHub and archival release.",
        "",
        "## Status",
        "",
        "- Release status: `private_github_release_candidate`",
        "- External DOI: not assigned",
        "- External archive URL: not assigned",
        f"- File count: {summary['file_count']}",
        f"- Total size: {summary['size_bytes']} bytes",
        "",
        "## Category summary",
        "",
        "| Category | Files | Size (bytes) |",
        "|---|---:|---:|",
    ]
    for name, bucket in summary["by_category"].items():
        lines.append(f"| {name} | {bucket['file_count']} | {bucket['size_bytes']} |")
    lines += [
        "",
        "## Integrity",
        "",
        "SHA-256 values cover every release file except Git metadata, generated",
        "build/output/cache directories, and the three self-referential manifest",
        "files. Regenerate after any release-package change:",
        "",
        "```bash",
        "python reproduce/rebuild_archive_manifest.py",
        "```",
        "",
        "Complete checksums are in `RELEASE_ARCHIVE_MANIFEST.csv` and",
        "`RELEASE_ARCHIVE_MANIFEST.json`.",
        "",
    ]
    (MATERIALS / "RELEASE_ARCHIVE_MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{summary['file_count']} files, {summary['size_bytes']} bytes")


if __name__ == "__main__":
    main()
