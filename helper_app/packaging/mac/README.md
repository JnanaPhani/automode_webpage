# macOS Packaging (Preview)

The macOS pipeline is still under construction. The plan is to deliver a signed `.app` bundle that runs the helper in the background (via LaunchAgent) and auto-checks for updates.

## Proposed Stack

- **Builder:** PyInstaller (short term) to produce a self-contained bundle; evaluate Briefcase or PyOxidizer for notarization friendliness.
- **Auto-start:** User-level LaunchAgent (`~/Library/LaunchAgents/com.zenithtek.helper.plist`) that runs `zenith-helper.app/Contents/MacOS/zenith-helper` on login.
- **Tray UI:** Optional Electron/Tauri wrapper to provide quick status and an exit/update button (post-MVP).

## Current Placeholder Steps

```bash
# From the repo root on macOS
python3 -m venv .packaging-venv
source .packaging-venv/bin/activate
pip install -r helper_app/requirements.txt
pip install pyinstaller

# Draft build (will be replaced with a dedicated spec)
pyinstaller helper_app/worker.py \
  --name zenith-helper \
  --distpath dist/mac \
  --workpath build/mac \
  --windowed \
  --osx-bundle-identifier com.zenithtek.helper \
  --icon helper_app/packaging/mac/icon.icns
```

> **Note:** The command above is merely illustrative. Once we finalise resource copying and LaunchAgent handling, the process will be scripted similar to `scripts/package_windows.py`.

## Upcoming Tasks

1. Create a dedicated PyInstaller spec (or Briefcase config) that mirrors the Windows build inputs.
2. Write a `scripts/package_mac.py` helper with signature/notarization hooks.
3. Generate a LaunchAgent plist template and a post-install script that registers it.

