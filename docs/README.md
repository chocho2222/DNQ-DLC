# DNQ-DLC Reproducibility and Video Evidence Site

This folder is a self-contained static release candidate for the DNQ-DLC paper.
It can be deployed unchanged with GitHub Pages, Netlify Drop, or a standard
static web server.

## Included evidence

- 22 MP4 simulation videos with explicit illustrative-evidence labels;
- the 200-case matched overtaking-success analysis and pairing audit;
- an eight-case sensitivity evaluation of four DLC-JTO training checkpoints;
- the revised publication figures in PDF, SVG, and PNG;
- randomized component-attribution data;
- source CSV/JSON files linked from the webpage;
- Python scripts for primary statistics and figure generation.

The videos do not estimate population performance. The central effectiveness
claim is supported by the matched 200-case source table and paired analysis.

## Recommended GitHub release layout

1. Create the author-owned private repository `chocho2222/DNQ-DLC`.
2. Copy this folder to `docs/` or the repository root.
3. Keep Pages disabled while the paper package is private.
4. Publish a versioned GitHub Release containing code, environment files,
   models, checkpoints, source data, and this site.
5. After manuscript submission and licence review, make the repository public,
   deploy Pages, and archive the frozen release through Zenodo or another
   DOI-issuing repository.

Do not publish through the simulator's upstream remote. Before publication,
replace the URL/DOI placeholders and confirm third-party asset licences.
