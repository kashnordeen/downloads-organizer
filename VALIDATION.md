# Validation record

Version **0.1.1**, verified **2026-10-01** on Windows 11 x64. This records local checks; it is not a CI badge or a certification.

## Environment

| Component | Verified version |
| :--- | :--- |
| Python | 3.14.7 |
| PySide6 / Qt | 6.11.2 |
| PyWinRT | 3.2.1 |
| PyInstaller / hooks | 6.22.3 / 2026.8 |
| Microsoft SDK build tools | 10.0.28000.2705 |

## Completed checks

- **26 tests passed:** rules and settings, exclusions, collision preservation, stale source rejection, source changes during copying, publication/source-removal failures, interrupted completion recovery, undo conflicts, and edited-destination rejection.
- **Desktop flow:** preview → confirmed move → restart → undo; automatic startup backlog priority, changing-file fairness, stopped-period catch-up, tray behavior, and startup policy handling.
- **Workspace:** navigation preserves valid previews and active monitoring; rule edits invalidate previews; reordering pauses automatic sorting before changing table items.
- **Native UI:** light/dark screenshots inspected at 1180×760 and 900×620 logical pixels; action controls stay accessible with table scrolling. Alt+1 and Tab checks passed.
- **Portable runtime:** ZIP extracted into a separate path containing spaces and Unicode. With Python environment variables cleared and PATH limited to Windows, the bundled executable passed UI, navigation, icon, preview, move, undo, tray, lock, worker, catch-up, startup-command, and WinRT import checks.
- **Packaging:** embedded `asInvoker` manifest inspected; MakeAppx validation/packing succeeded for identity version 0.1.1.0; ZIP/MSIX archive integrity and bundled artwork were checked. Packaged startup is disabled by default.
- **Security checks:** a Defender custom scan of the generated release found no threats. The pinned runtime audit found no known vulnerabilities at the verification date. These are point-in-time checks, not exhaustive security guarantees or SmartScreen reputation claims.
- **Source hygiene:** compilation and Git whitespace checks passed.

The [README tour](docs/media/workspace-tour.gif) uses demonstration files. Validation used isolated temporary files and mocked or temporary startup registrations. Real Downloads and login startup registration were not changed by those checks.

## Remaining verification

- The executable and MSIX are **unsigned**. Trusted publisher identity, installation, package activation, login startup, upgrade/uninstall, and package data retention remain untested.
- A separate clean PC, Windows 10, a real reboot, and a second native app launch remain untested. Competing QLockFile instances were checked.
- macOS/Linux runtime, native startup, and binary packaging remain unverified.
- Real multi-volume hardware, OS crash/disk failure, extended metadata preservation, and arbitrary external-writer races remain outside current validation.
- Complete the Qt corresponding-source and third-party attribution review before distributing compiled bundles publicly.

An early Windows build collected an unrelated incompatible ICU DLL from another tool. The build now narrows PATH and excludes that copy, using Windows' system ICU; the corrected runtime passed the checks above.
