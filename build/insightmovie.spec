# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for InsightMovie
One-file mode: すべてを1つのexeにまとめる
"""

block_cipher = None

a = Analysis(
    ['../src/insightmovie/main.py'],
    pathex=[],
    binaries=[
        ('tools/ffmpeg/bin/ffmpeg.exe', 'tools/ffmpeg/bin'),
        ('tools/ffmpeg/bin/ffprobe.exe', 'tools/ffmpeg/bin'),
    ],
    datas=[],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='InsightMovie',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if available
)
