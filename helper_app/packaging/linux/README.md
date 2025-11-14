# Linux Packaging

Current status: **PyInstaller bundle ready for testing**. AppImage/DEB wrapping will build on top of this payload.

## Prerequisites

- Python 3.11+
- `pyinstaller` installed in the active environment (`pip install pyinstaller`)
- Helper dependencies installed (`pip install -r helper_app/requirements.txt`)

## Build the Bundle

From the repository root:

```bash
python3 -m venv .packaging-venv
source .packaging-venv/bin/activate
pip install -r helper_app/requirements.txt
pip install pyinstaller

python helper_app/scripts/package_linux.py \
  --dist dist/linux \
  --work build/linux
```

The command places the packaged helper under `dist/linux/zenith-helper/` containing:

- `zenith-helper` – executable binary (launches the FastAPI worker)
- `helper_app/legacy/...` – bundled legacy sensor scripts
- `env.example` – template for Supabase credentials and allowed origins

## Systemd User Service (optional)

A starter unit file is included at `helper_app/packaging/linux/zenith-helper.service`. After copying the bundle to a desired location (for example `~/.zenith-helper/zenith-helper`), enable it with:

```bash
mkdir -p ~/.zenith-helper
cp -r dist/linux/zenith-helper ~/.zenith-helper/
mkdir -p ~/.config/systemd/user
cp helper_app/packaging/linux/zenith-helper.service ~/.config/systemd/user/
systemctl --user enable --now zenith-helper.service
```

Adjust `ExecStart` in the unit file if you move the binary to a different directory. Use `journalctl --user -u zenith-helper.service` to tail logs.

## Next Steps

- AppImage wrapper and `.deb` packaging scripts.
- Automated smoke test that runs the packaged helper and exercises `/pair`, `/status`, and connect/detect commands.

