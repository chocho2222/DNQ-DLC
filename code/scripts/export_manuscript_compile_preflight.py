#!/usr/bin/env python
import argparse
import csv
import json
import re
import shutil
from pathlib import Path


CITEP_RE = re.compile(r"\\citep\{([^}]+)\}")
BIB_KEY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_row(check_id, label, status, evidence, author_action, required=True):
    return {
        "check_id": check_id,
        "label": label,
        "status": status,
        "evidence": evidence,
        "author_action": author_action,
        "required_before_submission": required,
    }


def extract_abstract(tex):
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def build_report(root):
    source = load_json(root / "materials" / "MANUSCRIPT_SOURCE_PACKAGE_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")

    tex_path = root / "manuscript" / "main.tex"
    bib_path = root / "manuscript" / "references.bib"
    tex = tex_path.read_text(encoding="utf-8") if tex_path.exists() else ""
    bib = bib_path.read_text(encoding="utf-8") if bib_path.exists() else ""

    cite_keys = []
    for group in CITEP_RE.findall(tex):
        cite_keys.extend(key.strip() for key in group.split(",") if key.strip())
    bib_keys = set(BIB_KEY_RE.findall(bib))
    missing_bib_keys = sorted(set(cite_keys) - bib_keys)
    abstract_text = extract_abstract(tex)

    tools = {
        "pdflatex": shutil.which("pdflatex"),
        "bibtex": shutil.which("bibtex"),
        "latexmk": shutil.which("latexmk"),
    }
    compile_tool_status = "pass" if tools["latexmk"] or (tools["pdflatex"] and tools["bibtex"]) else "author_action_required"

    checks = [
        check_row(
            "tex_file_present",
            "main.tex exists.",
            "pass" if tex_path.exists() else "review_required",
            "manuscript/main.tex",
            "Regenerate the manuscript source package.",
        ),
        check_row(
            "bib_file_present",
            "references.bib exists.",
            "pass" if bib_path.exists() else "review_required",
            "manuscript/references.bib",
            "Regenerate the manuscript draft package or restore references.bib.",
        ),
        check_row(
            "document_environment",
            "LaTeX document environment is present.",
            "pass" if r"\begin{document}" in tex and r"\end{document}" in tex else "review_required",
            "begin/end document markers",
            "Repair main.tex before target-journal conversion.",
        ),
        check_row(
            "abstract_environment",
            "Abstract environment is present and non-empty.",
            "pass" if abstract_text else "review_required",
            f"abstract_char_count={len(abstract_text)}",
            "Repair Markdown-to-TeX conversion so the abstract text remains inside the abstract environment.",
        ),
        check_row(
            "citation_commands",
            "LaTeX citation commands are present and not escaped.",
            "pass" if source["summary"]["citation_conversion_status"] == "pass" else "review_required",
            (
                f"markdown={source['summary']['markdown_citation_count']}; "
                f"citep={source['summary']['tex_citep_count']}; "
                f"escaped={source['summary']['escaped_citation_count']}"
            ),
            "Regenerate manuscript source package after citation-conversion fixes.",
        ),
        check_row(
            "bib_key_resolution",
            "All LaTeX citation keys resolve in references.bib.",
            "pass" if not missing_bib_keys else "review_required",
            f"cite_key_count={len(set(cite_keys))}; missing={','.join(missing_bib_keys)}",
            "Add missing BibTeX entries or correct citation keys before compiling.",
        ),
        check_row(
            "compile_tools_available",
            "Local LaTeX compile tools are available.",
            compile_tool_status,
            "; ".join(f"{name}={path or 'missing'}" for name, path in tools.items()),
            "Install latexmk or pdflatex+bibtex, then compile the final target-journal source.",
            required=False,
        ),
        check_row(
            "publication_verification_snapshot",
            "Publication package verification is passing.",
            verification["summary"]["status"],
            f"failed_gates={verification['summary']['failed_gates']}",
            "Rerun publication verification after source-package changes.",
        ),
    ]

    blocking = [row for row in checks if row["required_before_submission"] and row["status"] != "pass"]
    return {
        "root": str(root),
        "title": "Manuscript compile preflight",
        "purpose": "Record LaTeX source, citation, bibliography, and local compile-tool readiness before final journal template conversion.",
        "summary": {
            "check_count": len(checks),
            "blocking_check_count": len(blocking),
            "status": "pass" if not blocking else "review_required",
            "compile_tool_status": compile_tool_status,
            "pdflatex_available": bool(tools["pdflatex"]),
            "bibtex_available": bool(tools["bibtex"]),
            "latexmk_available": bool(tools["latexmk"]),
            "abstract_char_count": len(abstract_text),
            "cite_key_count": len(set(cite_keys)),
            "missing_bib_key_count": len(missing_bib_keys),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
        },
        "checks": checks,
        "missing_bib_keys": missing_bib_keys,
        "tool_paths": tools,
        "interpretation": (
            "This preflight does not prove final PDF compilation when LaTeX tools are unavailable. "
            "It records static source readiness and the exact local tool gap."
        ),
    }


def write_csv(report, path):
    fields = ["check_id", "label", "status", "evidence", "author_action", "required_before_submission"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["checks"]:
            writer.writerow(row)


def write_markdown(report, path):
    lines = [
        "# Manuscript Compile Preflight",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Status: `{report['summary']['status']}`",
        f"- Blocking checks: {report['summary']['blocking_check_count']}",
        f"- Compile-tool status: `{report['summary']['compile_tool_status']}`",
        f"- pdflatex available: {report['summary']['pdflatex_available']}",
        f"- bibtex available: {report['summary']['bibtex_available']}",
        f"- latexmk available: {report['summary']['latexmk_available']}",
        f"- Abstract characters: {report['summary']['abstract_char_count']}",
        f"- Citation keys: {report['summary']['cite_key_count']}",
        f"- Missing BibTeX keys: {report['summary']['missing_bib_key_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        "",
        "## Checks",
        "",
        "| check | status | required before submission | evidence | author action |",
        "|---|---|---:|---|---|",
    ]
    for row in report["checks"]:
        lines.append(
            f"| {row['label']} | {row['status']} | {row['required_before_submission']} | {row['evidence']} | {row['author_action']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export manuscript compile preflight audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "MANUSCRIPT_COMPILE_PREFLIGHT.json"
    out_md = materials / "MANUSCRIPT_COMPILE_PREFLIGHT.md"
    out_csv = materials / "MANUSCRIPT_COMPILE_PREFLIGHT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
