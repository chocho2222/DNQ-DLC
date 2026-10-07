#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


KEY_ARTIFACTS = [
    "materials/EXPERIMENT_REGISTRY.md",
    "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
    "tables/seed_outcome_ledger.md",
    "tables/artifact_provenance.md",
    "tables/reproducibility_audit.md",
    "materials/MANUSCRIPT_CLAIM_QA.md",
    "materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.md",
    "materials/REFERENCE_READINESS_AUDIT.md",
    "materials/RELEASE_ARCHIVE_MANIFEST.md",
    "materials/REPRODUCTION_GUIDE.md",
    "materials/DATA_CODE_AVAILABILITY.md",
    "materials/DATA_CODE_AVAILABILITY.json",
    "materials/DATA_CODE_AVAILABILITY.csv",
    "materials/FAIR_ARCHIVE_METADATA.md",
    "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
    "materials/RESEARCH_RISK_AND_SAFETY.md",
    "materials/SIMULATION_TO_REAL_APPLICABILITY.md",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
    "materials/SUBMISSION_METADATA_DRAFT.md",
    "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
    "materials/SIGNIFICANCE_BRIEFING.md",
    "materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.md",
    "materials/EDITORIAL_NARRATIVE_PACKAGE.md",
    "materials/COVER_LETTER_DRAFT_PACKAGE.md",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
    "materials/EDITORIAL_DECISION_BRIEF.md",
    "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md",
    "materials/REVIEWER_RESPONSE_SEED_PACK.md",
    "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.md",
    "materials/PORTAL_COPYEDIT_LOCK_AUDIT.md",
    "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.md",
    "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.md",
    "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.md",
    "materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
    "materials/REVIEWER_QUICKLOOK_PACKET.md",
    "materials/METHODS_REPRODUCIBILITY_CAPSULE.md",
    "materials/METHODS_TO_CODE_TRACEABILITY.md",
    "materials/ETHICS_DISCLOSURE_READINESS_PACK.md",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
    "materials/REVIEWER_REPLICATION_ROUTE.md",
    "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md",
    "materials/SUPPLEMENTARY_TABLE_LEGENDS.md",
    "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
    "materials/SUBMISSION_READINESS_DASHBOARD.md",
    "materials/MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.md",
    "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md",
    "materials/TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.md",
    "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.md",
    "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md",
    "materials/ARCHIVE_SIZE_BUDGET_REPORT.md",
    "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md",
    "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
    "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
    "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md",
    "materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.md",
    "materials/STATISTICAL_REPORTING_APPENDIX.md",
    "materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.md",
    "materials/FIGURE_SOURCE_DATA_AUDIT.md",
    "materials/FIGURE_PRODUCTION_HANDOFF.md",
    "materials/STATISTICAL_CONSISTENCY_AUDIT.md",
    "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.md",
    "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.md",
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.md",
    "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.md",
    "materials/ENDPOINT_SENSITIVITY_AUDIT.md",
    "materials/SELECTOR_DECISION_AUDIT.md",
    "materials/SEED_PARTITION_AUDIT.md",
    "materials/VISUAL_EVIDENCE_AUDIT.md",
    "materials/ARTIFACT_DEPENDENCY_MAP.md",
    "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.md",
    "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.md",
    "materials/POLICY_MODEL_CARD.md",
    "materials/STUDY_PROTOCOL_AND_DEVIATIONS.md",
    "materials/BASELINE_FAIRNESS_AUDIT.md",
    "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md",
    "materials/DATA_DICTIONARY.md",
    "materials/TRANSPARENT_REPORTING_CHECKLIST.md",
    "materials/CLAIM_EVIDENCE_MATRIX.md",
    "materials/CLAIM_DOWNGRADE_MAP.md",
    "materials/WHAT_THIS_PAPER_DOES_NOT_CLAIM.md",
    "materials/PUBLICATION_PACKAGE_SUMMARY.md",
    "figures/figure_3_cross_heldout_validation.png",
    "figures/figure_3_source_data.csv",
]

RELEASE_SELF_OUTPUTS = {
    "materials/RELEASE_ARCHIVE_MANIFEST.md",
    "materials/RELEASE_ARCHIVE_MANIFEST.json",
    "materials/RELEASE_ARCHIVE_MANIFEST.csv",
    "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
    "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
    "materials/PUBLICATION_PACKAGE_VERIFICATION.csv",
    "materials/PUBLICATION_SMOKE_TEST.md",
    "materials/PUBLICATION_SMOKE_TEST.json",
    "materials/PUBLICATION_SMOKE_TEST.csv",
    "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.md",
    "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.json",
    "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.csv",
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.md",
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.json",
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.csv",
    "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.md",
    "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.json",
    "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.csv",
    "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.md",
    "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.json",
    "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.csv",
    "materials/FINAL_CHECKSUM_FREEZE_RECORD.md",
    "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
    "materials/FINAL_CHECKSUM_FREEZE_RECORD.csv",
    "materials/FINAL_CHECKSUM_FREEZE_FILE_SNAPSHOTS.csv",
    "materials/FAIR_ARCHIVE_METADATA.md",
    "materials/FAIR_ARCHIVE_METADATA.json",
    "materials/FAIR_ARCHIVE_METADATA.csv",
    "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.md",
    "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.json",
    "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.csv",
    "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
    "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
    "materials/EXTERNAL_ARCHIVE_PREFLIGHT_ROWS.csv",
    "materials/EXTERNAL_ARCHIVE_KEY_FILES.csv",
    "materials/ARCHIVE_README.md",
    "materials/ARCHIVE_README.json",
    "materials/ARCHIVE_README.csv",
    "materials/ARCHIVE_SIZE_BUDGET_REPORT.md",
    "materials/ARCHIVE_SIZE_BUDGET_REPORT.json",
    "materials/ARCHIVE_SIZE_BUDGET_CATEGORIES.csv",
    "materials/ARCHIVE_SIZE_BUDGET_UPLOAD_PARTITIONS.csv",
    "materials/ARCHIVE_SIZE_BUDGET_LARGEST_FILES.csv",
    "materials/ARCHIVE_SIZE_BUDGET_CHECKS.csv",
    "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md",
    "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
    "materials/SLIM_SUBMISSION_PACKAGE_FILES.csv",
    "materials/SLIM_SUBMISSION_PACKAGE_ARCHIVE_ONLY.csv",
    "materials/SLIM_SUBMISSION_PACKAGE_PARTITIONS.csv",
    "materials/AUTHOR_UPLOAD_DECISION_MEMO.md",
    "materials/AUTHOR_UPLOAD_DECISION_MEMO.json",
    "materials/AUTHOR_UPLOAD_DECISION_MEMO.csv",
    "materials/REVIEWER_QUICKLOOK_PACKET.md",
    "materials/REVIEWER_QUICKLOOK_PACKET.json",
    "materials/REVIEWER_QUICKLOOK_PACKET.csv",
    "materials/TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.md",
    "materials/TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.json",
    "materials/TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.csv",
    "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.md",
    "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.json",
    "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.csv",
    "materials/FINAL_SUBMISSION_FILE_BUNDLE.md",
    "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
    "materials/FINAL_SUBMISSION_FILE_BUNDLE.csv",
    "materials/CITATION_METADATA.md",
    "materials/CITATION_METADATA.json",
    "materials/CITATION_METADATA.csv",
    "materials/CITATION.cff",
    "materials/CITATION.bib",
    "materials/SUBMISSION_READINESS_DASHBOARD.md",
    "materials/SUBMISSION_READINESS_DASHBOARD.json",
    "materials/SUBMISSION_READINESS_DASHBOARD.csv",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.csv",
    "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md",
    "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
    "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.csv",
    "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md",
    "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.json",
    "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.csv",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.json",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.csv",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.csv",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.csv",
    "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md",
    "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.json",
    "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.csv",
    "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md",
    "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.json",
    "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.csv",
    "materials/REVIEWER_RISK_RESPONSE_DOSSIER.md",
    "materials/REVIEWER_RISK_RESPONSE_DOSSIER.json",
    "materials/REVIEWER_RISK_RESPONSE_DOSSIER.csv",
    "materials/REVIEWER_RESPONSE_SEED_PACK.md",
    "materials/REVIEWER_RESPONSE_SEED_PACK.json",
    "materials/REVIEWER_RESPONSE_SEED_PACK.csv",
    "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.md",
    "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.json",
    "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.csv",
    "materials/PORTAL_COPYEDIT_LOCK_AUDIT.md",
    "materials/PORTAL_COPYEDIT_LOCK_AUDIT.json",
    "materials/PORTAL_COPYEDIT_LOCK_AUDIT.csv",
    "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.md",
    "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.json",
    "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.csv",
    "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.md",
    "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json",
    "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.csv",
    "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.md",
    "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.json",
    "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.csv",
    "materials/BLINDED_REVIEW_ANONYMIZATION_SCAN_HITS.csv",
    "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.md",
    "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.json",
    "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.csv",
    "materials/AI_TOOL_USE_DISCLOSURE_SCAN_HITS.csv",
    "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md",
    "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.json",
    "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.csv",
    "materials/SOFTWARE_DEPENDENCY_LICENSE_METADATA.csv",
    "materials/ARTIFACT_DEPENDENCY_MAP.md",
    "materials/ARTIFACT_DEPENDENCY_MAP.json",
    "materials/ARTIFACT_DEPENDENCY_MAP.csv",
    "materials/FIGURE_PRODUCTION_HANDOFF.md",
    "materials/FIGURE_PRODUCTION_HANDOFF.json",
    "materials/FIGURE_PRODUCTION_HANDOFF.csv",
    "materials/FIGURE_PRODUCTION_HANDOFF_FILES.csv",
    "materials/FIGURE_PRODUCTION_HANDOFF_SOURCE_DATA.csv",
    "materials/METHODS_TO_CODE_TRACEABILITY.md",
    "materials/METHODS_TO_CODE_TRACEABILITY.json",
    "materials/METHODS_TO_CODE_TRACEABILITY.csv",
    "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.md",
    "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json",
    "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.csv",
    "materials/SCRIPT_SNAPSHOT_EXTRA_FILES.csv",
    "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.md",
    "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.json",
    "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.csv",
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.md",
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.json",
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.csv",
}


LEDGER_EXPECTED = {
    "heldout1_original": ("tables/portfolio_probe_selector_1200_heldout_dagger_v2.json", 10, 10),
    "heldout2_original": ("tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json", 5, 7),
    "heldout1_expanded": ("tables/portfolio_probe_selector_1200_heldout_expanded.json", 10, 10),
    "heldout2_expanded": ("tables/portfolio_probe_selector_1200_heldout2_expanded.json", 7, 10),
    "heldout3_expanded": ("tables/portfolio_probe_selector_1200_heldout3_expanded.json", 4, 8),
    "heldout3_targeted_expanded": ("tables/portfolio_probe_selector_1200_heldout3_targeted_expanded.json", 4, 9),
    "heldout4_targeted_expanded": ("tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.json", 6, 8),
}


FORBIDDEN_PATTERNS = [
    r"\bdistributionally robust\b",
    r"\bdistributional robustness\b",
    r"\brobustly distributional\b",
]

STALE_RESULT_PATTERNS = [
    r"heldout2 oracle from 7/10 to 8/10",
    r"raises the heldout2 oracle from 7/10 to 8/10",
    r"remaining candidate gaps are seeds 101 and 103",
    r"leaving 101 and 103 as candidate gaps",
    r"leaving seeds 101 and 103 unresolved",
    r"candidate oracle itself misses 3/10",
    r"where the current candidate oracle itself fails",
]


TEXT_SCAN_FILES = [
    "materials/METHODS.md",
    "materials/RESULTS_STATUS.md",
    "materials/LIMITATIONS.md",
    "materials/SUPPLEMENTARY_INDEX.md",
    "materials/PUBLICATION_PACKAGE_SUMMARY.md",
    "materials/TOP_JOURNAL_READINESS_CHECKLIST.md",
    "materials/MANUSCRIPT_OUTLINE.md",
    "materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md",
    "materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.md",
    "materials/REFERENCE_READINESS_AUDIT.md",
    "materials/REVIEWER_RESPONSE_MAP.md",
    "materials/SUBMISSION_GAP_ACTION_PLAN.md",
    "materials/CLAIM_EVIDENCE_MATRIX.md",
    "materials/DATA_CODE_AVAILABILITY.md",
    "materials/FAIR_ARCHIVE_METADATA.md",
    "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
    "materials/RESEARCH_RISK_AND_SAFETY.md",
    "materials/SIMULATION_TO_REAL_APPLICABILITY.md",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
    "materials/SUBMISSION_METADATA_DRAFT.md",
    "materials/SIGNIFICANCE_BRIEFING.md",
    "materials/EDITORIAL_NARRATIVE_PACKAGE.md",
    "materials/COVER_LETTER_DRAFT_PACKAGE.md",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
    "materials/EDITORIAL_DECISION_BRIEF.md",
    "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
    "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
    "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md",
    "materials/CONFIRMATORY_FREEZE_AUDIT.md",
    "materials/CONFIRMATORY_ROADMAP.md",
    "materials/CLAIM_DECISION_TREE.md",
    "materials/FAILURE_MODE_ATLAS_SUMMARY.md",
    "materials/FIGURE_SOURCE_DATA_AUDIT.md",
    "materials/STATISTICAL_CONSISTENCY_AUDIT.md",
    "materials/ENDPOINT_SENSITIVITY_AUDIT.md",
    "materials/SELECTOR_DECISION_AUDIT.md",
    "materials/SEED_PARTITION_AUDIT.md",
    "materials/VISUAL_EVIDENCE_AUDIT.md",
    "materials/ARTIFACT_DEPENDENCY_MAP.md",
    "materials/POLICY_MODEL_CARD.md",
    "materials/STUDY_PROTOCOL_AND_DEVIATIONS.md",
    "materials/BASELINE_FAIRNESS_AUDIT.md",
    "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md",
    "materials/TRANSPARENT_REPORTING_CHECKLIST.md",
    "manuscript/main.md",
]


STALE_COUNT_FILES = [
    "materials/ARCHIVE_README.md",
    "materials/ARCHIVE_README.json",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
    "materials/METHODS_REPRODUCIBILITY_CAPSULE.md",
    "materials/METHODS_REPRODUCIBILITY_CAPSULE.json",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
    "materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
    "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
    "materials/SUBMISSION_READINESS_DASHBOARD.md",
    "materials/SUBMISSION_READINESS_DASHBOARD.json",
    "materials/EXPERIMENT_REGISTRY.md",
    "materials/EXPERIMENT_REGISTRY.json",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.json",
    "materials/TRANSPARENT_REPORTING_CHECKLIST.md",
    "materials/TRANSPARENT_REPORTING_CHECKLIST.json",
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def gate(gates, gate_id, description, passed, evidence=None, failures=None):
    gates.append(
        {
            "id": gate_id,
            "description": description,
            "status": "pass" if passed else "fail",
            "evidence": evidence or {},
            "failures": failures or [],
        }
    )


def line_no(text, index):
    return text.count("\n", 0, index) + 1


def scan_forbidden_text(root):
    findings = []
    regexes = [re.compile(pattern, re.IGNORECASE) for pattern in FORBIDDEN_PATTERNS]
    for rel in TEXT_SCAN_FILES:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for regex in regexes:
            for match in regex.finditer(text):
                findings.append(
                    {
                        "file": rel,
                        "line": line_no(text, match.start()),
                        "matched_text": match.group(0),
                    }
                )
    return findings


def scan_stale_result_text(root):
    findings = []
    regexes = [re.compile(pattern, re.IGNORECASE) for pattern in STALE_RESULT_PATTERNS]
    for rel in TEXT_SCAN_FILES:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for regex in regexes:
            for match in regex.finditer(text):
                findings.append(
                    {
                        "file": rel,
                        "line": line_no(text, match.start()),
                        "matched_text": match.group(0),
                    }
                )
    return findings


def scan_stale_artifact_counts(root, current_count):
    findings = []
    current = f"{current_count}/{current_count}"
    pattern = re.compile(r"\b(\d+)/(\d+)\b")
    for rel in STALE_COUNT_FILES:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            if line_end == -1:
                line_end = len(text)
            line = text[line_start:line_end]
            if "artifact_provenance" not in line and "Artifact provenance" not in line:
                continue
            value = match.group(0)
            if value != current:
                findings.append({"file": rel, "line": line_no(text, match.start()), "value": value, "expected": current})
    return findings


def check_ledger(root, ledger):
    failures = []
    by_stage = {row["stage"]: row for row in ledger["stage_summaries"]}
    for stage, (source, selector_pass, oracle_pass) in LEDGER_EXPECTED.items():
        if stage not in by_stage:
            failures.append({"stage": stage, "reason": "missing stage"})
            continue
        source_report = load_json(root / source)
        row = by_stage[stage]
        observed = {
            "selector_pass": row["selector_pass_count"],
            "oracle_pass": row["oracle_pass_count"],
            "source_selector_pass": source_report["pass_count"],
            "source_oracle_pass": source_report["oracle_pass_count"],
        }
        if row["selector_pass_count"] != selector_pass or row["oracle_pass_count"] != oracle_pass:
            failures.append({"stage": stage, "reason": "unexpected registered count", "observed": observed})
        if row["selector_pass_count"] != source_report["pass_count"] or row["oracle_pass_count"] != source_report["oracle_pass_count"]:
            failures.append({"stage": stage, "reason": "source mismatch", "observed": observed})
    return failures


def build_report(root):
    gates = []
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    audit = load_json(root / "tables" / "reproducibility_audit.json")
    qa = load_json(root / "materials" / "MANUSCRIPT_CLAIM_QA.json")
    frontmatter_qa = load_json(root / "materials" / "EDITORIAL_FRONTMATTER_CLAIM_AUDIT.json")
    claim_boundary_pack = load_json(root / "materials" / "CLAIM_BOUNDARY_COMMUNICATION_PACK.json")
    registry = load_json(root / "materials" / "EXPERIMENT_REGISTRY.json")
    ledger = load_json(root / "tables" / "seed_outcome_ledger.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    data_dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    cross_reference = load_json(root / "materials" / "MANUSCRIPT_CROSS_REFERENCE_AUDIT.json")
    reference_readiness = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")
    archive_preflight = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    submission_metadata = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    author_owned = load_json(root / "materials" / "AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json")
    local_author = load_json(root / "materials" / "LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json")
    submission_text = load_json(root / "materials" / "SUBMISSION_TEXT_FRESHNESS_AUDIT.json")

    current_count = len(provenance["artifacts"])
    gate(
        gates,
        "artifact_provenance_complete",
        "Artifact provenance complete count equals total artifact count.",
        provenance["complete_count"] == current_count and not provenance["incomplete_artifacts"],
        {"complete_count": provenance["complete_count"], "total": current_count},
        provenance["incomplete_artifacts"],
    )
    gate(
        gates,
        "reproducibility_audit_clear",
        "Reproducibility audit has no missing or weak items.",
        len(audit["missing_or_weak_items"]) == 0,
        {"missing_or_weak_count": len(audit["missing_or_weak_items"])},
        audit["missing_or_weak_items"],
    )
    gate(
        gates,
        "claim_qa_pass",
        "Manuscript claim QA passes with zero blockers.",
        qa["summary"]["status"] == "pass" and qa["summary"]["blockers"] == 0,
        qa["summary"],
        [row for row in qa["findings"] if row["severity"] == "blocker"],
    )
    gate(
        gates,
        "editorial_frontmatter_claim_audit_pass",
        "Editor-facing title/abstract/highlight, cover, significance, and triage materials have no overclaim blockers.",
        frontmatter_qa["summary"]["status"] == "pass" and frontmatter_qa["summary"]["blocker_count"] == 0,
        frontmatter_qa["summary"],
        [row for row in frontmatter_qa["findings"] if row["severity"] == "blocker"],
    )
    gate(
        gates,
        "claim_boundary_communication_pack_pass",
        "Claim downgrade and do-not-claim communication materials are evidence-complete and carry no unresolved support gaps.",
        claim_boundary_pack["summary"]["status"] == "pass",
        claim_boundary_pack["summary"],
        [
            row
            for row in claim_boundary_pack["downgrade_rows"]
            if not row["evidence_complete"]
        ],
    )
    gate(
        gates,
        "experiment_registry_consistent",
        "Experiment registry has complete evidence/provenance and current artifact count.",
        registry["summary"]["all_primary_evidence_present"]
        and registry["summary"]["all_provenance_complete"]
        and registry["summary"]["artifact_provenance_complete"] == f"{current_count}/{current_count}",
        registry["summary"],
    )

    ledger_failures = check_ledger(root, ledger)
    gate(
        gates,
        "seed_ledger_consistent",
        "Seed outcome ledger matches all source selector reports and expected stage counts.",
        not ledger_failures,
        ledger["summary"],
        ledger_failures,
    )

    gate(
        gates,
        "data_dictionary_complete",
        "Package-level data dictionary has all key files and field definitions.",
        data_dictionary["summary"]["complete"],
        data_dictionary["summary"],
        data_dictionary["missing_definitions"] + data_dictionary["summary"]["missing_files"],
    )

    cross_reference_failures = [
        row for row in cross_reference["path_references"] if row["status"] != "pass"
    ] + [row for row in cross_reference["numeric_checks"] if row["status"] != "pass"]
    gate(
        gates,
        "manuscript_cross_references_resolve",
        "Manuscript-facing local references resolve and key manuscript numbers match saved reports.",
        cross_reference["summary"]["status"] == "pass" and not cross_reference_failures,
        cross_reference["summary"],
        cross_reference_failures,
    )

    reference_failures = []
    if reference_readiness["summary"]["status"] != "pass":
        reference_failures.extend(reference_readiness.get("missing_bib_keys", []))
        reference_failures.extend(reference_readiness.get("placeholder_hits", []))
        reference_failures.extend([row for row in reference_readiness["topic_rows"] if row["status"] == "missing"])
    gate(
        gates,
        "reference_readiness_pass",
        "Manuscript citation keys resolve to references.bib and the bibliography is no longer a placeholder.",
        reference_readiness["summary"]["status"] == "pass",
        reference_readiness["summary"],
        reference_failures,
    )

    archive_failures = [row for row in archive_preflight["preflight_rows"] if row["status"] == "fail"]
    archive_failures.extend([row for row in archive_preflight["key_file_rows"] if row["status"] == "review"])
    gate(
        gates,
        "external_archive_preflight_pass",
        "External archive preflight has no local failures while author-required DOI/metadata fields remain explicit.",
        archive_preflight["summary"]["status"] == "pass" and not archive_failures,
        archive_preflight["summary"],
        archive_failures,
    )

    metadata_failures = []
    if submission_metadata["summary"]["status"] != "pass":
        metadata_failures.append(submission_metadata["summary"])
    gate(
        gates,
        "submission_metadata_draft_present",
        "Submission metadata draft exists and keeps author-required disclosures explicit.",
        submission_metadata["summary"]["status"] == "pass"
        and submission_metadata["summary"]["author_required_count"] > 0,
        submission_metadata["summary"],
        metadata_failures,
    )

    author_owned_failures = [row for row in author_owned["rows"] if row["status"] != "pass"]
    gate(
        gates,
        "author_owned_submission_integrity_pass",
        "Author-owned submission integrity audit passes and prevents local automation from marking author-certified fields complete.",
        author_owned["summary"]["status"] == "pass" and not author_owned_failures,
        author_owned["summary"],
        author_owned_failures,
    )

    local_author_failures = [row for row in local_author["checks"] if row["status"] != "pass"]
    gate(
        gates,
        "local_author_readiness_separation_pass",
        "Local-vs-author readiness separation audit passes, proving remaining blockers are author/journal/archive actions rather than local evidence defects.",
        local_author["summary"]["status"] == "pass" and not local_author_failures,
        local_author["summary"],
        local_author_failures,
    )

    submission_text_failures = [row for row in submission_text["rows"] if row["status"] != "pass"]
    gate(
        gates,
        "submission_text_freshness_pass",
        "Journal-facing short-form and portal-draft text have no stale package counts or failed gate snapshots.",
        submission_text["summary"]["status"] == "pass" and not submission_text_failures,
        submission_text["summary"],
        submission_text_failures,
    )

    missing_key_artifacts = [rel for rel in KEY_ARTIFACTS if not (root / rel).exists()]
    gate(
        gates,
        "key_artifacts_present",
        "Reviewer-facing key artifacts are present.",
        not missing_key_artifacts,
        {"checked": KEY_ARTIFACTS},
        missing_key_artifacts,
    )

    release_paths = {row["path"] for row in release["files"]}
    missing_from_release = [
        rel for rel in KEY_ARTIFACTS if rel not in release_paths and rel not in RELEASE_SELF_OUTPUTS and (root / rel).exists()
    ]
    gate(
        gates,
        "release_manifest_covers_key_artifacts",
        "Release manifest includes key artifacts.",
        not missing_from_release,
        {"key_artifact_coverage_checked": True},
        missing_from_release,
    )

    forbidden_findings = scan_forbidden_text(root)
    gate(
        gates,
        "forbidden_text_absent",
        "Manuscript-facing files avoid banned overclaim phrases outside the QA detector itself.",
        not forbidden_findings,
        {"scanned_files": TEXT_SCAN_FILES, "patterns": FORBIDDEN_PATTERNS},
        forbidden_findings,
    )

    stale_counts = scan_stale_artifact_counts(root, current_count)
    gate(
        gates,
        "artifact_count_references_current",
        "Artifact provenance counts in reviewer-facing materials match the current provenance total.",
        not stale_counts,
        {"expected": f"{current_count}/{current_count}", "scanned_files": STALE_COUNT_FILES},
        stale_counts,
    )

    stale_result_findings = scan_stale_result_text(root)
    gate(
        gates,
        "stale_result_text_absent",
        "Reviewer-facing files avoid stale heldout2 result wording after candidate expansion.",
        not stale_result_findings,
        {"scanned_files": TEXT_SCAN_FILES, "patterns": STALE_RESULT_PATTERNS},
        stale_result_findings,
    )

    failed = [row for row in gates if row["status"] != "pass"]
    return {
        "root": str(root),
        "timestamp_policy": "stable report; no timestamp is written to avoid release-checksum drift",
        "summary": {
            "status": "pass" if not failed else "fail",
            "gate_count": len(gates),
            "failed_gates": len(failed),
            "artifact_provenance": f"{provenance['complete_count']}/{current_count}",
            "claim_qa": qa["summary"]["status"],
        },
        "gates": gates,
        "interpretation": (
            "This verification report is a submission-preflight gate for the local evidence package. "
            "It checks cross-file consistency and overclaim guardrails; it does not rerun simulations."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["id", "description", "status", "failure_count"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["gates"]:
            writer.writerow(
                {
                    "id": row["id"],
                    "description": row["description"],
                    "status": row["status"],
                    "failure_count": len(row["failures"]),
                }
            )


def write_markdown(report, path):
    lines = [
        "# Publication Package Verification",
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Status: `{report['summary']['status']}`",
        f"- Gates: {report['summary']['gate_count']}",
        f"- Failed gates: {report['summary']['failed_gates']}",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- Claim QA: {report['summary']['claim_qa']}",
        f"- Timestamp policy: {report['timestamp_policy']}",
        "",
        "## Gates",
        "",
        "| gate | status | failures |",
        "|---|---|---:|",
    ]
    for row in report["gates"]:
        lines.append(f"| {row['id']} | {row['status']} | {len(row['failures'])} |")
    failed = [row for row in report["gates"] if row["status"] != "pass"]
    if failed:
        lines.extend(["", "## Failures", ""])
        for row in failed:
            lines.extend([f"### {row['id']}", "", "```json", json.dumps(row["failures"], indent=2), "```", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export publication package preflight verification report.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "PUBLICATION_PACKAGE_VERIFICATION.json"
    out_md = materials / "PUBLICATION_PACKAGE_VERIFICATION.md"
    out_csv = materials / "PUBLICATION_PACKAGE_VERIFICATION.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "status": report["summary"]["status"]}, indent=2))


if __name__ == "__main__":
    main()
