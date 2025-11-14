from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_pyinstaller(spec_path: Path, dist_path: Path, work_path: Path) -> None:
    env = os.environ.copy()
    env["ZENITH_HELPER_PROJECT_ROOT"] = str(spec_path.resolve().parent.parent.parent)
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
    subprocess.check_call(command, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description="Package the Zenith Helper for Linux using PyInstaller.")
    parser.add_argument(
        "--dist",
        default="helper_app/dist/linux",
        help="Output directory for packaged artifacts (default: helper_app/dist/linux)",
    )
    parser.add_argument(
        "--work",
        default="helper_app/build/linux",
        help="Temporary work directory used by PyInstaller (default: helper_app/build/linux)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    spec_path = project_root / "helper_app" / "packaging" / "linux" / "zenith_helper.spec"

    if not spec_path.exists():
        raise SystemExit(f"Spec file not found: {spec_path}")

    dist_path = project_root / args.dist
    work_path = project_root / args.work

    dist_path.mkdir(parents=True, exist_ok=True)
    work_path.mkdir(parents=True, exist_ok=True)

    run_pyinstaller(spec_path, dist_path, work_path)


if __name__ == "__main__":
    main()

