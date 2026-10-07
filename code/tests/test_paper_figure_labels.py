"""Guard against stale identifiers and non-English text inside paper figures.

The manuscript figures are produced by scripts that once carried the earlier
method acronym and Chinese annotation banners. Both classes of defect are
invisible in the .tex source, because the offending text lives inside the
rendered figure, so the check reads the referenced figure files themselves.
"""
import re
import hashlib
import json
import shutil
import subprocess
import unittest
from pathlib import Path


from _repo_paths import PAPER
TEX_FILES = ("main.tex", "supplementary.tex")
INCLUDE_RE = re.compile(r"\\includegraphics\[[^\]]*\]\{([^}]*)\}")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def referenced_figures():
    figures = set()
    for name in TEX_FILES:
        path = PAPER / name
        if path.exists():
            figures.update(INCLUDE_RE.findall(path.read_text(encoding="utf-8")))
    return sorted(figures)


@unittest.skipUnless(shutil.which("pdftotext") and PAPER.exists(),
                     "paper sources or pdftotext unavailable")
class PaperFigureLabelTests(unittest.TestCase):
    def figure_text(self, relative):
        path = PAPER / relative
        if not path.exists():
            self.fail(f"referenced figure is missing: {relative}")
        if path.suffix.lower() != ".pdf":
            return None
        result = subprocess.run(["pdftotext", str(path), "-"],
                                capture_output=True, text=True, check=True)
        return result.stdout

    def test_figures_exist(self):
        self.assertTrue(referenced_figures())

    def test_no_retired_acronym_in_figures(self):
        offenders = []
        for relative in referenced_figures():
            text = self.figure_text(relative)
            if text and "DRQ" in text:
                offenders.append(relative)
        self.assertEqual(offenders, [], f"retired acronym inside figures: {offenders}")

    def test_raster_contact_sheets_match_their_provenance_record(self):
        """The rebuilt contact sheets are images, so verify them by provenance.

        The record is written by
        ``scripts/rebuild_archived_contact_sheets.py`` and names the archived
        summary/trace/GIF of every panel, so a silently edited or re-exported
        sheet is caught even though its banner text cannot be extracted.

        Rasters that are drawings rather than result figures have no archived
        run behind them. They are recorded, with a SHA-256, in
        ``figure_raster_sources.json``, so the same guarantee holds: a raster
        referenced by the paper must match a recorded digest, whichever record
        it is listed in.
        """
        record_path = PAPER / "figures" / "figure_contact_sheet_sources.json"
        self.assertTrue(record_path.exists(), "contact-sheet provenance record missing")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(record["banner_language"], "en")
        self.assertFalse(record["re_simulated"])
        entries = {entry["file"]: entry for entry in record["sheets"]}
        drawings_path = PAPER / "figures" / "figure_raster_sources.json"
        self.assertTrue(drawings_path.exists(), "raster drawing record missing")
        drawings = json.loads(drawings_path.read_text(encoding="utf-8"))
        entries.update({entry["file"]: entry for entry in drawings["drawings"]})
        for relative in referenced_figures():
            path = PAPER / relative
            if path.suffix.lower() not in (".png", ".jpg", ".tiff"):
                continue
            entry = entries.get(path.name)
            self.assertIsNotNone(entry, f"{path.name} has no provenance record")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, entry["sha256"], f"{path.name} does not match its record")
            for panel in entry.get("panels", []):
                for field in ("source_summary", "source_trace", "source_gif"):
                    self.assertTrue(Path(panel[field]).exists(), f"{field} missing: {panel[field]}")

    def test_no_cjk_in_figures(self):
        offenders = []
        for relative in referenced_figures():
            text = self.figure_text(relative)
            if text and CJK_RE.search(text):
                offenders.append(relative)
        self.assertEqual(offenders, [], f"non-English text inside figures: {offenders}")


if __name__ == "__main__":
    unittest.main()
