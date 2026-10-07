#!/usr/bin/env python
"""Refresh the manifest after derived analysis artifacts are generated."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "outputs/tits_dynamic_graph_expanded/current_paper_data_20260916"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    status = json.loads((PACK / "status.json").read_text(encoding="utf-8"))
    files = []
    for path in sorted(PACK.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files.append({
                "path": str(path.relative_to(PACK)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    manifest = {
        "root": str(PACK),
        "status": status,
        "files": files,
        "analysis_included": any(x["path"].startswith("analysis/") for x in files),
    }
    (PACK / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(files), "analysis_included": manifest["analysis_included"]}, indent=2))


if __name__ == "__main__":
    main()
