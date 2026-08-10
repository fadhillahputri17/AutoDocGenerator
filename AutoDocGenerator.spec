from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPECPATH).resolve()
source_directory = project_root / "src"

hidden_imports = [
    *collect_submodules("PIL"),
    *collect_submodules("docx"),
    *collect_submodules("pytesseract"),
]

analysis = Analysis(
    ["launcher.py"],
    pathex=[
        str(source_directory),
        str(project_root),
    ],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "ruff",
        "mypy",
    ],
    noarchive=False,
    optimize=0,
)

python_archive = PYZ(
    analysis.pure
)

executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="AutoDocGenerator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

application = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AutoDocGenerator",
)