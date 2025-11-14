# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for packaging the Zenith Helper on Linux.

Usage:
    pyinstaller helper_app/packaging/linux/zenith_helper.spec
"""

from pathlib import Path

block_cipher = None

project_root = Path(__file__).resolve().parents[2]

legacy_tree = Tree(project_root / "helper_app" / "legacy", prefix="helper_app/legacy")

datas = [
    legacy_tree,
    (project_root / "helper_app" / "env.example", "helper_app"),
    (project_root / "helper_app" / "version.py", "helper_app"),
    (project_root / "helper_app" / "config.py", "helper_app"),
    (project_root / "helper_app" / "logging_utils.py", "helper_app"),
    (project_root / "helper_app" / "session.py", "helper_app"),
    (project_root / "helper_app" / "updater.py", "helper_app"),
    (project_root / "helper_app" / "controller.py", "helper_app"),
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
    ["helper_app/worker.py"],
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

