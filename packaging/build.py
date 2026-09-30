"""Build on the target OS; package with its native tools."""
import hashlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from organizer import __version__

def run(*args):
    subprocess.run([str(arg) for arg in args], cwd=root, check=True)

if __name__ == "__main__":
    dist = root / "dist"
    release = dist / "release"
    release.mkdir(parents=True, exist_ok=True)
    run(sys.executable, root / "packaging/prepare_assets.py")
    if sys.platform == "win32":
        os.environ["PATH"] = os.pathsep.join([str(Path(sys.executable).parent),
            str(Path(os.environ["SystemRoot"]) / "System32"), os.environ["SystemRoot"]])
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", root / "packaging/windows/bundle.spec")
    bundle = dist / "DownloadsOrganizer"
    executable = bundle / ("DownloadsOrganizer.exe" if sys.platform == "win32" else "DownloadsOrganizer")
    if sys.platform == "darwin":
        bundle = dist / "Downloads Organizer.app"
        executable = bundle / "Contents/MacOS/DownloadsOrganizer"
    run(executable, "--verify-bundle", dist / "bundle-check.json")
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x64"
    name = f"DownloadsOrganizer-{__version__}"
    if sys.platform == "win32":
        run(sys.argv[1], f"/DBundleDir={bundle}", f"/DOutputDir={release}", root / "packaging/windows/installer.iss")
        shutil.make_archive(str(release / f"{name}-windows-{arch}-portable"), "zip", dist, bundle.name)
    elif sys.platform == "darwin":
        stage = root / "build/dmg"
        stage.mkdir(parents=True, exist_ok=True)
        run("ditto", bundle, stage / bundle.name)
        (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
        run("hdiutil", "create", "-volname", "Downloads Organizer", "-srcfolder", stage,
            "-ov", "-format", "UDZO", release / f"{name}-macos-{arch}-unsigned.dmg")
        run("codesign", "--verify", "--deep", "--strict", bundle)
    else:
        shutil.make_archive(str(release / f"{name}-linux-{arch}-portable"), "gztar", dist, bundle.name)
        stage = root / "build/deb"
        (stage / "DEBIAN").mkdir(parents=True, exist_ok=True)
        (stage / "DEBIAN/control").write_text(f"Package: downloads-organizer\nVersion: {__version__}\n"
            "Architecture: amd64\nMaintainer: kashnordeen <kash.nordeen@gmail.com>\n"
            "Depends: libc6 (>= 2.34), libstdc++6, libgcc-s1, libgl1, libegl1, libopengl0, libfontconfig1, libdbus-1-3, libxkbcommon0, "
            "libxcb-cursor0, libxcb-shape0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, "
            "libxcb-xinerama0, libxcb-xkb1, libxkbcommon-x11-0, libgtk-3-0, libssl3, libsqlite3-0, "
            "libbz2-1.0, liblzma5, libreadline8, libexpat1, zlib1g, libwayland-client0, libwayland-cursor0, libwayland-egl1, libgssapi-krb5-2\n"
            "Section: utils\nPriority: optional\nDescription: Local Downloads organizer with preview and undo\n", encoding="utf-8")
        shutil.copytree(bundle, stage / "opt/downloads-organizer", dirs_exist_ok=True)
        desktop = stage / "usr/share/applications/downloads-organizer.desktop"
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text("[Desktop Entry]\nType=Application\nName=Downloads Organizer\n"
            "Exec=/opt/downloads-organizer/DownloadsOrganizer\nIcon=downloads-organizer\n"
            "Terminal=false\nCategories=Utility;FileTools;\n", encoding="utf-8")
        icon = stage / "usr/share/icons/hicolor/256x256/apps/downloads-organizer.png"
        icon.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / "packaging/windows/Assets/Organizer.ico", stage / "opt/downloads-organizer/Organizer.ico")
        shutil.copy2(root / "organizer/assets/icon.png", icon)
        run("dpkg-deb", "--root-owner-group", "--build", stage, release / f"{name}-linux-{arch}.deb")
    checksums = []
    for path in sorted(release.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            with path.open("rb") as stream:
                checksums.append(f"{hashlib.file_digest(stream, 'sha256').hexdigest()}  {path.name}")
    (release / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
