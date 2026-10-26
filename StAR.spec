# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for StAR.
Build with:  pyinstaller StAR.spec
"""

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
ROOT = os.path.dirname(os.path.abspath(SPEC))

# Optional Stereology dependency: bundle it (and its own deps) only if present
# in the build environment. Missing -> the built app simply lacks Stereology.
_stereology_hidden = []
try:
    import pysizeunfolder  # noqa: F401
    _stereology_hidden = (
        collect_submodules('pysizeunfolder')
        + collect_submodules('KDEpy')
        + collect_submodules('statsmodels')
        + collect_submodules('sklearn')
    )
except Exception:
    pass

a = Analysis(
    [os.path.join(ROOT, 'star_gui.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        # Include src package
        (os.path.join(ROOT, 'src'), 'src'),
    ],
    hiddenimports=[
        'scipy.optimize',
        'scipy.io',
        'scipy.io.matlab',
        'scipy.special',
        'scipy.special._cdflib',
        'scipy.spatial',
        'pandas',
        'skimage',
        'skimage.io',
        'skimage.measure',
        'skimage.color',
        'PIL',
        # Pillow loads its Tk support dynamically; PyInstaller may miss it.
        'PIL.ImageTk',
        'PIL._imagingtk',
        'PIL._tkinter_finder',
        'matplotlib',
        'matplotlib.backends.backend_agg',
        'matplotlib.backends.backend_tkagg',
    ] + _stereology_hidden,
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
    [],
    exclude_binaries=True,
    name='StAR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No console window, only the GUI
    icon=None,              # Add .ico path here if desired
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StAR',
)
