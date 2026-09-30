# Downloads Organizer - personal preview

Implemented: local rule editing, ordered extension/filename matching, settings, preview, verified moves, numbered duplicates, history, restart reconciliation, undo, automatic startup catch-up, folder monitoring, tray controls, and optional login startup. A Windows x64 runtime bundle and unsigned MSIX are provided. Trusted installer testing still needs a publisher certificate; macOS/Linux binaries are not yet validated.

## Windows portable build
Extract `DownloadsOrganizer-0.1.0-windows-x64.zip`, keep the entire `DownloadsOrganizer` folder together, and run `DownloadsOrganizer.exe`. Python is included. Intended minimum: Windows 10 version 2004; runtime verification currently covers this Windows 11 PC. Review rules in manual mode before enabling automatic sorting. The executable is unsigned, so Windows reputation checks may show a warning; no signing or SmartScreen acceptance claim is made.

For a portable upgrade, quit the old app and extract the new version into a separate folder. Settings/history remain in per-user application data. Uncheck Start at login before moving or removing a portable folder; enable it again from the new location. Removing the portable folder does not erase your organized files or settings.

## MSIX signing and installation
`DownloadsOrganizer-0.1.0-x64-unsigned.msix` passed MakeAppx packing/manifest validation. It is a packaging artifact, not a trusted installable release. No certificate has been installed and Windows security remains enabled. A release publisher must rebuild with the certificate's exact subject using `-Publisher`, sign the MSIX with SHA-256 using SignTool, verify its signature, then test installation, login startup, upgrade, and uninstall. No private keys or passwords belong in this repository.

The MSIX declares a disabled startup task. The app uses Windows StartupTask APIs to request enabling/disabling it and honors Windows user/policy disablement. MSIX startup launches with `--background`. Actual package activation and login startup remain untested until trusted installation is possible. Windows may remove package-managed settings on uninstall; export/back up settings/history before uninstalling if you need to retain them. Upgrade/uninstall data behavior must be verified on the signed package.

Official guidance: [MSIX command-line packaging](https://learn.microsoft.com/en-us/windows/msix/package/manual-packaging-root), [SignTool signing](https://learn.microsoft.com/en-us/windows/msix/package/sign-app-package-using-signtool), [Windows startup tasks](https://learn.microsoft.com/en-us/uwp/api/windows.applicationmodel.startuptask).

## Rebuild on Windows
Install source/runtime dependencies and `packaging/build-requirements.txt` in an isolated Python environment. Run `python packaging/prepare_assets.py`, then:

```powershell
.\packaging\windows\build.ps1 -Python .venv\Scripts\python.exe -MakeAppx 'C:\path\to\WindowsSDK\x64\makeappx.exe' -Output C:\path\to\release
```

Omit `-MakeAppx` for a portable-only build. The script bundles with pinned PyInstaller 6.22.3 instead of a compiler-dependent build, embeds `asInvoker`, uses fresh MSIX staging, and excludes incompatible external ICU copies in favor of Windows' ICU. It temporarily narrows the build process PATH to avoid other tools' DLLs. It never installs the package, changes security settings, or signs with a generated certificate. License texts in `licenses/` must remain present; see `THIRD_PARTY.md` for redistribution limits.

To verify a built bundle without touching Downloads or changing startup:

```powershell
.\DownloadsOrganizer.exe --verify-bundle C:\existing\folder\bundle-check.json
```

The explicit check uses temporary files under the report directory, writes a report/screenshot, and exits. It checks native UI, preview, move, undo, tray behavior, configuration locking, automatic sorting, catch-up after stopping, frozen startup command, and compiled Windows API imports. A complete clean-machine and signed-install check remains a release gate. See [PyInstaller documentation](https://pyinstaller.org/en/stable/usage.html).

## Run from source
Requires Python 3.12–3.14. In this project folder:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\pythonw.exe -m organizer
```

On macOS/Linux replace `py` with `python3` and `.venv\Scripts\python.exe` with `.venv/bin/python`; launch with `.venv/bin/python -m organizer`. Those systems have not yet been tested. On Linux the OS must provide Qt's required display libraries.

The current workspace also has a prepared environment at `../../work/organizer-venv`. `Launch preview.cmd` uses that environment without installing anything. It is a development launcher for this workspace, not an installer.

## Use
Choose a folder. Default rules place files in category subfolders. Add filename text if desired: when both extension and text filters exist, both must match. Rules run from top to bottom; the first enabled match wins. Select a rule and browse its destination, or edit the absolute path. Save rules, click Preview, then Organize previewed files and confirm. Changed rules invalidate the preview.

History lists completed and interrupted operations. Select a completed move and click Undo. Undo refuses edited destination files and conflicts at the original path. Interrupted operations retain ambiguous copies for review; inspect the original/destination paths before manually resolving them. Hidden `.organizer-*.tmp` recovery files may remain after failures; they are intentionally not automatically deleted.

Settings and SQLite history live in the per-user Qt application data location for `LocalOrganizer/DownloadsOrganizer`. No accounts, network access, telemetry, administrator privileges, or security exclusions are used during normal operation.

## Background operation
Check **Automatically organize using saved rules** after reviewing the selected folder and rules. Ready startup files are processed before later downloads; changing/incomplete files wait without blocking other ready files. Folder notifications wake the worker and periodic scans recover missed events. Editing rules or changing the watched folder pauses automatic mode; review and enable it again to resume. Pause before manual moves or undo. Interrupted moves needing review are not retried automatically.

Check **Keep running in tray when window closes** to keep sorting after closing the window. The tray menu offers Show, Pause/Resume, and Quit. **Quit app** stops after finishing the current file safely. Automatic mode remains saved on Quit, so reopening catches up on files downloaded while stopped. Without a usable system tray, closing exits instead of hiding an unreachable app.

**Start at login** is off by default. The source/portable app uses a Startup `.cmd` on Windows, a LaunchAgent on macOS, and an autostart `.desktop` on Linux. Unchecking removes that registration. Existing identical registrations are not recreated, so OS disablement remains in control. MSIX uses the Windows package startup API instead. `--background` hides the window only when tray mode was enabled and a tray is available; otherwise it shows the window. Moving/deleting a source/portable app invalidates its startup command. Live login boot, macOS, and Linux startup remain unverified.

## Safety limits
Only direct regular files are considered; subfolders, symlinks/junctions, system files, and common unfinished downloads are skipped. Manual moves require unchanged files since preview and an age of at least two seconds. Automatic mode additionally observes stable metadata across scans separated by at least two seconds. These checks cannot prove completion for every downloader, especially paused downloads. Preview manually before organizing important files.

Moves use a verified temporary copy and atomic no-overwrite hard-link publication within the destination filesystem. Filesystems without hard-link support fail safely and retain the source/recovery copy. Same-volume moves also use copying, so large files need temporary disk space. Changes detected during copying retain the original. A final check and source removal are separate filesystem calls: an external writer can still race that narrow interval; do not organize files actively modified by another program. SHA-256 verification covers content, not arbitrary extended filesystem metadata.

## Verify
```powershell
python -m unittest discover -s tests -v
python -m compileall -q organizer
```

Tests use temporary files and an offscreen desktop window, including preview → move → restart → undo. Actual multi-volume hardware and macOS/Linux packaging remain unverified.

## Dependencies
PySide6 6.11.2 (with matching shiboken6, Essentials, and Addons), and Windows-only PyWinRT 3.2.1, verified on 2026-10-01. Python standard library supplies filesystem operations, JSON, SQLite, and tests. Pinned runtime/build dependency lists and accompanying notices are supplied under `packaging/` and `licenses/`. The personal preview is not a completed public redistribution licensing review.

Sources: [Qt for Python](https://doc.qt.io/qtforpython-6/), [PySide6 release metadata](https://pypi.org/project/PySide6/), [Microsoft standard-user guidance](https://learn.microsoft.com/en-us/windows/win32/secbp/running-with-administrator-privileges).
