# PyInstaller one-folder build keeps Qt libraries replaceable.
from pathlib import Path
root = Path(SPECPATH).parent.parent
analysis = Analysis([str(root / "packaging/entry.py")], pathex=[str(root)],
    hiddenimports=["winrt.windows.applicationmodel", "winrt.windows.foundation"],
    excludes=["PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets"],
    datas=[], binaries=[])
# Qt uses Windows' system ICU ABI; an unrelated ICU from PATH can break imports.
analysis.binaries = [entry for entry in analysis.binaries
    if Path(entry[0]).name.lower() not in {"icuuc.dll", "icudt78.dll"}]
archive = PYZ(analysis.pure)
executable = EXE(archive, analysis.scripts, [], exclude_binaries=True,
    name="DownloadsOrganizer", console=False, upx=False,
    manifest=str(root / "packaging/windows/app.manifest"),
    icon=str(root / "packaging/windows/Assets/Organizer.ico"))
distribution = COLLECT(executable, analysis.binaries, analysis.datas,
    name="DownloadsOrganizer", upx=False)
