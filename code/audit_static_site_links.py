#!/usr/bin/env python
"""Audit repository-relative links in the static evidence site."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.links.append(value)


def local_target(html_path: Path, raw_link: str) -> Path | None:
    parsed = urlsplit(raw_link)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    if raw_link.startswith(("#", "mailto:", "javascript:", "data:")):
        return None
    target = html_path.parent / unquote(parsed.path)
    if parsed.path.endswith("/"):
        target = target / "index.html"
    return target.resolve()


def audit(site_root: Path) -> tuple[int, list[dict[str, str]]]:
    site_root = site_root.resolve()
    checked = 0
    missing: list[dict[str, str]] = []
    for html_path in sorted(site_root.rglob("*.html")):
        collector = LinkCollector()
        collector.feed(html_path.read_text(encoding="utf-8"))
        for raw_link in collector.links:
            target = local_target(html_path, raw_link)
            if target is None:
                continue
            checked += 1
            if not target.exists():
                missing.append(
                    {
                        "source": html_path.relative_to(site_root).as_posix(),
                        "link": raw_link,
                    }
                )
    return checked, missing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-root", default="docs")
    parser.add_argument(
        "--output", default="docs/tables/public_site_link_audit.json"
    )
    args = parser.parse_args()

    checked, missing = audit(Path(args.site_root))
    report = {
        "checked_date": datetime.now(timezone.utc).date().isoformat(),
        "relative_link_count": checked,
        "missing": missing,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Checked {checked} relative links; missing={len(missing)}")
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
