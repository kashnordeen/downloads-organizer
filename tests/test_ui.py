import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QTimer, Qt, QAbstractAnimation
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
from organizer.app import Window

APP = QApplication.instance() or QApplication([])


class DesktopFlowTest(unittest.TestCase):
    def setUp(self):
        # Keep UI checks independent of this PC's real startup registration.
        startup = patch("organizer.app.startup_enabled", return_value=False)
        startup.start()
        self.addCleanup(startup.stop)

    def test_first_launch_requires_selection_and_preserves_saved_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            downloads = root / "Downloads"
            downloads.mkdir()
            source = downloads / "leave-me.pdf"
            source.write_bytes(b"unchanged")
            window = Window(root / "data")
            with patch("organizer.app.initial_folder", return_value=None):
                window.setup_first_run()
            self.assertIsNone(window.folder)
            self.assertFalse(window.settings_path.exists())
            with patch("organizer.app.initial_folder", return_value=str(downloads)), \
                 patch("organizer.app.guided_tour") as tour:
                window.setup_first_run()
            tour.assert_called_once_with(window)
            self.assertTrue(window.tour_done)
            self.assertFalse(window.automatic.isChecked())
            self.assertEqual(source.read_bytes(), b"unchanged")
            window.rules.item(0, 1).setText("My documents")
            window.save()
            window.close()
            restarted = Window(root / "data")
            with patch("organizer.app.initial_folder") as setup:
                restarted.setup_first_run()
                setup.assert_not_called()
            self.assertEqual(restarted.read_rules()[0].name, "My documents")
            self.assertFalse(restarted.automatic.isChecked())
            restarted.close()

    def test_update_checks_are_opt_in_and_preference_survives_upgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with patch("organizer.updates.latest_release", return_value=("2.0.0", "https://github.com/kashnordeen/downloads-organizer/releases/tag/v2.0.0")) as lookup:
                window = Window(root / "data")
                window.set_folder(root)
                APP.processEvents()
                self.assertFalse(window.update_notifications.isChecked())
                lookup.assert_not_called()
                window.check_updates()
                self.wait_until(lambda: not window.update_worker.isRunning())
                APP.processEvents()
                self.assertIn("2.0.0", window.update_status.text())
                self.assertTrue(window.download_update.isEnabled())
                window.update_notifications.setChecked(True)
                self.wait_until(lambda: not window.update_worker.isRunning())
                APP.processEvents()
                window.close()
                restarted = Window(root / "data")
                self.assertTrue(restarted.update_notifications.isChecked())
                APP.processEvents()
                self.wait_until(lambda: restarted.update_worker is not None and not restarted.update_worker.isRunning())
                APP.processEvents()
                restarted.close()

    def test_guided_tour_visits_every_workspace_page(self):
        from organizer.ui import guided_tour
        with tempfile.TemporaryDirectory() as directory:
            window = Window(Path(directory).resolve() / "data")
            pages = []
            def advance():
                pages.append(window.pages.currentIndex())
                dialog = APP.activeModalWidget()
                next_button = next(child for child in dialog.findChildren(QPushButton)
                                   if child.text() in ("Next", "Finish tour"))
                next_button.click()
                if len(pages) < 5:
                    QTimer.singleShot(0, advance)
            QTimer.singleShot(0, advance)
            guided_tour(window)
            self.assertEqual(pages, [1, 0, 2, 3, 0])
            self.assertEqual(window.pages.currentIndex(), 0)
            window.close()

    def test_rule_form_rejects_invalid_destination_and_saves_normalized_rule(self):
        from organizer.ui import RuleDialog
        from organizer.core import Rule
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            window = Window(root / "data")
            window.set_folder(root)
            dialog = RuleDialog(window, Rule("PDFs", [".PDF"], "", str(root)))
            with patch.object(QMessageBox, "warning") as warning:
                dialog.accept()
                warning.assert_called_once()
                self.assertIsNone(dialog.rule)
                dialog.destination.setText(str(root / "PDFs"))
                dialog.accept()  # Never let a failing check leave a modal prompt open in CI.
                self.assertEqual(warning.call_count, 1)
            self.assertEqual(dialog.rule.extensions, ["pdf"])
            with patch("organizer.app.RuleDialog", return_value=dialog):
                with patch.object(dialog, "exec", return_value=1):
                    window.edit_rule(new=True)
            self.assertEqual(window.read_rules()[-1].name, "PDFs")
            self.assertEqual(window.files.rowCount(), 0)
            window.close()

    def test_workspace_navigation_preserves_preview_and_icon(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "sample.pdf").write_bytes(b"data")
            window = Window(root / "data")
            window.set_folder(root)
            window.refresh()
            proposals = list(window.proposals)
            self.assertFalse(window.windowIcon().isNull())
            self.assertFalse(window.tray.icon().isNull())
            for index in [1, 2, 3, 0]:
                window.navigation.button(index).click()
                self.assertEqual(window.pages.currentIndex(), index)
                self.assertEqual(window.proposals, proposals)
                self.assertTrue(window.organize.isEnabled())
            window.rules.item(0, 1).setText("Changed rule")
            self.assertFalse(window.organize.isEnabled())
            self.assertEqual(window.files.rowCount(), 0)
            window.close()

    def test_rule_numbers_follow_priority_and_tab_motion_survives_rapid_switches(self):
        from organizer.core import Rule
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            window = Window(root / "data")
            window.set_folder(root)
            window.show()
            APP.processEvents()
            self.assertFalse(window.rules.verticalHeader().isHidden())
            def numbers():
                return [int(window.rules.model().headerData(row, Qt.Vertical))
                        for row in range(window.rules.rowCount())]
            window.add_rule(Rule("PDFs", ["pdf"], "", str(root / "PDFs")))
            window.rules.setCurrentCell(window.rules.rowCount() - 1, 1)
            window.reorder(-1)
            self.assertEqual(numbers(), list(range(1, window.rules.rowCount() + 1)))
            self.assertEqual(window.read_rules()[-2].name, "PDFs")
            window.remove_rule()
            self.assertEqual(numbers(), list(range(1, window.rules.rowCount() + 1)))
            with patch.object(QApplication, "isEffectEnabled", return_value=True):
                for index in [1, 3, 2, 0, 1]:
                    window.navigation.button(index).click()
                    self.assertEqual(window.pages.currentIndex(), index)
                    self.assertEqual(window.page_animation.state(), QAbstractAnimation.Running)
                    self.assertTrue(window.navigation.button(index).isEnabled())
                self.wait_until(lambda: window.page_animation.state() == QAbstractAnimation.Stopped)
                self.assertEqual(window.page_opacity.opacity(), 1.0)
            with patch.object(QApplication, "isEffectEnabled", return_value=False):
                window.show_page(3)
                self.assertEqual(window.page_animation.state(), QAbstractAnimation.Stopped)
                self.assertEqual(window.page_opacity.opacity(), 1.0)
            window.close()

    def test_tray_close_show_and_quit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with patch("organizer.app.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
                window = Window(root / "data")
                window.set_folder(root)
                window.tray_mode.setChecked(True)
                window.show()
                APP.processEvents()
                window.close()
                self.assertFalse(window.isVisible())
                self.assertFalse(window.quitting)
                window.show_window()
                self.assertTrue(window.isVisible())
                window.request_quit()
                self.assertTrue(window.quitting)
                self.assertFalse(window.tray.isVisible())

    def test_no_tray_fallback_and_single_instance_lock(self):
        from PySide6.QtCore import QLockFile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with patch("organizer.app.QSystemTrayIcon.isSystemTrayAvailable", return_value=False):
                window = Window(root / "data")
                self.assertFalse(window.tray_mode.isEnabled())
                window.tray_mode.setChecked(True)
                window.show()
                window.close()
                self.assertFalse(window.isVisible())
            first = QLockFile(str(root / "instance.lock"))
            second = QLockFile(str(root / "instance.lock"))
            self.assertTrue(first.tryLock(0))
            self.assertFalse(second.tryLock(0))
            first.unlock()
            self.assertTrue(second.tryLock(0))
            second.unlock()

    def test_startup_checkbox_failure_is_reverted(self):
        with tempfile.TemporaryDirectory() as directory:
            window = Window(Path(directory).resolve() / "data")
            window.login_start.setChecked(False)
            with patch("organizer.app.set_startup", side_effect=PermissionError("Denied")):
                window.login_start.setChecked(True)
            self.assertFalse(window.login_start.isChecked())
            self.assertIn("could not be changed", window.status.text())
            window.close()

    def test_automatic_backlog_new_download_and_restart_catchup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            downloads = root / "Downloads"
            downloads.mkdir()
            def ready(name):
                path = downloads / name
                path.write_bytes(b"download")
                os.utime(path, (time.time() - 10, time.time() - 10))
                return path
            old = ready("old.pdf")
            partial = ready("still.pdf.crdownload")
            window = Window(root / "data")
            window.set_folder(downloads)
            window.automatic.setChecked(True)
            self.wait_until(lambda: window.monitor.pending.backlog is not None)
            for index in [1, 2, 3, 0]:
                window.navigation.button(index).click()
                self.assertTrue(window.automatic.isChecked())
                self.assertTrue(window.monitor.isRunning())
            new = ready("new.pdf")
            self.wait_until(lambda: not old.exists() and not new.exists())
            from organizer.moves import Journal
            with Journal(root / "data" / "history.db") as journal:
                sources = [Path(row[1]).name for row in reversed(journal.history())]
            self.assertEqual(sources, ["old.pdf", "new.pdf"])
            self.assertTrue(partial.exists())
            window.close()
            self.wait_until(lambda: not window.monitor.isRunning())
            APP.processEvents()
            offline = ready("while-stopped.pdf")
            restarted = Window(root / "data")
            self.addCleanup(lambda: self.stop_monitor(restarted))
            self.wait_until(lambda: not offline.exists())
            self.assertTrue(restarted.automatic.isChecked())
            original_first = restarted.rules.item(0, 1).text()
            restarted.rules.setCurrentCell(1, 1)
            restarted.reorder(-1)
            self.assertFalse(restarted.automatic.isChecked())
            self.assertEqual(restarted.read_rules()[1].name, original_first)
            self.stop_monitor(restarted)

    def stop_monitor(self, window):
        window.quitting = True
        if window.monitor is not None and window.monitor.isRunning():
            window.monitor.stop()
            self.wait_until(lambda: not window.monitor.isRunning())
        APP.processEvents()
        window.close()

    def wait_until(self, condition):
        deadline = time.monotonic() + 12
        while not condition() and time.monotonic() < deadline:
            APP.processEvents()
            time.sleep(.01)
        self.assertTrue(condition(), "Timed out waiting for desktop operation")

    def test_preview_move_restart_and_undo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
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

    def test_cancel_keeps_navigation_responsive_and_stops_remaining_files(self):
        import threading
        from organizer.moves import chunks
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            downloads = root / "Downloads"
            downloads.mkdir()
            for name in ("large.pdf", "next.pdf"):
                path = downloads / name
                path.write_bytes(b"data" * 600000)
                os.utime(path, (time.time() - 10, time.time() - 10))
            window = Window(root / "data")
            window.set_folder(downloads)
            window.refresh()
            entered, release = threading.Event(), threading.Event()
            def slow_chunks(*args, **kwargs):
                for chunk in chunks(*args, **kwargs):
                    entered.set()
                    release.wait(5)
                    yield chunk
            with patch("organizer.moves.chunks", slow_chunks):
                window.start_worker(window.proposals)
                try:
                    self.wait_until(entered.is_set)
                    window.navigation.button(2).click()
                    self.assertEqual(window.pages.currentIndex(), 2)
                    self.assertTrue(window.isEnabled())
                    self.assertFalse(window.rules.isEnabled())
                    self.assertTrue(window.cancel_button.isEnabled())
                    window.cancel_button.click()
                    self.assertTrue(window.worker.isInterruptionRequested())
                    self.assertFalse(window.cancel_button.isEnabled())
                finally:
                    release.set()
                    self.wait_worker(window)
            self.assertTrue((downloads / "large.pdf").exists())
            self.assertTrue((downloads / "next.pdf").exists())
            self.assertFalse((downloads / "Documents" / "large.pdf").exists())
            self.assertIn("Cancelled", window.status.text())
            self.assertTrue(window.rules.isEnabled())
            window.close()

    def test_review_keep_and_preview_button(self):
        from organizer.moves import Journal
        from organizer.core import preview
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            downloads = root / "Downloads"
            downloads.mkdir()
            source = downloads / "report.pdf"
            source.write_bytes(b"report")
            os.utime(source, (time.time() - 10, time.time() - 10))
            data = root / "data"
            window = Window(data)
            window.set_folder(downloads)
            proposal = preview(downloads, window.read_rules())[0]
            unlink = Path.unlink

            def locked(path, *args, **kwargs):
                if path == source:
                    raise PermissionError("Locked")
                return unlink(path, *args, **kwargs)

            with Journal(data / "history.db") as journal:
                with patch.object(Path, "unlink", locked):
                    with self.assertRaises(PermissionError):
                        journal.move(proposal)
            window.load_history(recover=True)
            window.history_table.setCurrentCell(0, 0)
            self.assertTrue(window.review_keep.isEnabled())
            with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
                window.review_keep.click()
            self.wait_worker(window)
            self.assertTrue(source.exists())
            self.assertFalse(proposal.destination.exists())
            self.assertEqual(window.history_table.item(0, 3).text(), "kept")
            window.refresh()
            self.assertFalse(window.organize.isEnabled())
            self.assertEqual(window.files.item(0, 2).text(), "Left in Downloads after review")
            window.close()

            second = downloads / "another.pdf"
            second.write_bytes(b"another")
            os.utime(second, (time.time() - 10, time.time() - 10))
            restarted = Window(data)
            restarted.set_folder(downloads)
            restarted.refresh()
            self.assertTrue(restarted.organize.isEnabled())
            with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
                restarted.organize.click()
            self.wait_worker(restarted)
            self.assertTrue((downloads / "Documents" / second.name).exists())
            self.assertTrue(source.exists())
            restarted.close()

    def test_original_only_interruption_retries_from_preview(self):
        from organizer.moves import Journal
        from organizer.core import preview
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            downloads = root / "Downloads"
            downloads.mkdir()
            source = downloads / "installer.exe"
            source.write_bytes(b"installer")
            os.utime(source, (time.time() - 10, time.time() - 10))
            window = Window(root / "data")
            window.set_folder(downloads)
            proposal = preview(downloads, window.read_rules())[0]
            with Journal(root / "data" / "history.db") as journal:
                with patch("organizer.moves.os.link", side_effect=OSError("Temporary publish failure")):
                    with self.assertRaises(OSError):
                        journal.move(proposal)
            window.load_history(recover=True)
            window.refresh()
            self.assertTrue(window.organize.isEnabled())
            with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
                window.organize.click()
            self.wait_worker(window)
            self.assertFalse(source.exists())
            self.assertEqual(proposal.destination.read_bytes(), b"installer")
            self.assertEqual(window.history_table.item(0, 3).text(), "complete")
            window.close()

    def test_editing_rules_invalidates_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
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
