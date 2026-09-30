import plistlib
import tempfile
import unittest
import sys
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from organizer.startup import set_startup, startup_enabled, packaged_windows, package_startup


class StartupTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Windows package API")
    def test_package_api_refuses_windows_disablement_and_can_disable(self):
        from PySide6.QtWidgets import QApplication
        from winrt.windows.applicationmodel import StartupTaskState
        from winrt.windows.foundation import AsyncStatus
        app = QApplication.instance() or QApplication([])
        def completed(value):
            return SimpleNamespace(status=AsyncStatus.COMPLETED, get_results=lambda: value)
        task = SimpleNamespace(state=StartupTaskState.DISABLED_BY_USER,
            request_enable_async=lambda: completed(StartupTaskState.DISABLED_BY_USER))
        def disable():
            task.state = StartupTaskState.DISABLED
        task.disable = disable
        fake_api = SimpleNamespace(get_async=lambda task_id: completed(task))
        with patch("winrt.windows.applicationmodel.StartupTask", fake_api):
            self.assertFalse(package_startup())
            with self.assertRaisesRegex(OSError, "Windows has disabled"):
                package_startup(True)
            self.assertFalse(package_startup(False))
            self.assertEqual(task.state, StartupTaskState.DISABLED)
            task.state = StartupTaskState.ENABLED_BY_POLICY
            task.disable = lambda: None
            self.assertTrue(package_startup(True))
            with self.assertRaisesRegex(OSError, "policy keeps"):
                package_startup(False)

    def test_packaged_startup_uses_api_instead_of_registration_files(self):
        with patch("organizer.startup.packaged_windows", return_value=True), \
             patch("organizer.startup.package_startup", return_value=True) as api:
            self.assertTrue(startup_enabled())
            set_startup(True)
            set_startup(False)
            self.assertEqual(api.call_args_list, [unittest.mock.call(), unittest.mock.call(True), unittest.mock.call(False)])
        with patch("organizer.startup.sys.platform", "linux"):
            self.assertFalse(packaged_windows())

    def test_registrations_and_disable_only_touch_supplied_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = [r"C:\Example Folder\pythonw.exe", "-m", "organizer", "--background"]
            with patch("organizer.startup.launch_command", return_value=(args, r"C:\Example Folder\app")):
                for platform, name in [("win32", "app.cmd"), ("darwin", "app.plist"), ("linux", "app.desktop")]:
                    path = root / name
                    set_startup(True, path, platform)
                    before = path.stat().st_mtime_ns
                    set_startup(True, path, platform)
                    self.assertEqual(before, path.stat().st_mtime_ns)
                    if platform == "darwin":
                        self.assertTrue(plistlib.loads(path.read_bytes())["RunAtLoad"])
                    else:
                        self.assertIn("--background", path.read_text())
                    set_startup(False, path, platform)
                    self.assertFalse(path.exists())

    def test_rejects_injected_newline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.cmd"
            with patch("organizer.startup.launch_command", return_value=(["python\nother-command"], None)):
                with self.assertRaises(ValueError):
                    set_startup(True, path, "win32")
            self.assertFalse(path.exists())
