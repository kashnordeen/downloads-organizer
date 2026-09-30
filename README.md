<div align="center">

<img src="organizer/assets/icon.png" width="88" alt="Downloads Organizer icon">

# Downloads Organizer

**A calmer downloads folder. Every file stays on your device.**

Preview file moves, build your own rules, and let a local desktop app handle the routine sorting—with history and safe undo.

![Version](https://img.shields.io/badge/version-0.2.0_preview-2457d6?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.12%E2%80%933.14-3776AB?style=flat-square&logo=python&logoColor=white)
![Qt](https://img.shields.io/badge/Qt-6.11.2-41CD52?style=flat-square&logo=qt&logoColor=white)
[![MIT license](https://img.shields.io/badge/license-MIT-2457d6?style=flat-square)](LICENSE)
![Local](https://img.shields.io/badge/files-stay_local-2457d6?style=flat-square)

[Download preview](https://github.com/kashnordeen/downloads-organizer/releases/tag/v0.2.0-preview) · [How it works](#daily-use) · [Build and install](docs/BUILDING.md) · [Validation](VALIDATION.md)

<img src="docs/media/workspace-tour.gif" width="1000" alt="Animated tour of the real Downloads Organizer: preview demo downloads, edit rules, review move history, and open settings">

*Actual application UI with demonstration files. The tour loops automatically.*

</div>

## Built for everyday downloads

| Capability | What you control |
| :--- | :--- |
| **Preview first** | See destinations and skipped reasons before confirming a manual move. |
| **Rules that make sense** | Add or edit rules with a guided form and folder picker. The first enabled rule wins. |
| **First-launch guidance** | Confirm a folder and review starter rules. Automatic sorting starts off. |
| **Automatic catch-up** | On reopening, ready files downloaded while stopped are processed before later ready arrivals. |
| **Background sorting** | Keep the app in the system tray; optionally start it at login. |
| **History and undo** | Review moves and restore unchanged files when the original path is free. |
| **A focused workspace** | Separate Preview, Rules, History, and Settings pages, with blue light/dark themes. |

No account, cloud service, telemetry, or administrator privileges are required for normal operation. Python is included in the downloads.

## Platform status

| Platform | Current status |
| :--- | :--- |
| **Windows x64** | Per-user Setup installer and portable ZIP. CI tests on Windows Server 2022; local source UI tested on Windows 11. Intended minimum: Windows 10 version 2004. |
| **macOS Intel / Apple Silicon** | Separate x64 and arm64 DMGs with app bundles. CI tests on macOS 15. |
| **Linux x64** | Debian/Ubuntu package and portable tar.gz. CI tests on Ubuntu 22.04; native display libraries and glibc 2.34+ required. |

Version **0.2.0** is a public preview. Windows builds are unsigned; macOS builds are ad-hoc signed but lack Developer ID signing and notarization. OS security policies may warn or block installation. Earlier OS versions, real desktop tray/login/reboot behavior on macOS/Linux, and signed installation remain manual validation tasks. See [installation guidance](docs/BUILDING.md).

## Get started

[Download the preview for your OS](https://github.com/kashnordeen/downloads-organizer/releases/tag/v0.2.0-preview), install it, and open **Downloads Organizer**. Confirm the folder on first launch, review Rules, and refresh Preview. Nothing moves until you confirm a manual move or enable automatic sorting.

Windows Setup creates a Start-menu shortcut. On macOS, drag the app from the DMG to Applications before launching. On Ubuntu/Debian, install the `.deb` with the package installer. Portable downloads are also available for Windows/Linux. [Full instructions and upgrades](docs/BUILDING.md).

<details>
<summary><strong>Run from source (developers)</strong></summary>

Install **Python 3.12–3.14** and Git, then clone the repository.

### Windows

```powershell
git clone https://github.com/kashnordeen/downloads-organizer.git
cd downloads-organizer
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\pythonw.exe -m organizer
```

<details>
<summary><strong>macOS / Linux source setup</strong></summary>

```bash
git clone https://github.com/kashnordeen/downloads-organizer.git
cd downloads-organizer
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m organizer
```

Use a supported Python version. On Linux, install the display libraries required by your distribution's Qt environment.

</details>

</details>

## Daily use

1. **Choose a folder.** The default rules suggest category subfolders.
2. **Review Rules.** Use Add rule or Edit selected for a guided form. Choose extensions, filename text, and a destination. Reorder rules to set priority, then save.
3. **Refresh Preview.** Inspect every proposed destination and skipped reason.
4. **Organize files.** Confirm the manual move, or enable automatic sorting after reviewing your rules.
5. **Review History.** Select a completed move to undo when needed.

Switch pages with the sidebar or **Alt+1** through **Alt+4**. Resize table columns or hover over a path to read it in full. Navigation preserves the current preview and automatic monitoring. Editing rules or changing the watched folder pauses sorting and invalidates the preview.

### When the window closes

With **Keep running in the tray** enabled and a usable tray available, closing the window keeps the app running. The tray menu offers Show, Pause/Resume, and Quit. Without a usable tray, closing exits safely.

**Quit app** finishes the current file before stopping. Automatic mode remains saved, so reopening catches up on downloads created during the stopped period. **Start at login** is optional and respects operating-system disablement.

## Safety and privacy

- **Preview never moves files.** Manual moves require confirmation and recheck the source against the preview.
- **Existing destinations are preserved.** Collisions receive numbered names; files are not overwritten.
- **Moves are journaled.** A verified temporary copy is published using a no-overwrite hard link. Interrupted, ambiguous operations retain copies for review instead of automatically retrying.
- **Undo checks first.** Edited destination files and occupied original paths prevent restoration.
- **Only direct regular files are considered.** Subfolders, symlinks/junctions, system files, and common partial downloads are skipped.

Readiness uses file age and, in automatic mode, stable metadata observed across scans at least two seconds apart. This cannot prove every download is complete. Avoid files actively modified by other programs: an external writer can race the final source check/removal. Copying requires temporary disk space; filesystems without hard-link support fail safely and retain the source/recovery copy. SHA-256 verifies content, not arbitrary extended metadata.

Settings and SQLite history use Qt's per-user application data location under **LocalOrganizer / DownloadsOrganizer**. No file data is sent to a server. Interrupted operations may leave hidden `.organizer-*.tmp` files for manual review.

## Inside the app

```mermaid
flowchart LR
    UI[Qt desktop workspace] --> Rules[Ordered rules and preview]
    Folder[Watched folder] --> Scan[Startup scan and readiness checks]
    Scan --> Worker[Automatic worker]
    Rules --> Move[Manual move worker]
    Worker --> Journal[Verified moves and SQLite journal]
    Move --> Journal
    Journal --> Destination[Category folders]
    UI --> Undo[History and safe undo]
    Undo --> Journal
```

| Module | Responsibility |
| :--- | :--- |
| [`ui.py`](organizer/ui.py) / [`app.py`](organizer/app.py) | Native layout, theme, navigation, and desktop actions. |
| [`core.py`](organizer/core.py) | Rules, exclusions, previews, and settings. |
| [`worker.py`](organizer/worker.py) | Startup backlog priority, readiness tracking, notifications, and rescans. |
| [`moves.py`](organizer/moves.py) | Verified copying, collision handling, journal recovery, and undo. |
| [`startup.py`](organizer/startup.py) | Optional per-user startup and Windows packaged startup APIs. |

## Development and verification

Run from an activated project virtual environment:

```bash
python -m unittest discover -s tests -v
python -m compileall -q organizer
```

**29 tests** cover rule priority, exclusions, collisions, stale/changed files, recovery, undo, monitoring, stopped-period catch-up, navigation, tray behavior, startup policy handling, first-launch consent, saved settings, link protection, and rule-form validation. The [desktop workflow](.github/workflows/build.yml) runs them and bundled runtime checks on all release targets. Tests use temporary files and offscreen Qt windows, with platform-specific skips. See [validation details and remaining gates](VALIDATION.md).

Runtime dependencies are pinned in [`pyproject.toml`](pyproject.toml); build pins are in [`packaging/build-requirements.txt`](packaging/build-requirements.txt). Python's standard library supplies filesystem operations, JSON, SQLite, and tests.

For a bug report, include the OS, Python/app version, reproduction steps, and the displayed error. Use sample files and redact personal paths. Test rule changes against temporary folders before contributing changes that move files.

## License

Project code is licensed under [MIT](LICENSE). Dependencies retain their separate licenses. Qt/PySide/Shiboken use the LGPL v3 option; bundles include license texts and upstream attribution files. Releases supply corresponding source archives with checksums and [replacement/build instructions](docs/DEPENDENCIES.md). See [THIRD_PARTY.md](THIRD_PARTY.md).
