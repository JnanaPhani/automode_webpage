from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_pyinstaller(spec_path: Path, dist_path: Path, work_path: Path) -> None:
    import shutil
    # Remove existing output directory if it exists
    output_dir = dist_path / "ZenithTek-SensorConfig"
    if output_dir.exists():
        try:
            shutil.rmtree(output_dir)
        except PermissionError:
            # If we can't delete, PyInstaller will handle it with --noconfirm
            pass
    
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(spec_path),
        "--distpath",
        str(dist_path),
        "--workpath",
        str(work_path),
        "--noconfirm",
    ]
    subprocess.check_call(command)


def main() -> None:
    parser = argparse.ArgumentParser(description="Package the Zenith Helper desktop GUI for Windows.")
    parser.add_argument(
        "--dist",
        default="desktop_app/dist/windows",
        help="Output directory for packaged artifacts (default: desktop_app/dist/windows)",
    )
    parser.add_argument(
        "--work",
        default="desktop_app/build/windows",
        help="Temporary work directory used by PyInstaller (default: desktop_app/build/windows)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    spec_path = project_root / "desktop_app" / "packaging" / "windows" / "desktop_helper.spec"
    if not spec_path.exists():
        raise SystemExit(f"Spec file not found: {spec_path}")

    dist_path = project_root / args.dist
    work_path = project_root / args.work
    dist_path.mkdir(parents=True, exist_ok=True)
    work_path.mkdir(parents=True, exist_ok=True)

    run_pyinstaller(spec_path, dist_path, work_path)


if __name__ == "__main__":
    main()


