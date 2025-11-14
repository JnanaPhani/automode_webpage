from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import textwrap
from pathlib import Path
from urllib.request import urlretrieve

APPIMAGETOOL_URL = "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
APPDIR_NAME = "ZenithHelper.AppDir"
APPIMAGE_NAME = "ZenithHelper-x86_64.AppImage"


def ensure_appimagetool(cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / "appimagetool.AppImage"
    if target.exists():
        target.chmod(target.stat().st_mode | stat.S_IXUSR)
        return target
    print(f"Downloading appimagetool to {target}")
    urlretrieve(APPIMAGETOOL_URL, target)
    target.chmod(target.stat().st_mode | stat.S_IXUSR)
    return target


def write_apprun(appdir: Path) -> None:
    apprun = appdir / "AppRun"
    apprun.write_text(
        textwrap.dedent(
            """\
            #!/bin/bash
            HERE="$(dirname "$(readlink -f "$0")")"
            exec "$HERE/usr/bin/zenith-helper" "$@"
            """
        ),
        encoding="utf-8",
    )
    apprun.chmod(0o755)


def write_desktop_file(appdir: Path) -> None:
    desktop = appdir / "zenith-helper.desktop"
    desktop.write_text(
        textwrap.dedent(
            """\
            [Desktop Entry]
            Type=Application
            Name=Zenith Sensor Helper
            Comment=Background bridge that connects the Zenith portal to local sensors
            Exec=zenith-helper
            Icon=zenith-helper
            Categories=Utility;X-Zenith;
            Terminal=false
            """
        ),
        encoding="utf-8",
    )
    applications_dir = appdir / "usr" / "share" / "applications"
    applications_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(desktop, applications_dir / desktop.name)


def copy_icon(project_root: Path, appdir: Path) -> None:
    src_icon = project_root / "public" / "app-icon.png"
    if not src_icon.exists():
        raise SystemExit(f"Icon not found at {src_icon}")
    icon_dir = appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
    icon_dir.mkdir(parents=True, exist_ok=True)
    dest_icon = icon_dir / "zenith-helper.png"
    shutil.copy2(src_icon, dest_icon)
    shutil.copy2(src_icon, appdir / ".DirIcon")
    shutil.copy2(src_icon, appdir / "zenith-helper.png")


def stage_bundle(bundle_dir: Path, appdir: Path) -> None:
    target_bin = appdir / "usr" / "bin"
    target_bin.mkdir(parents=True, exist_ok=True)
    for item in bundle_dir.iterdir():
        dest = target_bin / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
    launcher = target_bin / "zenith-helper"
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def build_appimage(appdir: Path, output_path: Path, appimagetool: Path) -> None:
    env = os.environ.copy()
    env.setdefault("ARCH", "x86_64")
    subprocess.check_call(
        [str(appimagetool), str(appdir), str(output_path)],
        env=env,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an AppImage wrapper around the Linux helper bundle.")
    parser.add_argument(
        "--dist",
        default="helper_app/dist/linux",
        help="Directory containing the PyInstaller bundle and where the AppImage will be written (default: helper_app/dist/linux)",
    )
    parser.add_argument(
        "--work",
        default="helper_app/build/linux/appimage",
        help="Working directory used to assemble the AppDir (default: helper_app/build/linux/appimage)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    bundle_dir = (project_root / args.dist / "zenith-helper").resolve()
    if not bundle_dir.exists():
        raise SystemExit(f"PyInstaller bundle not found at {bundle_dir}. Run package_linux.py first.")

    work_dir = (project_root / args.work).resolve()
    appdir = work_dir / APPDIR_NAME
    if appdir.exists():
        shutil.rmtree(appdir)
    appdir.mkdir(parents=True, exist_ok=True)

    stage_bundle(bundle_dir, appdir)
    write_apprun(appdir)
    write_desktop_file(appdir)
    copy_icon(project_root, appdir)

    cache_dir = project_root / "helper_app" / ".appimage-tools"
    appimagetool = ensure_appimagetool(cache_dir)

    work_dir.mkdir(parents=True, exist_ok=True)
    output_path = (project_root / args.dist / APPIMAGE_NAME).resolve()
    if output_path.exists():
        output_path.unlink()

    build_appimage(appdir, output_path, appimagetool)
    print(f"AppImage written to {output_path}")


if __name__ == "__main__":
    main()


