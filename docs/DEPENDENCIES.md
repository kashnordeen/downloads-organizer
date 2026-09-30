# Dependency source and replacement

The release's `corresponding-source-6.11.2.tar.gz` contains unmodified upstream
Qt Base, SVG, Image Formats, Translations, Wayland, and PySide/Shiboken 6.11.2
source archives with upstream SHA-256 values and URLs in `SOURCES.json`.
License texts and third-party attribution files from these archives are also
included inside each app bundle under `licenses/upstream/`. Keep the notices
with the bundle. Application source is included in GitHub's source downloads.

Qt/PySide/Shiboken are dynamically loaded under the LGPL v3 option. You may
replace them with compatible builds, and reverse engineer the application to
debug modifications to those libraries. The application imposes no additional
restriction on those activities. The standalone folder format keeps the
libraries accessible; no one-file archive or library integrity lock is used.

To rebuild the application, install the pinned requirements and run the native
build commands in [BUILDING.md](BUILDING.md). To build modified Qt, unpack the
source archives and follow their included CMake build instructions; install
Qt Base first, then any required add-on modules into the same prefix. Build
PySide/Shiboken against that Qt prefix with the included `setup.py` and build
documentation. Official instructions: [Qt from source](https://doc.qt.io/qt-6/build-sources.html)
and [Qt for Python build](https://doc.qt.io/qtforpython-6/building_from_source/index.html).
Use the same OS, CPU architecture, Python ABI, Qt major/minor ABI, and compatible
compiler/runtime. Replace corresponding PySide6/Shiboken extension modules and
Qt shared libraries together in `_internal/` (macOS: inside `Contents/Frameworks`).
Replace matching plugins too when their ABI changes. Alternatively rebuild the
app against your modified libraries using the supplied specification.

On macOS, changing an app bundle invalidates its ad-hoc signature. Re-sign the
modified app locally with `codesign --force --deep --sign - 'Downloads Organizer.app'`.
This creates a local ad-hoc signature, not a Developer ID signature or Apple
notarization. Operating-system security and managed-device policies still apply.

The app bundles CPython, PyInstaller's bootloader (GPL with its distribution
exception), and their included third-party notices. Windows additionally bundles
MIT-licensed PyWinRT and the MSVC runtime delivered by the official Python/Qt
wheels. See [THIRD_PARTY.md](../THIRD_PARTY.md) for versions and license copies.
An installed package may require OS libraries supplied by the OS/distribution;
those retain their own licenses. No commercial Qt license is claimed.
