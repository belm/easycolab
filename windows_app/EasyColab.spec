# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification for EasyColab Windows Desktop Client (EasyColab.exe).
Bundles the Qt6 Studio UI, QtMultimedia MP4 audio/video plugins, colab_bridge.py,
google-colab-cli OAuth config, app.py, and EasyColab_Server.ipynb into a standalone
distribution requiring ZERO Python installation on user machines.
"""
import os
import re
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

SPEC_DIR = Path(SPECPATH).resolve()
PROJECT_ROOT = SPEC_DIR.parent
ICON_PATH = SPEC_DIR / "assets" / "AppIcon.ico"
VERSION_FILE = PROJECT_ROOT / "VERSION"
APP_VERSION = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.is_file() else "1.1.0"
_ver_nums = [int(x) for x in re.findall(r"\d+", APP_VERSION)[:4]]
while len(_ver_nums) < 4:
    _ver_nums.append(0)
APP_VERSION_QUAD = tuple(_ver_nums[:4])

win_version_info = None
if sys.platform == "win32":
    try:
        from PyInstaller.utils.win32.versioninfo import (
            FixedFileInfo,
            StringFileInfo,
            StringStruct,
            StringTable,
            VarFileInfo,
            VarStruct,
            VSVersionInfo,
        )

        win_version_info = VSVersionInfo(
            ffi=FixedFileInfo(
                filevers=APP_VERSION_QUAD,
                prodvers=APP_VERSION_QUAD,
                mask=0x3F,
                flags=0x0,
                OS=0x40004,
                fileType=0x1,
                subtype=0x0,
                date=(0, 0),
            ),
            kids=[
                StringFileInfo(
                    [
                        StringTable(
                            "040904B0",
                            [
                                StringStruct("CompanyName", "EasyColab Open Source"),
                                StringStruct("FileDescription", "EasyColab AI Studio"),
                                StringStruct("FileVersion", ".".join(str(n) for n in APP_VERSION_QUAD)),
                                StringStruct("InternalName", "EasyColab"),
                                StringStruct("OriginalFilename", "EasyColab.exe"),
                                StringStruct("ProductName", "EasyColab"),
                                StringStruct("ProductVersion", APP_VERSION),
                            ],
                        )
                    ]
                ),
                VarFileInfo([VarStruct("Translation", [1033, 1200])]),
            ],
        )
    except Exception:
        win_version_info = None

datas = []
for res_name in ("VERSION", "app.py", "colab_bridge.py", "EasyColab_Server.ipynb", "requirements.txt"):
    src = PROJECT_ROOT / res_name
    if src.exists():
        datas.append((str(src), "."))

if ICON_PATH.exists():
    datas.append((str(ICON_PATH), "assets"))
png_path = SPEC_DIR / "assets" / "AppIcon.png"
if png_path.exists():
    datas.append((str(png_path), "assets"))

# Include colab_cli oauth_config.json and package metadata
datas += collect_data_files("colab_cli")
datas += collect_data_files("certifi")
for pkg in ("google-colab-cli", "google-auth", "google-auth-oauthlib", "requests"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

hiddenimports = [
    "colab_bridge",
    "google.auth.transport.requests",
    "google.oauth2.credentials",
    "google_auth_oauthlib.flow",
    "requests_oauthlib",
    "websocket",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
]
hiddenimports += collect_submodules("colab_cli")
try:
    hiddenimports += collect_submodules("jupyter_kernel_client")
except Exception:
    pass

excludes = [
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQml",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "tkinter",
    "matplotlib",
    "scipy",
    "torch",
]

a = Analysis(
    [str(SPEC_DIR / "easycolab_win.py")],
    pathex=[str(PROJECT_ROOT), str(SPEC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EasyColab",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ICON_PATH) if ICON_PATH.exists() else None,
    version=win_version_info,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="EasyColab",
)
