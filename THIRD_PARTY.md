# Third-party notices

Application code is MIT-licensed. Dependencies retain their own licenses.
The app dynamically loads unmodified Python, Qt/PySide, and Shiboken libraries.
Keep the entire bundle and its notices together. You may replace compatible
LGPL libraries; reverse engineering needed to debug changes to those libraries
is permitted. No application lock prevents replacing them.

| Component | Version | License / source |
|---|---|---|
| CPython | 3.14.7 | PSF and included third-party notices in Python-LICENSE.txt; https://www.python.org/downloads/source/ |
| Qt Base, SVG, Image Formats, Translations, Wayland | 6.11.2 | LGPL v3 option for used modules, plus their third-party notices; source archives supplied with release |
| PySide / Shiboken | 6.11.2 | LGPL v3 option; source archive supplied with release |
| ICU (Linux Qt wheel) | 73.2 | Unicode/ICU terms in licenses/ICU-73.2-LICENSE.txt; https://github.com/unicode-org/icu/tree/release-73-2 |
| PyWinRT runtime, ApplicationModel, Foundation (Windows) | 3.2.1 | MIT; https://github.com/pywinrt/pywinrt/tree/v3.2.1 |
| typing_extensions (Windows) | 4.16.0 | PSF; https://github.com/python/typing_extensions |
| PyInstaller bootloader | 6.22.3 | GPL v2 with bootloader distribution exception; https://github.com/pyinstaller/pyinstaller/tree/v6.22.3 |

License copies, third-party attribution manifests, and referenced license files
are under `licenses/` inside each bundle. Qt wheels also include a commercial
license reference as an alternative; this app uses the open-source LGPL option.
LGPL v3 and GPL v3 texts accompany it. Qt's unused PDF, QML/Quick, and virtual
keyboard plugins/libraries are excluded from these Widgets builds.

The release includes `corresponding-source-6.11.2.tar.gz`, containing upstream
sources and checksums. [Build and replacement instructions](docs/DEPENDENCIES.md)
explain rebuilding the application or replacing compatible library binaries.
The application's tagged source is also available on the release page.

Python's notices cover its included libraries, including OpenSSL and SQLite.
Windows runtime DLLs supplied by official Python/Qt wheels retain Microsoft's
redistribution terms; OS-supplied libraries retain their respective licenses.
Inno Setup is a build tool; its generated installer contains its licensed stub.
Its terms are available at https://github.com/jrsoftware/issrc/blob/main/license.txt.
No license is changed by this application's MIT license.

Linux native system libraries are excluded from the app bundle and supplied by
the distribution's packages. The `.deb` declares those runtime dependencies;
portable users need the same packages. Python, Qt, PySide/Shiboken, and the Qt
wheel's ICU remain bundled with their notices.
