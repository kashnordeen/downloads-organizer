import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

PARTIAL = {".crdownload", ".part", ".parts", ".download", ".tmp"}
CATEGORIES = {
    "Documents": "pdf doc docx txt md odt",
    "Images": "jpg jpeg png gif webp svg psd heic",
    "Archives": "zip rar 7z tar gz",
    "Installers": "exe msi msix dmg deb rpm appimage",
    "Presentations": "ppt pptx odp",
    "Spreadsheets": "xls xlsx csv ods",
    "Code": "py ipynb html css js ts json",
}


def safe_path(path):
    path = Path(path).absolute()
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError("Symbolic links and junctions are not supported")
    return path.resolve()


@dataclass
class Rule:
    name: str
    extensions: list[str]
    contains: str
    destination: str
    enabled: bool = True

    def validate(self, folder):
        if (not isinstance(self.name, str) or not self.name.strip()
                or not isinstance(self.extensions, list)
                or not all(isinstance(e, str) for e in self.extensions)
                or not isinstance(self.contains, str)
                or not isinstance(self.destination, str)
                or not isinstance(self.enabled, bool)):
            raise ValueError("Invalid rule fields")
        self.extensions = [e.strip().lower().lstrip(".") for e in self.extensions if e.strip()]
        if not self.extensions and not self.contains.strip():
            raise ValueError(f"{self.name}: add an extension or filename filter")
        if not Path(self.destination).is_absolute():
            raise ValueError(f"{self.name}: choose an absolute destination")
        if safe_path(self.destination) == safe_path(folder):
            raise ValueError(f"{self.name}: destination cannot be the watched folder")

    def matches(self, path):
        return (self.enabled and (not self.extensions or path.suffix.lower().lstrip(".") in self.extensions)
                and (not self.contains or self.contains.casefold() in path.name.casefold()))


@dataclass
class Proposal:
    source: Path
    destination: Path | None
    reason: str
    signature: tuple | None = None


def signature(path):
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def preview(folder, rules):
    folder = safe_path(folder)
    for rule in rules:
        rule.validate(folder)
    rows = []
    for path in sorted(folder.iterdir(), key=lambda p: p.name.casefold()):
        if path.is_symlink() or path.is_junction():
            rows.append(Proposal(path, None, "Link skipped"))
        elif path.is_file():
            reason = "No matching rule"
            if path.suffix.lower() in PARTIAL or path.name.startswith(("~$", ".")):
                reason = "Temporary or incomplete file"
            elif path.name.lower() in {"desktop.ini", "thumbs.db"}:
                reason = "System file"
            else:
                rule = next((r for r in rules if r.matches(path)), None)
                if rule:
                    rows.append(Proposal(path, safe_path(rule.destination) / path.name, rule.name, signature(path)))
                    continue
            rows.append(Proposal(path, None, reason))
    return rows


def defaults(folder):
    return [Rule(name, extensions.split(), "", str(Path(folder) / name))
            for name, extensions in CATEGORIES.items()]


def save_settings(path, folder, rules):
    folder = safe_path(folder)
    for rule in rules:
        rule.validate(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump({"folder": str(folder), "rules": [asdict(r) for r in rules]}, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def load_settings(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        folder = safe_path(data["folder"])
        rules = [Rule(**item) for item in data["rules"]]
        for rule in rules:
            rule.validate(folder)
        return folder, rules
    except (TypeError, KeyError, OSError, ValueError) as error:
        raise ValueError(f"Settings could not be loaded: {error}") from error
