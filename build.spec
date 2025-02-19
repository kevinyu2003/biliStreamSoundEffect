# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

app_a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('sound', 'sound'),
        ('config.json', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

app_pyz = PYZ(app_a.pure, app_a.zipped_data, cipher=block_cipher)

app_exe = EXE(
    app_pyz,
    app_a.scripts,
    [],
    exclude_binaries=True,
    name='app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

ws_a = Analysis(
    ['ws.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('sound', 'sound'),
        ('config.json', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

ws_pyz = PYZ(ws_a.pure, ws_a.zipped_data, cipher=block_cipher)

ws_exe = EXE(
    ws_pyz,
    ws_a.scripts,
    [],
    exclude_binaries=True,
    name='ws',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    app_exe,
    app_a.binaries,
    app_a.zipfiles,
    app_a.datas,
    ws_exe,
    ws_a.binaries,
    ws_a.zipfiles,
    ws_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='build',
)