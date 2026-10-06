# Validation record

## 1.1.0 stable release

Version **1.1.0**, checked **2026-10-06**, uses packages from the
[desktop build](https://github.com/kashnordeen/downloads-organizer/actions/runs/37481666269)
for commit `56c4cfe09d916fbe4ddc1f3f4bbf2d23a090bcc0`. All four release
targets passed tests, dependency audits, bundled-runtime checks and packaging.
Windows passed installation, repeat installation/upgrade, uninstall and
user-data retention checks. Linux passed package installation and runtime checks;
macOS passed app/DMG generation and ad-hoc signature integrity checks.

The Windows source suite discovered **47 tests: 46 passed and one existing
symlink-privilege check was skipped**. Added checks cover interrupted moves,
copy/hash cancellation, retained published copies, responsive navigation,
optional update notices, timestamp migration, saved themes, rule numbering,
rapid tab switches and rendered tray-menu contrast.

Native Windows captures checked all four pages during and after transitions
at 900×620 and 1180×760, in Day, Night and Night → Day. Repeated switching
while refreshing 200 isolated History rows showed a single clean page.
Tray menus were checked with the window shown and hidden. The opacity effect
was removed; opaque pages retain a short slide when desktop effects are enabled.
These checks used demonstration files and did not change real Downloads or
startup registration.

Packages remain unsigned on Windows and ad-hoc signed without notarization
on macOS. See [signing status](docs/SIGNING.md). The release includes combined
SHA-256 checksums and corresponding dependency sources; earlier platform and
filesystem limits below still apply.

## 1.0.0 stable release

Version **1.0.0**, checked **2026-10-03**, was built from merged commit
`6e5db7e97d6a4d2ba8c505d2d12655a8c8ed7edd`. The
[desktop build](https://github.com/kashnordeen/downloads-organizer/actions/runs/37108313059)
passed on Windows x64, macOS Intel, macOS Apple Silicon, and Linux x64. The
Apple Silicon DMG creation hit a runner `hdiutil` resource-busy error on the
first attempt; a retry passed all package and bundled-runtime checks.

The Windows source suite ran 35 tests: 34 passed and one Windows
symlink-privilege test was skipped. It covers review choices, keeping a file
in Downloads, the guided tour, and clicking **Organize files** in Preview
after confirmation, including a retry after an original-only interruption.
The release's six packages, corresponding source, and combined checksums were
verified locally and against GitHub's uploaded SHA-256 digests. Windows
packages remain unsigned; macOS packages are ad-hoc signed but not notarized.
See the [code signing policy](docs/SIGNING.md).

## 0.2.0 preview history

Version **0.2.0 public preview**, checked **2026-10-01**. Build source:
`0f5945de01c827ad898a51820c280dafcffc811d`.
[Final desktop build](https://github.com/kashnordeen/downloads-organizer/actions/runs/36824119673)
completed successfully for all four release targets.

| Target | Checks completed |
|---|---|
| Windows x64 / Server 2022 | Tests, dependency audit, bundled runtime, per-user Setup installation, repeat installation/upgrade, uninstall, and retained user-data sentinel |
| macOS 15 Intel | Tests, dependency audit, bundled runtime, app/DMG generation, and ad-hoc signature integrity |
| macOS 15 Apple Silicon | Tests, dependency audit, bundled runtime, app/DMG generation, and ad-hoc signature integrity |
| Ubuntu 22.04 x64 | Tests, dependency audit, bundled runtime with X11 under Xvfb, Debian package install/runtime/uninstall, and portable archive |

## Completed verification

- **29 tests discovered per target**, with one platform-specific skip. They cover rules/settings, link exclusions, collision preservation, stale/changed source rejection, recovery, undo, startup policy handling, automatic backlog priority, stopped-period catch-up, navigation, first-launch selection, settings retention, and rule-form validation.
- **Bundled runtime:** preview, verified move, undo, icons, navigation, competing QLockFile instances, automatic sorting, restart catch-up, and the frozen startup command. WinRT imports were checked on Windows. CI bundle reports accurately omit tray checks when a tray is unavailable.
- **Windows 11 native run:** the final portable ZIP was extracted to a path containing spaces and Unicode. With PYTHONHOME/PYTHONPATH cleared and PATH restricted to Windows, the app passed its isolated runtime check, including real tray close/show/quit.
- **UI review:** the first-launch dialog, rule form, and compact 900x620 logical-pixel Rules page were captured and inspected. A dialog background contrast defect was corrected. The animated README tour was refreshed from the updated app with demo files and redacted paths.
- **Security checks:** pinned runtime/build dependency audits passed on every target. A local Defender custom scan of the final Windows installer/portable downloads found no threats. These are point-in-time results, not a certification or SmartScreen reputation guarantee.
- **Distribution:** all six package checksums matched the build outputs; Windows ZIP integrity passed. Unused Qt PDF/QML/Quick/virtual-keyboard libraries were excluded. Linux system libraries remain distribution-managed, and the package declares its dependencies.
- **Notices/source:** bundles retain runtime notices, Qt attribution manifests and referenced license texts, and the Linux Qt wheel's ICU 73.2 notice. Six upstream corresponding-source archives matched their published checksums and are supplied with the release. See [dependency instructions](docs/DEPENDENCIES.md).
- **Public source:** local documentation links, compilation, whitespace checks, and the repository history scan passed; no unexpected generated files or credential patterns were found.

All functional checks used isolated temporary files. Real Downloads and login
startup registration were not changed. Windows Setup retention was tested with
a user-data sentinel; app settings/history retention was also exercised by the
desktop restart tests. CI install checks used fresh hosted runners.

## Practical limits

Windows builds are unsigned. Mac apps are ad-hoc signed, without Developer ID
signing or Apple notarization. OS security policy can warn or block installation.

Earlier OS versions, a separate clean Windows user/PC, real macOS/Linux desktop
tray/login/reboot behavior, and signed installations remain manual checks.
CI does not grant protected-folder permissions or bypass OS controls. Quit before
upgrading and disable Start at login before uninstalling or moving a portable app.

Large-history stress, unusual filesystems/hardware, actual power/disk failures,
extended metadata, and arbitrary external-writer races are outside this record.
The file-safety limits are explained in [README.md](README.md).
