# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# 1. Recolección de archivos de tema y configuraciones JSON de CustomTkinter
ctk_datas = collect_data_files('customtkinter')

# 2. Manejo seguro de assets (no falla si la carpeta no existe en el repositorio)
added_datas = list(ctk_datas)
if os.path.exists('assets') and os.path.isdir('assets'):
    added_datas.append(('assets', 'assets'))

# 3. Verificación de existencia del icono .ico
icon_path = 'assets/icon.ico' if os.path.exists('assets/icon.ico') else None

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=added_datas,
    hiddenimports=[
        'PIL._tkinter_finder',
        'matplotlib.backends.backend_tkagg',
        'openpyxl',
        'sqlite3',
        'customtkinter'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'scipy',
        'IPython',
        'notebook',
        'pytest',
        'unittest'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TheGaragePOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,               # False para que no abra ventana negra de terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path
)
