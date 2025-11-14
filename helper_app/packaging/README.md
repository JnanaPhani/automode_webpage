# Packaging Overview

This folder contains platform-specific assets used to bundle the Zenith Helper into native executables. Each subdirectory targets a single operating system and is intentionally self-contained, allowing CI/CD jobs or local developers to produce distribution artefacts per platform.

## Layout

- `windows/` – PyInstaller spec and helper scripts for generating a standalone `.exe` bundle. Future milestones will add a tray/service wrapper and MSI installer.
- `mac/` – Placeholder for macOS builds. We will use PyInstaller (or Briefcase) to output a `.app` bundle and ship a LaunchAgent for auto-start.
- `linux/` – Placeholder for Linux packages. Planned outputs include an AppImage and `.deb` with a systemd user service.

## Common Expectations

- All builds embed the helper’s Python runtime and dependencies so end users do not need a system-wide Python installation.
- The helper continues to bind to `127.0.0.1:7421`, exposes `/pair`, and stores its token in `~/.zenith_helper_token` regardless of platform.
- Update checks (Supabase) and logging behave uniformly across platforms.

## Next Steps

1. Implement GUI/tray or service wrappers for each OS to keep the helper running silently in the background.
2. Wire the packaging scripts into a top-level `make package-*` pipeline and CI workflows.
3. Add smoke-test automation that launches the packaged helper, verifies `/status`, `/pair`, and runs a short connect/detect cycle.

