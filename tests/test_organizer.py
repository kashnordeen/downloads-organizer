import json
import tempfile
import os
import time
import sys
from unittest.mock import patch
import unittest
from pathlib import Path

from organizer.core import Rule, preview, load_settings, save_settings, safe_path
from organizer.moves import Journal


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()  # macOS /var aliases /private/var.
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

    @unittest.skipIf(sys.platform == "win32", "Creating Windows symlinks requires a privilege")
    def test_linked_folder_is_rejected(self):
        alias = self.root / "linked-downloads"
        alias.symlink_to(self.downloads, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symbolic links"):
            safe_path(alias)

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

    def test_undo_and_conflicting_original(self):
        proposal = self.ready_proposal()
        with Journal(self.root / "history.db") as journal:
            destination = journal.move(proposal)
            proposal.source.write_bytes(b"new original")
            with self.assertRaises(ValueError):
                journal.undo(1)
            proposal.source.unlink()
            journal.undo(1)
            self.assertEqual(proposal.source.read_bytes(), b"important data")
            self.assertFalse(destination.exists())
            self.assertEqual(journal.history()[1][3], "undone")

    def test_undo_refuses_modified_destination(self):
        proposal = self.ready_proposal()
        with Journal(self.root / "history.db") as journal:
            destination = journal.move(proposal)
            destination.write_bytes(b"edited")
            with self.assertRaises(ValueError):
                journal.undo(1)
            self.assertTrue(destination.exists())

    def test_recovery_after_final_database_update_failure(self):
        proposal = self.ready_proposal()
        path = self.root / "history.db"
        with Journal(path) as journal:
            original_update = journal.update
            def interrupted(operation, **fields):
                if fields.get("state") == "complete":
                    raise RuntimeError("Simulated interruption")
                return original_update(operation, **fields)
            with patch.object(journal, "update", side_effect=interrupted):
                with self.assertRaises(RuntimeError):
                    journal.move(proposal)
        with Journal(path) as journal:
            journal.recover()
            self.assertEqual(journal.history()[0][3], "complete")
            self.assertEqual(proposal.destination.read_bytes(), b"important data")

    def test_interrupted_move_with_original_only_is_safe_to_retry(self):
        proposal = self.ready_proposal()
        with Journal(self.root / "history.db") as journal:
            with patch("organizer.moves.os.link", side_effect=OSError("Unsupported filesystem")):
                with self.assertRaises(OSError):
                    journal.move(proposal)
            journal.recover()
            self.assertEqual(proposal.source.read_bytes(), b"important data")
            self.assertEqual(journal.history()[0][3], "retryable")
            self.assertIn("original is intact", journal.history()[0][4])
            self.assertEqual(list(proposal.destination.parent.glob(".organizer-*.tmp")), [])
            self.assertEqual(journal.move(proposal), proposal.destination)
            self.assertEqual([row[3] for row in journal.history()], ["complete", "retryable"])
            self.assertFalse(proposal.source.exists())
            self.assertEqual(proposal.destination.read_bytes(), b"important data")

    def test_source_removal_failure_preserves_both_copies(self):
        proposal = self.ready_proposal()
        unlink = Path.unlink
        def locked(path, *args, **kwargs):
            if path == proposal.source:
                raise PermissionError("Download is locked")
            return unlink(path, *args, **kwargs)
        with Journal(self.root / "history.db") as journal:
            with patch.object(Path, "unlink", locked):
                with self.assertRaises(PermissionError):
                    journal.move(proposal)
            journal.recover()
            self.assertEqual(proposal.source.read_bytes(), b"important data")
            self.assertEqual(proposal.destination.read_bytes(), b"important data")
            self.assertEqual(journal.history()[0][3], "review")

    def test_review_move_and_keep_verify_copies(self):
        for choice in ("move", "keep"):
            with self.subTest(choice=choice):
                proposal = self.ready_proposal()
                with Journal(self.root / f"{choice}.db") as journal:
                    unlink = Path.unlink
                    def locked(path, *args, **kwargs):
                        if path == proposal.source:
                            raise PermissionError("Download is locked")
                        return unlink(path, *args, **kwargs)
                    with patch.object(Path, "unlink", locked):
                        with self.assertRaises(PermissionError):
                            journal.move(proposal)
                    journal.recover()
                    self.assertEqual(journal.history()[0][3], "review")
                    resolved = journal.resolve_review(1, choice)
                    self.assertEqual(journal.history()[0][3], "complete" if choice == "move" else "kept")
                    self.assertEqual(resolved, proposal.destination if choice == "move" else proposal.source)
                    self.assertEqual(proposal.source.exists(), choice == "keep")
                    self.assertEqual(proposal.destination.exists(), choice == "move")
                    if choice == "keep":
                        self.assertEqual(journal.kept_sources()[str(proposal.source)], proposal.signature)
                    else:
                        resolved.unlink()

    def test_review_rejects_changed_destination(self):
        proposal = self.ready_proposal()
        with Journal(self.root / "changed.db") as journal:
            unlink = Path.unlink
            def locked(path, *args, **kwargs):
                if path == proposal.source:
                    raise PermissionError("Locked")
                return unlink(path, *args, **kwargs)
            with patch.object(Path, "unlink", locked):
                with self.assertRaises(PermissionError):
                    journal.move(proposal)
            proposal.destination.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                journal.resolve_review(1, "keep")
            self.assertTrue(proposal.source.exists())
            self.assertEqual(proposal.destination.read_bytes(), b"changed")

    def test_interrupted_keep_remains_kept_after_restart(self):
        proposal = self.ready_proposal()
        with Journal(self.root / "keep-crash.db") as journal:
            journal.db.execute("""INSERT INTO operations (source,destination,state,hash,signature,error)
                VALUES (?,?,'keep_pending',?,?, '')""",
                (str(proposal.source), str(proposal.destination), "", "[]"))
            journal.db.commit()
            journal.recover()
            self.assertEqual(journal.history()[0][3], "kept")
            self.assertEqual(journal.kept_sources()[str(proposal.source)], proposal.signature)

    def test_source_change_during_copy_is_preserved(self):
        proposal = self.ready_proposal()
        import shutil
        copy = shutil.copyfileobj
        def changing(origin, target, length):
            copy(origin, target, length)
            proposal.source.write_bytes(b"new download data")
        with Journal(self.root / "history.db") as journal:
            with patch("organizer.moves.shutil.copyfileobj", changing):
                with self.assertRaises(ValueError):
                    journal.move(proposal)
            self.assertEqual(proposal.source.read_bytes(), b"new download data")
            self.assertFalse(proposal.destination.exists())

    def test_disappearing_file_does_not_break_scan(self):
        proposal = self.ready_proposal()
        rules = [Rule("PDF", ["pdf"], "", str(self.root / "PDF"))]
        with patch("organizer.core.signature", side_effect=FileNotFoundError):
            self.assertEqual(preview(self.downloads, rules), [])
        self.assertTrue(proposal.source.exists())


if __name__ == "__main__":
    unittest.main()
