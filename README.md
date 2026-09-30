# Downloads Organizer — development preview

Implemented: local rule editing, ordered extension/filename matching, settings, preview, verified file moves, numbered duplicates, history, restart reconciliation, and undo. No automatic sorting or installer yet: this is checkpoint A of the approved implementation plan.

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

Settings and SQLite history live in the per-user Qt application data location for `LocalOrganizer/DownloadsOrganizer`. No accounts, network access, telemetry, administrator privileges, or security exclusions are used during normal operation. Quit/closing currently exits the app; closing during a move requests stop after the current file.

## Safety limits
Only direct regular files are considered; subfolders, symlinks/junctions, system files, and common unfinished downloads are skipped. Files must be unchanged since preview and at least two seconds old. Stability/age checks cannot prove completion for every downloader, especially paused downloads. Preview manually before organizing important files.

Moves use a verified temporary copy and atomic no-overwrite hard-link publication within the destination filesystem. Filesystems without hard-link support fail safely and retain the source/recovery copy. Same-volume moves also use copying, so large files need temporary disk space. Changes detected during copying retain the original. A final check and source removal are separate filesystem calls: an external writer can still race that narrow interval; do not organize files actively modified by another program. SHA-256 verification covers content, not arbitrary extended filesystem metadata.

## Verify
```powershell
python -m unittest discover -s tests -v
python -m compileall -q organizer
```

Tests use temporary files and an offscreen desktop window, including preview → move → restart → undo. Actual multi-volume hardware and macOS/Linux packaging remain unverified.

## Dependencies
PySide6 6.11.2 (with matching shiboken6, Essentials, and Addons), current stable release verified on 2026-10-01. Python standard library supplies filesystem operations, JSON, SQLite, and tests. Qt/PySide licensing notices must accompany later bundled distributions.

Sources: [Qt for Python](https://doc.qt.io/qtforpython-6/), [PySide6 release metadata](https://pypi.org/project/PySide6/), [Microsoft standard-user guidance](https://learn.microsoft.com/en-us/windows/win32/secbp/running-with-administrator-privileges).
