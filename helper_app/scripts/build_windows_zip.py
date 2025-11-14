from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path


def build_zip(bundle_dir: Path, output_zip: Path, readme_template: Path) -> None:
    if not bundle_dir.exists():
        raise SystemExit(f"Bundle directory not found: {bundle_dir}")

    staging_readme = bundle_dir / "README.txt"
    shutil.copy2(readme_template, staging_readme)

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in bundle_dir.rglob("*"):
            relative = path.relative_to(bundle_dir.parent)
            archive.write(path, relative)
    print(f"Windows zip bundle written to {output_zip}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a ZIP archive of the Windows helper bundle.")
    parser.add_argument(
        "--dist",
        default="helper_app/dist/windows/zenith-helper",
        help="Path to the PyInstaller Windows bundle directory (default: helper_app/dist/windows/zenith-helper)",
    )
    parser.add_argument(
        "--output",
        default="helper_app/dist/windows/ZenithHelper-windows.zip",
        help="Output ZIP file path (default: helper_app/dist/windows/ZenithHelper-windows.zip)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    bundle_dir = (project_root / args.dist).resolve()
    output_zip = (project_root / args.output).resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    readme_template = project_root / "helper_app" / "packaging" / "windows" / "README-enduser.txt"

    build_zip(bundle_dir, output_zip, readme_template)


if __name__ == "__main__":
    main()


