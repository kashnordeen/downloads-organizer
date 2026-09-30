import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QThread, Signal, QLockFile, QTimer, QFileSystemWatcher
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QMessageBox,
    QTableWidgetItem, QSystemTrayIcon, QMenu)

from .core import Rule, defaults, load_settings, load_options, preview, save_settings
from .moves import Journal
from .worker import MonitorWorker
from .startup import set_startup, startup_enabled
from .ui import build_ui


class MoveWorker(QThread):
    report = Signal(str)

    def __init__(self, data_dir, proposals, parent):
        super().__init__(parent)
        self.data_dir, self.proposals = data_dir, proposals

    def run(self):
        try:
            with Journal(self.data_dir / "history.db") as journal:
                if isinstance(self.proposals, int):
                    restored = journal.undo(self.proposals)
                    self.report.emit(f"Restored {restored}")
                    return
                for proposal in self.proposals:
                    if self.isInterruptionRequested():
                        break
                    try:
                        destination = journal.move(proposal)
                        self.report.emit(f"Moved {proposal.source.name} → {destination}")
                    except (OSError, ValueError) as error:
                        self.report.emit(f"Skipped {proposal.source.name}: {error}")
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
        self.quitting = False
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
                self.automatic.setChecked(options.get("automatic", False))
                self.tray_mode.setChecked(options.get("tray", False))
            except ValueError as error:
                self.status.setText(str(error) + " Original settings were preserved.")
        self.rules.itemChanged.connect(self.invalidate)
        self.load_history(recover=True)
        self.automatic.toggled.connect(self.toggle_automatic)
        self.automatic.toggled.connect(self.update_ui)
        self.tray_mode.toggled.connect(self.save)
        try:
            self.login_start.setChecked(startup_enabled())
        except (OSError, ImportError, RuntimeError) as error:
            self.login_start.setEnabled(False)
            self.status.setText(f"Login startup unavailable: {error}")
        self.login_start.toggled.connect(self.toggle_login)
        self.update_ui()
        if self.automatic.isChecked():
            QTimer.singleShot(0, lambda: self.toggle_automatic(True))

    def show_page(self, index):
        titles = ["Preview your downloads", "Organization rules", "Move history", "Settings"]
        descriptions = ["Review where each file will go before you organize it.",
                        "Rules run from top to bottom. The first enabled match wins. Double-click a field to edit.",
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
        if self.quitting:
            self.close()
            return
        message = self.status.text()
        if self.automatic.isChecked():
            self.automatic.setChecked(False)
        self.undo_button.setEnabled(True)
        self.invalidate()
        self.status.setText(message)

    def options(self):
        return {"automatic": self.automatic.isChecked(), "tray": self.tray_mode.isChecked()}

    def load_history(self, recover=False):
        try:
            with Journal(self.data_dir / "history.db") as journal:
                if recover:
                    journal.recover()
                history = journal.history()
            self.history_table.setRowCount(len(history))
            for row, operation in enumerate(history):
                for col, value in enumerate(operation):
                    item = QTableWidgetItem(str(value or ""))
                    item.setToolTip(str(value or ""))
                    self.history_table.setItem(row, col, item)
            if recover and any(row[3] == "review" for row in history):
                self.status.setText("Some interrupted moves need review. Copies have been retained; inspect History.")
        except Exception as error:
            self.organize.setEnabled(False)
            self.status.setText(f"History unavailable: {error}")
        self.update_ui()

    def undo(self):
        row = self.history_table.currentRow()
        if row < 0:
            self.status.setText("Select a completed move in History first.")
            return
        operation = int(self.history_table.item(row, 0).text())
        self.start_worker(operation)

    def start_worker(self, work):
        if self.monitor is not None and self.monitor.isRunning():
            self.status.setText("Pause automatic sorting before a manual move or undo.")
            return
        self.setEnabled(False)
        self.worker = MoveWorker(self.data_dir, work, self)
        self.worker.report.connect(self.status.setText)
        self.worker.finished.connect(self.finished)
        self.worker.start()

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
        self.setEnabled(True)
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
            self.status.setText("Finishing the current file before exiting.")
            event.ignore()
            return
        if self.worker is not None and self.worker.isRunning():
            self.worker.requestInterruption()
            self.status.setText("Finishing the current file safely. Close again when finished.")
            event.ignore()
        else:
            self.tray.hide()
            event.accept()
            if self.quitting:
                QApplication.instance().quit()

    def add_rule(self, rule):
        if hasattr(self, "automatic") and self.automatic.isChecked():
            self.invalidate()
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

    def choose_destination(self):
        row = self.rules.currentRow()
        if row >= 0:
            folder = QFileDialog.getExistingDirectory(self, "Choose destination")
            if folder:
                self.rules.item(row, 4).setText(folder)

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
    sys.exit(app.exec())
