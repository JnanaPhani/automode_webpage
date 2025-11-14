from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_pyinstaller(spec_path: Path, dist_path: Path, work_path: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(spec_path),
        "--distpath",
        str(dist_path),
        "--workpath",
        str(work_path),
    ]
    subprocess.check_call(command)


def main() -> None:
    parser = argparse.ArgumentParser(description="Package the Zenith Helper for Windows using PyInstaller.")
    parser.add_argument(
        "--dist",
        default="dist/windows",
        help="Output directory for packaged artifacts (default: dist/windows)",
    )
    parser.add_argument(
        "--work",
        default="build/windows",
        help="Temporary work directory used by PyInstaller (default: build/windows)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    spec_path = project_root / "helper_app" / "packaging" / "windows" / "zenith_helper.spec"
    if not spec_path.exists():
        raise SystemExit(f"Spec file not found: {spec_path}")

    dist_path = project_root / args.dist
    work_path = project_root / args.work

    dist_path.mkdir(parents=True, exist_ok=True)
    work_path.mkdir(parents=True, exist_ok=True)

    run_pyinstaller(spec_path, dist_path, work_path)


if __name__ == "__main__":
    main()

