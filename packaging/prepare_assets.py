"""Convert the approved icon to package sizes and copy runtime license notices."""
import importlib.metadata
import shutil
import sys
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QLibraryInfo
from PySide6.QtGui import QImage

root = Path(__file__).resolve().parent.parent
assets = root / "packaging/windows/Assets"
assets.mkdir(parents=True, exist_ok=True)
source = QImage(str(root / "organizer/assets/icon.png"))
if source.isNull():
    raise RuntimeError("Approved app icon is missing")
for name, size in [("StoreLogo.png", 50), ("Square44x44Logo.png", 44),
                   ("Square150x150Logo.png", 150), ("Organizer.ico", 256)]:
    image = source.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    if not image.save(str(assets / name)):
        raise RuntimeError(f"Could not save {name}")
if sys.platform == "darwin":
    iconset = root / "build/Organizer.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            suffix = "@2x" if scale == 2 else ""
            image = source.scaled(size * scale, size * scale, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if not image.save(str(iconset / f"icon_{size}x{size}{suffix}.png")):
                raise RuntimeError("Could not create macOS icon")
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(assets / "Organizer.icns")], check=True)
licenses = root / "licenses"
licenses.mkdir(exist_ok=True)
if sys.platform.startswith("linux"):
    import ctypes
    library = next(Path(QLibraryInfo.path(QLibraryInfo.LibrariesPath)).glob("libicuuc.so.73*"))
    icu = ctypes.CDLL(str(library))
    version = (ctypes.c_uint8 * 4)()
    icu.u_getVersion_73(version)
    if tuple(version[:2]) != (73, 2):
        raise RuntimeError("Update the bundled ICU notice to match the new runtime version")
for name in ["PySide6", "PySide6_Essentials", "shiboken6", "pyinstaller", "winrt-runtime",
             "winrt-Windows.ApplicationModel", "winrt-Windows.Foundation", "typing_extensions"]:
    if name.startswith("winrt") and sys.platform != "win32":
        continue
    try:
        distribution = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        if name == "typing_extensions" and sys.platform != "win32":
            continue
        raise
    for file in distribution.files or []:
        if "license" in str(file).lower() or Path(str(file)).name.lower() == "copying.txt":
            source = Path(distribution.locate_file(file))
            if source.is_file():
                target = licenses / name / Path(str(file)).name
                target.parent.mkdir(exist_ok=True)
                shutil.copy2(source, target)
for python_license in [Path(sys.base_prefix) / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE"]:
    if python_license.exists():
        shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
        break
