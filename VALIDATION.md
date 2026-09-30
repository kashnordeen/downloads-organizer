# Checkpoint A validation — 2026-10-01

Environment: Windows, Python 3.14.7, PySide6 6.11.2 in the workspace-local environment.

13 unittest checks passed. Filesystem checks cover preview/rule priority, exclusions, settings corruption preservation, duplicate filenames, stale source rejection, content changes during copying, publication failure, source-removal failure, interrupted completion recovery, undo conflicts, and edited-destination rejection. Offscreen Qt runtime tests exercise rule editing invalidation and preview → confirmed move → application restart → undo via desktop buttons.

Compileall passed. Git whitespace check passed. The app was rendered and visually inspected; `../organizer-preview.png` shows demonstration files only. The real Downloads folder was not selected or mutated during development.

This is a source development preview, not an installer. Automatic catch-up, tray operation, login startup, release signing, and packaging remain pending. Real cross-volume hardware, arbitrary external-writer races, OS crash/disk failure behavior, macOS, and Linux remain unverified. Unsupported destination hard-link filesystems fail safely. See README for readiness and metadata limitations.

## Checkpoint B — 2026-10-01
Added automatic catch-up and monitoring, persisted automatic/tray options, tray Show/Pause/Resume/Quit, single-instance exclusion, and opt-in source startup registration.

23 tests cover startup backlog priority/deduplication, changing backlog fairness, re-observation after disappearance, stale sources, no retry of unresolved moves, source scan races, registration content/idempotence/removal in temporary locations, startup error reversal, no-tray fallback, lock exclusion, and desktop catch-up across a stopped period. Existing preview/move/recovery/undo checks remain passing.

A native Windows Qt runtime probe confirmed system tray availability and exercised actual hide-to-tray, show, and quit. It rendered the updated `../organizer-preview.png` with demo files. Actual Windows startup registration was not changed; startup generation and disabling were tested in temporary directories. A real login/reboot and simultaneous second GUI launch remain unverified; locking was tested with competing QLockFile instances. Packaging/signing, macOS/Linux runtime, and release security testing remain pending.

## Checkpoint C — Windows packaging preview, 2026-10-01

25 unittest checks pass, including package startup routing and refusal to override user/policy disablement. Those package-policy cases use projected API mocks, not a signed installation. Compile and whitespace checks pass.

Built with Python 3.14.7, PySide6 6.11.2, PyWinRT 3.2.1, PyInstaller 6.22.3 / hooks 2026.8, and Microsoft SDK build tools 10.0.28000.2705. The final ZIP was extracted into a different workspace folder containing spaces and Unicode. With PATH limited to Windows and PYTHONHOME/PYTHONPATH cleared, the bundled executable passed native window, preview, verified move, undo, tray close/show/quit, configuration lock, automatic worker, stopped-period catch-up, frozen startup command, and WinRT import checks. No separately launched Python interpreter was used. Report/screenshot: `../windows-bundle-check.json` and `.png`. A separate clean PC without Python remains untested.

The embedded executable manifest was inspected and requests `asInvoker`, with no UIAccess. MakeAppx created the MSIX with validation enabled; archive integrity was checked. Package startup is disabled by default and passes `--background`; package identity Publisher is a placeholder (`CN=LocalOrganizer`) that must match a future signing certificate. AppxSignature.p7x is absent: the MSIX and executable are unsigned. SignTool cannot validate the unsigned MSIX; no trusted install/release claim is made.

Windows Defender antivirus and real-time protection were reported enabled. A custom Defender scan of the generated release found no threats. No security settings or certificate trust were changed. The pinned runtime dependency audit found no known vulnerabilities; `../runtime-audit.json` records all eight checked distributions. These checks do not predict future SmartScreen reputation or establish exhaustive security.

An initial bundle failed because PyInstaller collected another tool's incompatible ICU DLL from PATH. The build now narrows PATH and excludes that external ICU, using Windows' system ICU. The corrected final ZIP passed the runtime checks above.

Remaining gates: trusted publisher identity/signing, actual MSIX installation/activation/login/upgrade/uninstall and data retention, a second native app launch, real reboot, clean-machine/Windows 10 tests, macOS/Linux builds/runtime tests, and complete public redistribution source/Qt attribution review. No actual Downloads files or login startup registration were changed during this checkpoint.
