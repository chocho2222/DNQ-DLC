#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


CITATION_RE = re.compile(r"\[@([A-Za-z0-9:_-]+)\]")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def tex_escape(text):
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def convert_inline(text):
    protected = []

    def protect(value):
        protected.append(value)
        return f"@@CODE{len(protected) - 1}@@"

    text = INLINE_CODE_RE.sub(lambda match: protect(r"\texttt{" + tex_escape(match.group(1)) + "}"), text)
    text = CITATION_RE.sub(lambda match: protect(r"\citep{" + match.group(1) + "}"), text)
    text = tex_escape(text)
    for index, value in enumerate(protected):
        text = text.replace(tex_escape(f"@@CODE{index}@@"), value)
    text = re.sub(r"\*\*([^*]+)\*\*", lambda match: r"\textbf{" + match.group(1) + "}", text)
    return text


def heading_to_tex(line):
    hashes, title = line.split(" ", 1)
    level = len(hashes)
    title = tex_escape(title.strip())
    if level == 1:
        return r"\title{" + title + "}"
    if level == 2:
        return r"\section{" + title + "}"
    if level == 3:
        return r"\subsection{" + title + "}"
    return r"\paragraph{" + title + "}"


def markdown_to_tex(markdown):
    lines = markdown.splitlines()
    out = []
    in_itemize = False
    title_written = False
    abstract_open = False

    def close_itemize():
        nonlocal in_itemize
        if in_itemize:
            out.append(r"\end{itemize}")
            in_itemize = False

    for raw in lines:
        line = raw.rstrip()
        if not line:
            close_itemize()
            out.append("")
            continue
        if line.startswith(">"):
            close_itemize()
            out.append("% " + tex_escape(line.lstrip("> ")))
            continue
        if line.startswith("# "):
            close_itemize()
            out.append(heading_to_tex(line))
            out.extend(
                [
                    r"\author{Author metadata pending final confirmation}",
                    r"\date{}",
                    r"\maketitle",
                ]
            )
            title_written = True
            continue
        if line == "## Abstract":
            close_itemize()
            out.append(r"\begin{abstract}")
            abstract_open = True
            continue
        if line.startswith("## ") or line.startswith("### "):
            close_itemize()
            if abstract_open:
                out.append(r"\end{abstract}")
                abstract_open = False
            out.append(heading_to_tex(line))
            continue
        if line.startswith("- "):
            if not in_itemize:
                out.append(r"\begin{itemize}")
                in_itemize = True
            out.append(r"\item " + convert_inline(line[2:]))
            continue
        close_itemize()
        out.append(convert_inline(line))

    close_itemize()
    if abstract_open:
        out.append(r"\end{abstract}")
    if not title_written:
        out.insert(0, r"\title{Manuscript title pending}")
    return "\n".join(out)


def build_tex(root):
    markdown = (root / "manuscript" / "main.md").read_text(encoding="utf-8")
    body = markdown_to_tex(markdown)
    preamble = "\n".join(
        [
            r"\documentclass[11pt]{article}",
            r"\usepackage[margin=1in]{geometry}",
            r"\usepackage{graphicx}",
            r"\usepackage{booktabs}",
            r"\usepackage{hyperref}",
            r"\usepackage[numbers,sort&compress]{natbib}",
            r"\hypersetup{colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue}",
            "",
            "% Journal-neutral source scaffold generated from manuscript/main.md.",
            "% Authors must convert this file to the selected journal template before submission.",
            "",
            r"\begin{document}",
            "",
        ]
    )
    ending = "\n".join(
        [
            "",
            r"\section*{Data and code availability}",
            "See the manuscript text and materials/DATA_CODE_AVAILABILITY.md. External DOI or accession is pending author deposition.",
            "",
            r"\section*{Acknowledgements}",
            "Author acknowledgements, funding, competing interests, and CRediT contributions require author confirmation.",
            "",
            r"\bibliographystyle{plainnat}",
            r"\bibliography{references}",
            "",
            r"\end{document}",
            "",
        ]
    )
    return preamble + body + ending


def build_report(root):
    manifest = load_json(root / "manifest.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    cross = load_json(root / "materials" / "MANUSCRIPT_CROSS_REFERENCE_AUDIT.json")
    reference = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")
    claim = load_json(root / "materials" / "MANUSCRIPT_CLAIM_QA.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    tex_text = (root / "manuscript" / "main.tex").read_text(encoding="utf-8")
    md_text = (root / "manuscript" / "main.md").read_text(encoding="utf-8")
    markdown_citation_count = len(CITATION_RE.findall(md_text))
    tex_citep_count = tex_text.count(r"\citep{")
    escaped_citation_count = tex_text.count(r"\textbackslash{}citep")

    files = [
        {
            "path": "manuscript/main.md",
            "role": "source_markdown",
            "required": True,
            "status": "ready",
            "note": "Evidence-linked conservative manuscript draft.",
        },
        {
            "path": "manuscript/main.tex",
            "role": "journal_neutral_latex_source",
            "required": True,
            "status": "ready",
            "note": "Generated source scaffold; convert to selected journal template before submission.",
        },
        {
            "path": "manuscript/references.bib",
            "role": "starter_bibliography",
            "required": True,
            "status": "ready",
            "note": "Reference readiness audit passes, but final related-work breadth remains author-curated.",
        },
        {
            "path": "manuscript/SOURCE_PACKAGE_README.md",
            "role": "source_package_readme",
            "required": True,
            "status": "ready",
            "note": "Explains journal-neutral source package scope and remaining author actions.",
        },
        {
            "path": "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.md",
            "role": "source_package_audit",
            "required": True,
            "status": "ready",
            "note": "Machine-readable and human-readable audit for source package readiness.",
        },
    ]

    for item in files:
        path = root / item["path"]
        item["exists"] = path.exists()
        item["size_bytes"] = path.stat().st_size if path.exists() and path.is_file() else None
        if not item["exists"]:
            item["status"] = "review_required"

    return {
        "root": str(root),
        "title": "Manuscript source package audit",
        "purpose": "Provide a journal-neutral LaTeX/source scaffold tied to the evidence-linked Markdown manuscript.",
        "scope": {
            "package_title": manifest["title"],
            "not_final_journal_template": True,
            "author_action_boundary": "Final journal class file, title page metadata, disclosures, and PDF generation remain author actions.",
        },
        "files": files,
        "summary": {
            "file_count": len(files),
            "ready_count": sum(1 for item in files if item["status"] == "ready"),
            "review_required_count": sum(1 for item in files if item["status"] != "ready"),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "cross_reference_status": cross["summary"]["status"],
            "missing_reference_count": cross["summary"]["missing_reference_count"],
            "reference_status": reference["summary"]["status"],
            "claim_qa_status": claim["summary"]["status"],
            "claim_qa_blockers": claim["summary"]["blockers"],
            "markdown_citation_count": markdown_citation_count,
            "tex_citep_count": tex_citep_count,
            "escaped_citation_count": escaped_citation_count,
            "citation_conversion_status": "pass"
            if markdown_citation_count == tex_citep_count and escaped_citation_count == 0
            else "review_required",
        },
        "author_actions": [
            "Select target journal and article type.",
            "Move main.tex into the target journal class/template.",
            "Insert verified author names, affiliations, ORCIDs, funding, competing interests, acknowledgements, and CRediT contributions.",
            "Insert public archive DOI/URL after deposition.",
            "Compile the final PDF and rerun manuscript claim and cross-reference QA.",
        ],
        "interpretation": (
            "This source package improves local manuscript traceability but is not a final journal source/PDF package."
        ),
    }


def write_csv(report, path):
    fields = ["path", "role", "required", "exists", "size_bytes", "status", "note"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["files"]:
            writer.writerow({field: row[field] for field in fields})


def write_markdown(report, path):
    lines = [
        "# Manuscript Source Package Audit",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- File count: {report['summary']['file_count']}",
        f"- Ready count: {report['summary']['ready_count']}",
        f"- Review required count: {report['summary']['review_required_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- Cross-reference status: `{report['summary']['cross_reference_status']}`",
        f"- Reference status: `{report['summary']['reference_status']}`",
        f"- Claim QA status: `{report['summary']['claim_qa_status']}`",
        f"- Markdown citations: {report['summary']['markdown_citation_count']}",
        f"- LaTeX citep commands: {report['summary']['tex_citep_count']}",
        f"- Escaped citation commands: {report['summary']['escaped_citation_count']}",
        f"- Citation conversion status: `{report['summary']['citation_conversion_status']}`",
        "",
        "## Files",
        "",
        "| path | role | required | status | size bytes | note |",
        "|---|---|---:|---|---:|---|",
    ]
    for row in report["files"]:
        lines.append(
            f"| `{row['path']}` | {row['role']} | {row['required']} | {row['status']} | {row['size_bytes']} | {row['note']} |"
        )
    lines.extend(["", "## Author Actions", ""])
    lines.extend(f"- {item}" for item in report["author_actions"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_readme(report, path):
    lines = [
        "# Manuscript Source Package",
        "",
        "This directory contains an evidence-linked manuscript draft and a journal-neutral LaTeX source scaffold.",
        "",
        "Files:",
        "",
        "- `main.md`: authoritative evidence-linked Markdown draft.",
        "- `main.tex`: generated journal-neutral LaTeX scaffold for author/template conversion.",
        "- `references.bib`: starter bibliography.",
        "- `manuscript_manifest.json`: local manuscript file map.",
        "- `figures/README.md`: figure source mapping.",
        "",
        "Boundary:",
        "",
        "- This is not a final journal template or submitted PDF.",
        "- Author metadata, disclosures, target journal class files, and external archive DOI/URL are intentionally pending.",
        "- Rerun `materials/MANUSCRIPT_CLAIM_QA.md` and `materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.md` after final manuscript edits.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export journal-neutral manuscript source package.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    manuscript = root / "manuscript"
    materials = root / "materials"
    manuscript.mkdir(parents=True, exist_ok=True)
    materials.mkdir(parents=True, exist_ok=True)

    (manuscript / "main.tex").write_text(build_tex(root), encoding="utf-8")
    report = build_report(root)
    readme = manuscript / "SOURCE_PACKAGE_README.md"
    out_json = materials / "MANUSCRIPT_SOURCE_PACKAGE_AUDIT.json"
    out_md = materials / "MANUSCRIPT_SOURCE_PACKAGE_AUDIT.md"
    out_csv = materials / "MANUSCRIPT_SOURCE_PACKAGE_AUDIT.csv"
    write_readme(report, readme)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"tex": str(manuscript / "main.tex"), "readme": str(readme), "json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
