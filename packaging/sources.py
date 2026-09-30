"""Retain corresponding upstream sources and notices alongside public releases."""
import hashlib
import json
import posixpath
import tarfile
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sources = root / "dist/corresponding-source"
sources.mkdir(parents=True, exist_ok=True)
urls = [f"https://download.qt.io/archive/qt/6.11/6.11.2/submodules/{module}-everywhere-src-6.11.2.tar.xz"
        for module in ("qtbase", "qtsvg", "qtimageformats", "qttranslations", "qtwayland")]
urls.append("https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/pyside-setup-everywhere-src-6.11.2.tar.xz")
manifest = []
for url in urls:
    path = sources / url.rsplit("/", 1)[1]
    with urllib.request.urlopen(url + ".sha256", timeout=60) as response:
        expected = response.read().decode().split()[0].lower()
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise ValueError(f"Invalid upstream checksum: {url}")
    if not path.exists() or hashlib.file_digest(path.open("rb"), "sha256").hexdigest() != expected:
        print(f"Downloading {path.name}", flush=True)
        urllib.request.urlretrieve(url, path)
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError(f"Source checksum mismatch: {path.name}")
    manifest.append({"file": path.name, "url": url, "sha256": expected})
    with tarfile.open(path) as archive:
        members = {member.name: member for member in archive.getmembers() if member.isfile()}
        notices = set(name for name in members if any(term in name.lower() for term in
            ("license", "copying", "copyright", "notice", "attribution")))
        for name in list(notices):
            if name.endswith("qt_attribution.json") and "/tests/" not in name:
                data = json.load(archive.extractfile(members[name]), strict=False)
                for entry in data if isinstance(data, list) else [data]:
                    files = entry.get("LicenseFiles", [])
                    if isinstance(files, str):
                        files = [files]
                    for file in files:
                        notices.add(posixpath.normpath(posixpath.join(posixpath.dirname(name), file)))
        for name in sorted(notices):
            if name not in members:
                raise ValueError(f"Missing attribution file: {name}")
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe archive path")
            target = root / "licenses/upstream" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(members[name]).read())
(sources / "SOURCES.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
