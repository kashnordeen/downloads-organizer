# Windows build guide

Use a supported Python 3.12–3.14 environment on Windows. The validated build uses Python 3.14.7, PySide6 6.11.2, PyWinRT 3.2.1, PyInstaller 6.22.3, and Microsoft SDK build tools 10.0.28000.2705.

## Portable bundle

From the repository root:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m pip install -r packaging/build-requirements.txt
.venv\Scripts\python.exe packaging/prepare_assets.py
.\packaging\windows\build.ps1 -Python .venv\Scripts\python.exe -Output .\dist
```

Extract the generated ZIP, keep the complete `DownloadsOrganizer` folder together, and run `DownloadsOrganizer.exe`. Python is included. The executable is unsigned; Windows reputation checks may show a warning. No SmartScreen acceptance claim is made.

The build embeds `asInvoker`, dynamically bundles the native runtime, and uses Windows' ICU rather than incompatible external ICU copies. It temporarily narrows PATH to avoid DLLs exported by other development tools. It does not install anything, change security settings, or create a signing certificate.

### Portable upgrades

Disable **Start at login** before moving/removing the old portable folder, then quit the app. Extract the new version into a separate folder and enable startup again from that location. Per-user settings/history remain outside the portable folder. Removing the bundle does not erase organized files or settings.

## Unsigned MSIX

Install the Microsoft Windows SDK build tools, then provide MakeAppx:

```powershell
.\packaging\windows\build.ps1 -Python .venv\Scripts\python.exe `
  -MakeAppx 'C:\path\to\WindowsSDK\x64\makeappx.exe' -Output .\dist
```

The output is an **unsigned packaging artifact**, not a trusted installer. The placeholder publisher is `CN=LocalOrganizer`; rebuild with `-Publisher` matching the exact subject of a release certificate. Sign with SHA-256 using SignTool, verify the signature, and test installation, activation, login startup, upgrade, uninstall, and data retention. Keep private keys and passwords outside the repository.

MSIX startup is disabled by default. The app uses Windows StartupTask APIs and honors user/policy disablement. Startup launches with `--background`, which hides the window only when tray mode is enabled and a tray is available. Package-managed data may be removed on uninstall; back up settings/history before uninstalling when needed.

Official references: [MSIX manual packaging](https://learn.microsoft.com/en-us/windows/msix/package/manual-packaging-root), [SignTool signing](https://learn.microsoft.com/en-us/windows/msix/package/sign-app-package-using-signtool), [Windows startup tasks](https://learn.microsoft.com/en-us/uwp/api/windows.applicationmodel.startuptask), and [PyInstaller](https://pyinstaller.org/en/stable/usage.html).

## Verify a bundle

Use an existing writable report directory:

```powershell
.\DownloadsOrganizer.exe --verify-bundle C:\existing\folder\bundle-check.json
```

This explicit check uses isolated temporary files under the report directory, writes a report and screenshot, then exits. It covers native UI, navigation, icons, preview, move, undo, tray controls, locking, automatic sorting, stopped-period catch-up, the frozen startup command, and WinRT imports. It does not organize your Downloads or change your startup registration.

Clean-machine, Windows 10, signed-install, and macOS/Linux binary verification remain pending. Keep license notices with bundles and complete the public binary redistribution review described in [THIRD_PARTY.md](../THIRD_PARTY.md).
