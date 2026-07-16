# Publishing workflow

The repository is intentionally private until the manuscript has been
submitted. The private remote is the collaboration and preservation copy; it
is not yet the citable public release.

## Private phase

1. Keep repository visibility set to `private`.
2. Push reviewed changes to `main`; require CI to pass.
3. Keep the release candidate as a draft prerelease.
4. Do not enable public GitHub Pages.
5. Do not create a Zenodo record from a private or mutable candidate.

## Public-release gates

Before changing visibility:

1. freeze author names, affiliations, ORCID identifiers and contact details;
2. replace `CITATION.cff.template` with a valid `CITATION.cff`;
3. complete the custom-track and rendered-media review in
   `ASSET_LICENSES.md`;
4. rerun the primary analysis, link audit, source compilation and release
   manifest;
5. confirm that no credentials, private data or proprietary game assets are
   present;
6. tag the frozen commit as `v0.1.0` and publish the GitHub Release;
7. enable Pages with GitHub Actions and run the Pages workflow;
8. connect the public repository to Zenodo, archive `v0.1.0`, and record the
   DOI in the manuscript and repository metadata.

## Visibility transition

After manuscript submission:

```bash
gh repo edit chocho2222/DNQ-DLC --visibility public \
  --accept-visibility-change-consequences
gh workflow run pages.yml --repo chocho2222/DNQ-DLC
```

Record the public repository URL, release tag, commit hash, Pages URL and DOI
in `docs/release_status.json` and the manuscript Data/Code Availability
statements.
