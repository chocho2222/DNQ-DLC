#!/usr/bin/env python
"""Audit and freeze the local DNQ-DLC static release candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="outputs/tits_dynamic_graph_expanded/DNQ_DLC_video_evidence_public_site")
    args = parser.parse_args()
    site = Path(args.site)
    index = (site / "index.html").read_text(encoding="utf-8")

    references = []
    for attribute in ("href", "src"):
        references.extend(re.findall(attribute + r'=\"([^\"]+)\"', index))
    references = sorted(set(
        ref for ref in references
        if not ref.startswith(("http:", "https:", "mailto:", "#"))
    ))
    missing = [ref for ref in references if not (site / ref).exists()]
    audit = {
        "checked_date": "2026-07-16",
        "relative_link_count": len(references),
        "missing": missing,
    }
    audit_path = site / "tables/public_site_link_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    if missing:
        raise SystemExit(f"Missing relative links: {missing}")

    contents = []
    for path in sorted(site.rglob("*")):
        if not path.is_file() or path.name == "revision_manifest.json":
            continue
        contents.append({
            "path": path.relative_to(site).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    manifest = {
        "status": "local_release_bundle_ready",
        "checked_date": "2026-07-16",
        "public_url": None,
        "file_count": len(contents),
        "contents": contents,
    }
    (site / "revision_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    zip_path = site.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(site.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(site.parent))

    print(json.dumps({
        "status": "pass",
        "site": str(site),
        "relative_links": len(references),
        "manifest_files": len(contents),
        "zip": str(zip_path),
        "zip_size_bytes": zip_path.stat().st_size,
    }, indent=2))


if __name__ == "__main__":
    main()
