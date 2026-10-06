"""Optional release notices; never download or run an installer automatically."""
import json
import re
from urllib.request import Request, urlopen

from PySide6.QtCore import QThread, Signal

RELEASES = "https://github.com/kashnordeen/downloads-organizer/releases"


def version_number(value):
    if not isinstance(value, str) or not re.fullmatch(r"v?\d{1,5}\.\d{1,5}\.\d{1,5}", value):
        raise ValueError("Unsupported release version")
    return tuple(map(int, value.removeprefix("v").split(".")))


def latest_release(current):
    request = Request("https://api.github.com/repos/kashnordeen/downloads-organizer/releases/latest",
                      headers={"Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2026-03-10",
                               "User-Agent": "DownloadsOrganizer/" + current})
    with urlopen(request, timeout=8) as response:
        payload = response.read(1024 * 1024 + 1)
    if len(payload) > 1024 * 1024:
        raise ValueError("Release response is too large")
    data = json.loads(payload)
    if not isinstance(data, dict) or not isinstance(data.get("draft"), bool) or not isinstance(data.get("prerelease"), bool):
        raise ValueError("Invalid release response")
    if data["draft"] or data["prerelease"]:
        return None
    tag = data.get("tag_name")
    if version_number(tag) <= version_number(current):
        return None
    # Construct the trusted project URL; never open a URL supplied by a response.
    return tag.removeprefix("v"), RELEASES + "/tag/" + tag


class UpdateWorker(QThread):
    result = Signal(object)
    failed = Signal(str)

    def run(self):
        from . import __version__
        try:
            self.result.emit(latest_release(__version__))
        except Exception:
            self.failed.emit("Could not check updates. Check your connection and try again.")
