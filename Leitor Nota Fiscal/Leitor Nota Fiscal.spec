# -*- mode: python ; coding: utf-8 -*-
import sys
import sysconfig
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


def existing_data(source, destination):
    path = Path(source)
    return [(str(path), destination)] if path.exists() else []


def existing_binary(source, destination="."):
    path = Path(source)
    return [(str(path), destination)] if path.exists() else []


datas = []
datas += existing_data("assets", "assets")

binaries = []
python_base = Path(sys.base_prefix)

tcl_candidates = [python_base / "tcl"]
installed_base = sysconfig.get_config_var("installed_base")
if installed_base:
    tcl_candidates.append(Path(installed_base) / "tcl")

for tcl_root in tcl_candidates:
    datas += existing_data(tcl_root / "tcl8.6", r"tcl\tcl8.6")
    datas += existing_data(tcl_root / "tk8.6", r"tcl\tk8.6")

dll_candidates = [
    python_base / "DLLs",
    Path(sys.executable).resolve().parent,
    python_base,
]
for dll_dir in dll_candidates:
    binaries += existing_binary(dll_dir / "_tkinter.pyd")
    binaries += existing_binary(dll_dir / "tcl86t.dll")
    binaries += existing_binary(dll_dir / "tk86t.dll")

hiddenimports = [
    'tkinter',
    'tkinter.constants',
    'tkinter.filedialog',
    'tkinter.font',
    'tkinter.ttk',
]
datas += collect_data_files('customtkinter')
datas = list(dict.fromkeys(datas))
binaries = list(dict.fromkeys(binaries))
hiddenimports = list(dict.fromkeys(hiddenimports))


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook_tkinter.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Leitor Nota Fiscal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app_icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Leitor Nota Fiscal',
)
