import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QHeaderView,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .core import Rule, defaults, load_settings, preview, save_settings


class Window(QMainWindow):
    def __init__(self, data_dir=None):
        super().__init__()
        self.setWindowTitle("Downloads Organizer — Preview")
        self.resize(1050, 700)
        self.data_dir = Path(data_dir or QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
        self.settings_path = self.data_dir / "settings.json"
        self.folder = None
        self.proposals = []
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        title = QLabel("Downloads Organizer")
        title.setStyleSheet("font-size: 26px; font-weight: 600; padding: 12px 0;")
        layout.addWidget(title)
        layout.addWidget(QLabel("Choose a folder, review your rules, then preview. Files stay local."))
        bar = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        bar.addWidget(self.folder_label, 1)
        choose = QPushButton("Choose folder…")
        choose.clicked.connect(self.choose_folder)
        bar.addWidget(choose)
        layout.addLayout(bar)
        self.rules = QTableWidget(0, 5)
        self.rules.setHorizontalHeaderLabels(["Enabled", "Rule", "Extensions (comma separated)", "Filename contains", "Destination folder"])
        self.rules.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.rules)
        bar = QHBoxLayout()
        for label, callback in [("Add rule", lambda: self.add_rule(Rule("New rule", [], "", ""))),
                                ("Remove selected", self.remove_rule), ("Move up", lambda: self.reorder(-1)),
                                ("Move down", lambda: self.reorder(1)), ("Browse destination…", self.choose_destination),
                                ("Save rules", self.save), ("Preview", self.refresh)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            bar.addWidget(button)
        layout.addLayout(bar)
        self.files = QTableWidget(0, 3)
        self.files.setHorizontalHeaderLabels(["File", "Destination", "Rule / skipped reason"])
        self.files.setEditTriggers(QTableWidget.NoEditTriggers)
        self.files.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.files)
        self.status = QLabel("Manual mode. Preview never moves files.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        if self.settings_path.exists():
            try:
                folder, rules = load_settings(self.settings_path)
                self.set_folder(folder, rules)
            except ValueError as error:
                self.status.setText(str(error) + " Original settings were preserved.")

    def add_rule(self, rule):
        row = self.rules.rowCount()
        self.rules.insertRow(row)
        enabled = QTableWidgetItem()
        enabled.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        enabled.setCheckState(Qt.Checked if rule.enabled else Qt.Unchecked)
        self.rules.setItem(row, 0, enabled)
        for column, value in enumerate([rule.name, ", ".join(rule.extensions), rule.contains, rule.destination], 1):
            self.rules.setItem(row, column, QTableWidgetItem(value))

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
        self.folder = Path(folder)
        self.folder_label.setText(str(folder))
        self.rules.setRowCount(0)
        for rule in rules if rules is not None else defaults(folder):
            self.add_rule(rule)
        self.files.setRowCount(0)
        self.proposals = []

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
            self.rules.removeRow(row)

    def reorder(self, direction):
        row = self.rules.currentRow()
        other = row + direction
        if row >= 0 and 0 <= other < self.rules.rowCount():
            for column in range(5):
                first, second = self.rules.takeItem(row, column), self.rules.takeItem(other, column)
                self.rules.setItem(row, column, second)
                self.rules.setItem(other, column, first)
            self.rules.setCurrentCell(other, 1)

    def save(self):
        try:
            save_settings(self.settings_path, self.folder, self.read_rules())
            self.status.setText("Rules saved. No files were moved.")
        except (ValueError, OSError) as error:
            self.status.setText(str(error))

    def refresh(self):
        try:
            self.proposals = preview(self.folder, self.read_rules())
            self.files.setRowCount(len(self.proposals))
            for row, proposal in enumerate(self.proposals):
                for col, text in enumerate([proposal.source.name, str(proposal.destination or "—"), proposal.reason]):
                    self.files.setItem(row, col, QTableWidgetItem(text))
            count = sum(p.destination is not None for p in self.proposals)
            self.status.setText(f"{count} files match your rules. No files were moved.")
        except (ValueError, OSError) as error:
            self.proposals = []
            self.files.setRowCount(0)
            self.status.setText(str(error))


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("LocalOrganizer")
    app.setApplicationName("DownloadsOrganizer")
    window = Window()
    window.show()
    sys.exit(app.exec())
