import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox
from organizer.app import Window

APP = QApplication.instance() or QApplication([])


class DesktopFlowTest(unittest.TestCase):
    def test_preview_move_restart_and_undo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads = root / "Downloads"
            downloads.mkdir()
            source = downloads / "report.pdf"
            source.write_bytes(b"test report")
            os.utime(source, (time.time() - 10, time.time() - 10))
            window = Window(root / "data")
            window.set_folder(downloads)
            window.show()
            APP.processEvents()
            window.save()
            window.refresh()
            self.assertEqual(window.files.rowCount(), 1)
            self.assertTrue(window.organize.isEnabled())
            with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
                window.organize.click()
            self.wait_worker(window)
            self.assertTrue((downloads / "Documents" / source.name).exists())
            self.assertEqual(window.history_table.item(0, 3).text(), "complete")
            window.close()
            restarted = Window(root / "data")
            self.assertEqual(restarted.folder, downloads)
            restarted.history_table.setCurrentCell(0, 0)
            restarted.undo_button.click()
            self.wait_worker(restarted)
            self.assertEqual(source.read_bytes(), b"test report")
            restarted.close()

    def test_editing_rules_invalidates_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.pdf").write_bytes(b"data")
            window = Window(root / "data")
            window.set_folder(root)
            window.refresh()
            self.assertTrue(window.organize.isEnabled())
            window.rules.item(0, 1).setText("Changed rule")
            self.assertFalse(window.organize.isEnabled())
            self.assertEqual(window.proposals, [])
            window.close()

    def wait_worker(self, window):
        deadline = time.monotonic() + 10
        while window.worker.isRunning() and time.monotonic() < deadline:
            APP.processEvents()
            time.sleep(.01)
        self.assertFalse(window.worker.isRunning(), "Worker did not finish")
        APP.processEvents()
        self.assertTrue(window.isEnabled())
