# Windows Packaging (Preview)

This folder contains the draft PyInstaller configuration used to bundle the helper into a self-contained Windows executable. The current flow is developer-facing; later milestones will wrap the binary in an installer/service wrapper.

## Prerequisites

- Python 3.11+ on Windows
- A virtual environment with the helper dependencies installed (`pip install -r helper_app/requirements.txt`)
- `pyinstaller` v6.x (`pip install pyinstaller`)

## Build Steps

```powershell
# From the repository root
python -m venv .packaging-venv
.\\.packaging-venv\\Scripts\\activate
pip install -r helper_app\\requirements.txt
pip install pyinstaller

pyinstaller helper_app\\packaging\\windows\\zenith_helper.spec --distpath dist\\windows --workpath build\\windows

# or, with the helper script:
python helper_app\\scripts\\package_windows.py --dist dist\\windows --work build\\windows
```

The resulting bundle lives under `dist/windows/zenith-helper/`:

- `zenith-helper.exe` – launches the FastAPI service on `127.0.0.1:7421`
- Copied legacy sensor scripts in `helper_app/legacy`
- Default `.env` template and helper configuration modules

## Notes & Next Steps

- The build currently ships without an icon/service wrapper; those will be added alongside the tray/auto-start work.
- The helper reads `~/.zenith_helper_token` as usual; the portal still auto-pairs using `/pair`.
- Future automation (`make package-windows`) will call the same spec file so CI can produce installers.

