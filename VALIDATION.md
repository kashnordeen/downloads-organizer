# Checkpoint A validation — 2026-10-01

Environment: Windows, Python 3.14.7, PySide6 6.11.2 in the workspace-local environment.

13 unittest checks passed. Filesystem checks cover preview/rule priority, exclusions, settings corruption preservation, duplicate filenames, stale source rejection, content changes during copying, publication failure, source-removal failure, interrupted completion recovery, undo conflicts, and edited-destination rejection. Offscreen Qt runtime tests exercise rule editing invalidation and preview → confirmed move → application restart → undo via desktop buttons.

Compileall passed. Git whitespace check passed. The app was rendered and visually inspected; `../organizer-preview.png` shows demonstration files only. The real Downloads folder was not selected or mutated during development.

This is a source development preview, not an installer. Automatic catch-up, tray operation, login startup, release signing, and packaging remain pending. Real cross-volume hardware, arbitrary external-writer races, OS crash/disk failure behavior, macOS, and Linux remain unverified. Unsupported destination hard-link filesystems fail safely. See README for readiness and metadata limitations.

## Checkpoint B — 2026-10-01
Added automatic catch-up and monitoring, persisted automatic/tray options, tray Show/Pause/Resume/Quit, single-instance exclusion, and opt-in source startup registration.

23 tests cover startup backlog priority/deduplication, changing backlog fairness, re-observation after disappearance, stale sources, no retry of unresolved moves, source scan races, registration content/idempotence/removal in temporary locations, startup error reversal, no-tray fallback, lock exclusion, and desktop catch-up across a stopped period. Existing preview/move/recovery/undo checks remain passing.

A native Windows Qt runtime probe confirmed system tray availability and exercised actual hide-to-tray, show, and quit. It rendered the updated `../organizer-preview.png` with demo files. Actual Windows startup registration was not changed; startup generation and disabling were tested in temporary directories. A real login/reboot and simultaneous second GUI launch remain unverified; locking was tested with competing QLockFile instances. Packaging/signing, macOS/Linux runtime, and release security testing remain pending.
