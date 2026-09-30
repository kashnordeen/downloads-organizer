# Third-party notices

Project code is MIT-licensed. Dependencies retain their separate licenses.

This one-folder bundle dynamically loads unmodified Python and Qt/PySide DLLs. Keep the entire folder and its notices together. Qt DLLs can be replaced by compatible builds; rebuilding the organizer from the supplied source is also supported. This application does not restrict reverse engineering needed to debug changes to LGPL libraries.

| Component | Version | License / source |
|---|---|---|
| CPython | 3.14.7 | PSF and included third-party notices in Python-LICENSE.txt; https://www.python.org/downloads/source/ |
| Qt / PySide / Shiboken | 6.11.2 | LGPL v3 option for the used Core, Gui, Widgets modules; https://download.qt.io/archive/qt/6.11/6.11.2/ and https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| PyWinRT runtime, ApplicationModel, Foundation | 3.2.1 | MIT; https://github.com/pywinrt/pywinrt/tree/v3.2.1 |
| typing_extensions | 4.16.0 | PSF; https://github.com/python/typing_extensions |
| PyInstaller bootloader | 6.22.3 | GPL v2 with bootloader distribution exception; https://github.com/pyinstaller/pyinstaller/tree/v6.22.3 |

License copies are in `licenses/`. Qt wheels include a commercial-license reference as an alternative; the application uses the open-source LGPL option stated in the package metadata. LGPL v3 and GPL v3 texts accompany that option. The bundled Python notices also cover its included libraries, including OpenSSL and SQLite.

Before publicly distributing compiled bundles, complete the corresponding-source delivery and full Qt third-party attribution review, retain all runtime notices, and verify the licensing of replacement builds. That binary-release review is not yet complete. Publishing this application's MIT-licensed source does not replace those dependency obligations.
