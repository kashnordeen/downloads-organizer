import os
import plistlib
import sys
from pathlib import Path


def startup_file(platform=None):
    platform = platform or sys.platform
    if platform == "win32":
        return Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup/DownloadsOrganizer.cmd"
    if platform == "darwin":
        return Path.home() / "Library/LaunchAgents/local.downloadsorganizer.plist"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "autostart/downloads-organizer.desktop"


def launch_command():
    executable = Path(sys.executable)
    if getattr(sys, "frozen", False):
        return [str(executable), "--background"], None
    pythonw = executable.with_name("pythonw.exe")
    if sys.platform == "win32" and pythonw.exists():
        executable = pythonw
    return [str(executable), "-m", "organizer", "--background"], str(Path(__file__).resolve().parent.parent)


def set_startup(enabled, path=None, platform=None):
    platform = platform or sys.platform
    path = path or startup_file(platform)
    if not enabled:
        path.unlink(missing_ok=True)
        return
    args, working = launch_command()
    if any("\n" in value or "\r" in value or '"' in value for value in args + ([working] if working else [])):
        raise ValueError("Unsupported characters in startup command")
    if platform == "win32":
        quote = lambda value: '"' + value.replace("%", "%%") + '"'
        lines = ["@echo off", "@chcp 65001 >nul"]
        if working:
            lines.append("cd /d " + quote(working))
        lines.append('start "" ' + " ".join(quote(value) for value in args))
        content = ("\r\n".join(lines) + "\r\n").encode("utf-8")
    elif platform == "darwin":
        data = {"Label": "local.downloadsorganizer", "ProgramArguments": args, "RunAtLoad": True}
        if working:
            data["WorkingDirectory"] = working
        content = plistlib.dumps(data)
    else:
        quote = lambda value: '"' + value.replace("\\", "\\\\").replace("$", "\\$").replace("`", "\\`").replace("%", "%%") + '"'
        lines = ["[Desktop Entry]", "Type=Application", "Name=Downloads Organizer",
                 "Exec=" + " ".join(quote(value) for value in args), "Terminal=false"]
        if working:
            lines.append("Path=" + working.replace("\\", "\\\\"))
        content = ("\n".join(lines) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Preserve OS/user disablement: do not recreate an unchanged registration.
    if path.exists() and path.read_bytes() == content:
        return
    temp = path.with_suffix(".tmp")
    temp.write_bytes(content)
    os.replace(temp, path)
