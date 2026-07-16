#!/usr/bin/env python
"""Build deterministic release manifests for the public research package."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "materials"
OUTPUT_NAMES = {
    "RELEASE_ARCHIVE_MANIFEST.csv",
    "RELEASE_ARCHIVE_MANIFEST.json",
    "RELEASE_ARCHIVE_MANIFEST.md",
}
EXCLUDED_PARTS = {
    ".git",
    "__pycache__",
    "build",
    "dist",
    "outputs",
}


def is_included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS or part.endswith(".egg-info") for part in relative.parts):
        return False
    if path.parent == MATERIALS and path.name in OUTPUT_NAMES:
        return False
    return path.is_file()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def category(path: str) -> str:
    top = path.split("/", 1)[0]
    if top in {"checkpoints", "code", "configs", "docs", "source_data"}:
        return top
    if top == "materials":
        return "materials"
    return "governance"


def build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(ROOT.rglob("*")):
        if not is_included(path):
            continue
        relative = path.relative_to(ROOT).as_posix()
        rows.append(
            {
                "path": relative,
                "category": category(relative),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return rows


def summary(rows: list[dict[str, object]]) -> dict[str, object]:
    grouped: dict[str, dict[str, int]] = defaultdict(
        lambda: {"file_count": 0, "size_bytes": 0}
    )
    for row in rows:
        item = grouped[str(row["category"])]
        item["file_count"] += 1
        item["size_bytes"] += int(row["size_bytes"])
    return {
        "file_count": len(rows),
        "size_bytes": sum(int(row["size_bytes"]) for row in rows),
        "by_category": dict(sorted(grouped.items())),
    }


def write_csv(rows: list[dict[str, object]]) -> None:
    path = MATERIALS / "RELEASE_ARCHIVE_MANIFEST.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["path", "category", "size_bytes", "sha256"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: list[dict[str, object]], report: dict[str, object]) -> None:
    payload = {
        "root": ".",
        "release_status": "local_manifest_only",
        "external_archive": {
            "doi": None,
            "url": None,
            "note": "No external DOI or repository accession has been assigned yet.",
        },
        "summary": report,
        "files": rows,
    }
    path = MATERIALS / "RELEASE_ARCHIVE_MANIFEST.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(report: dict[str, object]) -> None:
    lines = [
        "# Release Archive Manifest",
        "",
        "Local integrity record for the DNQ-DLC GitHub and archival release.",
        "",
        "## Status",
        "",
        "- Release status: `local_manifest_only`",
        "- External DOI: not assigned",
        "- External archive URL: not assigned",
        f"- File count: {report['file_count']}",
        f"- Total size: {report['size_bytes']} bytes",
        "",
        "## Category summary",
        "",
        "| Category | Files | Size (bytes) |",
        "|---|---:|---:|",
    ]
    categories = report["by_category"]
    assert isinstance(categories, dict)
    for name, values in categories.items():
        lines.append(
            f"| {name} | {values['file_count']} | {values['size_bytes']} |"
        )
    lines.extend(
        [
            "",
            "## Integrity",
            "",
            "SHA-256 values cover every release file except Git metadata, generated",
            "build/output/cache directories, and the three self-referential manifest",
            "files. Regenerate after any release-package change:",
            "",
            "```bash",
            "python code/build_release_manifest.py",
            "```",
            "",
            "Complete checksums are in `RELEASE_ARCHIVE_MANIFEST.csv` and",
            "`RELEASE_ARCHIVE_MANIFEST.json`.",
            "",
        ]
    )
    path = MATERIALS / "RELEASE_ARCHIVE_MANIFEST.md"
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    MATERIALS.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    report = summary(rows)
    write_csv(rows)
    write_json(rows, report)
    write_markdown(report)
    print(
        f"Wrote {len(rows)} checksums covering "
        f"{report['size_bytes']} bytes to {MATERIALS}"
    )


if __name__ == "__main__":
    main()
