"""Focused native Qt layout and the shared blue color palette."""
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QPalette, QColor
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QFrame, QDialog,
    QDialogButtonBox, QFileDialog, QFormLayout, QLineEdit, QMessageBox,
    QHeaderView, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QStackedWidget,
    QTableWidget, QVBoxLayout, QWidget, QSystemTrayIcon, QProgressBar, QScrollArea,
    QGraphicsOpacityEffect)

from .core import Rule


class RuleDialog(QDialog):
    """Use the engine's validation before a rule enters the table."""
    def __init__(self, parent, rule):
        super().__init__(parent)
        self.setWindowTitle("Edit organization rule")
        self.setMinimumWidth(520)
        self.folder = parent.folder
        self.rule = None
        layout = QFormLayout(self)
        self.name = QLineEdit(rule.name)
        self.extensions = QLineEdit(", ".join(rule.extensions))
        self.extensions.setPlaceholderText("pdf, docx, txt")
        self.contains = QLineEdit(rule.contains)
        self.contains.setPlaceholderText("Optional text in the filename")
        self.destination = QLineEdit(rule.destination)
        self.destination.setAccessibleName("Destination folder")
        destination = QHBoxLayout()
        destination.addWidget(self.destination)
        destination.addWidget(button("Browse…", self.browse))
        self.enabled = switch("Enable this rule")
        self.enabled.setChecked(rule.enabled)
        layout.addRow("&Name", self.name)
        layout.addRow("&Extensions", self.extensions)
        layout.addRow("Filename &contains", self.contains)
        layout.addRow("Destination", destination)
        layout.addRow(self.enabled)
        note = QLabel("Use an extension, a filename filter, or both. Rules match from top to bottom.")
        note.setWordWrap(True)
        layout.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose destination", self.destination.text())
        if folder:
            self.destination.setText(folder)

    def accept(self):
        rule = Rule(self.name.text().strip(), self.extensions.text().split(","),
                    self.contains.text(), self.destination.text(), self.enabled.isChecked())
        try:
            rule.validate(self.folder)
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Check this rule", str(error))
            return
        self.rule = rule
        super().accept()


def initial_folder(window, suggestion):
    dialog = QDialog(window)
    dialog.setWindowTitle("Welcome to Downloads Organizer")
    dialog.setMinimumWidth(520)
    layout = QVBoxLayout(dialog)
    note = QLabel("Choose the folder you want to organize.\n\n"
                  "We will add starter rules for documents, images, and other file types. "
                  "Review Rules, then refresh Preview to see where files will go.\n\n"
                  "Automatic sorting starts off. Nothing moves during setup or preview.")
    note.setWordWrap(True)
    layout.addWidget(note)
    folder = QLineEdit(suggestion)
    folder.setReadOnly(True)
    layout.addWidget(folder)
    def browse():
        selected = QFileDialog.getExistingDirectory(dialog, "Choose folder to organize", folder.text())
        if selected:
            folder.setText(selected)
    layout.addWidget(button("Choose another folder…", browse))
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.button(QDialogButtonBox.Ok).setText("Use this folder")
    buttons.button(QDialogButtonBox.Ok).setEnabled(bool(suggestion))
    folder.textChanged.connect(lambda value: buttons.button(QDialogButtonBox.Ok).setEnabled(bool(value)))
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    return folder.text() if dialog.exec() == QDialog.Accepted else None


def guided_tour(window):
    steps = [
        (1, "Make your rules", "Starter rules sort common file types into category folders. Add or edit a rule, choose its destination, then save. Rules run top to bottom; the first match wins."),
        (0, "Preview before moving", "Refresh Preview to see each file, its destination, and any skipped reason. Organize files asks for confirmation and never overwrites an existing file."),
        (2, "Review and undo", "History records completed moves. Select one and choose Undo selected move to restore it. For a move marked review, choose Move to destination or Leave in Downloads."),
        (3, "Set up your app", "Settings lets you keep the app in the tray, start at login, replay this tour, or quit. Closing the window stops sorting unless tray mode is enabled."),
        (0, "Choose automatic mode", "Automatic sorting is optional and starts off. Turn it on only after checking your rules. On restart, the app checks files downloaded while it was stopped."),
    ]
    dialog = QDialog(window)
    dialog.setWindowTitle("Welcome · Downloads Organizer")
    dialog.setMinimumWidth(520)
    layout = QVBoxLayout(dialog)
    progress = QLabel()
    progress.setProperty("muted", True)
    title = QLabel()
    title.setObjectName("pageTitle")
    explanation = QLabel()
    explanation.setWordWrap(True)
    explanation.setMinimumHeight(100)
    layout.addWidget(progress)
    layout.addWidget(title)
    layout.addWidget(explanation)
    controls = QHBoxLayout()
    previous = button("Back", lambda: show_step(position[0] - 1))
    skip = button("Skip tour", dialog.accept)
    next_step = button("Next", lambda: show_step(position[0] + 1))
    controls.addWidget(previous)
    controls.addStretch()
    controls.addWidget(skip)
    controls.addWidget(next_step)
    layout.addLayout(controls)
    position = [0]

    def show_step(index):
        if index == len(steps):
            dialog.accept()
            return
        position[0] = index
        page, heading, body = steps[index]
        window.show_page(page)
        progress.setText(f"STEP {index + 1} OF {len(steps)}")
        title.setText(heading)
        explanation.setText(body)
        previous.setEnabled(index > 0)
        next_step.setText("Finish tour" if index == len(steps) - 1 else "Next")

    show_step(0)
    dialog.exec()
    window.show_page(0)


def button(text, callback, primary=False):
    control = QPushButton(text)
    control.setProperty("primary", primary)
    control.clicked.connect(callback)
    return control


def switch(text):
    control = QCheckBox(text)
    control.setProperty("switch", True)
    return control


def table(headers, editable=False):
    control = QTableWidget(0, len(headers))
    control.setHorizontalHeaderLabels(headers)
    control.setAccessibleName("Organization rules" if editable else headers[0] + " list")
    control.setWordWrap(False)
    control.setAlternatingRowColors(True)
    control.setShowGrid(True)
    control.setGridStyle(Qt.SolidLine)
    control.verticalHeader().hide()
    control.verticalHeader().setDefaultSectionSize(44)
    control.setSelectionBehavior(QTableWidget.SelectRows)
    control.setSelectionMode(QTableWidget.SingleSelection)
    if not editable:
        control.setEditTriggers(QTableWidget.NoEditTriggers)
    control.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    control.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    control.horizontalHeader().setStretchLastSection(True)
    return control


def apply_theme(window, scheme=None):
    if scheme is not None:
        window.theme_controls.button(int(scheme == Qt.ColorScheme.Dark)).setChecked(True)
    dark = window.theme_controls.checkedId() == 1
    bg, surface, ink, muted, border, accent, onaccent, soft = (
        ("#151a24", "#1d2431", "#eef3fc", "#adb9cf", "#343f53", "#a8c8ff", "#10264e", "#26354f")
        if dark else
        ("#f6f8fc", "#ffffff", "#24314a", "#58677f", "#dee5ef", "#2457d6", "#ffffff", "#edf2ff"))
    palette = window.palette()
    check = (Path(__file__).parent / "assets" / ("check-dark.svg" if dark else "check-light.svg")).as_posix()
    assets = (Path(__file__).parent / "assets").as_posix()
    for role, color in [(QPalette.Window, bg), (QPalette.WindowText, ink),
                        (QPalette.Base, surface), (QPalette.AlternateBase, bg),
                        (QPalette.Text, ink), (QPalette.Button, surface),
                        (QPalette.ButtonText, ink), (QPalette.Highlight, accent),
                        (QPalette.HighlightedText, onaccent)]:
        palette.setColor(role, QColor(color))
    window.setPalette(palette)
    window.setStyleSheet(f"""
        QWidget {{ color: {ink}; font-size: 14px; }}
        QMainWindow, QDialog, QWidget#workspace {{ background: {bg}; }}
        QWidget#settingsContent, QScrollArea {{ background: {bg}; }}
        QFrame#folderCard, QFrame#operation {{ background: {surface}; border: 1px solid {border}; border-radius: 10px; }}
        QFrame#topnav {{ background: {surface}; border-bottom: 1px solid {border}; }}
        QLabel#brand {{ font-size: 16px; font-weight: 600; }}
        QLabel#pageTitle {{ font-size: 28px; font-weight: 600; }}
        QLabel[muted="true"] {{ color: {muted}; }}
        QLabel#mode {{ color: {accent}; background: {soft}; border-radius: 6px; padding: 6px 12px; }}
        QPushButton {{ background: {surface}; border: 1px solid {border}; border-radius: 6px;
                       padding: 9px 14px; min-height: 18px; }}
        QPushButton:hover {{ background: {soft}; border-color: {accent}; }}
        QPushButton:pressed {{ background: {soft}; }}
        QPushButton:focus {{ border: 2px solid {accent}; padding: 8px 13px; }}
        QPushButton[primary="true"] {{ background: {accent}; color: {onaccent}; border-color: {accent}; font-weight: 600; }}
        QPushButton[primary="true"]:hover {{ border: 2px solid {ink}; padding: 8px 13px; }}
        QPushButton:disabled {{ color: {muted}; background: {bg}; border-color: {border}; }}
        QPushButton[nav="true"] {{ background: transparent; border-color: transparent; padding: 10px 16px; }}
        QPushButton[nav="true"]:checked {{ background: {soft}; color: {accent}; font-weight: 600; }}
        QPushButton[nav="true"]:focus {{ border-color: {accent}; }}
        QTableWidget {{ background: {surface}; alternate-background-color: {bg};
                        border: 1px solid {border}; border-radius: 6px;
                        gridline-color: {border};
                        selection-background-color: {soft}; selection-color: {ink}; }}
        QTableWidget::item {{ padding: 8px; }}
        QTableWidget::item:focus {{ border: 1px solid {accent}; }}
        QHeaderView::section {{ background: {bg}; color: {muted}; border: none;
                                border-right: 1px solid {border}; border-bottom: 1px solid {border};
                                padding: 12px; font-weight: 600; }}
        QTableCornerButton::section {{ background: {bg}; border: none;
                                     border-right: 1px solid {border}; border-bottom: 1px solid {border}; }}
        QLineEdit {{ background: {surface}; color: {ink}; border: 2px solid {accent}; padding: 4px; }}
        QCheckBox {{ spacing: 10px; padding: 7px 0; border: 1px solid transparent; border-radius: 4px; }}
        QCheckBox:focus {{ border-color: {accent}; }}
        QCheckBox::indicator {{ width: 18px; height: 18px;
            background: {surface}; border: 1px solid {muted}; border-radius: 4px; }}
        QCheckBox::indicator:checked {{
            background: {accent}; border-color: {accent}; image: url("{check}"); }}
        QCheckBox:disabled {{ color: {muted}; }}
        QCheckBox[switch="true"]::indicator {{ width: 36px; height: 20px; border-radius: 11px;
            background: {muted}; border-color: {muted}; image: url("{assets}/switch-off.svg"); }}
        QCheckBox[switch="true"]::indicator:checked {{ background: {accent}; border-color: {accent};
            image: url("{assets}/switch-on.svg"); }}
        QCheckBox[switch="true"]::indicator:disabled {{ background: {border}; border-color: {border}; }}
        QTableView::indicator {{ width: 36px; height: 20px; border-radius: 11px;
            background: {muted}; border: 1px solid {muted}; image: url("{assets}/switch-off.svg"); }}
        QTableView::indicator:checked {{ background: {accent}; border-color: {accent}; image: url("{assets}/switch-on.svg"); }}
        QProgressBar {{ background: {soft}; border: none; border-radius: 4px; min-height: 8px; max-height: 8px; }}
        QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}
        QLabel#operationTitle {{ font-weight: 600; }}
        QScrollBar:vertical {{ width: 12px; background: {bg}; margin: 0; }}
        QScrollBar:horizontal {{ height: 12px; background: {bg}; margin: 0; }}
        QScrollBar::handle {{ background: {border}; border-radius: 5px; }}
        QScrollBar::handle:vertical {{ min-height: 28px; }}
        QScrollBar::handle:horizontal {{ min-width: 28px; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
        QToolTip {{ background: {surface}; color: {ink}; border: 1px solid {border}; padding: 6px; }}
    """)


def build_ui(window):
    QApplication.setStyle("Fusion")
    window.resize(1180, 760)
    window.setMinimumSize(900, 620)
    window.setWindowIcon(QIcon(str(Path(__file__).parent / "assets/icon.png")))
    body = QWidget()
    body.setObjectName("workspace")
    window.setCentralWidget(body)
    shell = QVBoxLayout(body)
    shell.setContentsMargins(0, 0, 0, 0)
    shell.setSpacing(0)
    topnav = QFrame()
    topnav.setObjectName("topnav")
    nav_layout = QHBoxLayout(topnav)
    nav_layout.setContentsMargins(24, 12, 24, 12)
    nav_layout.setSpacing(8)
    logo = QLabel()
    logo.setPixmap(window.windowIcon().pixmap(QSize(36, 36)))
    nav_layout.addWidget(logo)
    brand = QLabel("Downloads Organizer")
    brand.setObjectName("brand")
    nav_layout.addWidget(brand)
    nav_layout.addStretch()
    window.navigation = QButtonGroup(window)
    window.pages = QStackedWidget()
    window.page_opacity = QGraphicsOpacityEffect(window.pages)
    window.page_opacity.setOpacity(1.0)
    window.pages.setGraphicsEffect(window.page_opacity)
    window.page_animation = QPropertyAnimation(window.page_opacity, b"opacity", window)
    window.page_animation.setDuration(160)
    window.page_animation.setStartValue(.65)
    window.page_animation.setEndValue(1.0)
    window.page_animation.setEasingCurve(QEasingCurve.OutCubic)

    def animate_page(_):
        window.page_animation.stop()
        window.page_opacity.setOpacity(1.0)
        if window.isVisible() and QApplication.isEffectEnabled(Qt.UI_AnimateMenu):
            window.page_animation.start()

    window.pages.currentChanged.connect(animate_page)
    for index, name in enumerate(["Preview", "Rules", "History", "Settings"]):
        nav = QPushButton(name)
        nav.setProperty("nav", True)
        nav.setCheckable(True)
        nav.setShortcut(f"Alt+{index + 1}")
        nav.setToolTip(f"{name} (Alt+{index + 1})")
        window.navigation.addButton(nav, index)
        nav_layout.addWidget(nav)
    shell.addWidget(topnav)
    content = QVBoxLayout()
    content.setContentsMargins(32, 24, 32, 20)
    content.setSpacing(12)
    shell.addLayout(content, 1)
    top = QHBoxLayout()
    caption = QLabel("FILES STAY ON THIS DEVICE")
    caption.setProperty("muted", True)
    top.addWidget(caption)
    top.addStretch()
    window.theme_controls = QButtonGroup(window)
    for index, name in enumerate(["Day", "Night"]):
        theme = QPushButton(name)
        theme.setProperty("nav", True)
        theme.setCheckable(True)
        theme.setAccessibleName(name + " mode")
        theme.setToolTip("Use " + name.lower() + " mode")
        window.theme_controls.addButton(theme, index)
        top.addWidget(theme)
    window.theme_controls.button(int(QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark)).setChecked(True)
    window.mode_label = QLabel("Manual mode")
    window.mode_label.setObjectName("mode")
    top.addWidget(window.mode_label)
    content.addLayout(top)
    window.update_banner = QFrame()
    notice = QHBoxLayout(window.update_banner)
    notice.setContentsMargins(0, 0, 0, 0)
    window.update_notice = QLabel()
    window.update_notice.setWordWrap(True)
    window.update_notice.setProperty("muted", True)
    notice.addWidget(window.update_notice, 1)
    notice.addWidget(button("View update", window.view_update))
    content.addWidget(window.update_banner)
    window.update_banner.hide()
    window.page_title = QLabel()
    window.page_title.setObjectName("pageTitle")
    content.addWidget(window.page_title)
    window.page_description = QLabel()
    window.page_description.setProperty("muted", True)
    window.page_description.setWordWrap(True)
    content.addWidget(window.page_description)
    folder = QFrame()
    folder.setObjectName("folderCard")
    folder_row = QHBoxLayout(folder)
    folder_row.setContentsMargins(16, 12, 16, 12)
    folder_text = QVBoxLayout()
    folder_caption = QLabel("WATCHED FOLDER")
    folder_caption.setProperty("muted", True)
    folder_text.addWidget(folder_caption)
    window.folder_label = QLabel("Choose a folder to get started")
    window.folder_label.setWordWrap(True)
    window.folder_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    window.folder_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    folder_text.addWidget(window.folder_label)
    folder_row.addLayout(folder_text, 1)
    window.change_folder = button("Change folder…", window.choose_folder)
    folder_row.addWidget(window.change_folder)
    content.addWidget(folder)
    window.operation_panel = QFrame()
    window.operation_panel.setObjectName("operation")
    operation = QHBoxLayout(window.operation_panel)
    operation.setContentsMargins(16, 12, 16, 12)
    progress_text = QVBoxLayout()
    window.operation_label = QLabel("Preparing…")
    window.operation_label.setObjectName("operationTitle")
    window.operation_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    window.operation_label.setWordWrap(True)
    window.operation_label.setTextFormat(Qt.PlainText)
    progress_text.addWidget(window.operation_label)
    window.progress_bar = QProgressBar()
    window.progress_bar.setAccessibleName("Current phase progress")
    window.progress_bar.setTextVisible(False)
    progress_text.addWidget(window.progress_bar)
    window.operation_detail = QLabel()
    window.operation_detail.setWordWrap(True)
    window.operation_detail.setProperty("muted", True)
    progress_text.addWidget(window.operation_detail)
    operation.addLayout(progress_text, 1)
    window.cancel_button = button("Cancel", window.cancel_operation)
    window.cancel_button.setAccessibleName("Cancel current operation and remaining files")
    operation.addWidget(window.cancel_button)
    content.addWidget(window.operation_panel)
    window.operation_panel.hide()
    for _ in range(4):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        window.pages.addWidget(page)
    content.addWidget(window.pages, 1)

    preview = window.pages.widget(0).layout()
    actions = QHBoxLayout()
    window.preview_summary = QLabel("Preview before moving files")
    window.preview_summary.setProperty("muted", True)
    actions.addWidget(window.preview_summary, 1)
    window.refresh_button = button("Refresh preview", window.refresh)
    actions.addWidget(window.refresh_button)
    window.organize = button("Organize files", window.execute, True)
    window.organize.setEnabled(False)
    actions.addWidget(window.organize)
    preview.addLayout(actions)
    window.files = table(["File", "Destination", "Rule / skipped reason"])
    window.files.setColumnWidth(0, 260)
    window.files.setColumnWidth(1, 320)
    preview.addWidget(window.files, 1)
    window.preview_empty = QLabel("Ready when you are\n\nChoose a folder, review Rules, then refresh the preview.\nPreviewing never moves your files.")
    window.preview_empty.setAlignment(Qt.AlignCenter)
    window.preview_empty.setProperty("muted", True)
    window.preview_empty.setWordWrap(True)
    preview.addWidget(window.preview_empty, 1)

    rules_page = window.pages.widget(1).layout()
    window.rules = table(["On", "Rule", "Extensions", "Filename contains", "Destination folder"], True)
    window.rules.setEditTriggers(QTableWidget.NoEditTriggers)
    window.rules.doubleClicked.connect(lambda: window.edit_rule())
    window.rules.setColumnHidden(3, True)
    # Qt's row headers automatically follow insertions, removal and rule priority.
    window.rules.verticalHeader().show()
    window.rules.verticalHeader().setFixedWidth(44)
    window.rules.verticalHeader().setAccessibleName("Rule serial number and priority")
    window.rules.verticalHeader().setDefaultSectionSize(60)
    for col, width in enumerate([60, 170, 230, 160, 280]):
        window.rules.setColumnWidth(col, width)
    window.rules.horizontalHeader().setMinimumSectionSize(44)
    rules_page.addWidget(window.rules, 1)
    rule_actions = QHBoxLayout()
    for text, callback in [("Add rule", lambda: window.edit_rule(new=True)),
                           ("Edit selected", window.edit_rule),
                           ("Remove", window.remove_rule),
                           ("↑", lambda: window.reorder(-1)), ("↓", lambda: window.reorder(1))]:
        control = button(text, callback)
        if text in ("↑", "↓"):
            control.setAccessibleName("Move rule up" if text == "↑" else "Move rule down")
            control.setToolTip(control.accessibleName())
        rule_actions.addWidget(control)
    rule_actions.addStretch()
    rule_actions.addWidget(button("Save rules", window.save, True))
    rules_page.addLayout(rule_actions)

    history = window.pages.widget(2).layout()
    window.history_table = table(["ID", "Original file", "Destination", "State", "Details"])
    for col, width in enumerate([56, 250, 250, 100, 250]):
        window.history_table.setColumnWidth(col, width)
    history.addWidget(window.history_table, 1)
    window.history_empty = QLabel("No moves yet\n\nCompleted moves appear here so you can review or undo them.")
    window.history_empty.setAlignment(Qt.AlignCenter)
    window.history_empty.setProperty("muted", True)
    window.history_empty.setWordWrap(True)
    history.addWidget(window.history_empty, 1)
    history_actions = QHBoxLayout()
    history_actions.addStretch()
    window.review_move = button("Move to destination", lambda: window.resolve_review("move"))
    window.review_keep = button("Leave in Downloads", lambda: window.resolve_review("keep"))
    history_actions.addWidget(window.review_move)
    history_actions.addWidget(window.review_keep)
    window.undo_button = button("Undo selected move", window.undo)
    history_actions.addWidget(window.undo_button)
    history.addLayout(history_actions)
    window.history_table.itemSelectionChanged.connect(window.update_history_actions)

    settings_content = QWidget()
    settings_content.setObjectName("settingsContent")
    settings = QVBoxLayout(settings_content)
    settings.setContentsMargins(0, 0, 12, 0)
    settings.setSpacing(12)
    settings_scroll = QScrollArea()
    settings_scroll.setFrameShape(QFrame.NoFrame)
    settings_scroll.setWidgetResizable(True)
    settings_scroll.setWidget(settings_content)
    window.pages.widget(3).layout().addWidget(settings_scroll)
    window.tray_mode = switch("Keep running when the window closes")
    window.tray_mode.setEnabled(QSystemTrayIcon.isSystemTrayAvailable())
    window.tray_mode.setToolTip("Without a system tray, closing exits safely.")
    settings.addWidget(window.tray_mode)
    window.login_start = switch("Start at login")
    window.login_start.setToolTip("Optional per-user startup. Your operating system can disable it.")
    settings.addWidget(window.login_start)
    window.update_notifications = switch("Notify me about updates when the app starts")
    settings.addWidget(window.update_notifications)
    privacy = QLabel("Optional checks contact GitHub. Your files, rules and history are never sent.\n"
                     "Download from the release page, quit the app, then install over your current version.")
    privacy.setProperty("muted", True)
    privacy.setWordWrap(True)
    settings.addWidget(privacy)
    window.update_status = QLabel("Update checks are off. You can check once at any time.")
    window.update_status.setWordWrap(True)
    settings.addWidget(window.update_status)
    update_actions = QHBoxLayout()
    window.check_updates_button = button("Check for updates", window.check_updates)
    update_actions.addWidget(window.check_updates_button)
    window.download_update = button("View release & download", window.view_update)
    window.download_update.setEnabled(False)
    update_actions.addWidget(window.download_update)
    update_actions.addStretch()
    settings.addLayout(update_actions)
    help_text = QLabel("Automatic sorting checks files downloaded while the app was stopped first.\n\n"
                       "Changing the folder or editing rules pauses sorting so you can review the changes.\n\n"
                       "Cancel stops copying and verification safely. Completed moves remain in History.\n"
                       "When you reopen, saved automatic mode resumes.")
    help_text.setProperty("muted", True)
    help_text.setWordWrap(True)
    settings.addWidget(help_text)
    from . import __version__
    about = QLabel(f"Downloads Organizer {__version__} · Files stay local\nSettings and history: {window.data_dir}")
    about.setObjectName("about")
    about.setWordWrap(True)
    about.setTextInteractionFlags(Qt.TextSelectableByMouse)
    settings.addWidget(about)
    window.tour_button = button("Replay guided tour", window.show_help)
    settings.addWidget(window.tour_button)
    settings.addStretch()
    quit_row = QHBoxLayout()
    quit_row.addWidget(button("Quit app", window.request_quit))
    quit_row.addStretch()
    settings.addLayout(quit_row)

    window.automatic = switch("Automatically organize using saved rules")
    content.addWidget(window.automatic)
    window.status = QLabel("Manual mode. Preview never moves files.")
    window.status.setProperty("muted", True)
    window.status.setTextFormat(Qt.PlainText)
    window.status.setWordWrap(True)
    window.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
    content.addWidget(window.status)
    window.mutation_controls = [window.pages.widget(1), window.rules, window.change_folder,
                                window.refresh_button, window.automatic, window.tour_button]
    window.navigation.idClicked.connect(window.show_page)
    window.show_page(0)
    apply_theme(window)
