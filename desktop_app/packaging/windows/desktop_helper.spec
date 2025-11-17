# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the Zenith desktop helper GUI.
"""

import inspect
from pathlib import Path

block_cipher = None

spec_file = Path(__file__).resolve() if "__file__" in globals() else Path(inspect.getfile(inspect.currentframe())).resolve()
project_root = spec_file.parents[3]
app_root = project_root / "helper_app"
desktop_root = project_root / "desktop_app"

legacy_tree = Tree(app_root / "legacy", prefix="helper_app/legacy")

public_root = project_root / "public"

datas = [
    (app_root / "env.example", "helper_app"),
    (app_root / "version.py", "helper_app"),
    (app_root / "config.py", "helper_app"),
    (app_root / "logging_utils.py", "helper_app"),
    (app_root / "session.py", "helper_app"),
    (app_root / "controller.py", "helper_app"),
    (public_root / "zenithtek-logo.png", "public"),
    (public_root / "app-icon.png", "public"),
    (public_root / "favicon.ico", "public"),
]

hidden_imports = [
    "helper_app.controller",
    "helper_app.session",
    "helper_app.legacy.imu.sensor_config",
    "helper_app.legacy.imu.sensor_comm",
    "helper_app.legacy.vibration.sensor_config",
    "helper_app.legacy.vibration.sensor_comm",
    "serial.tools.list_ports",
    "asyncio",
]

a = Analysis(
    [str(desktop_root / "app.py")],
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
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ZenithTek-SensorConfig",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    icon=str(public_root / "favicon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    legacy_tree,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ZenithTek-SensorConfig",
)


