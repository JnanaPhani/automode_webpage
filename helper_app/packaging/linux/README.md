# Linux Packaging (Preview)

We will ship two Linux deliverables:

1. **AppImage** for portable installs (no root required).
2. **.deb** package (targeting Debian/Ubuntu) that registers a systemd user service for auto-start.

## High-Level Plan

- Use PyInstaller to generate a stripped binary plus supporting files.
- Wrap the output with `appimagetool` to produce an AppImage.
- For `.deb`, assemble the PyInstaller payload under `/opt/zenith-helper` and create a `debian/` control set with a `systemd --user` unit.

## Placeholder Build Sketch

```bash
# From the repo root on Linux
python3 -m venv .packaging-venv
source .packaging-venv/bin/activate
pip install -r helper_app/requirements.txt
pip install pyinstaller

pyinstaller helper_app/worker.py \
  --name zenith-helper \
  --distpath dist/linux \
  --workpath build/linux \
  --noconfirm

# TODO: bundle into AppImage / deb using scripts
```

## Next Steps

1. Author a PyInstaller spec tuned for Linux (shared with AppImage step).
2. Add `scripts/package_linux.py` that orchestrates PyInstaller + AppImage creation.
3. Provide a systemd unit template (`~/.config/systemd/user/zenith-helper.service`) and installer scripts for `.deb`.

