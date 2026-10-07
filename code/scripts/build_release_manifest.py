#!/usr/bin/env python
"""Content digest for the released evaluation artifacts.

The manuscript has to point at an identifier that cannot silently change. A
content digest over the released files is such an identifier: it is derived from
the bytes, so any later edit produces a different value and the statement in the
paper stops matching the artifact.

The digest is computed over a sorted (relative path, SHA-256) listing, which
makes it independent of file order and of the absolute location of the
directory.

Usage:
    python3 scripts/build_release_manifest.py --root <dir> [--root <dir> ...] \
        --out <manifest.json> [--tag tits-2026-09-20] [--include-suffix .pt .json]
"""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", required=True,
                        help="repeat once per released directory or file")
    parser.add_argument("--out", required=True)
    parser.add_argument("--tag", default="")
    parser.add_argument("--include-suffix", nargs="*", default=[])
    parser.add_argument("--skip-dir", nargs="*", default=[".git", "__pycache__"])
    args = parser.parse_args()

    roots = [Path(item).resolve() for item in args.root]
    entries = []
    for root in roots:
        candidates = [root] if root.is_file() else sorted(root.rglob("*"))
        base = root.parent if root.is_file() else root
        for path in candidates:
            if not path.is_file():
                continue
            if any(part in args.skip_dir for part in path.parts):
                continue
            if args.include_suffix and path.suffix not in args.include_suffix:
                continue
            entries.append({"root": base.name,
                            "path": str(path.relative_to(base)),
                            "bytes": path.stat().st_size,
                            "sha256": sha256(path)})

    entries.sort(key=lambda item: (item["root"], item["path"]))
    combined = hashlib.sha256()
    for item in entries:
        combined.update(f'{item["root"]}/{item["path"]}:{item["sha256"]}\n'.encode("utf-8"))
    digest = combined.hexdigest()

    manifest = {"tag": args.tag or None, "content_digest": "sha256:" + digest,
                "file_count": len(entries),
                "total_bytes": sum(item["bytes"] for item in entries),
                "digest_recipe": "sha256 over the sorted '<root>/<relpath>:<sha256>' lines",
                "entries": entries}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"{manifest['file_count']} files, {manifest['total_bytes']} bytes")
    print(manifest["content_digest"])


if __name__ == "__main__":
    main()
