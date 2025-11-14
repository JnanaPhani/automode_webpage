# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for packaging the Zenith Helper on Linux.

Usage:
    pyinstaller helper_app/packaging/linux/zenith_helper.spec
"""

from pathlib import Path
import os

block_cipher = None

project_root_env = os.environ.get("ZENITH_HELPER_PROJECT_ROOT")
if not project_root_env:
    raise RuntimeError("ZENITH_HELPER_PROJECT_ROOT environment variable not set")

project_root = Path(project_root_env).resolve()

datas = [
    (str(project_root / "legacy"), "helper_app/legacy"),
    (project_root / "env.example", "helper_app"),
    (project_root / "version.py", "helper_app"),
    (project_root / "config.py", "helper_app"),
    (project_root / "logging_utils.py", "helper_app"),
    (project_root / "session.py", "helper_app"),
    (project_root / "updater.py", "helper_app"),
    (project_root / "controller.py", "helper_app"),
]

hidden_imports = [
    "helper_app.api",
    "helper_app.auth",
    "helper_app.controller",
    "helper_app.logging_utils",
    "helper_app.session",
    "helper_app.updater",
    "helper_app.legacy.imu.sensor_config",
    "helper_app.legacy.imu.sensor_comm",
    "helper_app.legacy.vibration.sensor_config",
    "helper_app.legacy.vibration.sensor_comm",
    "uvicorn",
    "uvicorn.main",
    "uvicorn.config",
    "uvicorn.server",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "asyncio",
    "serial.tools.list_ports",
]

a = Analysis(
    [str(project_root / "worker.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tests", "docs"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="zenith-helper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="zenith-helper",
)

