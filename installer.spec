import os
import shutil

payload_src = None
if os.path.exists('dist/Dlives.exe'):
    payload_src = 'dist/Dlives.exe'
elif os.path.exists('Dlives.exe'):
    payload_src = 'Dlives.exe'
elif os.path.exists('dist_app/Dlives.exe'):
    payload_src = 'dist_app/Dlives.exe'

if payload_src:
    shutil.copy2(payload_src, 'Dlives_Payload.bin')
    print(f"[SPEC SUCCESS]: Copied payload '{payload_src}' -> 'Dlives_Payload.bin'")
else:
    raise RuntimeError("CRITICAL ERROR: Dlives.exe payload binary missing! Build Dlives.spec first before running installer.spec.")

datas_list = [
    ('Dlives_Payload.bin', '.'),
    ('app_icon.ico', '.'),
    ('assets', 'assets')
]

excludes_list = [
    'PyQt6.QtMultimedia',
    'PyQt6.QtNetwork',
    'PyQt6.QtQml',
    'PyQt6.QtQuick',
    'PyQt6.QtSql',
    'PyQt6.QtSvg',
    'PyQt6.QtTest',
    'PyQt6.QtXml',
    'numpy',
    'psutil',
    'wmi',
    'pynput',
    'comtypes',
    'system_monitor',
    'ui_components',
    'full_app_window'
]

a = Analysis(
    ['installer.py'],
    pathex=[],
    binaries=[],
    datas=datas_list,
    hiddenimports=['win32com.client'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes_list,
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Dlives_Setup',
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
    icon=['app_icon.ico'],
    version='installer_version_info.txt',
)
