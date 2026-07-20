#!/usr/bin/env python
"""Build the deterministic checksum manifest for the documentation site."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUTPUT = DOCS / "revision_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    contents = []
    for path in sorted(DOCS.rglob("*")):
        if not path.is_file() or path == OUTPUT or "__pycache__" in path.parts:
            continue
        contents.append(
            {
                "path": path.relative_to(DOCS).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    payload = {
        "status": "private_release_bundle_ready",
        "checked_date": date.today().isoformat(),
        "public_url": None,
        "reserved_public_url": "https://chocho2222.github.io/DNQ-DLC/",
        "file_count": len(contents),
        "contents": contents,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(contents)} documentation checksums to {OUTPUT}")


if __name__ == "__main__":
    main()
