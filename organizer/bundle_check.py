"""Explicit bundle verification using temporary files, never real Downloads."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from .app import Window
from .core import preview
from .moves import Journal
from .startup import launch_command, packaged_windows


def verify(report_path):
    report = Path(report_path).resolve()
    app = QApplication([])
    def wait_until(condition):
        deadline = time.monotonic() + 10
        while not condition():
            if time.monotonic() >= deadline:
                raise TimeoutError("Bundled automatic worker did not finish")
            app.processEvents()
            time.sleep(.02)

    with tempfile.TemporaryDirectory(prefix="bundle-check-", dir=report.parent) as directory:
        root = Path(directory)
        downloads = root / "Downloads"
        downloads.mkdir()
        original = downloads / "report.pdf"
        original.write_bytes(b"Bundle verification only")
        os.utime(original, (time.time() - 10, time.time() - 10))
        window = Window(root / "data")
        window.set_folder(downloads)
        window.refresh()
        assert window.files.rowCount() == 1
        proposals = preview(downloads, window.read_rules())
        with Journal(root / "data/history.db") as journal:
            moved = journal.move(proposals[0])
            assert moved.exists() and not original.exists()
            journal.undo(journal.history()[0][0])
            assert original.read_bytes() == b"Bundle verification only"
        window.show()
        app.processEvents()
        tray = QSystemTrayIcon.isSystemTrayAvailable()
        if tray:
            window.tray_mode.setChecked(True)
            window.close()
            assert not window.isVisible() and window.tray.isVisible()
            window.show_window()
            app.processEvents()
            assert window.isVisible()
        assert window.grab().save(str(report.with_suffix(".png")))
        first, second = QLockFile(str(root / "instance.lock")), QLockFile(str(root / "instance.lock"))
        assert first.tryLock(0) and not second.tryLock(0)
        first.unlock()
        try:
            window.automatic.setChecked(True)
            wait_until(lambda: not original.exists())
        finally:
            window.request_quit()
            if window.monitor is not None:
                window.monitor.stop()
                window.monitor.wait()
            app.processEvents()
        assert not window.tray.isVisible()
        offline = downloads / "downloaded-while-stopped.pdf"
        offline.write_bytes(b"Offline catch-up verification")
        os.utime(offline, (time.time() - 10, time.time() - 10))
        restarted = Window(root / "data")
        try:
            wait_until(lambda: not offline.exists())
            assert restarted.automatic.isChecked()
        finally:
            restarted.request_quit()
            if restarted.monitor is not None:
                restarted.monitor.stop()
                restarted.monitor.wait()
            app.processEvents()
        command, working = launch_command()
        assert getattr(sys, "frozen", False) and command == [sys.executable, "--background"] and working is None
        # Import compiled WinRT bindings in the Windows bundle without changing startup.
        if sys.platform == "win32":
            from winrt.windows.applicationmodel import StartupTask
            from winrt.windows.foundation import AsyncStatus
            assert StartupTask.get_async and AsyncStatus.STARTED == 0
        report.write_text(json.dumps({"passed": True, "executable": sys.executable,
            "python": sys.version, "tray_available": tray, "packaged": packaged_windows(),
            "checks": ["native window", "preview", "move", "undo", "tray close/show/quit", "configuration lock", "automatic worker", "stopped-period catch-up", "frozen startup command", "WinRT imports"]}, indent=2), encoding="utf-8")
