#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


OFFICIAL_SOURCES = [
    {
        "source_id": "TITS_AUTHOR_INFO",
        "title": "IEEE Transactions on Intelligent Transportation Systems author information",
        "url": "https://ieee-itss.org/pub/t-its/",
        "used_for": "Scope, paper type, suggested regular-paper length, abstract constraints, keyword categories, and author-portal route.",
    },
    {
        "source_id": "IEEE_REPRO",
        "title": "IEEE Author Center reproducible research guidance",
        "url": "https://ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-the-text-of-your-article/reproducible-research/",
        "used_for": "Data/code availability, source data, and reproducibility routing.",
    },
    {
        "source_id": "IEEE_AI",
        "title": "IEEE Author Guidelines for Artificial Intelligence (AI)-Generated Text",
        "url": "https://open.ieee.org/author-guidelines-for-artificial-intelligence-ai-generated-text/",
        "used_for": "AI-tool disclosure draft and author-side declaration checklist.",
    },
]

TITLE = "Dynamic-Neighborhood World Models for Online Multi-Car Overtaking"
ABSTRACT = (
    "Online overtaking in multi-vehicle traffic is challenging because nearby vehicles enter, leave, and change their interaction relevance during execution, whereas many learned world-model controllers rely on a fixed interaction structure. This paper presents a dynamic-neighborhood world-model controller for autonomous overtaking. The ego vehicle rebuilds a local interaction graph at runtime, selects surrounding vehicles by interaction priority, and evaluates overtake-aware candidate actions using learned progress, risk, uncertainty, lane-quality, and off-track penalties. The same trained graph model is evaluated across different traffic sizes by masking padded neighbor slots rather than retraining for each vehicle count. We assess the method in a 240-run matched online benchmark covering procedural tracks, an eight-vehicle extrapolation setting, and a Monza track converted from external comma-separated-value data. Relative to the original world-model baseline, the safety-oriented dynamic-neighborhood variant increases overtake success from 0.633 to 0.933, increases desirable overtaking behavior from 0.077 to 0.455, and reduces start-to-completion overtaking time from 378.5 to 85.3 simulation steps. The release includes paired statistical tests, failure-mode diagnostics, top-down and first-person visual evidence, source data, frozen commands, and checksum manifests to support reproducible evaluation."
)

KEYWORDS = [
    {
        "keyword": "Autonomous driving",
        "category": "application",
        "source_list": "T-ITS application keyword list",
        "rationale": "The evaluated task is autonomous multi-car overtaking.",
    },
    {
        "keyword": "Connected and Autonomous Vehicles",
        "category": "application",
        "source_list": "T-ITS application keyword list",
        "rationale": "The method models interaction among multiple vehicles.",
    },
    {
        "keyword": "Data-based approaches (learning, deep learning, reinforcement learning)",
        "category": "methodology",
        "source_list": "T-ITS methodology keyword list",
        "rationale": "The controller uses learned world-model predictions and learned proposal components.",
    },
    {
        "keyword": "Multi-agent systems",
        "category": "methodology",
        "source_list": "T-ITS methodology keyword list",
        "rationale": "The benchmark and graph construction are explicitly multi-vehicle.",
    },
    {
        "keyword": "World-model planning",
        "category": "free",
        "source_list": "optional free keyword",
        "rationale": "Clarifies the algorithmic focus beyond the controlled source-list terms.",
    },
    {
        "keyword": "Autonomous overtaking",
        "category": "free",
        "source_list": "optional free keyword",
        "rationale": "Clarifies the task-specific contribution.",
    },
]


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def word_count(text):
    return len(re.findall(r"\b[\w.-]+\b", text))


def sentence_count(text):
    return len([part for part in re.split(r"[.!?]+", text) if part.strip()])


def load_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_title_abstract_keywords_md():
    keyword_lines = "\n".join(
        f"- {row['keyword']} ({row['category']}; {row['source_list']})" for row in KEYWORDS
    )
    return f"""# T-ITS Title, Abstract and Keywords Draft

## Proposed Title

{TITLE}

## One-Paragraph Abstract Draft

{ABSTRACT}

## Abstract Checks

- Word count: {word_count(ABSTRACT)}
- Paragraph count: 1
- Contains displayed equations/tables: no
- Contains references/footnotes: no
- Use boundary: final authors should verify terminology and word limit against the live T-ITS portal before upload.

## Proposed Keywords

{keyword_lines}

## Keyword Compliance Notes

- Total keywords: {len(KEYWORDS)}.
- Application keywords: {sum(1 for row in KEYWORDS if row['category'] == 'application')} (target range from T-ITS page: 1-2).
- Methodology keywords: {sum(1 for row in KEYWORDS if row['category'] == 'methodology')} (target range from T-ITS page: 1-2).
- Optional free keywords: {sum(1 for row in KEYWORDS if row['category'] == 'free')} (target maximum from T-ITS page: 2).
"""


def build_cover_letter_md():
    return f"""# Cover Letter Draft

Dear Editor-in-Chief and Editorial Office,

We are pleased to submit our manuscript entitled "{TITLE}" for consideration as a regular paper in IEEE Transactions on Intelligent Transportation Systems.

The manuscript addresses online autonomous overtaking in multi-vehicle traffic, a transportation automation problem involving coordinated vehicle interactions, planning, learned world models, and simulation-based evaluation. The proposed controller extends a learned world-model overtaking framework with runtime dynamic-neighborhood graph construction, overtake-aware candidate planning, and safety-oriented scoring. This design allows the ego vehicle to rebuild its local interaction graph from surrounding traffic during execution and to evaluate different vehicle counts without retraining the graph model for each traffic size.

The submission includes a matched 240-run online benchmark across procedural tracks, an eight-vehicle extrapolation setting, and a Monza external-track setting converted from comma-separated-value data. Compared with the original world-model baseline, the primary safety-oriented dynamic-neighborhood variant improves benchmark-defined overtake success, desirable and on-track overtaking, and start-to-completion overtaking time. The manuscript also reports paired statistical tests, multiple-comparison-aware analysis, failure-mode diagnostics, runtime scalability, top-down and first-person visual evidence, and a reproducibility package with frozen commands, source data, model artifacts, and SHA256 checksums.

We confirm that the final manuscript should be submitted only to IEEE Transactions on Intelligent Transportation Systems and should not be under concurrent consideration elsewhere. Any related prior work, if applicable, must be cited and distinguished in the final manuscript. All author metadata, conflict-of-interest statements, funding statements, AI-tool disclosures, data/code repository URLs, and final template compliance checks remain to be completed by the authors before portal submission.

Sincerely,

[Corresponding author name, affiliation, and contact information]
"""


def build_declarations_md():
    return """# Author Declarations and AI-Tool Disclosure Draft

## AI-Tool Disclosure Draft

During manuscript preparation, AI-assisted tools were used to help organize technical notes, draft reproducibility checklists, and improve language clarity. The authors reviewed, edited, and take full responsibility for all text, code, data, analyses, figures, and claims. AI tools were not used to fabricate or manipulate data, create unsupported results, or replace author judgment in the scientific analysis.

Author-side action before submission: replace this paragraph with the exact AI systems used, the manuscript sections affected, and the level of use, following the current IEEE policy and the journal submission portal requirements.

## Conflict of Interest Draft

The authors declare no competing interests. [Authors must verify and edit this statement before submission.]

## Funding Draft

This work was supported by [funding agency, grant number]. [Authors must replace this placeholder.]

## Data and Code Availability Draft

The source data, configuration files, trained model artifacts, analysis scripts, figure source data, visual evidence, and checksum manifest required to reproduce the reported simulation benchmark are organized under the T-ITS dynamic graph artifact package. The final public repository URL, release tag, and data-archive DOI/accession must be inserted after deposition.

## Ethics and Safety Scope

The study reports simulation experiments only. The results do not certify real-vehicle safety, legal compliance, collision-free operation, or arbitrary traffic-density generalization.

## Author-Side Required Fields

- Final author list and author order.
- ORCID identifiers.
- Affiliations and corresponding author contact.
- Funding and acknowledgments.
- Conflict-of-interest declaration.
- AI-tool disclosure.
- Data/code repository URLs and DOI/accession.
- Prior-work or preprint disclosure, if applicable.
"""


def build_data_code_finalization_md(artifact, release, final_readiness):
    file_count = artifact.get("summary", {}).get("file_count")
    release_status = release.get("status")
    readiness = final_readiness.get("status")
    return f"""# Data and Code Availability Finalization Plan

## Current Local Status

- Artifact manifest file count: {file_count}
- Public release routing status: `{release_status}`
- Final readiness dashboard status: `{readiness}`

## Code Repository Contents

Recommended public-code contents:

- `configs/`
- `dlc/`
- `gym_multi_car_racing/`
- selected reproducibility scripts under `scripts/`
- `tracks/monza_scaled.npz` and `tracks/monza_scaled.json`
- `docs/tits_dynamic_graph_reproducibility_protocol.md`
- `README.md`, `environment.yml`, `LICENSE`, and setup files

## Data Archive Contents

Recommended data/release contents:

- frozen confirmatory matrix summaries and source data
- model artifacts and baseline weights
- figure source data and multi-format figure exports
- publication GIFs and trace summaries
- statistical, casewise, fairness, runtime, and experimental-design audit packs
- reviewer replication packet
- public release plan and SHA256 artifact manifest

## Final Manuscript Wording Template

The code and data supporting the simulation experiments will be made available at [repository URL] and [data archive DOI/accession]. The release includes source data, trained model artifacts, track files, configuration files, scripts for reproducing the benchmark and figures, and SHA256 checksums for archived artifacts. The released materials support reproduction of the simulator benchmark and figures but do not certify real-vehicle deployment safety.

## Author-Side Steps

1. Create a clean public repository or release tag.
2. Deposit the formal data archive and obtain DOI/accession.
3. Replace all local paths in the final manuscript with repository-relative paths or DOI-backed references.
4. Re-run `export_tits_dynamic_graph_artifact_manifest.py` after final file movement.
5. Re-run the public release plan and cross-reference audit after DOI/URL insertion.
"""


def build_submission_checklist_rows():
    return [
        {
            "item": "Paper type",
            "local_status": "draft_ready",
            "evidence": "IEEE_TITS_SUBMISSION_METADATA_PACK.md",
            "author_action": "Confirm regular-paper type and final page count in IEEE double-column template.",
        },
        {
            "item": "Title",
            "local_status": "draft_ready",
            "evidence": "TITLE_ABSTRACT_KEYWORDS_DRAFT.md",
            "author_action": "Confirm final title with all authors.",
        },
        {
            "item": "Abstract",
            "local_status": "draft_ready",
            "evidence": "TITLE_ABSTRACT_KEYWORDS_DRAFT.md",
            "author_action": "Verify live word limit and final one-paragraph wording in portal.",
        },
        {
            "item": "Keywords",
            "local_status": "draft_ready",
            "evidence": "keyword_plan.csv",
            "author_action": "Select final keywords in the portal using current T-ITS category lists.",
        },
        {
            "item": "Cover letter",
            "local_status": "draft_ready",
            "evidence": "COVER_LETTER_DRAFT.md",
            "author_action": "Add corresponding author identity, prior-work disclosure, and final declarations.",
        },
        {
            "item": "AI disclosure",
            "local_status": "author_finalization_required",
            "evidence": "AUTHOR_DECLARATIONS_AND_AI_DISCLOSURE_DRAFT.md",
            "author_action": "Replace placeholder with exact tools, sections, and level of use.",
        },
        {
            "item": "Data/code availability",
            "local_status": "author_archive_required",
            "evidence": "DATA_CODE_AVAILABILITY_FINALIZATION.md",
            "author_action": "Insert public repository URL and data archive DOI/accession.",
        },
        {
            "item": "Final PDF",
            "local_status": "author_format_required",
            "evidence": "IEEE_TITS_COMPLIANCE_MATRIX.md",
            "author_action": "Convert to IEEE template, check page count, figures, references, and PDF compliance.",
        },
    ]


def build_submission_pack_md(summary):
    lines = [
        "# IEEE T-ITS Submission Metadata Pack",
        "",
        "This package converts the local evidence chain into author-facing submission metadata drafts. It does not replace the live IEEE/T-ITS portal, legal checks, author declarations, or final template conversion.",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Main Draft Files",
            "",
            "- Title/abstract/keywords: `outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/TITLE_ABSTRACT_KEYWORDS_DRAFT.md`",
            "- Cover letter: `outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/COVER_LETTER_DRAFT.md`",
            "- Author declarations and AI disclosure: `outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/AUTHOR_DECLARATIONS_AND_AI_DISCLOSURE_DRAFT.md`",
            "- Data/code finalization plan: `outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/DATA_CODE_AVAILABILITY_FINALIZATION.md`",
            "- Submission checklist: `outputs/tits_dynamic_graph/tits_submission_metadata_pack/tables/submission_portal_checklist.csv`",
            "",
            "## Official-Rule Interpretation",
            "",
            "- T-ITS requires a transportation-systems focus; the manuscript should frame multi-car overtaking as autonomous-driving and vehicle-interaction planning.",
            "- The abstract draft is one paragraph and within the 150-250 word target from the T-ITS author information page.",
            "- The keyword plan follows the T-ITS category structure: application keywords, methodology keywords, and optional free keywords.",
            "- IEEE AI-generated content policy requires disclosure when AI-generated content is used; the provided text is a placeholder that authors must finalize with exact tool and section details.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_submission_metadata_pack.py --out-dir outputs/tits_dynamic_graph/tits_submission_metadata_pack",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export IEEE T-ITS submission metadata and declaration drafts.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_submission_metadata_pack")
    parser.add_argument("--artifact", default="outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json")
    parser.add_argument("--release", default="outputs/tits_dynamic_graph/public_release_plan/public_release_plan_manifest.json")
    parser.add_argument("--final-readiness", default="outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    artifact = load_json(args.artifact)
    release = load_json(args.release)
    final_readiness = load_json(args.final_readiness)
    checklist_rows = build_submission_checklist_rows()
    keyword_rows = KEYWORDS
    source_rows = OFFICIAL_SOURCES
    abstract_words = word_count(ABSTRACT)
    checks = {
        "abstract_one_paragraph": "\n\n" not in ABSTRACT.strip(),
        "abstract_word_count_150_250": 150 <= abstract_words <= 250,
        "keyword_count_max_6": len(KEYWORDS) <= 6,
        "application_keyword_count_1_to_2": 1 <= sum(1 for row in KEYWORDS if row["category"] == "application") <= 2,
        "methodology_keyword_count_1_to_2": 1 <= sum(1 for row in KEYWORDS if row["category"] == "methodology") <= 2,
        "free_keyword_count_max_2": sum(1 for row in KEYWORDS if row["category"] == "free") <= 2,
        "title_nonempty": bool(TITLE.strip()),
        "cover_letter_draft_created": True,
        "ai_disclosure_placeholder_created": True,
        "data_code_plan_created": True,
    }
    summary = {
        "status": "pass" if all(checks.values()) else "review_required",
        "title": TITLE,
        "abstract_word_count": abstract_words,
        "abstract_sentence_count": sentence_count(ABSTRACT),
        "keyword_count": len(KEYWORDS),
        "application_keyword_count": sum(1 for row in KEYWORDS if row["category"] == "application"),
        "methodology_keyword_count": sum(1 for row in KEYWORDS if row["category"] == "methodology"),
        "free_keyword_count": sum(1 for row in KEYWORDS if row["category"] == "free"),
        "checklist_item_count": len(checklist_rows),
        "official_source_count": len(source_rows),
        "author_finalization_required": True,
    }
    paths = {
        "pack_md": "",
        "title_abstract_keywords_md": write_text(materials / "TITLE_ABSTRACT_KEYWORDS_DRAFT.md", build_title_abstract_keywords_md()),
        "cover_letter_md": write_text(materials / "COVER_LETTER_DRAFT.md", build_cover_letter_md()),
        "declarations_md": write_text(materials / "AUTHOR_DECLARATIONS_AND_AI_DISCLOSURE_DRAFT.md", build_declarations_md()),
        "data_code_md": write_text(materials / "DATA_CODE_AVAILABILITY_FINALIZATION.md", build_data_code_finalization_md(artifact, release, final_readiness)),
        "keyword_csv": write_csv(tables / "keyword_plan.csv", keyword_rows, ["keyword", "category", "source_list", "rationale"]),
        "checklist_csv": write_csv(tables / "submission_portal_checklist.csv", checklist_rows, ["item", "local_status", "evidence", "author_action"]),
        "official_sources_csv": write_csv(tables / "official_source_crosswalk.csv", source_rows, ["source_id", "title", "url", "used_for"]),
        "qa_json": "",
    }
    qa = {
        "status": summary["status"],
        "checks": checks,
        "note": "This package provides editable submission drafts. Live portal rules, author metadata, DOI/accession, license and final PDF checks remain author-owned.",
    }
    paths["qa_json"] = write_json(materials / "SUBMISSION_METADATA_QA.json", qa)
    paths["pack_md"] = write_text(materials / "IEEE_TITS_SUBMISSION_METADATA_PACK.md", build_submission_pack_md(summary))
    manifest = {
        "status": summary["status"],
        "out_dir": args.out_dir,
        "summary": summary,
        "paths": paths,
        "checks": checks,
        "official_sources": source_rows,
    }
    manifest_path = write_json(out_dir / "tits_submission_metadata_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": summary["status"], "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
