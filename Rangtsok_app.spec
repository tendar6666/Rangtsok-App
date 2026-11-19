# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Rangtsok_app.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.ico', '.'), ('logo.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'PyQt5', 'PyQt6', 'PySide6', 'IPython', 'notebook',
        'pytest', 'jinja2', 'sqlalchemy', 'psycopg2', 'cryptography', 'lxml',
        'bokeh', 'numba', 'pyarrow', 'html5lib', 'beautifulsoup4', 'bs4',
        'wx', 'django', 'flask', 'PyQt4', 'pydoc'
    ],
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
    name='Rangtsok_app',
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
    version='version_info.txt',
    icon=['logo.ico'],
)
