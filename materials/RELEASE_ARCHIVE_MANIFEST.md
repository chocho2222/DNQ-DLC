# Release Archive Manifest

Local integrity record for the DNQ-DLC GitHub and archival release.

## Status

- Release status: `private_github_release_candidate`
- External DOI: not assigned
- External archive URL: not assigned
- File count: 2019
- Total size: 166891825 bytes

## Category summary

| Category | Files | Size (bytes) |
|---|---:|---:|
| checkpoints | 77 | 104128154 |
| code | 479 | 6929790 |
| configs | 98 | 523451 |
| docs | 98 | 21574690 |
| governance | 50 | 726207 |
| paper | 28 | 5667860 |
| source_data | 1189 | 27341673 |

## Integrity

SHA-256 values cover every release file except Git metadata, generated
build/output/cache directories, and the three self-referential manifest
files. Regenerate after any release-package change:

```bash
python reproduce/rebuild_archive_manifest.py
```

Complete checksums are in `RELEASE_ARCHIVE_MANIFEST.csv` and
`RELEASE_ARCHIVE_MANIFEST.json`.
