# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for OmniDoc Studio
# Build with: pyinstaller OmniDocStudio.spec --noconfirm
#         or: build.bat (recommended)

from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_dynamic_libs

datas = [('ui', 'ui')]
datas += collect_data_files('paddlex')
datas += collect_data_files('paddleocr')
datas += collect_data_files('customtkinter')
datas += copy_metadata('paddlex')
datas += copy_metadata('paddleocr')

binaries = []
binaries += collect_dynamic_libs('paddle')
binaries += collect_dynamic_libs('paddleocr')
binaries += collect_dynamic_libs('paddlex')

a = Analysis(
    ['main.py'],          # CLI entry point
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'paddlex',
        'paddleocr',
        'customtkinter',
        'webview',
        'pikepdf',
        'dotenv',
        'httpx',
        'rich',
        'rich.console',
        'rich.panel',
        'rich.prompt',
        'rich.progress',
        'rich.table',
        'rich.text',
        'rich.rule',
        'tqdm',
        'pdf2image',
        'docx',
        'openai',
        'logger',
        'batch_processor',
        'pdf_toolkit',
        'gui_app',
        'run_ui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# -- CLI exe (console=True) -------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OmniDocStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='OmniDocStudio',
)
