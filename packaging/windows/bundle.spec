# PyInstaller one-folder build keeps Qt libraries replaceable.
from pathlib import Path
import sys
root = Path(SPECPATH).parent.parent
analysis = Analysis([str(root / "packaging/entry.py")], pathex=[str(root)],
    hiddenimports=["winrt.windows.applicationmodel", "winrt.windows.foundation"] if sys.platform == "win32" else [],
    excludes=["PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf", "PySide6.QtVirtualKeyboard",
              "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets"],
    datas=[(str(root / "organizer/assets"), "organizer/assets"), (str(root / "licenses"), "licenses"),
           (str(root / "LICENSE"), "."), (str(root / "THIRD_PARTY.md"), ".")], binaries=[])
# Qt uses Windows' system ICU ABI; an unrelated ICU from PATH can break imports.
def needed(entry):
    name = entry[0].lower().replace("\\", "/")
    # Widgets do not use PDF rendering, QML, or Qt's virtual keyboard.
    return not any(part in name for part in ("qt6qml", "qtqml", "qt6quick", "qtquick",
        "qt6pdf", "qtpdf", "qt6virtualkeyboard", "qtvirtualkeyboard", "qt_help_")) \
        and not Path(name).name.startswith(("qpdf.", "libqpdf.")) \
        and (sys.platform != "win32" or Path(name).name not in {"icuuc.dll", "icudt78.dll"})
analysis.binaries = [entry for entry in analysis.binaries if needed(entry)]
analysis.datas = [entry for entry in analysis.datas if needed(entry)]
if sys.platform.startswith("linux"):
    # Native libraries stay distribution-managed; Python and Qt remain bundled.
    analysis.exclude_system_libraries()
archive = PYZ(analysis.pure)
executable = EXE(archive, analysis.scripts, [], exclude_binaries=True,
    name="DownloadsOrganizer", console=False, upx=False,
    manifest=str(root / "packaging/windows/app.manifest") if sys.platform == "win32" else None,
    icon=str(root / "packaging/windows/Assets" / ("Organizer.icns" if sys.platform == "darwin" else "Organizer.ico")))
distribution = COLLECT(executable, analysis.binaries, analysis.datas,
    name="DownloadsOrganizer", upx=False)
if sys.platform == "darwin":
    app = BUNDLE(distribution, name="Downloads Organizer.app",
        icon=str(root / "packaging/windows/Assets/Organizer.icns"),
        bundle_identifier="local.downloadsorganizer", version="1.1.0",
        info_plist={"NSHighResolutionCapable": True,
                    "NSDownloadsFolderUsageDescription": "Organize the Downloads folder you select.",
                    "NSDocumentsFolderUsageDescription": "Organize files in a folder you select."})
