"""Create a non-destructive final hash manifest for a development stage."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    manifest = {}
    for path in sorted(args.root.rglob('*')):
        if path.is_file() and path.name not in {'sha256_manifest_final.json'}:
            manifest[str(path.relative_to(args.root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    output = args.root/'sha256_manifest_final.json'
    output.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'files_hashed': len(manifest), 'output': str(output)}))


if __name__ == '__main__':
    main()
