# Build and install

Public builds use Python 3.14.7, PySide6/Qt 6.11.2, PyWinRT 3.2.1 on Windows,
and PyInstaller 6.22.3. Build on each target OS; PyInstaller does not cross-compile.
The [desktop workflow](../.github/workflows/build.yml) records the complete build.

## Download and install

Choose your OS and CPU at [GitHub releases](https://github.com/kashnordeen/downloads-organizer/releases).
Python is included; there is no account or server to configure.

- **Windows:** run the `windows-x64-setup.exe` installer. It installs for the current
  user without requesting administrator access. Alternatively extract the portable
  ZIP and keep its whole folder together.
- **macOS:** open the DMG and drag **Downloads Organizer.app** to Applications
  (or your user Applications folder). Eject the disk image before launching.
  Choose `arm64` for Apple Silicon and `x64` for Intel. Builds are ad-hoc
  signed for execution, but lack Developer ID signing and Apple notarization.
  Gatekeeper or managed-device policies may block them. Follow Apple's normal
  guidance for software you trust; do not disable Gatekeeper.
- **Linux:** install the `.deb` with your distribution's package installer or
  `sudo apt install ./DownloadsOrganizer-1.0.0-linux-x64.deb` on Ubuntu/Debian.
  Or extract the portable tar.gz and run `DownloadsOrganizer/DownloadsOrganizer`.
  The portable build still needs the native display libraries listed in the workflow.
  Native system libraries remain managed by the distribution; the `.deb` declares
  the required packages so its installer can resolve them.
  Builds target glibc 2.34 or newer; the build/test runner uses Ubuntu 22.04.

Windows binaries are unsigned. SmartScreen/antivirus reputation checks may show
a warning or block them. A passing scanner result does not guarantee acceptance
on every PC. macOS trusted distribution requires Developer ID signing and
notarization; Windows trusted distribution requires a release signing identity.
Neither identity is supplied by this repository. Verify release SHA-256 checksums
and download from the project's release page.

On first launch, confirm a folder and follow the guided tour, then preview before moving.
Automatic sorting is off until you enable it. Grant access to the selected folder
through normal OS privacy prompts when required.

## Upgrades and uninstall

Quit the app before upgrading. Windows Setup installs over the same stable path
and leaves per-user settings/history intact. On macOS, replace the app in the same
location. Linux package upgrades replace `/opt/downloads-organizer`; per-user
settings/history stay separate. Uninstalling these packages does not delete
organized files or the app's per-user settings/history.

Disable **Start at login** before uninstalling, or before moving a portable app.
For portable upgrades, extract the replacement into its final location, then
enable startup again. No startup entry is created by an installer; it is an
explicit app setting. Keep backup copies of important files and settings.

## Reproduce a build

Create a virtual environment, activate it, then run:

```sh
python -m pip install -e . -r packaging/runtime-requirements.txt -r packaging/build-requirements.txt
python -m unittest discover -s tests -v
python packaging/sources.py
```

This downloads version-matched upstream sources, verifies their published checksums,
and copies notices. On **Windows**, install the official Inno Setup compiler and run:

```powershell
python packaging/build.py 'C:\path\to\InnoSetup\ISCC.exe'
```

On **macOS** or **Linux**:

```sh
python packaging/build.py
```

Linux requires `dpkg-deb` and the display libraries in the workflow. macOS uses
native `iconutil`, `hdiutil`, and `codesign`. Windows Setup uses
`PrivilegesRequired=lowest`, and the executable embeds Microsoft's `asInvoker`
manifest. Bundles keep Qt libraries replaceable and include dependency notices.
See [source/replacement instructions](DEPENDENCIES.md).

Outputs are in `dist/release/`, with platform checksums. Publish the corresponding
source archive with binaries; keep the per-platform validation reports with each
release. The unsigned MSIX builder in `packaging/windows/build.ps1` remains available
for signing experiments, but MSIX is not the public installation route.

## Verify the built app

```sh
DownloadsOrganizer --verify-bundle /existing/writable/folder/bundle-check.json
```

Use `.exe` on Windows or `Contents/MacOS/DownloadsOrganizer` inside the macOS app.
This explicit check uses isolated temporary files, writes a report and screenshot,
and exits. It checks preview, moves, undo, navigation, icons, locking, automatic
sorting, catch-up after stopping, and frozen startup commands. Tray actions are
tested when a system tray is available. It does not organize your Downloads or
change your login startup registration.

CI tests use Qt offscreen; Linux bundle and installation checks also launch with
the X11 plugin under Xvfb. Real desktop tray/login/reboot behavior, OS security prompts,
earlier OS versions, and signed installs need separate manual testing.

Official references: [PyInstaller](https://pyinstaller.org/en/stable/usage.html),
[per-user Inno Setup](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm),
[Microsoft app manifests](https://learn.microsoft.com/en-us/windows/win32/sbscs/application-manifests),
and [Apple opening guidance](https://support.apple.com/en-us/102445).
