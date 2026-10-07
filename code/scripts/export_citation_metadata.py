#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cff_quote(value):
    text = "" if value is None else str(value)
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def split_person(name):
    parts = name.split()
    if len(parts) <= 1:
        return {"family-names": name, "given-names": ""}
    return {"family-names": parts[-1], "given-names": " ".join(parts[:-1])}


def cff_author(creator):
    name = creator["name"]
    if "Laboratory" in name or "MIT " in name:
        return {"name": name}
    return split_person(name)


def bibtex_key(title):
    words = "".join(ch if ch.isalnum() else " " for ch in title).lower().split()
    return "multicar_overtake_" + "_".join(words[:4])


def build_metadata(root):
    fair = load_json(root / "materials" / "FAIR_ARCHIVE_METADATA.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    archive_readme = load_json(root / "materials" / "ARCHIVE_README.json")
    blockers = load_json(root / "materials" / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json")

    authors = [cff_author(creator) for creator in fair["creators"]]
    external_doi = fair["identifier"]["external_doi"]
    external_url = fair["identifier"]["external_url"]
    title = fair["title"]
    version = fair["version"]["package_label"]
    license_name = fair["license"]["name"] or "License text present"
    license_spdx = "MIT" if license_name == "MIT License" else "NOASSERTION"

    cff = {
        "cff-version": "1.2.0",
        "message": "If you use this code/data package, please cite it using this metadata and update DOI fields after public deposition.",
        "title": title,
        "version": version,
        "type": "dataset",
        "authors": authors,
        "abstract": fair["description"],
        "keywords": fair["keywords"],
        "license": license_spdx,
        "repository-code": external_url or "",
        "url": external_url or "",
        "doi": external_doi or "",
        "date-released": "",
    }

    rows = [
        {
            "field": "title",
            "value": title,
            "status": "package_supported",
            "author_action": "Review title against final journal wording.",
        },
        {
            "field": "authors",
            "value": "; ".join(creator["name"] for creator in fair["creators"]),
            "status": "author_review_required",
            "author_action": "Confirm author list, order, affiliations, ORCID IDs, and corresponding author.",
        },
        {
            "field": "version",
            "value": version,
            "status": "package_supported",
            "author_action": "Update if a final frozen release tag is assigned.",
        },
        {
            "field": "doi",
            "value": external_doi or "",
            "status": "author_required",
            "author_action": "Insert DOI after public archive deposition.",
        },
        {
            "field": "url",
            "value": external_url or "",
            "status": "author_required",
            "author_action": "Insert public repository URL after deposition.",
        },
        {
            "field": "license",
            "value": license_name,
            "status": "package_supported_with_author_review",
            "author_action": "Confirm third-party and repository-license handling before release.",
        },
        {
            "field": "release_files",
            "value": str(release["summary"]["file_count"]),
            "status": "package_supported",
            "author_action": "Regenerate release manifest after final edits.",
        },
        {
            "field": "artifact_provenance",
            "value": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "status": "package_supported",
            "author_action": "Keep provenance complete after final edits.",
        },
    ]

    return {
        "root": str(root),
        "title": "Citation metadata package",
        "purpose": "Provide machine-readable citation metadata for public archive deposition and journal data/code availability.",
        "citation_key": bibtex_key(title),
        "cff": cff,
        "rows": rows,
        "summary": {
            "row_count": len(rows),
            "author_required_count": sum(1 for row in rows if row["status"] == "author_required"),
            "author_review_required_count": sum(1 for row in rows if "author_review" in row["status"]),
            "creator_count": len(fair["creators"]),
            "external_doi_present": external_doi is not None,
            "external_url_present": external_url is not None,
            "license": license_name,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "archive_readme_ready": archive_readme["summary"]["review_required_count"] == 0,
            "remaining_author_required_count": blockers["summary"]["author_required_count"],
        },
        "boundaries": [
            "Citation metadata is a local archive draft until a public DOI or URL is assigned.",
            "Author order, ORCID IDs, affiliations, and corresponding-author metadata require author confirmation.",
            "The package supports simulator-only non-VLM evidence and must not be cited as real-road validation.",
        ],
    }


def write_cff(report, path):
    cff = report["cff"]
    lines = [
        f"cff-version: {cff_quote(cff['cff-version'])}",
        f"message: {cff_quote(cff['message'])}",
        f"title: {cff_quote(cff['title'])}",
        f"version: {cff_quote(cff['version'])}",
        f"type: {cff_quote(cff['type'])}",
        "authors:",
    ]
    for author in cff["authors"]:
        lines.append("  -")
        for key, value in author.items():
            if value:
                lines.append(f"    {key}: {cff_quote(value)}")
    lines.extend(
        [
            f"abstract: {cff_quote(cff['abstract'])}",
            "keywords:",
        ]
    )
    for keyword in cff["keywords"]:
        lines.append(f"  - {cff_quote(keyword)}")
    lines.append(f"license: {cff_quote(cff['license'])}")
    if cff["repository-code"]:
        lines.append(f"repository-code: {cff_quote(cff['repository-code'])}")
    if cff["url"]:
        lines.append(f"url: {cff_quote(cff['url'])}")
    if cff["doi"]:
        lines.append(f"doi: {cff_quote(cff['doi'])}")
    if cff["date-released"]:
        lines.append(f"date-released: {cff_quote(cff['date-released'])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_bibtex(report, path):
    cff = report["cff"]
    author_names = []
    for author in cff["authors"]:
        if "name" in author:
            author_names.append(author["name"])
        else:
            given = author.get("given-names", "")
            family = author.get("family-names", "")
            author_names.append(f"{family}, {given}".strip(", "))
    fields = {
        "title": cff["title"],
        "author": " and ".join(author_names),
        "year": "forthcoming",
        "version": cff["version"],
        "note": "Local code/data archive metadata draft; DOI and URL pending public deposition.",
    }
    if cff["doi"]:
        fields["doi"] = cff["doi"]
    if cff["url"]:
        fields["url"] = cff["url"]
    lines = [f"@misc{{{report['citation_key']},"]
    for key, value in fields.items():
        lines.append(f"  {key} = {{{value}}},")
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(report, path):
    fields = ["field", "value", "status", "author_action"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Citation Metadata Package",
        "",
        report["purpose"],
        "",
        "## Summary",
        "",
        f"- Citation key: `{report['citation_key']}`",
        f"- Creators: {report['summary']['creator_count']}",
        f"- External DOI present: {report['summary']['external_doi_present']}",
        f"- External URL present: {report['summary']['external_url_present']}",
        f"- License: {report['summary']['license']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        "",
        "## Files",
        "",
        "- `materials/CITATION.cff`",
        "- `materials/CITATION.bib`",
        "- `materials/CITATION_METADATA.json`",
        "- `materials/CITATION_METADATA.csv`",
        "",
        "## Fields",
        "",
        "| field | status | value | author action |",
        "|---|---|---|---|",
    ]
    for row in report["rows"]:
        lines.append(f"| {row['field']} | {row['status']} | {row['value']} | {row['author_action']} |")
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {item}" for item in report["boundaries"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export citation metadata package.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_metadata(root)
    out_json = materials / "CITATION_METADATA.json"
    out_md = materials / "CITATION_METADATA.md"
    out_csv = materials / "CITATION_METADATA.csv"
    out_cff = materials / "CITATION.cff"
    out_bib = materials / "CITATION.bib"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    write_cff(report, out_cff)
    write_bibtex(report, out_bib)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "cff": str(out_cff),
                "bibtex": str(out_bib),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
