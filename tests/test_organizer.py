import json
import tempfile
import os
import time
import unittest
from pathlib import Path

from organizer.core import Rule, preview, load_settings, save_settings
from organizer.moves import Journal


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.downloads = self.root / "Downloads"
        self.downloads.mkdir()

    def test_preview_matches_first_rule_and_never_moves(self):
        source = self.downloads / "Invoice.PDF"
        source.write_bytes(b"invoice")
        rules = [Rule("Invoices", ["pdf"], "invoice", str(self.downloads / "Invoices")),
                 Rule("PDFs", ["pdf"], "", str(self.downloads / "PDFs"))]
        rows = preview(self.downloads, rules)
        self.assertEqual(rows[0].destination, self.downloads / "Invoices" / source.name)
        self.assertTrue(source.exists())
        self.assertFalse((self.downloads / "Invoices").exists())

    def test_skips_partial_system_unmatched_and_subfolders(self):
        for name in ["x.pdf.crdownload", "desktop.ini", "~$temp.pdf", "unknown.xyz"]:
            (self.downloads / name).write_bytes(b"x")
        (self.downloads / "Existing").mkdir()
        rows = preview(self.downloads, [Rule("PDF", ["pdf"], "", str(self.root / "PDF"))])
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row.destination is None for row in rows))

    def test_settings_round_trip_and_invalid_rule(self):
        path = self.root / "settings.json"
        rules = [Rule("PDF", [".PDF"], "", str(self.root / "PDF"))]
        save_settings(path, self.downloads, rules)
        folder, restored = load_settings(path)
        self.assertEqual(folder, self.downloads)
        self.assertEqual(restored[0].extensions, ["pdf"])
        with self.assertRaises(ValueError):
            Rule("No filter", [], "", str(self.root)).validate(self.downloads)
        with self.assertRaises(ValueError):
            Rule("Loop", ["pdf"], "", str(self.downloads)).validate(self.downloads)
        path.write_text('{"broken":true}', encoding="utf-8")
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            load_settings(path)
        self.assertEqual(path.read_bytes(), before)

    def ready_proposal(self):
        source = self.downloads / "sample.pdf"
        source.write_bytes(b"important data")
        os.utime(source, (time.time() - 10, time.time() - 10))
        return preview(self.downloads, [Rule("PDF", ["pdf"], "", str(self.root / "PDF"))])[0]

    def test_move_preserves_collision_and_records_history(self):
        proposal = self.ready_proposal()
        proposal.destination.parent.mkdir()
        proposal.destination.write_bytes(b"existing")
        with Journal(self.root / "history.db") as journal:
            actual = journal.move(proposal)
            self.assertEqual(actual.name, "sample (1).pdf")
            self.assertEqual(actual.read_bytes(), b"important data")
            self.assertEqual(proposal.destination.read_bytes(), b"existing")
            self.assertFalse(proposal.source.exists())
            self.assertEqual(journal.history()[0][3], "complete")

    def test_changed_or_new_download_is_not_moved(self):
        proposal = self.ready_proposal()
        proposal.source.write_bytes(b"changed")
        with Journal(self.root / "history.db") as journal:
            with self.assertRaises(ValueError):
                journal.move(proposal)
            self.assertEqual(proposal.source.read_bytes(), b"changed")


if __name__ == "__main__":
    unittest.main()
