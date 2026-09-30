"""Generate simple app icons and copy installed runtime license notices."""
import importlib.metadata
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter

root = Path(__file__).resolve().parent.parent
assets = root / "packaging/windows/Assets"
assets.mkdir(parents=True, exist_ok=True)
for name, size in [("StoreLogo.png", 50), ("Square44x44Logo.png", 44),
                   ("Square150x150Logo.png", 150), ("Organizer.ico", 256)]:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(QColor("#183b39"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#f1c66a"))
    painter.drawRoundedRect(QRectF(size * .18, size * .3, size * .35, size * .2), size * .03, size * .03)
    painter.drawRoundedRect(QRectF(size * .18, size * .4, size * .64, size * .35), size * .04, size * .04)
    painter.end()
    if not image.save(str(assets / name)):
        raise RuntimeError(f"Could not save {name}")
licenses = root / "licenses"
licenses.mkdir(exist_ok=True)
for name in ["PySide6", "PySide6_Essentials", "shiboken6", "pyinstaller", "winrt-runtime",
             "winrt-Windows.ApplicationModel", "winrt-Windows.Foundation", "typing_extensions"]:
    distribution = importlib.metadata.distribution(name)
    for file in distribution.files or []:
        if "license" in str(file).lower() or Path(str(file)).name.lower() == "copying.txt":
            source = Path(distribution.locate_file(file))
            if source.is_file():
                target = licenses / name / Path(str(file)).name
                target.parent.mkdir(exist_ok=True)
                shutil.copy2(source, target)
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.exists():
    shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
