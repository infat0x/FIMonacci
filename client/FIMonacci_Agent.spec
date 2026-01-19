# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\orxan\\OneDrive\\Desktop\\FIMonacci-main\\client\\client.py', '.'), ('C:\\Users\\orxan\\OneDrive\\Desktop\\FIMonacci-main\\client\\icon.ico', '.'), ('C:\\Users\\orxan\\OneDrive\\Desktop\\FIMonacci-main\\client\\logo.png', '.')]
binaries = []
hiddenimports = ['requests', 'urllib3', 'watchdog', 'watchdog.observers', 'watchdog.events', 'psutil', 'PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL._tkinter_finder', 'win32security', 'win32api', 'pywintypes']
datas += collect_data_files('customtkinter')
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\orxan\\OneDrive\\Desktop\\FIMonacci-main\\client\\app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FIMonacci_Agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\orxan\\OneDrive\\Desktop\\FIMonacci-main\\client\\icon.ico'],
)
