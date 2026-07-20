# Release Archive Manifest

Local integrity record for the DNQ-DLC GitHub and archival release.

## Status

- Release status: `local_manifest_only`
- External DOI: not assigned
- External archive URL: not assigned
- File count: 197
- Total size: 52603435 bytes

## Category summary

| Category | Files | Size (bytes) |
|---|---:|---:|
| checkpoints | 18 | 28679361 |
| code | 32 | 439759 |
| configs | 2 | 26558 |
| docs | 98 | 20861520 |
| governance | 28 | 49514 |
| source_data | 19 | 2546723 |

## Integrity

SHA-256 values cover every release file except Git metadata, generated
build/output/cache directories, and the three self-referential manifest
files. Regenerate after any release-package change:

```bash
python code/build_release_manifest.py
```

Complete checksums are in `RELEASE_ARCHIVE_MANIFEST.csv` and
`RELEASE_ARCHIVE_MANIFEST.json`.
