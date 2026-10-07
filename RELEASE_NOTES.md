# DNQ-DLC release candidate

Release candidate for the DNQ-DLC paper artefact.

## Included

- the simulator, controller, evaluation, analysis and figure code, with unit
  tests;
- the proposed controller, its training draws and admission-rule controls, the
  DLC training draws and the continuous-control checkpoints;
- the frozen per-case endpoint, containment, controller-signal and audit tables
  behind the manuscript;
- the manuscript sources, its six figures, and the compiled PDF;
- the content digest `tits-2026-09-29` and a script that recomputes it;
- model and data cards, licences, provenance boundaries and a per-file SHA-256
  record.

## Evaluated result

Every method is evaluated on the same 48 cases. The proposed controller, averaged
over five draws of its training recipe, completes 45.8 cases and reaches the
strict overtaking tier in 20.2 of them, against 12 for the rule expert and 17.5,
18.5 and 13.5 for the three DLC variants. Rank gain and containment separate it
from every comparator draw; the strict-tier range overlaps the three world-model
variants and is therefore reported as counts with intervals.

The evaluation is a two-dimensional kinematic simulator study over 4 to 10
vehicles on one procedural track family. The learned comparators are trained
under their own budgets and none is trained to convergence.

## Release-candidate boundary

This draft is private and non-citable. Final author metadata, public track and
media clearance, the archival DOI and the manuscript links are added at
`v0.1.0`.
