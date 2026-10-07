#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export a clean public-ready static site for DNQ-DLC video evidence."""

import json
import re
import shutil
import zipfile
from pathlib import Path


SRC = Path("outputs/tits_dynamic_graph_expanded/topjournal_video_evidence_pack_v1")
OUT = Path("outputs/tits_dynamic_graph_expanded/DNQ_DLC_video_evidence_public_site")
ZIP_PATH = Path("outputs/tits_dynamic_graph_expanded/DNQ_DLC_video_evidence_public_site.zip")


def referenced_paths(index_text):
    refs = set()
    for attr in ["href", "src"]:
        for match in re.finditer(attr + r'="([^"]+)"', index_text):
            url = match.group(1)
            if url.startswith(("http:", "https:", "mailto:", "#")):
                continue
            refs.add(url)
    return sorted(refs)


def copy_public_site():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    index_text = (SRC / "index.html").read_text(encoding="utf-8")
    refs = referenced_paths(index_text)
    missing = []

    (OUT / "index.html").write_text(index_text, encoding="utf-8")
    for ref in refs:
        src = SRC / ref
        dst = OUT / ref
        if not src.exists():
            missing.append(ref)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    readme = """# DNQ-DLC Video Evidence Public Site

This directory is a clean static website for public review of DNQ-DLC video evidence.

Open `index.html` locally, or upload the whole directory to any static host:

- GitHub Pages
- Netlify Drop
- Vercel static project
- Nginx/Apache server
- University web hosting

The site uses only relative links. It contains MP4 videos, source CSV/JSON files,
and analysis figures referenced by the webpage. It intentionally excludes stale
GIFs, screenshots, and rejected weak videos.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    return refs, missing


def make_zip():
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUT.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(OUT.parent))


def main():
    refs, missing = copy_public_site()
    make_zip()
    report = {
        "public_site_dir": OUT.as_posix(),
        "zip": ZIP_PATH.as_posix(),
        "referenced_file_count": len(refs),
        "missing": missing,
        "zip_size_bytes": ZIP_PATH.stat().st_size,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
