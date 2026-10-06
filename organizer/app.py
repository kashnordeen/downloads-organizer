import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QThread, Signal, QLockFile, QTimer, QFileSystemWatcher, QUrl
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QMessageBox,
    QTableWidgetItem, QSystemTrayIcon, QMenu)
from PySide6.QtGui import QDesktopServices

from .core import Rule, defaults, load_settings, load_options, preview, save_settings
from .moves import Journal, OperationCancelled
from .worker import MonitorWorker
from .startup import set_startup, startup_enabled
from .ui import build_ui, apply_theme, RuleDialog, initial_folder, guided_tour
from .updates import UpdateWorker


class MoveWorker(QThread):
    report = Signal(str)
    progress = Signal(str, str, object, object)

    def __init__(self, data_dir, proposals, parent):
        super().__init__(parent)
        self.data_dir, self.proposals = data_dir, proposals

    def run(self):
        try:
            with Journal(self.data_dir / "history.db", cancelled=self.isInterruptionRequested,
                         progress=lambda path, phase, done, total: self.progress.emit(path.name, phase, done, total)) as journal:
                if self.proposals == "recover":
                    journal.recover()
                    self.report.emit("Recovery checked. Refresh Preview to review current files.")
                    return
                if isinstance(self.proposals, int):
                    restored = journal.undo(self.proposals)
                    self.report.emit(f"Restored {restored}")
                    return
                if isinstance(self.proposals, tuple):
                    operation, choice = self.proposals
                    result = journal.resolve_review(operation, choice)
                    self.report.emit(f"{'Moved to destination' if choice == 'move' else 'Left in Downloads'}: {result}")
                    return
                for index, proposal in enumerate(self.proposals, 1):
                    if self.isInterruptionRequested():
                        raise OperationCancelled("Cancelled; remaining files were left untouched")
                    try:
                        self.report.emit(f"File {index} of {len(self.proposals)} · {proposal.source.name}")
                        destination = journal.move(proposal)
                        self.report.emit(f"Moved {proposal.source.name} → {destination}")
                    except (OSError, ValueError) as error:
                        self.report.emit(f"Skipped {proposal.source.name}: {error}")
        except OperationCancelled as error:
            self.report.emit(str(error))
        except Exception as error:
            self.report.emit(f"Operation stopped safely: {error}")


class Window(QMainWindow):
    def __init__(self, data_dir=None):
        super().__init__()
        self.setWindowTitle("Downloads Organizer")
        self.data_dir = Path(data_dir or QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
        self.settings_path = self.data_dir / "settings.json"
        self.folder = None
        self.proposals = []
        self.worker = None
        self.monitor = None
        self.update_worker = None
        self.update_url = None
        self.quitting = False
        self.tour_done = False
        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self.wake_monitor)
        build_ui(self)
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip("Downloads Organizer")
        menu = QMenu(self)
        menu.addAction("Show organizer", self.show_window)
        self.pause_action = menu.addAction("Resume automatic sorting", lambda: self.automatic.setChecked(not self.automatic.isChecked()))
        menu.addAction("Quit", self.request_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_window() if reason in
            (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        if self.settings_path.exists():
            try:
                folder, rules = load_settings(self.settings_path)
                self.set_folder(folder, rules)
                options = load_options(self.settings_path)
                self.tour_done = options.get("tour_done", False)
                self.automatic.setChecked(options.get("automatic", False))
                self.tray_mode.setChecked(options.get("tray", False))
                self.update_notifications.setChecked(options.get("update_notifications", False))
                if "night_mode" in options:
                    self.theme_controls.button(int(options["night_mode"])).setChecked(True)
                    apply_theme(self)
            except ValueError as error:
                self.status.setText(str(error) + " Original settings were preserved.")
        self.rules.itemChanged.connect(self.invalidate)
        self.load_history(recover=True)
        self.automatic.toggled.connect(self.toggle_automatic)
        self.automatic.toggled.connect(self.update_ui)
        self.tray_mode.toggled.connect(self.save)
        self.update_notifications.toggled.connect(self.toggle_updates)
        self.theme_controls.idClicked.connect(self.set_theme)
        try:
            self.login_start.setChecked(startup_enabled())
        except (OSError, ImportError, RuntimeError) as error:
            self.login_start.setEnabled(False)
            self.status.setText(f"Login startup unavailable: {error}")
        self.login_start.toggled.connect(self.toggle_login)
        self.update_ui()
        if self.automatic.isChecked():
            QTimer.singleShot(0, lambda: self.toggle_automatic(True))
        if self.update_notifications.isChecked():
            QTimer.singleShot(0, self.check_updates)

    def set_theme(self, _):
        apply_theme(self)
        if self.folder is not None:
            self.save()

    def toggle_updates(self, enabled):
        self.save()
        if enabled:
            self.check_updates()

    def check_updates(self):
        if self.update_worker and self.update_worker.isRunning():
            return
        self.check_updates_button.setEnabled(False)
        self.update_status.setText("Checking GitHub for a stable release…")
        self.update_worker = UpdateWorker(self)
        self.update_worker.result.connect(self.update_result)
        self.update_worker.failed.connect(self.update_status.setText)
        self.update_worker.finished.connect(self.update_finished)
        self.update_worker.start()

    def update_result(self, release):
        self.update_url = release[1] if release else None
        self.download_update.setEnabled(bool(release))
        self.update_banner.setVisible(bool(release))
        message = f"Version {release[0]} is available. Install when you’re ready." if release else "You’re up to date with the latest stable release."
        self.update_status.setText(message)
        self.update_notice.setText(message)

    def update_finished(self):
        self.check_updates_button.setEnabled(True)
        if self.quitting:
            self.close()

    def view_update(self):
        if self.update_url:
            QDesktopServices.openUrl(QUrl(self.update_url))

    def show_page(self, index):
        titles = ["Organize with confidence.", "Your rules. Your folders.", "Every move, accounted for.", "Make it work for you."]
        descriptions = ["Review where each file will go before you organize it.",
                        "Rules run from top to bottom. Select a rule to edit its filters and destination.",
                        "Select a completed move to undo. Changed files and occupied paths are protected.",
                        "Control how the organizer runs on this device."]
        self.pages.setCurrentIndex(index)
        self.navigation.button(index).setChecked(True)
        self.page_title.setText(titles[index])
        self.page_description.setText(descriptions[index])

    def update_ui(self):
        automatic = self.automatic.isChecked()
        self.mode_label.setText("Automatic mode" if automatic else "Manual mode")
        if hasattr(self, "pause_action"):
            self.pause_action.setText("Pause automatic sorting" if automatic else "Resume automatic sorting")
        self.files.setVisible(self.files.rowCount() > 0)
        self.preview_empty.setVisible(self.files.rowCount() == 0)
        self.history_table.setVisible(self.history_table.rowCount() > 0)
        self.history_empty.setVisible(self.history_table.rowCount() == 0)

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def setup_first_run(self):
        if self.settings_path.exists():
            return
        suggestion = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        if not suggestion or not Path(suggestion).is_dir():
            suggestion = ""
        folder = initial_folder(self, suggestion)
        if folder:
            self.set_folder(folder)
            self.save()
            self.show_page(1)
            self.show_tour()

    def show_help(self):
        self.show_tour()

    def show_tour(self):
        guided_tour(self)
        self.tour_done = True
        self.save()

    def toggle_login(self, enabled):
        self.login_start.setEnabled(False)
        try:
            set_startup(enabled)
            self.status.setText("Login startup enabled." if enabled else "Login startup disabled.")
        except (OSError, ValueError, ImportError, RuntimeError) as error:
            self.login_start.blockSignals(True)
            self.login_start.setChecked(not enabled)
            self.login_start.blockSignals(False)
            self.status.setText(f"Startup setting could not be changed: {error}")
        finally:
            self.login_start.setEnabled(True)

    def request_quit(self):
        self.quitting = True
        self.tray.hide()
        self.close()

    def wake_monitor(self):
        if self.monitor is not None:
            self.monitor.wakeup.set()

    def toggle_automatic(self, enabled):
        if not enabled:
            if self.monitor is not None and self.monitor.isRunning():
                self.monitor.stop()
            self.save()
            return
        try:
            rules = self.read_rules()
            if self.worker is not None and self.worker.isRunning():
                raise ValueError("Wait for the current operation to finish")
            if self.monitor is not None and self.monitor.isRunning():
                raise ValueError("Previous monitoring session is stopping; try again shortly")
            save_settings(self.settings_path, self.folder, rules, self.options())
            if self.watcher.directories():
                self.watcher.removePaths(self.watcher.directories())
            self.watcher.addPath(str(self.folder))
            self.monitor = MonitorWorker(self.folder, rules, self.data_dir, self)
            self.monitor.report.connect(self.status.setText)
            self.monitor.progress.connect(self.show_progress)
            self.monitor.idle.connect(self.operation_idle)
            self.monitor.changed.connect(self.load_history)
            self.monitor.finished.connect(self.monitor_finished)
            self.organize.setEnabled(False)
            self.undo_button.setEnabled(False)
            self.monitor.start()
            self.status.setText("Automatic mode: checking startup files first, then watching new downloads.")
        except (ValueError, OSError) as error:
            self.automatic.blockSignals(True)
            self.automatic.setChecked(False)
            self.automatic.blockSignals(False)
            self.status.setText(str(error))
        self.update_ui()

    def monitor_finished(self):
        self.operation_idle()
        if self.quitting:
            self.close()
            return
        message = self.status.text()
        if self.automatic.isChecked():
            self.automatic.setChecked(False)
        self.invalidate()
        self.update_history_actions()
        self.status.setText(message)

    def options(self):
        return {"automatic": self.automatic.isChecked(), "tray": self.tray_mode.isChecked(),
                "tour_done": self.tour_done, "update_notifications": self.update_notifications.isChecked(),
                "night_mode": self.theme_controls.checkedId() == 1}

    def load_history(self, recover=False):
        deferred = False
        try:
            with Journal(self.data_dir / "history.db") as journal:
                if recover:
                    deferred = journal.recover(verify=False)
                history = journal.history()
            self.history_table.setRowCount(len(history))
            for row, operation in enumerate(history):
                recorded = (datetime.fromtimestamp(operation[5]).astimezone()
                            if operation[5] is not None else None)
                time_text = recorded.strftime("%d %b %Y · %H:%M:%S") if recorded else "Time unavailable (older entry)"
                details = time_text + (" | " + operation[4] if operation[4] else "")
                for col, value in enumerate((*operation[:4], details)):
                    item = QTableWidgetItem(str(value or ""))
                    item.setToolTip(str(value or ""))
                    if col == 4 and recorded:
                        item.setToolTip(f"Recorded (local time): {recorded.strftime('%d %b %Y %H:%M:%S %z')}\n{operation[4] or ''}")
                    self.history_table.setItem(row, col, item)
            if recover and any(row[3] == "review" for row in history):
                self.status.setText("Some moves need review. Select one in History to move or leave in Downloads.")
        except Exception as error:
            self.organize.setEnabled(False)
            self.status.setText(f"History unavailable: {error}")
        self.update_ui()
        self.update_history_actions()
        if deferred and not self.automatic.isChecked():
            self.start_worker("recover")

    def update_history_actions(self):
        row = self.history_table.currentRow()
        state = self.history_table.item(row, 3).text() if row >= 0 and self.history_table.item(row, 3) else ""
        busy = bool((self.worker and self.worker.isRunning()) or (self.monitor and self.monitor.isRunning()))
        self.undo_button.setEnabled(state == "complete" and not busy)
        self.review_move.setEnabled(state == "review" and not busy)
        self.review_keep.setEnabled(state == "review" and not busy)

    def resolve_review(self, choice):
        row = self.history_table.currentRow()
        if row < 0 or self.history_table.item(row, 3).text() != "review":
            self.status.setText("Select a move marked review in History first.")
            return
        source = self.history_table.item(row, 1).text()
        target = self.history_table.item(row, 2).text()
        action = "move it to the recorded destination" if choice == "move" else "leave it in Downloads"
        consequence = ("The original will be removed after its destination copy is verified."
                       if choice == "move" else
                       "The original stays; any verified destination copy will be removed.")
        answer = QMessageBox.question(self, "Resolve reviewed file",
            f"Original: {source}\nDestination: {target}\n\n{action.capitalize()}?\n"
            f"{consequence} The app stops if a file has changed.")
        if answer == QMessageBox.Yes:
            self.start_worker((int(self.history_table.item(row, 0).text()), choice))

    def undo(self):
        row = self.history_table.currentRow()
        if row < 0:
            self.status.setText("Select a completed move in History first.")
            return
        operation = int(self.history_table.item(row, 0).text())
        self.start_worker(operation)

    def start_worker(self, work):
        if self.worker is not None and self.worker.isRunning():
            return
        if self.monitor is not None and self.monitor.isRunning():
            self.status.setText("Pause automatic sorting before a manual move or undo.")
            return
        self.operation_panel.show()
        self.operation_label.setText("Preparing operation…")
        self.operation_detail.setText("You can cancel safely. Completed moves stay in History.")
        self.progress_bar.setRange(0, 0)
        self.cancel_button.setText("Cancel")
        self.cancel_button.setEnabled(True)
        self.worker = MoveWorker(self.data_dir, work, self)
        self.worker.report.connect(self.status.setText)
        self.worker.progress.connect(self.show_progress)
        self.worker.finished.connect(self.finished)
        self.worker.start()
        self.set_operation_busy(True)

    def set_operation_busy(self, busy):
        for control in self.mutation_controls:
            control.setEnabled(not busy)
        self.organize.setEnabled(False)
        self.update_history_actions()

    def show_progress(self, name, phase, done, total):
        if self.monitor and self.monitor.isRunning():
            self.set_operation_busy(True)
        self.operation_panel.show()
        self.operation_label.setText(name)
        self.operation_label.setToolTip(name)
        self.progress_bar.setRange(0, 100 if total else 0)
        if total:
            self.progress_bar.setValue(min(100, int(done * 100 / total)))
        stopping = bool((self.worker and self.worker.isInterruptionRequested()) or
                        (self.monitor and self.monitor.isInterruptionRequested()))
        detail = f"{phase} · {min(100, int(done * 100 / total))}% · {done / (1024 * 1024):,.1f} / {total / (1024 * 1024):,.1f} MB" if total else phase
        self.operation_detail.setText("Stopping safely… " + detail if stopping else detail)
        self.cancel_button.setText("Stopping…" if stopping else "Cancel")
        self.cancel_button.setEnabled(not stopping and phase != "Finishing")

    def cancel_operation(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
        if self.monitor and self.monitor.isRunning():
            self.automatic.setChecked(False)
            self.monitor.stop()
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Stopping…")
        self.operation_detail.setText("Stopping safely… Waiting for the current disk operation to return.")

    def operation_idle(self):
        self.operation_panel.hide()
        if not (self.worker and self.worker.isRunning()):
            self.set_operation_busy(False)

    def invalidate(self):
        self.proposals = []
        self.files.setRowCount(0)
        self.preview_summary.setText("Refresh to review current files")
        self.preview_empty.setText("Preview needs a refresh\n\nRefresh the preview to review your files and current rules.")
        self.organize.setEnabled(False)
        if self.automatic.isChecked():
            self.automatic.setChecked(False)
        self.update_ui()

    def execute(self):
        proposals = [p for p in self.proposals if p.destination is not None]
        if not proposals:
            return
        answer = QMessageBox.question(self, "Organize files", f"Move {len(proposals)} previewed files?\nExisting files will never be overwritten.")
        if answer != QMessageBox.Yes:
            return
        self.start_worker(proposals)

    def finished(self):
        self.operation_idle()
        self.set_operation_busy(False)
        self.invalidate()
        self.load_history()
        if self.quitting:
            self.close()

    def closeEvent(self, event):
        if not self.quitting and self.tray_mode.isChecked() and QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            event.ignore()
            return
        if self.monitor is not None and self.monitor.isRunning():
            self.quitting = True
            self.monitor.stop()
            self.status.setText("Stopping safely before exiting.")
            event.ignore()
            return
        if self.worker is not None and self.worker.isRunning():
            self.quitting = True
            self.cancel_operation()
            self.status.setText("Stopping safely before exiting.")
            event.ignore()
        elif self.update_worker is not None and self.update_worker.isRunning():
            self.quitting = True
            self.status.setText("Waiting for the update check to finish before exiting.")
            event.ignore()
        else:
            self.tray.hide()
            event.accept()
            if self.quitting:
                QApplication.instance().quit()

    def edit_rule(self, new=False):
        if self.folder is None:
            self.status.setText("Choose a folder before adding rules.")
            return
        row = self.rules.currentRow()
        if not new and row < 0:
            self.status.setText("Select a rule to edit first.")
            return
        rule = Rule("", [], "", str(self.folder / "Organized")) if new else Rule(
            self.rules.item(row, 1).text(), self.rules.item(row, 2).text().split(","),
            self.rules.item(row, 3).text(), self.rules.item(row, 4).text(),
            self.rules.item(row, 0).checkState() == Qt.Checked)
        dialog = RuleDialog(self, rule)
        if dialog.exec():
            self.invalidate()
            self.add_rule(dialog.rule, None if new else row)
            self.status.setText("Rule updated. Save rules, then refresh Preview.")

    def add_rule(self, rule, row=None):
        if hasattr(self, "automatic") and self.automatic.isChecked():
            self.invalidate()
        if row is None:
            row = self.rules.rowCount()
            self.rules.insertRow(row)
        enabled = QTableWidgetItem()
        enabled.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        enabled.setCheckState(Qt.Checked if rule.enabled else Qt.Unchecked)
        self.rules.setItem(row, 0, enabled)
        for column, value in enumerate([rule.name, ", ".join(rule.extensions), rule.contains, rule.destination], 1):
            item = QTableWidgetItem(value)
            item.setToolTip(value)
            self.rules.setItem(row, column, item)

    def read_rules(self):
        if self.folder is None:
            raise ValueError("Choose a folder first")
        rules = []
        for row in range(self.rules.rowCount()):
            values = [self.rules.item(row, c).text() for c in range(1, 5)]
            rule = Rule(values[0], values[1].split(","), values[2], values[3],
                        self.rules.item(row, 0).checkState() == Qt.Checked)
            rule.validate(self.folder)
            rules.append(rule)
        return rules

    def set_folder(self, folder, rules=None):
        if hasattr(self, "automatic") and self.automatic.isChecked():
            self.automatic.setChecked(False)
        self.folder = Path(folder)
        self.folder_label.setText(str(folder))
        self.folder_label.setToolTip(str(folder))
        self.rules.setRowCount(0)
        for rule in rules if rules is not None else defaults(folder):
            self.add_rule(rule)
        self.files.setRowCount(0)
        self.proposals = []
        self.organize.setEnabled(False)
        self.preview_summary.setText("Preview before moving files")
        self.preview_empty.setText("Ready when you are\n\nReview Rules, then refresh the preview.\nPreviewing never moves your files.")
        self.update_ui()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose folder to organize")
        if folder:
            self.set_folder(folder)

    def remove_rule(self):
        row = self.rules.currentRow()
        if row >= 0:
            self.invalidate()
            self.rules.removeRow(row)

    def reorder(self, direction):
        row = self.rules.currentRow()
        other = row + direction
        if row >= 0 and 0 <= other < self.rules.rowCount():
            self.invalidate()  # Pause before temporarily removing table items.
            for column in range(5):
                first, second = self.rules.takeItem(row, column), self.rules.takeItem(other, column)
                self.rules.setItem(row, column, second)
                self.rules.setItem(other, column, first)
            self.rules.setCurrentCell(other, 1)

    def save(self):
        try:
            save_settings(self.settings_path, self.folder, self.read_rules(), self.options())
            self.status.setText("Settings saved.")
        except (ValueError, OSError) as error:
            self.status.setText(str(error))

    def refresh(self):
        try:
            self.proposals = preview(self.folder, self.read_rules())
            with Journal(self.data_dir / "history.db") as journal:
                deferred = journal.recover(verify=False)
                kept = journal.kept_sources()
                blocked = journal.unresolved_sources()
            for proposal in self.proposals:
                if kept.get(str(proposal.source)) == proposal.signature:
                    proposal.destination, proposal.reason = None, "Left in Downloads after review"
                elif str(proposal.source) in blocked:
                    proposal.destination, proposal.reason = None, "Needs review in History"
            self.files.setRowCount(len(self.proposals))
            for row, proposal in enumerate(self.proposals):
                destination = str(proposal.destination or "—")
                if proposal.destination is not None and proposal.destination.is_relative_to(self.folder):
                    destination = str(proposal.destination.relative_to(self.folder))
                for col, text in enumerate([proposal.source.name, destination, proposal.reason]):
                    item = QTableWidgetItem(text)
                    item.setToolTip(str(proposal.destination) if col == 1 and proposal.destination else text)
                    self.files.setItem(row, col, item)
            count = sum(p.destination is not None for p in self.proposals)
            self.preview_summary.setText(f"{count} ready to organize · {len(self.proposals) - count} skipped")
            self.preview_empty.setText("All clear\n\nNo files to review in the watched folder.")
            self.status.setText(f"{count} files match your rules. No files were moved.")
            self.organize.setEnabled(count > 0 and not self.automatic.isChecked()
                                     and not (self.monitor and self.monitor.isRunning()))
            if deferred and not self.automatic.isChecked():
                self.start_worker("recover")
        except (ValueError, OSError) as error:
            self.proposals = []
            self.files.setRowCount(0)
            self.organize.setEnabled(False)
            self.status.setText(str(error))
            self.preview_summary.setText("Preview unavailable")
            self.preview_empty.setText("Preview unavailable\n\n" + str(error))
        self.update_ui()


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("LocalOrganizer")
    app.setApplicationName("DownloadsOrganizer")
    data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    data_dir.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(data_dir / "organizer.lock"))
    if not lock.tryLock(0):
        QMessageBox.information(None, "Already running", "Downloads Organizer is already running.")
        return
    window = Window(data_dir)
    if "--background" in sys.argv and window.tray_mode.isChecked() and QSystemTrayIcon.isSystemTrayAvailable():
        app.setQuitOnLastWindowClosed(False)
    else:
        window.show()
        QTimer.singleShot(0, window.setup_first_run)
    sys.exit(app.exec())
