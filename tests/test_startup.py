import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from organizer.startup import set_startup


class StartupTests(unittest.TestCase):
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
